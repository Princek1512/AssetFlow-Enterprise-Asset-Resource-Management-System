import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import AssetBrief, UserBrief


class DashboardKPIs(BaseModel):
    """
    Snapshot counters for the dashboard's KPI cards. All four are point-in-time
    aggregate counts computed fresh on each request — deliberately not cached,
    since a hackathon-scale table doesn't need it and staleness here would be
    actively misleading (e.g. "Active Bookings" being wrong).
    """

    assets_available: int
    assets_allocated: int
    maintenance_today: int
    active_bookings: int
    pending_transfers: int
    upcoming_returns: int
    overdue_returns: int


class OverdueBookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_id: uuid.UUID
    resource: AssetBrief | None = None
    employee_id: uuid.UUID
    employee: UserBrief | None = None
    start_time: datetime
    end_time: datetime
    hours_overdue: float


class OverdueBookingListOut(BaseModel):
    total: int
    items: list[OverdueBookingOut]
