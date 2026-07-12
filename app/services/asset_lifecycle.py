"""
Asset lifecycle rules: which AssetStatusEnum transitions are legal.

Kept separate from app/models/asset.py so the transition policy can evolve
(e.g. Phase 3 wiring RESERVED into the booking flow, Phase 4 wiring
UNDER_MAINTENANCE into the maintenance-approval workflow) without touching
the ORM model.
"""

from app.core.state_machine import StateMachine
from app.models.enums import AssetStatusEnum as S

# fmt: off
ASSET_STATUS_TRANSITIONS: dict[S, set[S]] = {
    # A fresh/free asset can be handed out, booked, sent for maintenance,
    # or written off directly.
    S.AVAILABLE:          {S.ALLOCATED, S.RESERVED, S.UNDER_MAINTENANCE, S.LOST, S.RETIRED},

    # Direct allocation (Phase 3 double-allocation guard sits in front of this).
    S.ALLOCATED:           {S.AVAILABLE, S.UNDER_MAINTENANCE, S.LOST},

    # Booked via the shared-resource booking flow (Phase 3).
    S.RESERVED:            {S.AVAILABLE, S.ALLOCATED, S.UNDER_MAINTENANCE},

    # A maintenance request being approved (Phase 4) is what actually
    # drives AVAILABLE/ALLOCATED -> UNDER_MAINTENANCE in practice, but the
    # manual endpoint is left open for ad-hoc corrections too.
    S.UNDER_MAINTENANCE:   {S.AVAILABLE, S.RETIRED, S.DISPOSED, S.LOST},

    # A lost asset can be recovered back into service or written off.
    S.LOST:                {S.AVAILABLE, S.RETIRED, S.DISPOSED},

    # Retired assets are only awaiting physical disposal.
    S.RETIRED:             {S.DISPOSED},

    # Disposed is terminal — no further transitions.
    S.DISPOSED:            set(),
}
# fmt: on

asset_state_machine: StateMachine[S] = StateMachine(ASSET_STATUS_TRANSITIONS)
