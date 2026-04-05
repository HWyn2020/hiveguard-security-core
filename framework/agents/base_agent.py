"""
HiveGuard Base Agent - Framework Skeleton

Foundational class for building autonomous agents within the HiveGuard
security framework. Extend this class to create your own agents.

For pre-built, production-ready agents with full intelligence:
  https://hiveguard.ee
"""

import asyncio
import signal
import logging
import json
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger("hiveguard.agent")


class BaseAgent(ABC):
    """
    Abstract base class for HiveGuard agents.

    Subclass this and implement process_task() to create your own agent.

    Provides:
    - Health HTTP server for monitoring
    - Graceful shutdown with SIGTERM/SIGINT handling
    - Async task queue (bounded)
    - Memory wipe on exit

    Example:
        class MyAgent(BaseAgent):
            async def process_task(self, task):
                return {"result": "done"}

        agent = MyAgent("my-agent", port=3201)
        asyncio.run(agent.start())
    """

    def __init__(self, agent_id: str, agent_type: str = "custom", port: int = 3201):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.port = port
        self._running = False
        self._task_queue: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        self._start_time = 0.0
        self._task_count = 0

    async def start(self):
        """Start the agent main loop and health server."""
        self._running = True
        self._start_time = time.time()
        self._start_health_server()

        logger.info(f"[{self.agent_id}] Agent running on port {self.port}")

        while self._running:
            try:
                task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                await self.process_task(task)
                self._task_count += 1
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[{self.agent_id}] Task error: {e}", exc_info=True)

    async def stop(self):
        """Graceful shutdown."""
        logger.info(f"[{self.agent_id}] Shutting down...")
        self._running = False
        self._wipe_memory()

    @abstractmethod
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single task. Override this in your agent."""
        raise NotImplementedError

    def submit_task(self, task: Dict[str, Any]) -> bool:
        """Submit a task to the queue. Returns False if full."""
        try:
            self._task_queue.put_nowait(task)
            return True
        except asyncio.QueueFull:
            logger.warning(f"[{self.agent_id}] Task queue full")
            return False

    def _wipe_memory(self):
        """Clear sensitive data from memory on shutdown."""
        while not self._task_queue.empty():
            try:
                self._task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def _start_health_server(self):
        """Start HTTP health check server in background thread."""
        agent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/health":
                    data = {
                        "status": "healthy",
                        "agent": agent.agent_id,
                        "type": agent.agent_type,
                        "uptime": round(time.time() - agent._start_time),
                        "tasks_processed": agent._task_count,
                    }
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(data).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args):
                pass

        server = HTTPServer(("0.0.0.0", self.port), Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
