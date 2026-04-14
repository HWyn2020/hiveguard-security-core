"""Integration tests for examples.monitor_agent — proves the enforcement
decorator stack composes cleanly on a realistic agent shape."""
import asyncio

import pytest

from examples.monitor_agent import MonitorAgent
from framework.security.enforcement import InvariantViolation, clear_audit_log, get_audit_log


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestMonitorAgentConstruction:
    def test_bounded_queue_enforced_at_construction(self):
        a = MonitorAgent("m-1", port=0)
        assert a._task_queue.maxsize > 0

    def test_agent_type_is_monitor(self):
        a = MonitorAgent("m-2", port=0)
        assert a.agent_type == "monitor"


class TestProcessTaskHappyPath:
    def setup_method(self):
        clear_audit_log()

    def test_valid_task_processes(self):
        a = MonitorAgent("m-happy", port=0)
        result = _run(
            a.process_task({"url": "https://example.com/", "label": "smoke"})
        )
        assert result["ok"] is True
        assert result["label"] == "smoke"
        assert result["outcome"]["status"] == "ok"

    def test_task_without_url_returns_error(self):
        a = MonitorAgent("m-err", port=0)
        result = _run(a.process_task({"label": "no-url"}))
        assert result["ok"] is False
        assert "url" in result["error"]

    def test_every_process_task_call_is_audit_logged(self):
        a = MonitorAgent("m-audit", port=0)
        _run(a.process_task({"url": "https://example.com/", "label": "a"}))
        _run(a.process_task({"url": "https://example.com/b", "label": "b"}))
        log = get_audit_log()
        method_calls = [r for r in log if "MonitorAgent.process_task" in r["method"]]
        assert len(method_calls) == 2
        assert all(r["success"] for r in method_calls)


class TestSsrfProtection:
    def test_localhost_url_raises(self):
        a = MonitorAgent("m-ssrf", port=0)
        with pytest.raises(InvariantViolation) as exc_info:
            _run(a.process_task({"url": "http://localhost/", "label": "x"}))
        assert exc_info.value.invariant_id == "INV-12"

    def test_cloud_metadata_url_raises(self):
        a = MonitorAgent("m-meta", port=0)
        with pytest.raises(InvariantViolation) as exc_info:
            _run(
                a.process_task(
                    {"url": "http://169.254.169.254/latest/meta-data/", "label": "aws"}
                )
            )
        assert exc_info.value.invariant_id == "INV-12"

    def test_private_range_url_raises(self):
        a = MonitorAgent("m-priv", port=0)
        with pytest.raises(InvariantViolation) as exc_info:
            _run(a.process_task({"url": "http://10.0.0.5/", "label": "priv"}))
        assert exc_info.value.invariant_id == "INV-12"


class TestInputSanitization:
    def test_control_chars_stripped_from_label(self):
        a = MonitorAgent("m-sanitize", port=0)
        result = _run(
            a.process_task(
                {"url": "https://example.com/", "label": "smoke\x00test\x07"}
            )
        )
        assert result["label"] == "smoketest"


class TestHealthPayload:
    def test_health_payload_is_safe(self):
        a = MonitorAgent("m-health", port=0)
        payload = a.health_payload()
        assert payload["agent_id"] == "m-health"
        assert payload["agent_type"] == "monitor"
        assert payload["findings_count"] == 0
        assert "api_key" not in payload
        assert "password" not in payload


class TestShutdown:
    def test_clean_shutdown_passes(self):
        a = MonitorAgent("m-stop", port=0)
        a._task_queue.put_nowait({"n": 1})
        a._task_queue.put_nowait({"n": 2})
        _run(a.stop())
        assert a._task_queue.qsize() == 0
        assert a._running is False
