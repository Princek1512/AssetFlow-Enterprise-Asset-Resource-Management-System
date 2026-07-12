import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_role
from app.models.enums import RoleEnum
from app.models.user import User
from app.schemas.auth import PromoteUserRequest, UserOut

router = APIRouter(
    prefix="/admin",
    tags=["Admin - Organization Management"],
<<<<<<< HEAD
)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER, RoleEnum.DEPARTMENT_HEAD))])
=======
    dependencies=[Depends(require_role(RoleEnum.ADMIN))],
)


@router.get("/users", response_model=list[UserOut])
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
async def list_users(db: AsyncSession = Depends(get_db)) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


<<<<<<< HEAD
@router.post("/users/{user_id}/promote", response_model=UserOut, dependencies=[Depends(require_role(RoleEnum.ADMIN))])
=======
@router.post("/users/{user_id}/promote", response_model=UserOut)
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
async def promote_user(
    user_id: uuid.UUID,
    payload: PromoteUserRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_role(RoleEnum.ADMIN)),
) -> User:
    """
    Promotes (or demotes) a user's role. Locks the target row for the duration
    of the transaction with SELECT ... FOR UPDATE so two concurrent promotion
    requests against the same user can't race and leave an inconsistent role.
    """
    try:
        payload.validate_promotable()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    if user_id == current_admin.id and payload.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot demote their own account through this endpoint.",
        )

    result = await db.execute(
        select(User).where(User.id == user_id).with_for_update()
    )
    target_user = result.scalar_one_or_none()

    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_user.role = payload.role

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role. Please retry.",
        )

    await db.refresh(target_user)
    return target_user


<<<<<<< HEAD
@router.patch("/users/{user_id}/deactivate", response_model=UserOut, dependencies=[Depends(require_role(RoleEnum.ADMIN))])
=======
@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
>>>>>>> 0b21ee9da9c9fae9a687d8d219bb9ee4966c31b9
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(require_role(RoleEnum.ADMIN)),
) -> User:
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate their own account.",
        )

    result = await db.execute(select(User).where(User.id == user_id).with_for_update())
    target_user = result.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    target_user.is_active = False

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate user. Please retry.",
        )

    await db.refresh(target_user)
    return target_user
