"""
Generic, reusable finite-state-machine helper.

Not asset-specific on purpose: Phase 2 uses this for Asset lifecycle status,
but Phase 4 workflows (MaintenanceRequest, TransferRequest, Booking status)
should reuse the same primitive instead of hand-rolling their own if/else
transition checks.
"""

import enum
from typing import Generic, TypeVar

StateT = TypeVar("StateT", bound=enum.Enum)


class InvalidTransitionError(ValueError):
    """Raised when a requested state transition is not allowed."""

    def __init__(self, current: enum.Enum, target: enum.Enum, allowed: set[enum.Enum]):
        self.current = current
        self.target = target
        self.allowed = allowed

        if current == target:
            message = f"Asset is already in state '{current.value}'."
        elif not allowed:
            message = f"'{current.value}' is a terminal state; no further transitions are allowed."
        else:
            allowed_values = ", ".join(sorted(s.value for s in allowed))
            message = (
                f"Cannot transition from '{current.value}' to '{target.value}'. "
                f"Allowed next states: {allowed_values}."
            )
        super().__init__(message)


class StateMachine(Generic[StateT]):
    """
    Wraps a `{state: {allowed_next_states}}` transition map and enforces it.

    Usage:
        machine = StateMachine({
            State.A: {State.B},
            State.B: {State.A, State.C},
            State.C: set(),  # terminal
        })
        machine.validate(State.A, State.B)   # OK, no exception
        machine.validate(State.A, State.C)   # raises InvalidTransitionError
    """

    def __init__(self, transitions: dict[StateT, set[StateT]]):
        self._transitions = transitions

    def allowed_next_states(self, current: StateT) -> set[StateT]:
        return self._transitions.get(current, set())

    def can_transition(self, current: StateT, target: StateT) -> bool:
        if current == target:
            return False
        return target in self.allowed_next_states(current)

    def validate(self, current: StateT, target: StateT) -> None:
        """Raises InvalidTransitionError if the transition isn't allowed."""
        if not self.can_transition(current, target):
            raise InvalidTransitionError(current, target, self.allowed_next_states(current))
