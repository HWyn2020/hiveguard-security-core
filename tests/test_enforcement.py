"""Tests for framework.security.enforcement — runtime invariant decorators.

Each decorator gets positive tests (compliant code runs) and negative tests
(violating code raises InvariantViolation with the correct invariant_id).
"""
import asyncio
import os

import pytest

from framework.security.enforcement import (
    APPROVED_HASHES,
    BANNED_HASHES,
    InvariantViolation,
    RateLimiter,
    approved_crypto_hash,
    audit_logged,
    bounded_queue,
    clear_audit_log,
    enforces,
    env_credentials_wiped,
    fail_closed,
    get_audit_log,
    memory_wiped_on_exit,
    no_direct_llm,
    no_sensitive_in_output,
    rate_limited,
    safe_url,
    sanitize_input,
    shutdown_within,
    validated_urls,
)


def _run(coro):
    """Run a coroutine in a fresh event loop (sync test helper)."""
    return asyncio.new_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# InvariantViolation base behavior
# ---------------------------------------------------------------------------


class TestInvariantViolation:
    def test_is_runtime_error_subclass(self):
        assert issubclass(InvariantViolation, RuntimeError)

    def test_exposes_invariant_id_and_message(self):
        exc = InvariantViolation("INV-99", "synthetic failure")
        assert exc.invariant_id == "INV-99"
        assert exc.message == "synthetic failure"
        assert "INV-99" in str(exc)
        assert "synthetic failure" in str(exc)


# ---------------------------------------------------------------------------
# INV-01 — no_direct_llm
# ---------------------------------------------------------------------------


class TestNoDirectLLM:
    def test_clean_function_passes(self):
        @no_direct_llm
        def process():
            return "ok"

        assert process() == "ok"

    def test_function_with_banned_sdk_in_globals_raises(self):
        # Simulate a function that has a banned LLM SDK in its globals.
        import types

        fake_anthropic = types.ModuleType("anthropic")
        fake_anthropic.__name__ = "anthropic"

        def target():
            return "would_call_llm"

        target.__globals__["anthropic"] = fake_anthropic  # type: ignore[misc]
        try:
            wrapped = no_direct_llm(target)
            with pytest.raises(InvariantViolation) as exc_info:
                wrapped()
            assert exc_info.value.invariant_id == "INV-01"
        finally:
            target.__globals__.pop("anthropic", None)


# ---------------------------------------------------------------------------
# INV-03 — memory_wiped_on_exit
# ---------------------------------------------------------------------------


class _StubWithQueue:
    def __init__(self, leave_n: int = 0):
        self._task_queue = asyncio.Queue(maxsize=10)
        self._leave_n = leave_n

    @memory_wiped_on_exit()
    async def stop(self):
        # Drain the queue (correct behavior) leaving _leave_n items behind
        while self._task_queue.qsize() > self._leave_n:
            self._task_queue.get_nowait()


class TestMemoryWipedOnExit:
    def test_clean_shutdown_passes(self):
        s = _StubWithQueue(leave_n=0)
        for i in range(5):
            s._task_queue.put_nowait({"n": i})
        _run(s.stop())
        assert s._task_queue.qsize() == 0

    def test_leaked_items_raise(self):
        s = _StubWithQueue(leave_n=2)
        for i in range(5):
            s._task_queue.put_nowait({"n": i})
        with pytest.raises(InvariantViolation) as exc_info:
            _run(s.stop())
        assert exc_info.value.invariant_id == "INV-03"


# ---------------------------------------------------------------------------
# INV-05 — bounded_queue
# ---------------------------------------------------------------------------


class TestBoundedQueue:
    def test_bounded_queue_passes(self):
        class GoodAgent:
            @bounded_queue()
            def __init__(self):
                self._task_queue = asyncio.Queue(maxsize=100)

        GoodAgent()  # should not raise

    def test_unbounded_queue_raises(self):
        class BadAgent:
            @bounded_queue()
            def __init__(self):
                self._task_queue = asyncio.Queue()  # default maxsize=0 => unbounded

        with pytest.raises(InvariantViolation) as exc_info:
            BadAgent()
        assert exc_info.value.invariant_id == "INV-05"

    def test_missing_queue_attribute_raises(self):
        class NoQueueAgent:
            @bounded_queue()
            def __init__(self):
                pass  # never sets _task_queue

        with pytest.raises(InvariantViolation) as exc_info:
            NoQueueAgent()
        assert exc_info.value.invariant_id == "INV-05"


# ---------------------------------------------------------------------------
# INV-06 — audit_logged
# ---------------------------------------------------------------------------


class _LoggingAgent:
    def __init__(self, should_raise: bool = False):
        self.agent_id = "audit-test"
        self.should_raise = should_raise

    @audit_logged()
    async def process_task(self, task):
        if self.should_raise:
            raise ValueError("simulated failure")
        return {"ok": True, "echo": task}


class TestAuditLogged:
    def setup_method(self):
        clear_audit_log()

    def test_successful_call_logged(self):
        a = _LoggingAgent()
        result = _run(a.process_task({"input": "hello"}))
        assert result == {"ok": True, "echo": {"input": "hello"}}
        log = get_audit_log()
        assert len(log) == 1
        assert log[0]["agent_id"] == "audit-test"
        assert log[0]["success"] is True
        assert "_LoggingAgent.process_task" in log[0]["method"]

    def test_failed_call_logged_then_reraised(self):
        a = _LoggingAgent(should_raise=True)
        with pytest.raises(ValueError):
            _run(a.process_task({"input": "bad"}))
        log = get_audit_log()
        assert len(log) == 1
        assert log[0]["success"] is False
        assert "ValueError" in log[0]["error"]

    def test_custom_sink_receives_records(self):
        sink = []

        class LocalAgent:
            agent_id = "local"

            @audit_logged(sink=sink)
            async def run(self, payload):
                return payload

        _run(LocalAgent().run({"x": 1}))
        assert len(sink) == 1
        assert sink[0]["agent_id"] == "local"


# ---------------------------------------------------------------------------
# INV-08 — no_sensitive_in_output
# ---------------------------------------------------------------------------


class TestNoSensitiveInOutput:
    def test_clean_output_passes(self):
        @no_sensitive_in_output
        def health():
            return {"status": "healthy", "uptime": 123, "tasks": 5}

        assert health()["status"] == "healthy"

    def test_api_key_in_output_raises(self):
        @no_sensitive_in_output
        def bad_health():
            return {"status": "ok", "api_key": "sk-xxx"}

        with pytest.raises(InvariantViolation) as exc_info:
            bad_health()
        assert exc_info.value.invariant_id == "INV-08"

    def test_nested_password_raises(self):
        @no_sensitive_in_output
        def nested():
            return {"ok": True, "config": {"db": {"password": "hunter2"}}}

        with pytest.raises(InvariantViolation):
            nested()

    def test_secret_in_list_raises(self):
        @no_sensitive_in_output
        def listed():
            return {"items": [{"name": "x"}, {"secret": "shh"}]}

        with pytest.raises(InvariantViolation):
            listed()


# ---------------------------------------------------------------------------
# INV-09 — shutdown_within
# ---------------------------------------------------------------------------


class TestShutdownWithin:
    def test_fast_shutdown_passes(self):
        @shutdown_within(seconds=1.0)
        async def quick_stop():
            await asyncio.sleep(0.01)
            return "stopped"

        assert _run(quick_stop()) == "stopped"

    def test_slow_shutdown_raises(self):
        @shutdown_within(seconds=0.1)
        async def slow_stop():
            await asyncio.sleep(1.0)

        with pytest.raises(InvariantViolation) as exc_info:
            _run(slow_stop())
        assert exc_info.value.invariant_id == "INV-09"


# ---------------------------------------------------------------------------
# INV-10 — env_credentials_wiped
# ---------------------------------------------------------------------------


class TestEnvCredentialsWiped:
    def test_clean_env_passes(self):
        @env_credentials_wiped(prefixes=("HIVEGUARD_TEST_",))
        async def stop():
            return None

        _run(stop())  # no env vars with that prefix

    def test_leaked_env_raises(self):
        os.environ["HIVEGUARD_TEST_TOKEN"] = "leaked"

        try:

            @env_credentials_wiped(prefixes=("HIVEGUARD_TEST_",))
            async def stop():
                return None

            with pytest.raises(InvariantViolation) as exc_info:
                _run(stop())
            assert exc_info.value.invariant_id == "INV-10"
        finally:
            os.environ.pop("HIVEGUARD_TEST_TOKEN", None)

    def test_properly_wiped_env_passes(self):
        os.environ["HIVEGUARD_TEST_KEY"] = "temporary"

        @env_credentials_wiped(prefixes=("HIVEGUARD_TEST_",))
        async def stop():
            os.environ.pop("HIVEGUARD_TEST_KEY", None)
            return None

        _run(stop())


# ---------------------------------------------------------------------------
# INV-11 — sanitize_input
# ---------------------------------------------------------------------------


class _SanitizeAgent:
    @sanitize_input()
    async def process_task(self, task):
        return task


class TestSanitizeInput:
    def test_clean_dict_passes_through(self):
        a = _SanitizeAgent()
        result = _run(a.process_task({"message": "hello"}))
        assert result == {"message": "hello"}

    def test_control_chars_stripped(self):
        a = _SanitizeAgent()
        result = _run(a.process_task({"message": "hel\x00lo\x07world"}))
        assert result == {"message": "helloworld"}

    def test_excess_depth_raises(self):
        # Depth 10 exceeds default max_depth=8
        deep = current = {}
        for _ in range(10):
            current["next"] = {}
            current = current["next"]

        a = _SanitizeAgent()
        with pytest.raises(InvariantViolation) as exc_info:
            _run(a.process_task(deep))
        assert exc_info.value.invariant_id == "INV-11"

    def test_non_json_type_raises(self):
        class Weird:
            pass

        a = _SanitizeAgent()
        with pytest.raises(InvariantViolation):
            _run(a.process_task({"x": Weird()}))


# ---------------------------------------------------------------------------
# INV-12 — safe_url + validated_urls
# ---------------------------------------------------------------------------


class TestSafeUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/",
            "http://github.com/HWyn2020",
            "https://api.openai.com/v1/models",
            "https://hiveguard.ee",
        ],
    )
    def test_safe_urls_accepted(self, url):
        assert safe_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost/",
            "http://127.0.0.1/",
            "http://127.1.2.3/",
            "http://10.0.0.5/",
            "http://192.168.1.100/",
            "http://172.16.0.1/",
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "http://metadata.google.internal/",
            "file:///etc/passwd",
            "ftp://example.com/",
            "http://[::1]/",
        ],
    )
    def test_unsafe_urls_rejected(self, url):
        assert safe_url(url) is False


class TestValidatedUrls:
    def test_safe_url_call_passes(self):
        class Fetcher:
            @validated_urls()
            async def fetch(self, url):
                return f"fetched {url}"

        result = _run(Fetcher().fetch("https://example.com/"))
        assert "example.com" in result

    def test_unsafe_url_raises(self):
        class Fetcher:
            @validated_urls()
            async def fetch(self, url):
                return f"fetched {url}"

        with pytest.raises(InvariantViolation) as exc_info:
            _run(Fetcher().fetch("http://169.254.169.254/"))
        assert exc_info.value.invariant_id == "INV-12"


# ---------------------------------------------------------------------------
# INV-15 — fail_closed
# ---------------------------------------------------------------------------


class TestFailClosed:
    def test_sync_success_passes_through(self):
        @fail_closed(default_return="SAFE")
        def compute():
            return 42

        assert compute() == 42

    def test_sync_exception_returns_default(self):
        @fail_closed(default_return="SAFE")
        def compute():
            raise ValueError("boom")

        assert compute() == "SAFE"

    def test_async_success_passes_through(self):
        @fail_closed(default_return=None)
        async def compute():
            return {"ok": True}

        assert _run(compute()) == {"ok": True}

    def test_async_exception_returns_default(self):
        @fail_closed(default_return={"failed": True})
        async def compute():
            raise RuntimeError("boom")

        assert _run(compute()) == {"failed": True}


# ---------------------------------------------------------------------------
# INV-16 — rate_limited + RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_limiter_allows_within_budget(self):
        lim = RateLimiter(max_calls=3, window_seconds=60)
        assert lim.check() is True
        assert lim.check() is True
        assert lim.check() is True

    def test_limiter_rejects_over_budget(self):
        lim = RateLimiter(max_calls=2, window_seconds=60)
        assert lim.check() is True
        assert lim.check() is True
        assert lim.check() is False

    def test_limiter_resets_state(self):
        lim = RateLimiter(max_calls=1, window_seconds=60)
        assert lim.check() is True
        assert lim.check() is False
        lim.reset()
        assert lim.check() is True


class TestRateLimited:
    def test_within_budget_succeeds(self):
        @rate_limited(max_calls=5, window_seconds=60)
        async def call():
            return "ok"

        for _ in range(5):
            assert _run(call()) == "ok"

    def test_over_budget_raises(self):
        @rate_limited(max_calls=2, window_seconds=60)
        async def call():
            return "ok"

        _run(call())
        _run(call())
        with pytest.raises(InvariantViolation) as exc_info:
            _run(call())
        assert exc_info.value.invariant_id == "INV-16"


# ---------------------------------------------------------------------------
# INV-19 — approved_crypto_hash
# ---------------------------------------------------------------------------


class TestApprovedCryptoHash:
    @pytest.mark.parametrize("algo", sorted(APPROVED_HASHES))
    def test_approved_algorithms_pass(self, algo):
        approved_crypto_hash(algo)  # no raise
        approved_crypto_hash(algo.upper())  # case-insensitive

    @pytest.mark.parametrize("algo", sorted(BANNED_HASHES))
    def test_banned_algorithms_raise(self, algo):
        with pytest.raises(InvariantViolation) as exc_info:
            approved_crypto_hash(algo)
        assert exc_info.value.invariant_id == "INV-19"

    def test_unknown_algorithm_raises(self):
        with pytest.raises(InvariantViolation):
            approved_crypto_hash("rot13")

    def test_dash_and_underscore_normalized(self):
        # sha3-256 should resolve to sha3_256 on the approved list
        approved_crypto_hash("sha3-256")


# ---------------------------------------------------------------------------
# @enforces("INV-XX") declarative dispatch
# ---------------------------------------------------------------------------


class TestEnforcesDispatch:
    def test_unknown_invariant_raises_value_error(self):
        with pytest.raises(ValueError):
            enforces("INV-99")

    def test_unenforceable_invariant_raises_value_error(self):
        # INV-07 is documented but has no default runtime enforcement
        with pytest.raises(ValueError) as exc_info:
            enforces("INV-07")
        assert "INV-07" in str(exc_info.value)

    def test_enforceable_invariant_returns_decorator(self):
        decorator = enforces("INV-06")  # audit_logged
        assert callable(decorator)

    def test_enforces_inv01_blocks_banned_sdk(self):
        import types

        fake_openai = types.ModuleType("openai")
        fake_openai.__name__ = "openai"

        def bad():
            return "leak"

        # Install the banned SDK in the original function's globals BEFORE
        # wrapping, so the closure captured inside no_direct_llm sees it.
        bad.__globals__["openai"] = fake_openai  # type: ignore[misc]
        try:
            wrapped = enforces("INV-01")(bad)
            with pytest.raises(InvariantViolation) as exc_info:
                wrapped()
            assert exc_info.value.invariant_id == "INV-01"
        finally:
            bad.__globals__.pop("openai", None)
