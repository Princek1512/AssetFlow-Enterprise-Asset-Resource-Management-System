import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.state_machine import InvalidTransitionError
from app.models.asset import Asset
from app.models.enums import MaintenanceStatusEnum, RoleEnum
from app.models.maintenance_request import MaintenanceRequest
from app.models.user import User
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceListOut,
    MaintenanceOut,
    MaintenanceStatusUpdate,
)
from app.services.maintenance_lifecycle import (
    asset_status_effect_for_transition,
    maintenance_state_machine,
)

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])

# Only Admin / Asset Manager may drive the workflow forward (approve/reject/progress/complete).
# Any authenticated user may *report* an issue (create) and read the list.
REVIEW_MAINTENANCE = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER)

_EAGER = selectinload(MaintenanceRequest.asset), selectinload(MaintenanceRequest.reported_by)


@router.post("", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED)
async def report_maintenance_issue(
    payload: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MaintenanceRequest:
    """
    Any authenticated user can flag an asset issue — reporting a problem shouldn't
    require elevated privileges, only the subsequent approval does.
    """
    asset = await db.get(Asset, payload.asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    request = MaintenanceRequest(
        asset_id=asset.id,
        reported_by_id=current_user.id,
        issue_description=payload.issue_description.strip(),
        priority=payload.priority,
        status=MaintenanceStatusEnum.PENDING,
    )
    db.add(request)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create maintenance request. Please retry.",
        )

    await db.refresh(request, attribute_names=["asset", "reported_by"])
    return request


@router.get("", response_model=MaintenanceListOut)
async def list_maintenance_requests(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    asset_id: uuid.UUID | None = Query(default=None),
    status_filter: MaintenanceStatusEnum | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> MaintenanceListOut:
    filters = []
    if asset_id is not None:
        filters.append(MaintenanceRequest.asset_id == asset_id)
    if status_filter is not None:
        filters.append(MaintenanceRequest.status == status_filter)

    count_stmt = select(func.count()).select_from(MaintenanceRequest)
    list_stmt = select(MaintenanceRequest).options(*_EAGER)
    for condition in filters:
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = await db.scalar(count_stmt)
    list_stmt = list_stmt.order_by(MaintenanceRequest.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(list_stmt)
    items = list(result.scalars().all())

    return MaintenanceListOut(total=total or 0, skip=skip, limit=limit, items=items)


@router.get("/{request_id}", response_model=MaintenanceOut)
async def get_maintenance_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MaintenanceRequest:
    result = await db.execute(
        select(MaintenanceRequest).options(*_EAGER).where(MaintenanceRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found.")
    return request


@router.patch(
    "/{request_id}/status",
    response_model=MaintenanceOut,
    dependencies=[Depends(REVIEW_MAINTENANCE)],
)
async def update_maintenance_status(
    request_id: uuid.UUID,
    payload: MaintenanceStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> MaintenanceRequest:
    """
    Drives Pending -> Approved -> In Progress -> Completed (or -> Rejected).
    Both the MaintenanceRequest row and its linked Asset row are locked with
    SELECT ... FOR UPDATE and mutated in the same transaction, so an asset can never
    be left in a state that disagrees with its own maintenance history (e.g. Asset
    still AVAILABLE while a maintenance request on it sits APPROVED).
    """
    request_result = await db.execute(
        select(MaintenanceRequest).where(MaintenanceRequest.id == request_id).with_for_update()
    )
    request = request_result.scalar_one_or_none()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance request not found.")

    try:
        maintenance_state_machine.validate(request.status, payload.status)
    except InvalidTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    asset_result = await db.execute(
        select(Asset).where(Asset.id == request.asset_id).with_for_update()
    )
    asset = asset_result.scalar_one_or_none()
    if asset is None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked asset no longer exists.",
        )

    effect = asset_status_effect_for_transition(payload.status)
    if effect is not None:
        asset.status = effect

    request.status = payload.status
    if payload.status == MaintenanceStatusEnum.RESOLVED:
        from datetime import datetime, timezone
        request.resolved_at = datetime.now(timezone.utc)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update maintenance request. Please retry.",
        )

    await db.refresh(request, attribute_names=["asset", "reported_by"])
    return request
