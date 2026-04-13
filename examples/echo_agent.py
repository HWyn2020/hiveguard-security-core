"""
Example: Simple Echo Agent

Demonstrates how to build a basic HiveGuard agent.

Usage:
    pip install -e .
    python -m examples.echo_agent
"""

import asyncio
from typing import Any, Dict

from framework.agents.base_agent import BaseAgent


class EchoAgent(BaseAgent):
    """A simple agent that echoes tasks back."""

    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        print(f"[EchoAgent] Received: {task}")
        return {"echo": task, "processed_by": self.agent_id}


if __name__ == "__main__":
    agent = EchoAgent("echo-agent", agent_type="echo", port=3210)
    print("Starting Echo Agent on port 3210...")
    print("Health check: http://localhost:3210/health")
    asyncio.run(agent.start())
