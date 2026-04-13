# HiveGuard Security Core

**Open-source security framework for autonomous AI agents.**

Build, deploy, and harden your own multi-agent systems with production-grade security invariants.
Released under the **MIT License** — free to fork, modify, study, and build on.

---

## This Repo vs. The Complete HiveGuard

This repository contains the **security framework only** — the open-source skeleton that lets developers understand the architecture, build their own agents, and verify the security model.

The **complete HiveGuard autonomous agent system** — including the Bee Dance Protocol (BDP), Tumbler Vaults, vault integration, jurisdiction-aware autonomy, self-healing Fixer logic, and the full agent intelligence — is **not** in this repo. That IP remains private and is delivered as a managed service through the UBava privacy relay.

### Want the complete agents on day one?

Go to **[ubava.ee](https://ubava.ee)** and:

1. Create an account (no subscription)
2. Submit two forms of payment for verification
3. Prepay €50 to your token balance
4. Pay-as-you-go from there — no lock-in

Agents run on **Claude, Gemini, Grok, and ChatGPT** out of the gate, with full privacy enforcement provided by the UBava relay.

---

## What's In This Repo

This is the **framework** — the skeleton for building your own secure AI agents. It provides:

- Base agent class with health monitoring and graceful shutdown
- Agent lifecycle states (DORMANT → RUNNING → HIBERNATING → DECOMMISSIONED)
- 20 security invariants every agent must satisfy
- Type definitions for tasks, results, and configuration
- Example echo agent to get started

## What's Not In This Repo

- Pre-built agent intelligence or reasoning engines
- Domain-specific rules or decision logic
- Production agent implementations
- Bee Dance Protocol (BDP) internals
- Tumbler Vault cryptography and split-key mechanics
- Vault integration or credential management
- Jurisdiction-aware autonomy rules
- Relay infrastructure

Those live in the private repo and are available as managed agents through [ubava.ee](https://ubava.ee).

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

- 15 phases built
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

**MIT** — see [LICENSE](LICENSE).

You're free to use, modify, and distribute this framework, including commercially. Attribution via the copyright notice is all that's required.

## Learn More

- **Marketing site:** [hiveguard.ee](https://hiveguard.ee)
- **Managed agents & relay signup:** [ubava.ee](https://ubava.ee)
- **EU compliance posture:** [ubava.ee/legal-compliance](https://ubava.ee/legal-compliance)

## Built By

[UBava OÜ](https://ubava.ee) — Privacy-First Relay, Built for Europe.
