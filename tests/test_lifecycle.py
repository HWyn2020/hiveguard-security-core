"""Tests for framework.lifecycle.states — AgentState, VALID_TRANSITIONS, LifecycleManager."""
import pytest

from framework.lifecycle.states import (
    VALID_TRANSITIONS,
    AgentState,
    LifecycleManager,
)


class TestAgentStateEnum:
    def test_exactly_8_states_defined(self):
        expected = {
            "DORMANT",
            "RUNNING",
            "HIBERNATING",
            "PAUSED",
            "FROZEN",
            "ESCALATED",
            "RESTING",
            "DECOMMISSIONED",
        }
        actual = {s.value for s in AgentState}
        assert actual == expected

    def test_all_states_appear_in_transition_table(self):
        """Every AgentState must have an entry in VALID_TRANSITIONS."""
        for state in AgentState:
            assert state in VALID_TRANSITIONS, f"{state} missing from transitions"


class TestLifecycleManagerInitialState:
    def test_default_initial_state_is_dormant(self):
        lm = LifecycleManager()
        assert lm.state == AgentState.DORMANT

    def test_custom_initial_state(self):
        lm = LifecycleManager(AgentState.RUNNING)
        assert lm.state == AgentState.RUNNING


class TestValidTransitions:
    def test_dormant_to_running_allowed(self):
        lm = LifecycleManager()
        assert lm.transition(AgentState.RUNNING) is True
        assert lm.state == AgentState.RUNNING

    def test_dormant_to_frozen_rejected(self):
        lm = LifecycleManager()
        assert lm.transition(AgentState.FROZEN) is False
        assert lm.state == AgentState.DORMANT

    def test_running_to_all_documented_states(self):
        """From RUNNING the agent can go to: HIBERNATING, PAUSED, FROZEN, ESCALATED, RESTING, DECOMMISSIONED."""
        targets = [
            AgentState.HIBERNATING,
            AgentState.PAUSED,
            AgentState.FROZEN,
            AgentState.ESCALATED,
            AgentState.RESTING,
            AgentState.DECOMMISSIONED,
        ]
        for target in targets:
            lm = LifecycleManager()
            lm.transition(AgentState.RUNNING)
            assert lm.transition(target) is True, f"RUNNING -> {target} should be valid"

    def test_frozen_to_escalated_allowed(self):
        lm = LifecycleManager()
        lm.transition(AgentState.RUNNING)
        lm.transition(AgentState.FROZEN)
        assert lm.transition(AgentState.ESCALATED) is True

    def test_hibernating_cannot_go_to_frozen(self):
        lm = LifecycleManager()
        lm.transition(AgentState.RUNNING)
        lm.transition(AgentState.HIBERNATING)
        # HIBERNATING -> FROZEN is not permitted
        assert lm.transition(AgentState.FROZEN) is False
        assert lm.state == AgentState.HIBERNATING


class TestDecommissionedTerminal:
    def test_decommissioned_has_no_outgoing_transitions(self):
        assert VALID_TRANSITIONS[AgentState.DECOMMISSIONED] == []

    def test_decommissioned_rejects_all_transitions(self):
        lm = LifecycleManager()
        lm.transition(AgentState.RUNNING)
        lm.transition(AgentState.DECOMMISSIONED)
        assert lm.state == AgentState.DECOMMISSIONED
        # Attempt to revive from a terminal state
        for target in AgentState:
            assert lm.transition(target) is False
        assert lm.state == AgentState.DECOMMISSIONED


class TestListeners:
    def test_listener_fires_on_valid_transition(self):
        lm = LifecycleManager()
        events = []
        lm.on_transition(lambda old, new: events.append((old, new)))
        lm.transition(AgentState.RUNNING)
        assert events == [(AgentState.DORMANT, AgentState.RUNNING)]

    def test_listener_silent_on_invalid_transition(self):
        lm = LifecycleManager()
        events = []
        lm.on_transition(lambda old, new: events.append((old, new)))
        lm.transition(AgentState.FROZEN)  # invalid from DORMANT
        assert events == []

    def test_multiple_listeners_all_fire(self):
        lm = LifecycleManager()
        calls_a, calls_b = [], []
        lm.on_transition(lambda o, n: calls_a.append((o, n)))
        lm.on_transition(lambda o, n: calls_b.append((o, n)))
        lm.transition(AgentState.RUNNING)
        assert len(calls_a) == 1
        assert len(calls_b) == 1
