"""
Example: URL Monitor Agent

A second-tier example that composes several HiveGuard enforcement decorators
to build a real, safe URL-monitoring agent skeleton. Demonstrates how the
framework's runtime invariants snap together.

What it shows
-------------

- ``@bounded_queue`` (INV-05) — task queue has a maxsize, no memory bombs
- ``@audit_logged`` (INV-06) — every check is recorded to an audit sink
- ``@no_sensitive_in_output`` (INV-08) — health payload scrubbed
- ``@sanitize_input`` (INV-11) — task payloads stripped of control chars
- ``@validated_urls`` (INV-12) — SSRF / internal-IP blocked
- ``@fail_closed`` (INV-15) — exceptions downgrade to a failure sentinel
- ``@rate_limited`` (INV-16) — outbound fetches capped
- ``@shutdown_within`` (INV-09) — shutdown has a 5-second budget
- ``@memory_wiped_on_exit`` (INV-03) — shutdown must empty the queue

This agent does NOT actually fetch URLs — network I/O is left as an exercise
for the reader. The focus is showing how the enforcement layer composes.

Run it::

    python -m examples.monitor_agent
"""

import asyncio
from typing import Any, Dict, List

from framework.agents.base_agent import BaseAgent
from framework.security.enforcement import (
    audit_logged,
    bounded_queue,
    fail_closed,
    memory_wiped_on_exit,
    no_sensitive_in_output,
    rate_limited,
    sanitize_input,
    shutdown_within,
    validated_urls,
)


class MonitorAgent(BaseAgent):
    """Monitors a list of URLs for changes, enforcing HiveGuard invariants.

    The agent accepts tasks of shape ``{"url": "...", "label": "..."}`` and
    "checks" each URL (the actual fetch is stubbed out in ``_fetch``).
    Every invariant below is enforced at runtime — violations raise
    ``InvariantViolation``.
    """

    @bounded_queue()  # INV-05
    def __init__(self, agent_id: str = "monitor-1", port: int = 3220):
        super().__init__(agent_id, agent_type="monitor", port=port)
        self._findings: List[Dict[str, Any]] = []

    @audit_logged()  # INV-06
    @sanitize_input()  # INV-11
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the task shape and dispatch to the URL checker."""
        if "url" not in task:
            return {"ok": False, "error": "missing 'url' field"}
        label = task.get("label", "unlabeled")
        outcome = await self.check_url(url=task["url"])
        self._findings.append(
            {"label": label, "url": task["url"], "outcome": outcome}
        )
        return {"ok": True, "label": label, "outcome": outcome}

    @rate_limited(max_calls=30, window_seconds=60.0)  # INV-16
    @validated_urls(arg_name="url")  # INV-12
    @fail_closed(default_return={"status": "failed", "reason": "exception"})  # INV-15
    async def check_url(self, url: str) -> Dict[str, Any]:
        """Stubbed URL check — returns a synthetic OK payload.

        In a real agent this would perform the outbound request. The
        decorators above handle rate limiting, SSRF protection, and
        fail-closed behavior before control ever reaches this body.
        """
        fetched = await self._fetch(url)
        return {"status": "ok", "bytes": fetched}

    async def _fetch(self, url: str) -> int:
        """Placeholder for real network I/O — returns a stub byte count."""
        await asyncio.sleep(0)  # yield to the loop
        return len(url) * 10

    @no_sensitive_in_output  # INV-08
    def health_payload(self) -> Dict[str, Any]:
        """Return a safe health/status report, scrubbed of credentials."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "findings_count": len(self._findings),
            "queue_depth": self._task_queue.qsize(),
            "running": self._running,
        }

    @shutdown_within(seconds=5.0)  # INV-09
    @memory_wiped_on_exit()  # INV-03
    async def stop(self) -> None:
        """Graceful shutdown with a 5-second budget and queue wipe assertion."""
        self._running = False
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break


if __name__ == "__main__":

    async def _demo() -> None:
        agent = MonitorAgent("monitor-demo", port=0)
        print("Health (safe):", agent.health_payload())

        # Happy path
        result = await agent.process_task(
            {"url": "https://example.com/", "label": "example"}
        )
        print("OK task:", result)

        # Safe shutdown
        agent._task_queue.put_nowait({"stub": 1})
        await agent.stop()
        print("Stopped. queue size:", agent._task_queue.qsize())

    asyncio.run(_demo())
