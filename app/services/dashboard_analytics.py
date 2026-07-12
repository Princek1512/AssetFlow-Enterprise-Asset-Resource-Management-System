"""
Read-only aggregation queries backing the dashboard KPI cards and the overdue-returns
widget. Kept as plain SQLAlchemy Core-style aggregate `select()`s (COUNT/func) rather
than pulling full ORM rows into Python and counting there, since these are the queries
most likely to run on every dashboard page-load.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.asset import Asset
from app.models.booking import Booking
from app.models.transfer_request import TransferRequest
from app.models.enums import AssetStatusEnum, BookingStatusEnum, MaintenanceStatusEnum, TransferRequestStatusEnum
from app.models.maintenance_request import MaintenanceRequest
from app.schemas.dashboard import DashboardKPIs, OverdueBookingOut

_IN_MAINTENANCE_STATUSES = (
    MaintenanceStatusEnum.APPROVED,
    MaintenanceStatusEnum.TECHNICIAN_ASSIGNED,
    MaintenanceStatusEnum.IN_PROGRESS,
)


async def get_dashboard_kpis(db: AsyncSession) -> DashboardKPIs:
    now = datetime.now(timezone.utc)

    assets_available = await db.scalar(
        select(func.count()).select_from(Asset).where(Asset.status == AssetStatusEnum.AVAILABLE)
    )
    assets_allocated = await db.scalar(
        select(func.count()).select_from(Asset).where(Asset.status == AssetStatusEnum.ALLOCATED)
    )
    maintenance_today = await db.scalar(
        select(func.count())
        .select_from(MaintenanceRequest)
        .where(MaintenanceRequest.status.in_(_IN_MAINTENANCE_STATUSES))
    )
    active_bookings = await db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == BookingStatusEnum.ONGOING)
    )
    pending_transfers = await db.scalar(
        select(func.count())
        .select_from(TransferRequest)
        .where(TransferRequest.status == TransferRequestStatusEnum.REQUESTED)
    )
    upcoming_returns = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status == BookingStatusEnum.ONGOING, Booking.end_time > now)
    )
    overdue_returns = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status == BookingStatusEnum.ONGOING, Booking.end_time < now)
    )

    return DashboardKPIs(
        assets_available=assets_available or 0,
        assets_allocated=assets_allocated or 0,
        maintenance_today=maintenance_today or 0,
        active_bookings=active_bookings or 0,
        pending_transfers=pending_transfers or 0,
        upcoming_returns=upcoming_returns or 0,
        overdue_returns=overdue_returns or 0,
    )


async def get_overdue_bookings(db: AsyncSession) -> list[OverdueBookingOut]:
    """
    "Overdue" = a booking still marked ONGOING whose end_time has already passed —
    i.e. nobody has returned/released the resource and no scheduled sweep has closed
    it out yet. Surfaced separately from the KPI counters since the dashboard needs
    the actual list (who, what, how overdue), not just a count.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(Booking)
        .options(selectinload(Booking.resource), selectinload(Booking.employee))
        .where(Booking.status == BookingStatusEnum.ONGOING, Booking.end_time < now)
        .order_by(Booking.end_time.asc())
    )
    result = await db.execute(stmt)
    bookings = result.scalars().all()

    overdue: list[OverdueBookingOut] = []
    for b in bookings:
        hours_overdue = (now - b.end_time).total_seconds() / 3600
        overdue.append(
            OverdueBookingOut(
                id=b.id,
                resource_id=b.resource_id,
                resource=b.resource,
                employee_id=b.employee_id,
                employee=b.employee,
                start_time=b.start_time,
                end_time=b.end_time,
                hours_overdue=round(hours_overdue, 1),
            )
        )
    return overdue
