# HiveGuard Security Core

**Open-source security framework for autonomous AI agents.**

Build, deploy, and harden multi-agent systems with production-grade security invariants.

## Want the complete agents?

Pre-built, hardened, production-ready autonomous agents — Scout, Analyst, Fixer, WebScout — with full intelligence, reasoning, and self-healing:

**[hiveguard.ee](https://hiveguard.ee)**

---

## What This Repo Is

This is the **framework** — the skeleton for building your own secure AI agents. It provides:

- Base agent class with health monitoring and graceful shutdown
- Agent lifecycle states (DORMANT → RUNNING → HIBERNATING → DECOMMISSIONED)
- 20 security invariants every agent must satisfy
- Type definitions for tasks, results, and configuration
- Example echo agent to get started

## What This Repo Is Not

This repo does **not** include:
- Pre-built agent intelligence or reasoning engines
- Domain-specific rules or decision logic
- Production agent implementations
- Vault integration or credential management

Those are available as commercial, managed agents at [hiveguard.ee](https://hiveguard.ee).

## Quick Start

```python
from framework.agents.base_agent import BaseAgent
from typing import Any, Dict

class MyAgent(BaseAgent):
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Your logic here
        return {"result": "done"}

agent = MyAgent("my-agent", port=3201)
asyncio.run(agent.start())
```

## Security Invariants

HiveGuard enforces 20 security properties. See `framework/security/invariants.py` for the full list.

## Project Stats

- 16 phases built
- 8 red-teamed
- 1,976 passing tests
- 20 security invariants
- MIT License

## Architecture

```
framework/
├── agents/          # Base agent class
│   └── base_agent.py
├── lifecycle/       # Agent state management
│   └── states.py
├── security/        # Security invariants
│   └── invariants.py
└── types/           # Type definitions
    └── __init__.py
examples/
└── echo_agent.py    # Simple example agent
```

## License

MIT — see [LICENSE](LICENSE)

## Built By

[UBava OÜ](https://ubava.ee) — Privacy-First Relay, Built for Europe.
