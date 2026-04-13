"""Tests for framework.agents.base_agent.BaseAgent."""
import asyncio

import pytest

from framework.agents.base_agent import BaseAgent
from tests.conftest import DummyAgent


class TestBaseAgentConstruction:
    def test_cannot_instantiate_abstract_base_agent(self):
        """BaseAgent is abstract — direct instantiation must fail."""
        with pytest.raises(TypeError):
            BaseAgent("abstract", port=0)  # type: ignore[abstract]

    def test_default_construction(self):
        a = DummyAgent("scout-1")
        assert a.agent_id == "scout-1"
        assert a.agent_type == "custom"  # BaseAgent default when kwarg omitted
        assert a.port == 3201  # BaseAgent default port
        assert a._running is False
        assert a._task_count == 0
        assert a._start_time == 0.0

    def test_custom_construction(self):
        a = DummyAgent("fixer-1", agent_type="fixer", port=4500)
        assert a.agent_type == "fixer"
        assert a.port == 4500

    def test_task_queue_bounded_at_10000(self):
        a = DummyAgent("t", port=0)
        assert a._task_queue.maxsize == 10_000


class TestSubmitTask:
    def test_submit_task_success(self, dummy_agent):
        assert dummy_agent.submit_task({"x": 1}) is True
        assert dummy_agent._task_queue.qsize() == 1

    def test_submit_task_returns_false_when_queue_full(self):
        a = DummyAgent("t", port=0)
        # Replace queue with a tiny bounded one for speed
        a._task_queue = asyncio.Queue(maxsize=2)
        assert a.submit_task({"n": 1}) is True
        assert a.submit_task({"n": 2}) is True
        assert a.submit_task({"overflow": True}) is False
        assert a._task_queue.qsize() == 2


class TestMemoryWipe:
    def test_wipe_memory_drains_queue(self, dummy_agent):
        dummy_agent.submit_task({"a": 1})
        dummy_agent.submit_task({"b": 2})
        dummy_agent.submit_task({"c": 3})
        assert dummy_agent._task_queue.qsize() == 3
        dummy_agent._wipe_memory()
        assert dummy_agent._task_queue.qsize() == 0

    def test_wipe_memory_on_empty_queue_is_noop(self, dummy_agent):
        dummy_agent._wipe_memory()  # Should not raise
        assert dummy_agent._task_queue.qsize() == 0


class TestStop:
    def test_stop_sets_running_false(self, dummy_agent, run_async):
        dummy_agent._running = True
        run_async(dummy_agent.stop())
        assert dummy_agent._running is False

    def test_stop_wipes_queued_tasks(self, dummy_agent, run_async):
        dummy_agent._running = True
        dummy_agent.submit_task({"leak": "sensitive"})
        dummy_agent.submit_task({"also": "sensitive"})
        run_async(dummy_agent.stop())
        assert dummy_agent._task_queue.qsize() == 0


class TestProcessTask:
    def test_subclass_process_task_works(self, dummy_agent, run_async):
        result = run_async(dummy_agent.process_task({"in": "data"}))
        assert result["processed"] is True
        assert result["task"] == {"in": "data"}
