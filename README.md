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

HiveGuard defines **20 security properties** every agent must satisfy. They live in `framework/security/invariants.py` as a documented checklist — the **HiveGuard security spec**.

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

## Runtime Enforcement

The 20 invariants are not just documentation. **12 of them are runtime-enforceable decorators** shipping in `framework/security/enforcement.py`. Apply them to your agent methods, and the framework raises `InvariantViolation` the moment you violate the contract. Build any agent you want on top — HiveGuard guarantees the security floor.

### Quick example

```python
from framework.agents.base_agent import BaseAgent
from framework.security.enforcement import (
    audit_logged,         # INV-06
    bounded_queue,        # INV-05
    fail_closed,          # INV-15
    memory_wiped_on_exit, # INV-03
    no_sensitive_in_output, # INV-08
    rate_limited,         # INV-16
    sanitize_input,       # INV-11
    shutdown_within,      # INV-09
    validated_urls,       # INV-12
)


class MyAgent(BaseAgent):
    @bounded_queue()  # INV-05 — raises if you forget maxsize
    def __init__(self, agent_id, port):
        super().__init__(agent_id, agent_type="custom", port=port)

    @audit_logged()   # INV-06 — every call recorded
    @sanitize_input() # INV-11 — control chars stripped, depth capped
    async def process_task(self, task):
        return await self.fetch(url=task["url"])

    @rate_limited(max_calls=30, window_seconds=60)   # INV-16
    @validated_urls(arg_name="url")                  # INV-12 — SSRF blocked
    @fail_closed(default_return={"status": "failed"}) # INV-15
    async def fetch(self, url):
        ...  # your network code

    @no_sensitive_in_output  # INV-08 — scrubs api_key/password/token from output
    def health_payload(self):
        return {"agent_id": self.agent_id, "running": self._running}

    @shutdown_within(seconds=5)  # INV-09 — budget enforced
    @memory_wiped_on_exit()      # INV-03 — queue must be empty after return
    async def stop(self):
        self._running = False
```

### Enforceable in the public framework

| Invariant | Decorator | What it enforces |
|---|---|---|
| INV-01 | `no_direct_llm` | No LLM SDK imports in function globals (anthropic / openai / google / etc.) |
| INV-03 | `memory_wiped_on_exit()` | Task queue is empty after shutdown returns |
| INV-05 | `bounded_queue()` | `_task_queue.maxsize > 0` after `__init__` |
| INV-06 | `audit_logged()` | Every call appends to an audit sink (timestamp, args, result, success flag) |
| INV-08 | `no_sensitive_in_output` | Recursive scan for keys matching `api_key` / `password` / `secret` / `token` / `credential` / `private_key` / `session_id` / `auth` |
| INV-09 | `shutdown_within(seconds)` | Async shutdown wrapped in `asyncio.wait_for`, raises on timeout |
| INV-10 | `env_credentials_wiped(prefixes)` | No env vars matching the prefixes remain after shutdown |
| INV-11 | `sanitize_input(max_depth)` | Control chars stripped from strings, nesting depth capped, non-JSON types rejected |
| INV-12 | `validated_urls` / `safe_url()` | Blocks loopback, private ranges, link-local, cloud metadata, non-HTTP(S) schemes |
| INV-15 | `fail_closed(default_return)` | Exceptions downgraded to a failure sentinel (sync or async) |
| INV-16 | `rate_limited(N, window)` | Per-function sliding-window limiter |
| INV-19 | `approved_crypto_hash(algo)` | Allowlist: SHA-2/3, BLAKE2 — blocks MD5, SHA-1, MD4, RIPEMD-160 |

The remaining 8 invariants (INV-02, 04, 07, 13, 14, 17, 18, 20) are documented in the spec but can't be auto-enforced in a pure-Python skeleton — they require domain-specific context (jurisdiction rules, inter-agent auth, cross-agent scoping). The commercial HiveGuard via UBava enforces the full 20 end-to-end.

### Declarative @enforces("INV-XX")

For invariants with a default enforcement, you can use the spec ID directly:

```python
from framework.security.enforcement import enforces

class MyAgent(BaseAgent):
    @enforces("INV-06")  # resolves to audit_logged()
    async def process_task(self, task):
        return {"ok": True}
```

`@enforces` validates the ID against the spec and raises `ValueError` if the invariant is unknown or not enforceable in the public skeleton. Use the specific parameterized decorators (`shutdown_within`, `rate_limited`, `sanitize_input`, `env_credentials_wiped`, `validated_urls`) when you need to tune parameters.

### Second example agent

See `examples/monitor_agent.py` for a complete URL-monitoring agent that stacks nine decorators together — `bounded_queue`, `audit_logged`, `sanitize_input`, `rate_limited`, `validated_urls`, `fail_closed`, `no_sensitive_in_output`, `shutdown_within`, `memory_wiped_on_exit`. It's the reference for how real-world enforcement composes.

Run it:

```bash
python -m examples.monitor_agent
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
│   │   ├── invariants.py        # 20 security invariants (the spec)
│   │   └── enforcement.py       # Runtime decorators (12 enforceable)
│   └── types/
│       └── __init__.py          # Task, TaskResult, AgentConfig, AgentType
├── examples/
│   ├── echo_agent.py            # Minimal agent demo
│   └── monitor_agent.py         # URL monitor stacking 9 enforcement decorators
├── tests/                       # pytest suite
│   ├── conftest.py
│   ├── test_base_agent.py
│   ├── test_lifecycle.py
│   ├── test_invariants.py
│   ├── test_enforcement.py      # 70 tests covering every decorator
│   ├── test_types.py
│   ├── test_echo_agent.py
│   └── test_monitor_agent.py    # Integration tests for monitor example
├── pyproject.toml               # PEP 621 metadata, pip-installable
├── SECURITY.md                  # Responsible disclosure policy
├── CONTRIBUTING.md               # Dev setup, PR rules, scope guidelines
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
