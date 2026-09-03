"""Unit tests for agent session lifecycle state machine."""

import pytest

from nova.agent.lifecycle import AgentState, LifecycleStateMachine
from nova.errors import AgentRuntimeError


def test_initial_state() -> None:
    sm = LifecycleStateMachine()
    assert sm.current_state == AgentState.INITIALIZING
    assert len(sm.history) == 1


def test_valid_transitions() -> None:
    sm = LifecycleStateMachine()
    sm.transition_to(AgentState.READY, "Agent initialized")
    assert sm.current_state == AgentState.READY

    sm.transition_to(AgentState.PLANNING, "Parsing goal")
    assert sm.current_state == AgentState.PLANNING

    sm.transition_to(AgentState.EXECUTING, "Running tools")
    assert sm.current_state == AgentState.EXECUTING

    sm.transition_to(AgentState.VERIFYING, "Checking post-conditions")
    assert sm.current_state == AgentState.VERIFYING

    sm.transition_to(AgentState.READY, "Turn concluded successfully")
    assert sm.current_state == AgentState.READY

    sm.transition_to(AgentState.TERMINATED, "Session finished")
    assert sm.current_state == AgentState.TERMINATED


def test_invalid_transitions_raise_runtime_error() -> None:
    sm = LifecycleStateMachine()

    # Cannot jump directly from INITIALIZING to EXECUTING
    with pytest.raises(AgentRuntimeError) as exc_info:
        sm.transition_to(AgentState.EXECUTING)
    assert "Illegal lifecycle transition" in str(exc_info.value)
    assert exc_info.value.details["current_state"] == AgentState.INITIALIZING.value
    assert exc_info.value.details["attempted_state"] == AgentState.EXECUTING.value


def test_terminated_is_terminal() -> None:
    sm = LifecycleStateMachine()
    sm.transition_to(AgentState.READY)
    sm.transition_to(AgentState.TERMINATED)

    with pytest.raises(AgentRuntimeError):
        sm.transition_to(AgentState.READY)
