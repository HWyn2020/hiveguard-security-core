"""
Example: Simple Echo Agent

Demonstrates how to build a basic HiveGuard agent.

Usage:
    python examples/echo_agent.py
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from framework.agents.base_agent import BaseAgent
from typing import Any, Dict


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
