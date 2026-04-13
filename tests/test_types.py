"""Tests for framework.types — Task, TaskResult, AgentConfig, AgentType."""
from framework.types import AgentConfig, AgentType, Task, TaskResult


class TestTask:
    def test_task_basic_construction(self):
        t = Task(task_id="t1", task_type="crawl", payload={"url": "https://example.com"})
        assert t.task_id == "t1"
        assert t.task_type == "crawl"
        assert t.payload == {"url": "https://example.com"}
        assert t.priority == 0  # default
        assert t.metadata == {}  # default

    def test_task_with_priority_and_metadata(self):
        t = Task(
            task_id="t2",
            task_type="scan",
            payload={},
            priority=5,
            metadata={"source": "manual", "trace_id": "abc"},
        )
        assert t.priority == 5
        assert t.metadata == {"source": "manual", "trace_id": "abc"}

    def test_task_metadata_instance_isolation(self):
        """Default metadata must not be shared between instances (field default_factory)."""
        t1 = Task(task_id="a", task_type="x", payload={})
        t2 = Task(task_id="b", task_type="y", payload={})
        t1.metadata["key"] = "v1"
        assert "key" not in t2.metadata


class TestTaskResult:
    def test_task_result_success_minimal(self):
        r = TaskResult(task_id="t1", success=True)
        assert r.task_id == "t1"
        assert r.success is True
        assert r.result is None
        assert r.error is None
        assert r.duration_ms == 0.0

    def test_task_result_success_with_payload_and_duration(self):
        r = TaskResult(
            task_id="t1",
            success=True,
            result={"data": 42},
            duration_ms=123.4,
        )
        assert r.result == {"data": 42}
        assert r.duration_ms == 123.4
        assert r.error is None

    def test_task_result_failure_with_error_message(self):
        r = TaskResult(task_id="t1", success=False, error="timeout after 30s")
        assert r.success is False
        assert r.error == "timeout after 30s"
        assert r.result is None


class TestAgentConfig:
    def test_agent_config_required_fields_only(self):
        c = AgentConfig(agent_id="scout-1", agent_type=AgentType.SCOUT)
        assert c.agent_id == "scout-1"
        assert c.agent_type == AgentType.SCOUT
        # Defaults
        assert c.port == 3201
        assert c.max_queue_size == 10_000
        assert c.health_check_interval == 30

    def test_agent_config_full_overrides(self):
        c = AgentConfig(
            agent_id="fixer-prod-3",
            agent_type=AgentType.FIXER,
            port=4500,
            max_queue_size=500,
            health_check_interval=60,
        )
        assert c.port == 4500
        assert c.max_queue_size == 500
        assert c.health_check_interval == 60


class TestAgentType:
    def test_agent_type_enum_values(self):
        """All five agent types from the framework spec."""
        assert AgentType.SCOUT.value == "scout"
        assert AgentType.ANALYST.value == "analyst"
        assert AgentType.FIXER.value == "fixer"
        assert AgentType.WEB_SCOUT.value == "web-scout"
        assert AgentType.CUSTOM.value == "custom"

    def test_agent_type_membership(self):
        names = {t.name for t in AgentType}
        assert names == {"SCOUT", "ANALYST", "FIXER", "WEB_SCOUT", "CUSTOM"}
