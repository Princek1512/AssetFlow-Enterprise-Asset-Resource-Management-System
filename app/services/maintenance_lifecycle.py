"""
Maintenance-request lifecycle rules, reusing the same generic StateMachine used by
Asset status (Phase 2) and Booking status (Phase 3).

The workflow's whole point is that it isn't just a status label on the request — it
must drive the linked Asset's status too:
    * Pending  -> Approved     : Asset flips to UNDER_MAINTENANCE (taken out of service)
    * Approved -> In Progress  : Asset stays UNDER_MAINTENANCE (no-op on the asset)
    * *        -> Completed    : Asset flips back to AVAILABLE (returned to service)
    * Pending  -> Rejected     : Asset is untouched (never left service)

`asset_status_effect_for_transition` below is the single source of truth other layers
(namely app/api/v1/maintenance.py) call to know whether — and how — to also touch the
Asset row, so that side effect never has to be hand-rolled at the route level.
"""

from app.core.state_machine import StateMachine
from app.models.enums import AssetStatusEnum
from app.models.enums import MaintenanceStatusEnum as S

MAINTENANCE_STATUS_TRANSITIONS: dict[S, set[S]] = {
    S.PENDING:             {S.APPROVED},
    S.APPROVED:            {S.TECHNICIAN_ASSIGNED},
    S.TECHNICIAN_ASSIGNED: {S.IN_PROGRESS},
    S.IN_PROGRESS:         {S.RESOLVED},
    S.RESOLVED:            set(),  # terminal
}

maintenance_state_machine: StateMachine[S] = StateMachine(MAINTENANCE_STATUS_TRANSITIONS)

# States in which the linked Asset is considered "pulled" into maintenance.
_ASSET_IN_MAINTENANCE_STATES = {S.APPROVED, S.TECHNICIAN_ASSIGNED, S.IN_PROGRESS}


def asset_status_effect_for_transition(target: S) -> AssetStatusEnum | None:
    """
    Returns the AssetStatusEnum the linked Asset should be moved to as a side effect
    of the MaintenanceRequest reaching `target`, or None if the Asset shouldn't change.
    """
    if target in _ASSET_IN_MAINTENANCE_STATES:
        return AssetStatusEnum.UNDER_MAINTENANCE
    if target == S.RESOLVED:
        return AssetStatusEnum.AVAILABLE
    return None

