"""
Booking lifecycle rules. Reuses the same generic StateMachine introduced for Asset
status in Phase 2 — proof it wasn't asset-only scaffolding.

Only CANCELLED is exposed through the API in Phase 3 (see POST /bookings/{id}/cancel).
The UPCOMING -> ONGOING -> COMPLETED progression is time-driven and is intended to be
swept by a scheduled job in Phase 4 rather than a user action, but the transitions are
declared here now so that job has a single source of truth to validate against instead
of mutating status directly.
"""

from app.core.state_machine import StateMachine
from app.models.enums import BookingStatusEnum as S

BOOKING_STATUS_TRANSITIONS: dict[S, set[S]] = {
    S.UPCOMING:   {S.ONGOING, S.CANCELLED},
    S.ONGOING:    {S.COMPLETED, S.CANCELLED},
    S.COMPLETED:  set(),  # terminal
    S.CANCELLED:  set(),  # terminal
}

booking_state_machine: StateMachine[S] = StateMachine(BOOKING_STATUS_TRANSITIONS)
