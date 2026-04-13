"""Shared pytest fixtures for the HiveGuard security core test suite."""
import asyncio
from typing import Any, Dict

import pytest

from framework.agents.base_agent import BaseAgent


class DummyAgent(BaseAgent):
    """Minimal BaseAgent subclass for testing. Does not start the health server."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return {"processed": True, "task": task}


@pytest.fixture
def dummy_agent():
    """A fresh DummyAgent with port=0 (never actually bound)."""
    return DummyAgent("test-agent", agent_type="test", port=0)


@pytest.fixture
def run_async():
    """Run an async coroutine inside a sync test."""
    def _run(coro):
        return asyncio.new_event_loop().run_until_complete(coro)
    return _run
