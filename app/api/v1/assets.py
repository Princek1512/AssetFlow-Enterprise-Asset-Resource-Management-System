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
from app.models.enums import AssetStatusEnum, RoleEnum
from app.schemas.asset import (
    AssetCreate,
    AssetListOut,
    AssetOut,
    AssetStatusTransitionRequest,
    AssetUpdate,
)
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
    _current_user=Depends(get_current_user),
    status_filter: AssetStatusEnum | None = Query(default=None, alias="status"),
    category_id: uuid.UUID | None = Query(default=None),
    is_bookable: bool | None = Query(default=None),
    search: str | None = Query(
        default=None, max_length=200, description="Matches against asset name, tag, or serial number."
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> AssetListOut:
    """Asset directory — every authenticated role can browse it, filters are all optional."""
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
    _current_user=Depends(get_current_user),
) -> Asset:
    result = await db.execute(
        select(Asset).options(selectinload(Asset.category)).where(Asset.id == asset_id)
    )
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
