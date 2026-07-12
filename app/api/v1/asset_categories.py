import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.asset_category import AssetCategory
from app.models.enums import RoleEnum
from app.schemas.asset_category import AssetCategoryCreate, AssetCategoryOut, AssetCategoryUpdate

router = APIRouter(prefix="/asset-categories", tags=["Asset Categories"])

# Categories are foundational (assets reference them via FK RESTRICT), so writes are
# restricted to Admin and Asset Manager; any authenticated user can read the directory.
MANAGE_CATEGORIES = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER)


@router.post(
    "",
    response_model=AssetCategoryOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(MANAGE_CATEGORIES)],
)
async def create_category(
    payload: AssetCategoryCreate, db: AsyncSession = Depends(get_db)
) -> AssetCategory:
    category = AssetCategory(
        name=payload.name.strip(),
        description=payload.description,
        custom_fields=payload.custom_fields or {},
    )
    db.add(category)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset category with this name already exists.",
        )

    await db.refresh(category)
    return category


@router.get("", response_model=list[AssetCategoryOut])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> list[AssetCategory]:
    result = await db.execute(select(AssetCategory).order_by(AssetCategory.name.asc()))
    return list(result.scalars().all())


@router.get("/{category_id}", response_model=AssetCategoryOut)
async def get_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(get_current_user),
) -> AssetCategory:
    category = await db.get(AssetCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset category not found.")
    return category


@router.patch(
    "/{category_id}",
    response_model=AssetCategoryOut,
    dependencies=[Depends(MANAGE_CATEGORIES)],
)
async def update_category(
    category_id: uuid.UUID,
    payload: AssetCategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> AssetCategory:
    category = await db.get(AssetCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset category not found.")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        update_data["name"] = update_data["name"].strip()
    for field, value in update_data.items():
        setattr(category, field, value)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An asset category with this name already exists.",
        )

    await db.refresh(category)
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(MANAGE_CATEGORIES)],
)
async def delete_category(category_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    category = await db.get(AssetCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset category not found.")

    await db.delete(category)
    try:
        await db.commit()
    except IntegrityError:
        # FK is ON DELETE RESTRICT — assets still reference this category.
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a category that still has assets assigned to it.",
        )
