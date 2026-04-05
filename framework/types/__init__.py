"""HiveGuard type definitions for agent development."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum


class AgentType(Enum):
    SCOUT = "scout"
    ANALYST = "analyst"
    FIXER = "fixer"
    WEB_SCOUT = "web-scout"
    CUSTOM = "custom"


@dataclass
class Task:
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class AgentConfig:
    agent_id: str
    agent_type: AgentType
    port: int = 3201
    max_queue_size: int = 10_000
    health_check_interval: int = 30
