import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import require_role, get_current_user
from app.models.asset import Asset
from app.models.user import User
from app.models.enums import AssetStatusEnum, RoleEnum, TransferRequestStatusEnum
from app.models.transfer_request import TransferRequest
from app.schemas.transfer_request import TransferRequestDecision, TransferRequestOut
from app.services.asset_lifecycle import asset_state_machine

router = APIRouter(prefix="/transfer-requests", tags=["Transfer Requests"])

# Deciding a transfer request reassigns a real asset, so it's management-only —
# consistent with allocate/release in app/api/v1/assets.py.
DECIDE_TRANSFERS = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER, RoleEnum.DEPARTMENT_HEAD)

_EAGER = selectinload(TransferRequest.asset), selectinload(TransferRequest.requested_by), selectinload(
    TransferRequest.current_holder
)


@router.get("", response_model=list[TransferRequestOut], dependencies=[Depends(DECIDE_TRANSFERS)])
async def list_transfer_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: TransferRequestStatusEnum | None = Query(default=None, alias="status"),
    asset_id: uuid.UUID | None = Query(default=None),
) -> list[TransferRequest]:
    stmt = select(TransferRequest).options(*_EAGER)
    
    if current_user.role == RoleEnum.DEPARTMENT_HEAD:
        stmt = stmt.join(User, TransferRequest.current_holder_id == User.id).where(
            User.department_id == current_user.department_id
        )

    if status_filter is not None:
        stmt = stmt.where(TransferRequest.status == status_filter)
    if asset_id is not None:
        stmt = stmt.where(TransferRequest.asset_id == asset_id)
    stmt = stmt.order_by(TransferRequest.created_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{transfer_request_id}", response_model=TransferRequestOut, dependencies=[Depends(DECIDE_TRANSFERS)]
)
async def get_transfer_request(
    transfer_request_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> TransferRequest:
    result = await db.execute(
        select(TransferRequest).options(*_EAGER).where(TransferRequest.id == transfer_request_id)
    )
    transfer_request = result.scalar_one_or_none()
    if transfer_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer request not found.")
    return transfer_request


@router.post(
    "/{transfer_request_id}/approve",
    response_model=TransferRequestOut,
    dependencies=[Depends(DECIDE_TRANSFERS)],
)
async def approve_transfer_request(
    transfer_request_id: uuid.UUID,
    payload: TransferRequestDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransferRequest:
    """
    Approves the transfer: row-locks both the request and the underlying asset so this
    can't race with a concurrent approval/allocate/release on the same asset, re-checks
    the request is still PENDING and the asset's holder hasn't changed since the request
    was filed, then reassigns current_holder_id and auto-rejects any other pending
    requests for the same asset (they'd now conflict with the new holder).
    """
    tr_result = await db.execute(
        select(TransferRequest).where(TransferRequest.id == transfer_request_id).with_for_update()
    )
    transfer_request = tr_result.scalar_one_or_none()
    if transfer_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer request not found.")

    if current_user.role == RoleEnum.DEPARTMENT_HEAD:
        current_holder = await db.get(User, transfer_request.current_holder_id)
        if current_holder and current_holder.department_id != current_user.department_id:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to approve transfers for this department.")

    if transfer_request.status != TransferRequestStatusEnum.REQUESTED:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transfer request is already '{transfer_request.status.value}'.",
        )

    asset_result = await db.execute(
        select(Asset).where(Asset.id == transfer_request.asset_id).with_for_update()
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Underlying asset not found.")

    if asset.current_holder_id != transfer_request.current_holder_id:
        transfer_request.status = TransferRequestStatusEnum.REJECTED
        transfer_request.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The asset's holder has changed since this request was filed; request auto-rejected.",
        )

    # Approve request only, do not change current_holder_id yet.
    transfer_request.status = TransferRequestStatusEnum.APPROVED
    transfer_request.resolved_at = datetime.now(timezone.utc)
    if payload.reason:
        transfer_request.reason = f"{transfer_request.reason or ''}\n[Approved: {payload.reason}]".strip()

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve transfer request. Please retry.",
        )

    await db.refresh(
        transfer_request, attribute_names=["asset", "requested_by", "current_holder"]
    )
    return transfer_request


@router.post(
    "/{transfer_request_id}/reallocate",
    response_model=TransferRequestOut,
    dependencies=[Depends(DECIDE_TRANSFERS)],
)
async def reallocate_transfer_request(
    transfer_request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransferRequest:
    """
    Finalizes the approved transfer: executes the asset holder change and flips
    the request to RE_ALLOCATED.
    """
    tr_result = await db.execute(
        select(TransferRequest).where(TransferRequest.id == transfer_request_id).with_for_update()
    )
    transfer_request = tr_result.scalar_one_or_none()
    if transfer_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer request not found.")

    if current_user.role == RoleEnum.DEPARTMENT_HEAD:
        current_holder = await db.get(User, transfer_request.current_holder_id)
        if current_holder and current_holder.department_id != current_user.department_id:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reallocate transfers for this department.")

    if transfer_request.status != TransferRequestStatusEnum.APPROVED:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transfer request must be 'approved' before re-allocating.",
        )

    asset_result = await db.execute(
        select(Asset).where(Asset.id == transfer_request.asset_id).with_for_update()
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Underlying asset not found.")

    # Re-allocate: perform the physical handover in the DB
    asset.current_holder_id = transfer_request.requested_by_id
    asset.status = AssetStatusEnum.ALLOCATED

    transfer_request.status = TransferRequestStatusEnum.RE_ALLOCATED
    transfer_request.resolved_at = datetime.now(timezone.utc)

    # Any other still-pending (requested) requests for this asset now target a stale holder.
    other_pending = await db.execute(
        select(TransferRequest).where(
            TransferRequest.asset_id == asset.id,
            TransferRequest.id != transfer_request.id,
            TransferRequest.status == TransferRequestStatusEnum.REQUESTED,
        )
    )
    for other in other_pending.scalars().all():
        other.status = TransferRequestStatusEnum.REJECTED
        other.resolved_at = datetime.now(timezone.utc)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-allocate asset. Please retry.",
        )

    await db.refresh(
        transfer_request, attribute_names=["asset", "requested_by", "current_holder"]
    )
    return transfer_request


@router.post(
    "/{transfer_request_id}/reject",
    response_model=TransferRequestOut,
    dependencies=[Depends(DECIDE_TRANSFERS)],
)
async def reject_transfer_request(
    transfer_request_id: uuid.UUID,
    payload: TransferRequestDecision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransferRequest:
    result = await db.execute(
        select(TransferRequest).where(TransferRequest.id == transfer_request_id).with_for_update()
    )
    transfer_request = result.scalar_one_or_none()
    if transfer_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer request not found.")

    if current_user.role == RoleEnum.DEPARTMENT_HEAD:
        current_holder = await db.get(User, transfer_request.current_holder_id)
        if current_holder and current_holder.department_id != current_user.department_id:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reject transfers for this department.")

    if transfer_request.status != TransferRequestStatusEnum.REQUESTED:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transfer request is already '{transfer_request.status.value}'.",
        )

    transfer_request.status = TransferRequestStatusEnum.REJECTED
    transfer_request.resolved_at = datetime.now(timezone.utc)
    if payload.reason:
        transfer_request.reason = f"{transfer_request.reason or ''}\n[Rejected: {payload.reason}]".strip()

    await db.commit()
    await db.refresh(
        transfer_request, attribute_names=["asset", "requested_by", "current_holder"]
    )
    return transfer_request
