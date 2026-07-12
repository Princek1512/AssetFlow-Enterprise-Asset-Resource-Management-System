import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.state_machine import InvalidTransitionError
from app.models.asset import Asset, asset_tag_sequence
from app.models.asset_category import AssetCategory
<<<<<<< HEAD
from app.models.enums import AssetStatusEnum, RoleEnum, TransferRequestStatusEnum
from app.models.transfer_request import TransferRequest
from app.models.user import User
from app.schemas.asset import (
    AssetAllocateRequest,
=======
from app.models.enums import AssetStatusEnum, RoleEnum
from app.schemas.asset import (
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
    AssetCreate,
    AssetListOut,
    AssetOut,
    AssetStatusTransitionRequest,
    AssetUpdate,
)
<<<<<<< HEAD
from app.schemas.transfer_request import TransferRequestCreate, TransferRequestOut
=======
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
from app.services.asset_lifecycle import asset_state_machine

router = APIRouter(prefix="/assets", tags=["Assets"])

# Registration, directory edits, and manual status overrides are a management action;
# every authenticated user can still read the directory (list/get below).
MANAGE_ASSETS = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER)

ASSET_TAG_PREFIX = "AF"


def _format_asset_tag(sequence_value: int) -> str:
    return f"{ASSET_TAG_PREFIX}-{sequence_value:04d}"


@router.post(
    "",
    response_model=AssetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE_ASSETS)],
)
async def register_asset(payload: AssetCreate, db: AsyncSession = Depends(get_db)) -> Asset:
    """
    Registers a new asset. `asset_tag` is never client-supplied — it's derived from
    a Postgres sequence (`asset_tag_seq`) so concurrent registrations can never collide
    or race on the human-readable tag, without needing a row lock.
    """
    category = await db.get(AssetCategory, payload.category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="category_id does not reference an existing asset category.",
        )

    next_sequence_value = await db.scalar(select(asset_tag_sequence.next_value()))

    asset = Asset(
        name=payload.name.strip(),
        category_id=payload.category_id,
        tag_sequence=next_sequence_value,
        asset_tag=_format_asset_tag(next_sequence_value),
        serial_number=payload.serial_number,
        condition=payload.condition,
        location=payload.location,
        is_bookable=payload.is_bookable,
        status=AssetStatusEnum.AVAILABLE,
    )
    db.add(asset)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with this serial number already exists.",
        )

    await db.refresh(asset, attribute_names=["category"])
    return asset


@router.get("", response_model=AssetListOut)
async def list_assets(
    db: AsyncSession = Depends(get_db),
<<<<<<< HEAD
    current_user: User = Depends(get_current_user),
=======
    _current_user=Depends(get_current_user),
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
    status_filter: AssetStatusEnum | None = Query(default=None, alias="status"),
    category_id: uuid.UUID | None = Query(default=None),
    is_bookable: bool | None = Query(default=None),
    search: str | None = Query(
        default=None, max_length=200, description="Matches against asset name, tag, or serial number."
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> AssetListOut:
<<<<<<< HEAD
    """Asset directory — filtered by role."""
=======
    """Asset directory — every authenticated role can browse it, filters are all optional."""
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
    filters = []
    if status_filter is not None:
        filters.append(Asset.status == status_filter)
    if category_id is not None:
        filters.append(Asset.category_id == category_id)
    if is_bookable is not None:
        filters.append(Asset.is_bookable == is_bookable)
    if search:
        like_pattern = f"%{search.strip()}%"
        filters.append(
            (Asset.name.ilike(like_pattern))
            | (Asset.asset_tag.ilike(like_pattern))
            | (Asset.serial_number.ilike(like_pattern))
        )

    count_stmt = select(func.count()).select_from(Asset)
    list_stmt = select(Asset).options(selectinload(Asset.category))
<<<<<<< HEAD

    if current_user.role == RoleEnum.EMPLOYEE:
        filters.append((Asset.current_holder_id == current_user.id) | (Asset.is_bookable == True))
    elif current_user.role == RoleEnum.DEPARTMENT_HEAD:
        count_stmt = count_stmt.outerjoin(User, Asset.current_holder_id == User.id)
        list_stmt = list_stmt.outerjoin(User, Asset.current_holder_id == User.id)
        filters.append((User.department_id == current_user.department_id) | (Asset.is_bookable == True))

=======
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
    for condition in filters:
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = await db.scalar(count_stmt)
    list_stmt = list_stmt.order_by(Asset.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(list_stmt)
    items = list(result.scalars().all())

    return AssetListOut(total=total or 0, skip=skip, limit=limit, items=items)


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
<<<<<<< HEAD
    current_user: User = Depends(get_current_user),
) -> Asset:
    stmt = select(Asset).options(selectinload(Asset.category)).where(Asset.id == asset_id)
    if current_user.role == RoleEnum.EMPLOYEE:
        stmt = stmt.where((Asset.current_holder_id == current_user.id) | (Asset.is_bookable == True))
    elif current_user.role == RoleEnum.DEPARTMENT_HEAD:
        stmt = stmt.outerjoin(User, Asset.current_holder_id == User.id).where(
            (User.department_id == current_user.department_id) | (Asset.is_bookable == True)
        )
    result = await db.execute(stmt)
=======
    _current_user=Depends(get_current_user),
) -> Asset:
    result = await db.execute(
        select(Asset).options(selectinload(Asset.category)).where(Asset.id == asset_id)
    )
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


@router.patch("/{asset_id}", response_model=AssetOut, dependencies=[Depends(MANAGE_ASSETS)])
async def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    db: AsyncSession = Depends(get_db),
) -> Asset:
    """
    Edits directory metadata only. `status` is deliberately not accepted here —
    see POST /assets/{id}/status, which is the only path that goes through the
    asset lifecycle state machine.
    """
    result = await db.execute(
        select(Asset).options(selectinload(Asset.category)).where(Asset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    update_data = payload.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        new_category = await db.get(AssetCategory, update_data["category_id"])
        if new_category is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="category_id does not reference an existing asset category.",
            )

    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = update_data["name"].strip()

    for field, value in update_data.items():
        setattr(asset, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset with this serial number already exists.",
        )

    await db.refresh(asset, attribute_names=["category"])
    return asset


@router.post(
    "/{asset_id}/status",
    response_model=AssetOut,
    dependencies=[Depends(MANAGE_ASSETS)],
)
async def transition_asset_status(
    asset_id: uuid.UUID,
    payload: AssetStatusTransitionRequest,
    db: AsyncSession = Depends(get_db),
) -> Asset:
    """
    Guarded status transition. Row-locks the asset (consistent with the Phase 1
    promote/deactivate endpoints) so two concurrent transition requests against the
    same asset can't race past the state machine and leave an inconsistent status,
    then validates the move against the asset lifecycle rules before committing.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id).with_for_update())
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    try:
        asset_state_machine.validate(asset.status, payload.status)
    except InvalidTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    asset.status = payload.status

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update asset status. Please retry.",
        )

    await db.refresh(asset, attribute_names=["category"])
    return asset
<<<<<<< HEAD



# ---------------------------------------------------------------------------
# Direct allocation (non-bookable assets) — double-allocation prevention.
# ---------------------------------------------------------------------------


ALLOCATE_ASSETS = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER, RoleEnum.DEPARTMENT_HEAD)

@router.post(
    "/{asset_id}/allocate",
    response_model=AssetOut,
    dependencies=[Depends(ALLOCATE_ASSETS)],
)
async def allocate_asset(
    asset_id: uuid.UUID,
    payload: AssetAllocateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Asset:
    """
    Directly allocates a non-bookable asset to an employee. Row-locks the asset for the
    duration of the transaction so two concurrent allocation attempts against the same
    asset can never both succeed — the classic double-allocation race.

    Department Heads can only allocate to employees within their own department.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id).with_for_update())
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    if asset.is_bookable:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This asset is bookable and must go through POST /bookings instead of direct allocation.",
        )

    if asset.current_holder_id is not None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Asset is already allocated to another user.",
                "current_holder_id": str(asset.current_holder_id),
                "hint": f"Use POST /assets/{asset_id}/transfer-requests to request a transfer instead.",
            },
        )

    employee = await db.get(User, payload.employee_id)
    if employee is None or not employee.is_active:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="employee_id does not reference an active user.",
        )

    # Department Heads can only allocate within their department
    if current_user.role == RoleEnum.DEPARTMENT_HEAD:
        if employee.department_id != current_user.department_id:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department Heads can only allocate assets to employees within their own department.",
            )

    try:
        asset_state_machine.validate(asset.status, AssetStatusEnum.ALLOCATED)
    except InvalidTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    asset.status = AssetStatusEnum.ALLOCATED
    asset.current_holder_id = payload.employee_id

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to allocate asset. Please retry.",
        )

    await db.refresh(asset, attribute_names=["category"])
    return asset


@router.post(
    "/{asset_id}/release",
    response_model=AssetOut,
    dependencies=[Depends(MANAGE_ASSETS)],
)
async def release_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Asset:
    """Clears the current holder and returns a directly-allocated asset to AVAILABLE."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id).with_for_update())
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    if asset.current_holder_id is None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Asset is not currently allocated to anyone."
        )

    try:
        asset_state_machine.validate(asset.status, AssetStatusEnum.AVAILABLE)
    except InvalidTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    asset.status = AssetStatusEnum.AVAILABLE
    asset.current_holder_id = None

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to release asset. Please retry.",
        )

    await db.refresh(asset, attribute_names=["category"])
    return asset


# ---------------------------------------------------------------------------
# Transfer requests — the conflict-resolution path for already-allocated assets.
# Decision endpoints (approve/reject) live in app/api/v1/transfer_requests.py.
# ---------------------------------------------------------------------------

@router.delete(
    "/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE_ASSETS)],
)
async def delete_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Deletes an asset from the system. Admin/Asset Manager only."""
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    try:
        await db.delete(asset)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete asset. Ensure there are no unresolved constraints.",
        )

@router.post(
    "/{asset_id}/transfer-requests",
    response_model=TransferRequestOut,
    status_code=status.HTTP_201_CREATED,
)
async def request_asset_transfer(
    asset_id: uuid.UUID,
    payload: TransferRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransferRequest:
    """
    Any authenticated user can request an already-allocated asset be transferred to
    them. This is the "don't silently fail the write" path referenced on the
    TransferRequest model: instead of a rejected allocation attempt, the requester
    gets a trackable request an Admin / Asset Manager can approve or reject.
    """
    asset = await db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    if asset.current_holder_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Asset is not currently allocated to anyone — use POST /assets/{asset_id}/allocate instead.",
        )

    if asset.current_holder_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You already hold this asset."
        )

    transfer_request = TransferRequest(
        asset_id=asset.id,
        requested_by_id=current_user.id,
        current_holder_id=asset.current_holder_id,
        reason=payload.reason,
        status=TransferRequestStatusEnum.REQUESTED,
    )
    db.add(transfer_request)
    await db.commit()
    await db.refresh(
        transfer_request, attribute_names=["asset", "requested_by", "current_holder"]
    )
    return transfer_request
=======
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
