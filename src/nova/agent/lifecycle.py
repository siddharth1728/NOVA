"""Session lifecycle state machine for NOVA agent."""

from enum import Enum

from nova.errors import AgentRuntimeError


class AgentState(str, Enum):
    """Operational state of the NOVA agent session."""

    INITIALIZING = "INITIALIZING"
    READY = "READY"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    IDLE = "IDLE"
    TERMINATED = "TERMINATED"
    FAILED = "FAILED"


# Defined valid directional state transitions
LEGAL_TRANSITIONS: dict[AgentState, set[AgentState]] = {
    AgentState.INITIALIZING: {AgentState.READY, AgentState.FAILED},
    AgentState.READY: {
        AgentState.PLANNING,
        AgentState.EXECUTING,
        AgentState.IDLE,
        AgentState.TERMINATED,
    },
    AgentState.PLANNING: {
        AgentState.EXECUTING,
        AgentState.READY,
        AgentState.FAILED,
    },
    AgentState.EXECUTING: {
        AgentState.VERIFYING,
        AgentState.READY,
        AgentState.FAILED,
    },
    AgentState.VERIFYING: {
        AgentState.READY,
        AgentState.IDLE,
        AgentState.PLANNING,  # Failure recovery loop
        AgentState.FAILED,
    },
    AgentState.IDLE: {
        AgentState.PLANNING,
        AgentState.EXECUTING,
        AgentState.READY,
        AgentState.TERMINATED,
    },
    AgentState.FAILED: {
        AgentState.READY,  # Recovery reset
        AgentState.TERMINATED,
    },
    AgentState.TERMINATED: set(),  # Terminal state
}


class LifecycleStateMachine:
    """Manages agent session states and verifies valid transitions."""

    def __init__(self, initial_state: AgentState = AgentState.INITIALIZING) -> None:
        self._current_state = initial_state
        self._history: list[tuple[AgentState, str]] = [(initial_state, "Session created")]

    @property
    def current_state(self) -> AgentState:
        """Current operational state."""
        return self._current_state

    @property
    def history(self) -> list[tuple[AgentState, str]]:
        """History of transitions as (state, reason) tuples."""
        return list(self._history)

    def transition_to(self, target: AgentState, reason: str = "") -> None:
        """Transitions the agent to a target state after verifying legality.

        Raises:
            AgentRuntimeError: If the requested transition is illegal.
        """
        allowed = LEGAL_TRANSITIONS.get(self._current_state, set())
        if target not in allowed:
            raise AgentRuntimeError(
                f"Illegal lifecycle transition: cannot move from {self._current_state.value} to {target.value}.",
                details={
                    "current_state": self._current_state.value,
                    "attempted_state": target.value,
                    "legal_targets": [s.value for s in allowed],
                    "reason": reason,
                },
            )

        self._current_state = target
        self._history.append((target, reason))
