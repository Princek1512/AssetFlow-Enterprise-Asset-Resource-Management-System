from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardKPIs, OverdueBookingListOut
from app.services.dashboard_analytics import get_dashboard_kpis, get_overdue_bookings

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/kpis", response_model=DashboardKPIs)
async def dashboard_kpis(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> DashboardKPIs:
    """Available to any authenticated role — every role sees the same fleet-wide snapshot."""
    return await get_dashboard_kpis(db)


@router.get("/overdue-returns", response_model=OverdueBookingListOut)
async def dashboard_overdue_returns(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> OverdueBookingListOut:
    items = await get_overdue_bookings(db)
    return OverdueBookingListOut(total=len(items), items=items)
