import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.state_machine import InvalidTransitionError
from app.models.asset import Asset
from app.models.booking import Booking
from app.models.enums import BookingStatusEnum, RoleEnum
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingListOut, BookingOut
from app.services.booking_lifecycle import booking_state_machine

router = APIRouter(prefix="/bookings", tags=["Bookings"])

BOOK_ON_BEHALF = require_role(RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER)

_EAGER = selectinload(Booking.resource), selectinload(Booking.employee)

# Any booking in one of these states blocks a new booking that overlaps its time window.
_BLOCKING_STATUSES = (BookingStatusEnum.UPCOMING, BookingStatusEnum.ONGOING)


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    """
    Books a shared/bookable resource for a time window. This is the time-slot overlap
    guard: the resource (Asset) row is locked with SELECT ... FOR UPDATE for the whole
    transaction, which serializes every concurrent booking attempt against the same
    resource — the second of two racing requests always sees the first request's
    just-inserted row before it commits, so overlap can never slip through.
    """
    if payload.employee_id is not None and payload.employee_id != current_user.id:
        if current_user.role not in (RoleEnum.ADMIN, RoleEnum.ASSET_MANAGER):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin or Asset Manager can book a resource on someone else's behalf.",
            )
        employee = await db.get(User, payload.employee_id)
        if employee is None or not employee.is_active:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="employee_id does not reference an active user.",
            )
        employee_id = payload.employee_id
    else:
        employee_id = current_user.id

    resource_result = await db.execute(
        select(Asset).where(Asset.id == payload.resource_id).with_for_update()
    )
    resource = resource_result.scalar_one_or_none()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource (asset) not found.")

    if not resource.is_bookable:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This asset is not bookable — use POST /assets/{asset_id}/allocate instead.",
        )

    overlap_stmt = select(Booking).where(
        Booking.resource_id == resource.id,
        Booking.status.in_(_BLOCKING_STATUSES),
        Booking.start_time < payload.end_time,
        Booking.end_time > payload.start_time,
    )
    overlap_result = await db.execute(overlap_stmt)
    conflicting = overlap_result.scalars().first()
    if conflicting is not None:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "This resource is already booked for an overlapping time slot.",
                "conflicting_booking_id": str(conflicting.id),
                "conflicting_start_time": conflicting.start_time.isoformat(),
                "conflicting_end_time": conflicting.end_time.isoformat(),
            },
        )

    booking = Booking(
        resource_id=resource.id,
        employee_id=employee_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status=BookingStatusEnum.UPCOMING,
    )
    db.add(booking)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking. Please retry.",
        )

    await db.refresh(booking, attribute_names=["resource", "employee"])
    return booking


@router.get("", response_model=BookingListOut)
async def list_bookings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
    resource_id: uuid.UUID | None = Query(default=None),
    employee_id: uuid.UUID | None = Query(default=None),
    status_filter: BookingStatusEnum | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> BookingListOut:
    """
    Full visibility for any authenticated user — seeing the shared calendar is what
    lets people avoid booking conflicts in the first place, not just what the
    conflict check enforces server-side.
    """
    filters = []
    if resource_id is not None:
        filters.append(Booking.resource_id == resource_id)
    if employee_id is not None:
        filters.append(Booking.employee_id == employee_id)
    if status_filter is not None:
        filters.append(Booking.status == status_filter)

    count_stmt = select(func.count()).select_from(Booking)
    list_stmt = select(Booking).options(*_EAGER)
    for condition in filters:
        count_stmt = count_stmt.where(condition)
        list_stmt = list_stmt.where(condition)

    total = await db.scalar(count_stmt)
    list_stmt = list_stmt.order_by(Booking.start_time.asc()).offset(skip).limit(limit)
    result = await db.execute(list_stmt)
    items = list(result.scalars().all())

    return BookingListOut(total=total or 0, skip=skip, limit=limit, items=items)


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> Booking:
    result = await db.execute(select(Booking).options(*_EAGER).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    return booking


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    """The booking's own employee, or Admin / Asset Manager, may cancel it."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id).with_for_update())
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

    if booking.employee_id != current_user.id and current_user.role not in (
        RoleEnum.ADMIN,
        RoleEnum.ASSET_MANAGER,
    ):
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own bookings.",
        )

    try:
        booking_state_machine.validate(booking.status, BookingStatusEnum.CANCELLED)
    except InvalidTransitionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    booking.status = BookingStatusEnum.CANCELLED

    await db.commit()
    await db.refresh(booking, attribute_names=["resource", "employee"])
    return booking
