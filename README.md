# HiveGuard Security Core

**Open-source security framework for autonomous AI agents.**

The skeleton for building secure multi-agent systems with production-grade security invariants. Released under the **MIT License** — free to fork, modify, study, audit, and build on.

---

## This Repo vs. The Complete HiveGuard

This repository contains the **security framework only** — the open-source skeleton that lets developers understand the architecture, build their own agents, and verify the security model.

The **complete HiveGuard autonomous agent system** — including the Bee Dance Protocol (BDP), Tumbler Vaults, vault integration, jurisdiction-aware autonomy, self-healing Fixer logic, and the full agent intelligence — is **not** in this repo. That IP remains private and is delivered as a managed service.

### Want the complete agents?

Two ways to deploy the production system:

**1. Managed via UBava Relay** *(best for EU users running AI workflows)*
Routes all LLM calls through UBava's privacy relay — Claude, GPT, Gemini, Grok — with full GDPR / EU AI Act compliance via the VHH Privacy Air-Lock. Token usage + relay markup.

**2. HiveGuard Standalone Subscription** *(best for non-AI EU workflows or any non-EU deployment)*
Self-hosted autonomous agents on your own infrastructure. The Phase 13 JurisdictionEngine automatically blocks AI calls for EU subscribers (so you can't accidentally violate the AI Act). Outside the EU, no AI restrictions. Flat monthly subscription.

Both options live at **[ubava.ee](https://ubava.ee)**.

---

## What's In This Repo

This is the **framework** — the skeleton for building your own secure agents:

- **Base agent class** (`framework/agents/base_agent.py`) — async event loop, HTTP health endpoint, SIGTERM graceful shutdown, bounded task queue, memory wipe on exit
- **Agent lifecycle states** (`framework/lifecycle/states.py`) — 8 states (DORMANT → RUNNING → HIBERNATING → PAUSED → FROZEN → ESCALATED → RESTING → DECOMMISSIONED) with a validated transition table and listener hooks
- **20 security invariants** (`framework/security/invariants.py`) — the documented contract every HiveGuard agent must satisfy. This is the **spec**.
- **Type definitions** (`framework/types/__init__.py`) — Task, TaskResult, AgentConfig, AgentType
- **Example echo agent** (`examples/echo_agent.py`) — a minimal agent showing how to extend `BaseAgent`
- **Test suite** (`tests/`) — pytest tests covering the framework above

## What's NOT In This Repo

- Pre-built agent intelligence or reasoning engines
- Domain-specific decision logic (Scout, Analyst, Fixer, WebScout brains)
- The Bee Dance Protocol (BDP) implementation
- Tumbler Vaults — split-key crypto, self-destructing credential proxies
- Vault integration or credential management
- Jurisdiction-aware autonomy rule engine
- HiveNet inter-hive marketplace
- UBava Relay infrastructure
- Any code that touches PII or production credentials

These live in the private repo and ship as managed agents through [ubava.ee](https://ubava.ee).

---

## Installation

Requires Python 3.9+. Zero runtime dependencies — pure stdlib.

### From source

```bash
git clone https://github.com/HWyn2020/hiveguard-security-core
cd hiveguard-security-core
pip install -e ".[dev]"
```

The `-e` (editable) install lets you modify the framework and have your changes picked up immediately. The `[dev]` extra adds `pytest` for running the test suite.

---

## Quick Start

Build your own agent by extending `BaseAgent` and implementing `process_task`:

```python
import asyncio
from typing import Any, Dict

from framework.agents.base_agent import BaseAgent


class MyAgent(BaseAgent):
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Your logic here
        return {"result": "done"}


if __name__ == "__main__":
    agent = MyAgent("my-agent", agent_type="custom", port=3201)
    asyncio.run(agent.start())
```

The framework gives you:
- A `/health` HTTP endpoint on the chosen port
- Graceful SIGTERM/SIGINT shutdown
- A bounded async task queue (won't OOM under load)
- Memory wipe on shutdown (no sensitive data left behind)

Run the included example agent:

```bash
python -m examples.echo_agent
```

Then in another terminal:

```bash
curl http://localhost:3210/health
```

---

## Run the Tests

The framework ships with a real pytest suite. After installing with `[dev]`:

```bash
pytest -v
```

You should see all tests pass green. The suite covers:

- Base agent construction, task submission, queue bounds, memory wipe, shutdown
- Lifecycle state machine — every valid transition, every rejected transition, listener notification, terminal-state behavior
- All 20 security invariants — inventory, lookup, copy semantics
- Type definitions — Task, TaskResult, AgentConfig, AgentType
- Example echo agent integration

---

## Security Invariants

HiveGuard defines **20 security properties** every agent must satisfy. They live in `framework/security/invariants.py` as a documented checklist. Treat this as the **HiveGuard security spec** — anyone building autonomous agents on top of this framework should design against these invariants.

A few examples:

- **INV-01**: Agents MUST NOT call LLM APIs directly. All calls route through the designated entry point.
- **INV-03**: Agent memory MUST be wiped on shutdown.
- **INV-15**: Failed operations MUST fail closed, not fail open.
- **INV-20**: Agents MUST respect jurisdiction-aware autonomy constraints.

The full list:

```python
from framework.security.invariants import list_invariants

for inv in list_invariants():
    print(inv)
```

---

## Project Architecture

```
hiveguard-security-core/
├── framework/
│   ├── agents/
│   │   └── base_agent.py        # Abstract BaseAgent + health server + shutdown
│   ├── lifecycle/
│   │   └── states.py            # AgentState enum + LifecycleManager
│   ├── security/
│   │   └── invariants.py        # 20 security invariants (the spec)
│   └── types/
│       └── __init__.py          # Task, TaskResult, AgentConfig, AgentType
├── examples/
│   └── echo_agent.py            # Minimal agent demo
├── tests/                       # pytest suite
│   ├── conftest.py
│   ├── test_base_agent.py
│   ├── test_lifecycle.py
│   ├── test_invariants.py
│   ├── test_types.py
│   └── test_echo_agent.py
├── pyproject.toml               # PEP 621 metadata, pip-installable
├── LICENSE                      # MIT
└── README.md
```

---

## License

**MIT** — see [LICENSE](LICENSE).

You're free to use, modify, and distribute this framework, including commercially. Attribution via the copyright notice is all that's required.

---

## Learn More

- **Marketing site:** [hiveguard.ee](https://hiveguard.ee)
- **Managed agents & relay:** [ubava.ee](https://ubava.ee)
- **EU compliance posture:** [ubava.ee/legal-compliance](https://ubava.ee/legal-compliance)

## Built By

[UBava OÜ](https://ubava.ee) — Privacy-First Relay, Built for Europe.
