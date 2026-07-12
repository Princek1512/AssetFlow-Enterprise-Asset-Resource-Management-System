import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.asset import Asset
from app.models.enums import RoleEnum, AssetConditionEnum, AssetStatusEnum
from app.models.user import User
from app.models.audit import AuditCycle, AuditRecord, AuditStatusEnum
from app.schemas.audit import (
    AuditCycleCreate,
    AuditCycleOut,
    AuditRecordCreate,
    AuditRecordOut,
    DiscrepancyReport,
)
from app.schemas.common import AssetBrief

router = APIRouter(prefix="/audit", tags=["Audit System"])

MANAGE_AUDITS = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER)

@router.post("/cycles", response_model=AuditCycleOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(MANAGE_AUDITS)])
async def create_audit_cycle(payload: AuditCycleCreate, db: AsyncSession = Depends(get_db)):
    cycle = AuditCycle(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        is_completed=False,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return cycle

@router.get("/cycles", response_model=list[AuditCycleOut])
async def list_audit_cycles(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(AuditCycle).order_by(AuditCycle.created_at.desc()))
    return list(result.scalars().all())

@router.get("/cycles/{cycle_id}", response_model=AuditCycleOut)
async def get_audit_cycle(cycle_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    cycle = await db.get(AuditCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit cycle not found.")
    return cycle

@router.post("/cycles/{cycle_id}/records", response_model=AuditRecordOut, status_code=status.HTTP_201_CREATED)
async def submit_audit_record(
    cycle_id: uuid.UUID,
    payload: AuditRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cycle = await db.get(AuditCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit cycle not found.")
    if cycle.is_completed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot audit a completed cycle.")

    asset = await db.get(Asset, payload.asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    # Check if a record already exists for this asset in this cycle
    stmt = select(AuditRecord).where(AuditRecord.cycle_id == cycle_id, AuditRecord.asset_id == payload.asset_id)
    existing_result = await db.execute(stmt)
    existing_record = existing_result.scalar_one_or_none()

    if existing_record:
        # Update existing
        existing_record.status = payload.status
        existing_record.notes = payload.notes
        existing_record.auditor_id = current_user.id
        record = existing_record
    else:
        # Create new
        record = AuditRecord(
            cycle_id=cycle_id,
            asset_id=payload.asset_id,
            auditor_id=current_user.id,
            status=payload.status,
            notes=payload.notes,
        )
        db.add(record)

    # side effect: update live asset condition if damaged
    if payload.status == AuditStatusEnum.DAMAGED:
        asset.condition = AssetConditionEnum.DAMAGED # wait, is there a DAMAGED condition? Let's check AssetConditionEnum.
        # Yes, in enums.py it is NEW, GOOD, FAIR, POOR, DAMAGED.
    elif payload.status == AuditStatusEnum.MISSING:
        asset.status = AssetStatusEnum.LOST # mark asset as lost in status

    await db.commit()
    await db.refresh(record, attribute_names=["asset", "auditor"])
    return record

@router.get("/cycles/{cycle_id}/records", response_model=list[AuditRecordOut])
async def list_audit_records(
    cycle_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(AuditRecord)
        .options(selectinload(AuditRecord.asset), selectinload(AuditRecord.auditor))
        .where(AuditRecord.cycle_id == cycle_id)
        .order_by(AuditRecord.timestamp.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

@router.post("/cycles/{cycle_id}/complete", response_model=AuditCycleOut, dependencies=[Depends(MANAGE_AUDITS)])
async def complete_audit_cycle(cycle_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cycle = await db.get(AuditCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit cycle not found.")
    cycle.is_completed = True
    await db.commit()
    await db.refresh(cycle)
    return cycle

@router.get("/cycles/{cycle_id}/discrepancies", response_model=DiscrepancyReport, dependencies=[Depends(MANAGE_AUDITS)])
async def get_discrepancies(cycle_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cycle = await db.get(AuditCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit cycle not found.")

    # 1. Fetch all records for this cycle
    stmt = (
        select(AuditRecord)
        .options(selectinload(AuditRecord.asset), selectinload(AuditRecord.auditor))
        .where(AuditRecord.cycle_id == cycle_id)
    )
    records_res = await db.execute(stmt)
    records = list(records_res.scalars().all())

    missing = [r for r in records if r.status == AuditStatusEnum.MISSING]
    damaged = [r for r in records if r.status == AuditStatusEnum.DAMAGED]

    # 2. Find assets that were not audited in this cycle
    audited_asset_ids = {r.asset_id for r in records}
    
    assets_stmt = select(Asset).where(Asset.status.notin_((AssetStatusEnum.RETIRED, AssetStatusEnum.DISPOSED)))
    assets_res = await db.execute(assets_stmt)
    all_active_assets = list(assets_res.scalars().all())

    unaudited = []
    for asset in all_active_assets:
        if asset.id not in audited_asset_ids:
            unaudited.append(AssetBrief.model_validate(asset))

    return DiscrepancyReport(
        missing=missing,
        damaged=damaged,
        unaudited_assets=unaudited,
    )
