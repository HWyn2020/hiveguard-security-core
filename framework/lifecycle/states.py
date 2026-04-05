"""
HiveGuard Agent Lifecycle States

Agents transition through defined states during operation.
"""

from enum import Enum
from typing import Callable, Dict, List


class AgentState(Enum):
    DORMANT = "DORMANT"
    RUNNING = "RUNNING"
    HIBERNATING = "HIBERNATING"
    PAUSED = "PAUSED"
    FROZEN = "FROZEN"
    ESCALATED = "ESCALATED"
    RESTING = "RESTING"
    DECOMMISSIONED = "DECOMMISSIONED"


VALID_TRANSITIONS: Dict[AgentState, List[AgentState]] = {
    AgentState.DORMANT: [AgentState.RUNNING],
    AgentState.RUNNING: [AgentState.HIBERNATING, AgentState.PAUSED, AgentState.FROZEN, AgentState.ESCALATED, AgentState.RESTING, AgentState.DECOMMISSIONED],
    AgentState.HIBERNATING: [AgentState.RUNNING, AgentState.DECOMMISSIONED],
    AgentState.PAUSED: [AgentState.RUNNING, AgentState.DECOMMISSIONED],
    AgentState.FROZEN: [AgentState.RUNNING, AgentState.ESCALATED, AgentState.DECOMMISSIONED],
    AgentState.ESCALATED: [AgentState.RUNNING, AgentState.FROZEN, AgentState.DECOMMISSIONED],
    AgentState.RESTING: [AgentState.RUNNING, AgentState.DECOMMISSIONED],
    AgentState.DECOMMISSIONED: [],
}


class LifecycleManager:
    """Manages agent state transitions with validation."""

    def __init__(self, initial_state: AgentState = AgentState.DORMANT):
        self._state = initial_state
        self._listeners: list = []

    @property
    def state(self) -> AgentState:
        return self._state

    def transition(self, new_state: AgentState) -> bool:
        """Attempt a state transition. Returns True if valid."""
        if new_state in VALID_TRANSITIONS.get(self._state, []):
            old = self._state
            self._state = new_state
            for listener in self._listeners:
                listener(old, new_state)
            return True
        return False

    def on_transition(self, callback: Callable):
        """Register a listener for state transitions."""
        self._listeners.append(callback)
