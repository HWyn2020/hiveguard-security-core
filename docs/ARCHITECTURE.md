# HiveGuard Security Core — Architecture

This document explains how the free public framework is structured and how
its three layers relate to each other and to the commercial HiveGuard.

## The three layers

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   Layer 3  —  Your Agent Code                                      │
│   You write this. Extends BaseAgent, implements process_task,      │
│   decorates methods with @enforces(...) / safe_url / etc.          │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Layer 2  —  Runtime Enforcement  (framework/security/             │
│               enforcement.py)                                      │
│   12 decorators that turn the spec into executable guards:         │
│   @bounded_queue  @audit_logged  @sanitize_input                   │
│   @validated_urls @rate_limited  @fail_closed                      │
│   @shutdown_within  @memory_wiped_on_exit                          │
│   @no_sensitive_in_output  @no_direct_llm                          │
│   @env_credentials_wiped  approved_crypto_hash()                   │
│                                                                    │
│   Violations raise InvariantViolation at runtime.                  │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Layer 1  —  The Spec  (framework/security/invariants.py)         │
│   20 security invariants as a documented checklist.                │
│   INV-01 through INV-20.                                           │
│   Every HiveGuard agent — open or commercial — must satisfy all 20.│
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│   Layer 0  —  The Skeleton  (framework/agents/, lifecycle/, types/)│
│   BaseAgent class, lifecycle state machine, task / result types.   │
│   Zero runtime dependencies. Python stdlib only.                   │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## How a real agent is assembled

```python
from framework.agents.base_agent import BaseAgent
from framework.security.enforcement import (
    bounded_queue,       # Layer 2
    audit_logged,        # Layer 2
    sanitize_input,      # Layer 2
    validated_urls,      # Layer 2
    rate_limited,        # Layer 2
    fail_closed,         # Layer 2
    no_sensitive_in_output,  # Layer 2
    shutdown_within,     # Layer 2
    memory_wiped_on_exit,# Layer 2
)


class MyScoutAgent(BaseAgent):          # Layer 0: skeleton
    @bounded_queue()                    # Layer 2 → proves INV-05 (Layer 1)
    def __init__(self, agent_id, port):
        super().__init__(agent_id, agent_type="scout", port=port)

    @audit_logged()                     # Layer 2 → proves INV-06
    @sanitize_input()                   # Layer 2 → proves INV-11
    async def process_task(self, task):
        return await self.fetch(url=task["url"])

    @rate_limited(max_calls=30, window_seconds=60)  # INV-16
    @validated_urls(arg_name="url")                  # INV-12
    @fail_closed(default_return={"status":"failed"}) # INV-15
    async def fetch(self, url):
        ...  # Layer 3: your code goes here

    @no_sensitive_in_output             # INV-08
    def health_payload(self):
        return {"agent_id": self.agent_id, "running": self._running}

    @shutdown_within(seconds=5)         # INV-09
    @memory_wiped_on_exit()             # INV-03
    async def stop(self):
        ...
```

Each decorator references a specific invariant from Layer 1. At runtime,
violations raise `InvariantViolation(invariant_id, message)` so your tests
and monitors can pinpoint exactly which clause of the contract broke.

See [`examples/monitor_agent.py`](../examples/monitor_agent.py) for a full
working agent that composes 9 decorators together.

## Lifecycle state machine

Agents transition through a validated state machine defined in
[`framework/lifecycle/states.py`](../framework/lifecycle/states.py):

```
   DORMANT ─────────► RUNNING ─────────► HIBERNATING
                        │                      │
                        ├─► PAUSED ◄───────────┤
                        │                      │
                        ├─► FROZEN ◄──► ESCALATED
                        │                      │
                        ├─► RESTING             │
                        │                      │
                        └─► DECOMMISSIONED ◄────┘   (terminal)
```

- `LifecycleManager` enforces valid transitions — invalid ones return
  `False` without mutating state.
- Register listeners with `on_transition(callback)` to react to state
  changes (e.g. audit logging, metrics).
- `DECOMMISSIONED` is terminal — no transitions out of it.

## Why the framework has zero runtime dependencies

HiveGuard ships with stdlib only because:

1. **Supply-chain security.** Every dependency is a potential vector.
   A security framework with 47 transitive deps is a contradiction.
2. **Embeddability.** You can drop the framework into any Python project
   — including locked-down corporate environments — without negotiating a
   dependency tree with infosec.
3. **Stability.** stdlib APIs change on a Python-version cadence, not a
   PyPI-author cadence. The 0.1.0 release will still work in 5 years.

The only `[dev]` dependency is `pytest`. That's it.

## Relationship to the commercial HiveGuard

This repository is the **open-source security core**. It contains:

- The 20-invariant spec (the contract)
- 12 runtime-enforceable decorators (the subset checkable without private IP)
- Base class, lifecycle, types
- Two example agents and 129 tests

The **commercial HiveGuard** — Scout, Analyst, Fixer, WebScout agents, Bee
Dance Protocol, Tumbler Vaults, jurisdiction-aware autonomy, the UBava
Privacy Relay, and the full agent intelligence — is **private**. It enforces
the full 20-invariant spec end-to-end, including the 8 invariants that
can't be verified in a pure-Python framework skeleton:

| Invariant | Why it's unenforceable in the public skeleton |
|---|---|
| INV-02 (PII tokenization) | Requires a private PII detector + tokenizer |
| INV-04 (inter-agent auth/crypto) | Requires the Bee Dance Protocol implementation |
| INV-07 (privilege escalation) | Requires a role/capability model |
| INV-13 (decision memory integrity) | Requires a signed memory store |
| INV-14 (cross-agent data scoping) | Requires a multi-agent runtime |
| INV-17 (no PII in persistent storage) | Requires a PII classifier in the data layer |
| INV-18 (container restart policy preservation) | Requires infrastructure context |
| INV-20 (jurisdiction-aware autonomy) | Requires the private JurisdictionEngine |

If you need any of those enforced at runtime, the managed HiveGuard agents
ship with them. See [ubava.ee](https://ubava.ee).

## Testing philosophy

Every decorator in `framework/security/enforcement.py` has both:

1. **A positive test** — compliant code passes
2. **A negative test** — violating code raises `InvariantViolation` with
   the correct `invariant_id`

`tests/test_enforcement.py` has 70 tests. `tests/test_monitor_agent.py`
has 11 integration tests that prove the decorators **compose cleanly** on a
realistic agent shape (9 decorators stacked on a single class).

Total framework test count: **129 pytest tests, 100% green**, runtime
measured in milliseconds:

```
============================= 129 passed in 0.22s =============================
```

If you're building an agent on HiveGuard and your tests take minutes instead
of milliseconds, something is wrong with your test design — not the
framework.
