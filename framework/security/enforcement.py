"""
Runtime enforcement of HiveGuard security invariants.

The 20 invariants in ``invariants.py`` are a checklist. This module turns a
subset of them into enforceable runtime decorators. Apply them to your agent
methods to get automatic violation detection — violations raise
``InvariantViolation``.

Not every invariant is enforceable in a framework-level skeleton. The 12
that ARE enforceable without private IP are exported from this module. The
remaining 8 stay as spec strings in ``invariants.py`` — you design to them,
but runtime verification requires domain-specific code (the commercial
HiveGuard ships those via UBava).

Enforceable here
----------------

- INV-01 :func:`no_direct_llm`           — no LLM SDKs in function globals
- INV-03 :func:`memory_wiped_on_exit`    — queue empty after shutdown
- INV-05 :func:`bounded_queue`           — task queue has positive maxsize
- INV-06 :func:`audit_logged`            — record every call to an audit sink
- INV-08 :func:`no_sensitive_in_output`  — scan output for credential keys
- INV-09 :func:`shutdown_within`         — timeout wrapper on shutdown
- INV-10 :func:`env_credentials_wiped`   — env vars cleared on shutdown
- INV-11 :func:`sanitize_input`          — strip control chars, depth cap
- INV-12 :func:`validated_urls` / :func:`safe_url` — SSRF / internal-IP block
- INV-15 :func:`fail_closed`             — exception → failure sentinel
- INV-16 :func:`rate_limited`            — sliding-window limiter
- INV-19 :func:`approved_crypto_hash`    — allow SHA-2/3 + BLAKE2, block MD5/SHA-1

Declarative helper: :func:`enforces` dispatches ``@enforces("INV-XX")`` to
the default enforcement for the named invariant. Parameterized decorators
(``shutdown_within``, ``rate_limited``, ``sanitize_input``, etc.) should be
applied directly.
"""
from __future__ import annotations

import asyncio
import functools
import ipaddress
import os
import re
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from framework.security.invariants import check_invariant


class InvariantViolation(RuntimeError):
    """Raised when a HiveGuard security invariant is violated at runtime."""

    def __init__(self, invariant_id: str, message: str):
        self.invariant_id = invariant_id
        self.message = message
        super().__init__(f"[{invariant_id}] {message}")


# ---------------------------------------------------------------------------
# INV-01 — Agents MUST NOT call LLM APIs directly.
# ---------------------------------------------------------------------------

BANNED_LLM_MODULES = frozenset(
    {
        "anthropic",
        "openai",
        "google.generativeai",
        "google_generativeai",
        "groq",
        "cohere",
        "mistralai",
        "replicate",
    }
)


def no_direct_llm(func: Callable) -> Callable:
    """Enforce INV-01.

    Raises :class:`InvariantViolation` at call time if the decorated
    function's module globals contain any known LLM SDK. Agents must route
    LLM calls through the designated entry point (e.g. the UBava Relay).
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        fn_globals = getattr(func, "__globals__", {}) or {}
        for banned in BANNED_LLM_MODULES:
            top = banned.split(".")[0]
            if top not in fn_globals:
                continue
            module = fn_globals[top]
            name = getattr(module, "__name__", top)
            if name == banned or name.startswith(banned + "."):
                raise InvariantViolation(
                    "INV-01",
                    f"{func.__qualname__} has access to banned LLM SDK "
                    f"'{name}'. Route all LLM calls through the designated "
                    f"entry point.",
                )
        return func(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# INV-03 — Agent memory MUST be wiped on shutdown.
# ---------------------------------------------------------------------------


def memory_wiped_on_exit(queue_attr: str = "_task_queue") -> Callable:
    """Enforce INV-03.

    After the decorated async shutdown method returns, verify that the
    specified queue attribute on ``self`` is empty. Raises if not.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = await func(self, *args, **kwargs)
            q = getattr(self, queue_attr, None)
            if q is not None and hasattr(q, "qsize") and q.qsize() > 0:
                raise InvariantViolation(
                    "INV-03",
                    f"After {func.__qualname__}, {queue_attr} still has "
                    f"{q.qsize()} items. Memory must be wiped on shutdown.",
                )
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-05 — Task queues MUST be bounded.
# ---------------------------------------------------------------------------


def bounded_queue(queue_attr: str = "_task_queue") -> Callable:
    """Enforce INV-05.

    After ``__init__`` (or any factory method) runs, verify that the queue
    attribute has a positive ``maxsize``. Unbounded queues enable memory
    exhaustion attacks and must be rejected.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = func(self, *args, **kwargs)
            q = getattr(self, queue_attr, None)
            if q is None:
                raise InvariantViolation(
                    "INV-05",
                    f"{func.__qualname__} did not create attribute "
                    f"'{queue_attr}'.",
                )
            maxsize = getattr(q, "maxsize", 0)
            if maxsize <= 0:
                raise InvariantViolation(
                    "INV-05",
                    f"{queue_attr} is unbounded (maxsize={maxsize}). Set a "
                    f"positive maxsize to prevent memory exhaustion.",
                )
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-06 — Agent decisions MUST be logged for audit.
# ---------------------------------------------------------------------------

_audit_log: List[Dict[str, Any]] = []


def audit_logged(sink: Optional[List[Dict[str, Any]]] = None) -> Callable:
    """Enforce INV-06.

    Wrap an async method so every call appends an audit record (timestamp,
    agent id, method name, args summary, success/failure, result summary or
    error). If no sink is provided, uses a module-level default sink that
    can be inspected via :func:`get_audit_log`.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            target = sink if sink is not None else _audit_log
            record: Dict[str, Any] = {
                "timestamp": time.time(),
                "agent_id": getattr(self, "agent_id", "?"),
                "method": func.__qualname__,
                "args_summary": _summarize(args),
                "kwargs_summary": _summarize(kwargs),
            }
            try:
                result = await func(self, *args, **kwargs)
                record["success"] = True
                record["result_summary"] = _summarize(result)
                target.append(record)
                return result
            except Exception as e:
                record["success"] = False
                record["error"] = f"{type(e).__name__}: {e}"
                target.append(record)
                raise

        return wrapper

    return decorator


def _summarize(obj: Any, max_len: int = 200) -> str:
    s = repr(obj)
    if len(s) <= max_len:
        return s
    return s[:max_len] + "...[truncated]"


def get_audit_log() -> List[Dict[str, Any]]:
    """Return a copy of the default audit log."""
    return list(_audit_log)


def clear_audit_log() -> None:
    """Clear the default audit log (useful between tests)."""
    _audit_log.clear()


# ---------------------------------------------------------------------------
# INV-08 — Health endpoints MUST NOT expose sensitive data.
# ---------------------------------------------------------------------------

SENSITIVE_KEY_PATTERNS = re.compile(
    r"(api[_-]?key|password|secret|token|credential|private[_-]?key|"
    r"session[_-]?id|auth)",
    re.IGNORECASE,
)


def no_sensitive_in_output(func: Callable) -> Callable:
    """Enforce INV-08.

    Recursively scans the returned structure (dict / list / tuple) for keys
    matching sensitive patterns (``api_key``, ``password``, ``secret``,
    ``token``, ``credential``, ``private_key``, ``session_id``, ``auth``).
    Raises :class:`InvariantViolation` on any hit.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        _scan_for_sensitive(result, "INV-08")
        return result

    return wrapper


def _scan_for_sensitive(obj: Any, invariant_id: str, path: str = "root") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and SENSITIVE_KEY_PATTERNS.search(k):
                raise InvariantViolation(
                    invariant_id,
                    f"Output key '{path}.{k}' matches sensitive pattern. "
                    f"Health endpoints and public outputs must not expose "
                    f"credentials or tokens.",
                )
            _scan_for_sensitive(v, invariant_id, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _scan_for_sensitive(item, invariant_id, f"{path}[{i}]")


# ---------------------------------------------------------------------------
# INV-09 — Graceful shutdown MUST complete within N seconds.
# ---------------------------------------------------------------------------


def shutdown_within(seconds: float = 10.0) -> Callable:
    """Enforce INV-09.

    Wrap an async shutdown method in :func:`asyncio.wait_for` with the given
    timeout. Raises :class:`InvariantViolation` if the timeout fires.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs), timeout=seconds
                )
            except asyncio.TimeoutError:
                raise InvariantViolation(
                    "INV-09",
                    f"{func.__qualname__} exceeded {seconds}s shutdown budget.",
                )

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-10 — Agent credentials MUST be wiped from process env on shutdown.
# ---------------------------------------------------------------------------


def env_credentials_wiped(
    prefixes: Tuple[str, ...] = ("HIVEGUARD_", "AGENT_"),
) -> Callable:
    """Enforce INV-10.

    After the decorated async shutdown method returns, verify that no
    environment variables with the given prefixes are still set. Raises if
    any leaked credentials remain.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            leaked = [k for k in os.environ if k.startswith(prefixes)]
            if leaked:
                raise InvariantViolation(
                    "INV-10",
                    f"Shutdown left {len(leaked)} env credentials with "
                    f"prefixes {prefixes}: {leaked[:5]}"
                    + ("..." if len(leaked) > 5 else ""),
                )
            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-11 — All user input MUST be sanitized before processing.
# ---------------------------------------------------------------------------

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_input(
    allow_control_chars: bool = False, max_depth: int = 8
) -> Callable:
    """Enforce INV-11.

    Sanitize the first positional argument after ``self`` (the task payload)
    by recursively stripping control characters and enforcing a depth cap.
    Rejects non-JSON-serializable types. The cleaned value is passed on to
    the wrapped method.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self: Any, task: Any, *args: Any, **kwargs: Any) -> Any:
            clean = _sanitize_value(task, allow_control_chars, max_depth, 0)
            return await func(self, clean, *args, **kwargs)

        return wrapper

    return decorator


def _sanitize_value(v: Any, allow_ctrl: bool, max_depth: int, depth: int) -> Any:
    if depth > max_depth:
        raise InvariantViolation(
            "INV-11",
            f"Input nesting depth exceeds limit of {max_depth}.",
        )
    if isinstance(v, str):
        return v if allow_ctrl else _CONTROL_CHARS.sub("", v)
    if isinstance(v, dict):
        return {
            k: _sanitize_value(val, allow_ctrl, max_depth, depth + 1)
            for k, val in v.items()
        }
    if isinstance(v, list):
        return [_sanitize_value(x, allow_ctrl, max_depth, depth + 1) for x in v]
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    raise InvariantViolation(
        "INV-11",
        f"Unsupported input type: {type(v).__name__}. "
        f"Only JSON-serializable primitives are allowed.",
    )


# ---------------------------------------------------------------------------
# INV-12 — Agents MUST validate URL targets (no SSRF, no internal IPs).
# ---------------------------------------------------------------------------

_PRIVATE_HOSTNAMES = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata",
        "instance-data",
    }
)


def safe_url(url: str) -> bool:
    """Return ``True`` if the URL is safe for outbound requests.

    Blocks:

    - non-HTTP(S) schemes
    - loopback hosts (``localhost``, ``127.0.0.0/8``, ``::1``)
    - private ranges (``10.0.0.0/8``, ``172.16.0.0/12``, ``192.168.0.0/16``)
    - link-local (``169.254.0.0/16``, ``fe80::/10``)
    - ULA / reserved IPv6
    - cloud metadata endpoints (``169.254.169.254`` is covered by link-local)
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    if host in _PRIVATE_HOSTNAMES:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Hostname, not an IP. Accept — real DNS resolution is the caller's
        # concern. If you want to resolve-and-check, wrap this with a
        # DNS-aware guard in your agent code.
        return True
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return False
    return True


def validated_urls(arg_name: str = "url") -> Callable:
    """Enforce INV-12.

    Validate a URL argument (by keyword or first positional after ``self``)
    against SSRF-prone targets via :func:`safe_url`. Raises
    :class:`InvariantViolation` if the URL is unsafe.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            url = kwargs.get(arg_name)
            if url is None and len(args) >= 2:
                # Assume signature is (self, url, ...)
                url = args[1]
            if url is None:
                raise InvariantViolation(
                    "INV-12",
                    f"{func.__qualname__} called without a URL argument "
                    f"'{arg_name}'.",
                )
            if not safe_url(url):
                raise InvariantViolation(
                    "INV-12",
                    f"URL '{url}' rejected as unsafe (SSRF / internal / "
                    f"unsupported scheme).",
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-15 — Failed operations MUST fail closed.
# ---------------------------------------------------------------------------


def fail_closed(default_return: Any = None) -> Callable:
    """Enforce INV-15.

    If the decorated method raises, catch the exception and return the
    supplied ``default_return`` sentinel. Prevents silent partial-failure
    fall-through where callers assume success.

    Works on both sync and async functions.
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception:
                    return default_return

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception:
                return default_return

        return sync_wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-16 — Rate limiting MUST be enforced on all external calls.
# ---------------------------------------------------------------------------


class RateLimiter:
    """Sliding-window rate limiter (in-memory, per-instance)."""

    def __init__(self, max_calls: int, window_seconds: float):
        if max_calls <= 0:
            raise ValueError("max_calls must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls: Deque[float] = deque()

    def check(self) -> bool:
        """Return ``True`` if a new call fits in the window, ``False`` otherwise."""
        now = time.time()
        while self._calls and self._calls[0] < now - self.window:
            self._calls.popleft()
        if len(self._calls) >= self.max_calls:
            return False
        self._calls.append(now)
        return True

    def reset(self) -> None:
        self._calls.clear()


def rate_limited(max_calls: int = 60, window_seconds: float = 60.0) -> Callable:
    """Enforce INV-16.

    Apply a sliding-window rate limit to the decorated async function. Each
    decorated function gets its own limiter state. Raises
    :class:`InvariantViolation` when the limit is exceeded.
    """

    def decorator(func: Callable) -> Callable:
        limiter = RateLimiter(max_calls, window_seconds)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not limiter.check():
                raise InvariantViolation(
                    "INV-16",
                    f"Rate limit exceeded on {func.__qualname__}: "
                    f"{max_calls} calls per {window_seconds}s.",
                )
            return await func(*args, **kwargs)

        wrapper._limiter = limiter  # type: ignore[attr-defined]
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# INV-19 — Cryptographic operations MUST use approved algorithms.
# ---------------------------------------------------------------------------

APPROVED_HASHES = frozenset(
    {
        "sha256",
        "sha384",
        "sha512",
        "sha3_256",
        "sha3_384",
        "sha3_512",
        "blake2b",
        "blake2s",
    }
)

BANNED_HASHES = frozenset({"md5", "sha1", "md4", "md2", "ripemd160"})


def approved_crypto_hash(algorithm: str) -> None:
    """Enforce INV-19.

    Validate that ``algorithm`` is on the HiveGuard approved hash list.
    Raises :class:`InvariantViolation` if the algorithm is banned or unknown.
    Treat this as a guard at the start of any hashing code path.
    """
    algo = algorithm.lower().replace("-", "_")
    if algo in BANNED_HASHES:
        raise InvariantViolation(
            "INV-19",
            f"Hash algorithm '{algorithm}' is BANNED (cryptographically "
            f"broken or deprecated). Use one of: {sorted(APPROVED_HASHES)}.",
        )
    if algo not in APPROVED_HASHES:
        raise InvariantViolation(
            "INV-19",
            f"Hash algorithm '{algorithm}' is not on the approved list. "
            f"Approved: {sorted(APPROVED_HASHES)}.",
        )


# ---------------------------------------------------------------------------
# Declarative @enforces("INV-XX") dispatch
# ---------------------------------------------------------------------------

_ENFORCEMENT_REGISTRY: Dict[str, Callable] = {
    "INV-01": no_direct_llm,
    "INV-03": memory_wiped_on_exit(),
    "INV-05": bounded_queue(),
    "INV-06": audit_logged(),
    "INV-08": no_sensitive_in_output,
    "INV-15": fail_closed(),
}


def enforces(invariant_id: str) -> Callable:
    """Declarative enforcement dispatch.

    ``@enforces("INV-XX")`` applies the *default* runtime enforcement for
    the named invariant. Use this when you want the spec ID in your code for
    readability. For parameterized enforcement (``shutdown_within``,
    ``rate_limited``, ``sanitize_input``, ``env_credentials_wiped``,
    ``validated_urls``) call the specific decorator directly.

    Example::

        from framework.security.enforcement import enforces

        class MyAgent(BaseAgent):
            @enforces("INV-06")   # audit_logged
            async def process_task(self, task):
                return {"ok": True}

    Raises
    ------
    ValueError
        If ``invariant_id`` is unknown, or if it is documented but has no
        default runtime enforcement (use a specific decorator instead).
    """
    check_invariant(invariant_id)  # raises ValueError on unknown ID

    if invariant_id not in _ENFORCEMENT_REGISTRY:
        raise ValueError(
            f"{invariant_id} is a documented invariant but has no default "
            f"runtime enforcement in the public framework. Use a specific "
            f"decorator (shutdown_within, rate_limited, sanitize_input, "
            f"env_credentials_wiped, validated_urls) or enforce it in your "
            f"application code. The commercial HiveGuard via UBava enforces "
            f"the full spec end-to-end."
        )
    return _ENFORCEMENT_REGISTRY[invariant_id]


__all__ = [
    "InvariantViolation",
    "no_direct_llm",
    "memory_wiped_on_exit",
    "bounded_queue",
    "audit_logged",
    "get_audit_log",
    "clear_audit_log",
    "no_sensitive_in_output",
    "shutdown_within",
    "env_credentials_wiped",
    "sanitize_input",
    "safe_url",
    "validated_urls",
    "fail_closed",
    "RateLimiter",
    "rate_limited",
    "APPROVED_HASHES",
    "BANNED_HASHES",
    "approved_crypto_hash",
    "enforces",
]
