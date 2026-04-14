# Changelog

All notable changes to `hiveguard-security-core` are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/) once it reaches `1.0.0`.

## [Unreleased]

### Added

- **GitHub Actions CI** (`.github/workflows/test.yml`) running `pytest` on
  Python 3.9 – 3.13 across Ubuntu, macOS, and Windows. Also verifies zero
  runtime dependencies and that example agents import cleanly.
- **README badges** — CI status, license, Python versions, test count.
- **`docs/ARCHITECTURE.md`** — deeper explanation of the framework / spec /
  enforcement layer split.
- **`CHANGELOG.md`** (this file).

## [0.1.0] — 2026-04-13

First public release of the HiveGuard security framework.

### Added

#### Framework core

- `framework/agents/base_agent.py` — Abstract `BaseAgent` with async event
  loop, HTTP health endpoint, graceful SIGTERM shutdown, bounded task queue,
  memory wipe on exit.
- `framework/lifecycle/states.py` — 8-state `AgentState` enum
  (DORMANT → RUNNING → HIBERNATING → PAUSED → FROZEN → ESCALATED → RESTING →
  DECOMMISSIONED) with a validated transition table and `LifecycleManager`
  listener hooks.
- `framework/security/invariants.py` — 20 documented security invariants
  every HiveGuard agent must satisfy. The **spec**.
- `framework/types/__init__.py` — `Task`, `TaskResult`, `AgentConfig`,
  `AgentType` dataclasses / enum.

#### Runtime enforcement layer

- `framework/security/enforcement.py` — 12 runtime-enforceable decorators
  that turn invariants into executable guards. Violations raise
  `InvariantViolation` with the invariant id.
  - `no_direct_llm` (INV-01)
  - `memory_wiped_on_exit` (INV-03)
  - `bounded_queue` (INV-05)
  - `audit_logged` (INV-06)
  - `no_sensitive_in_output` (INV-08)
  - `shutdown_within` (INV-09)
  - `env_credentials_wiped` (INV-10)
  - `sanitize_input` (INV-11)
  - `validated_urls` / `safe_url()` (INV-12)
  - `fail_closed` (INV-15)
  - `rate_limited` / `RateLimiter` (INV-16)
  - `approved_crypto_hash` (INV-19)
- Declarative `@enforces("INV-XX")` dispatcher that validates invariant ids
  against the spec and raises on unknown or unenforceable ids.

#### Examples

- `examples/echo_agent.py` — minimal agent demonstrating how to extend
  `BaseAgent`.
- `examples/monitor_agent.py` — URL-monitoring agent that composes 9
  enforcement decorators in a realistic shape.

#### Tests

- **129 pytest tests** covering the full framework. 100% green.
  - `tests/test_base_agent.py` (11 tests)
  - `tests/test_lifecycle.py` (14 tests)
  - `tests/test_invariants.py` (9 tests)
  - `tests/test_enforcement.py` (70 tests — positive + negative coverage
    for every decorator)
  - `tests/test_types.py` (10 tests)
  - `tests/test_echo_agent.py` (4 tests)
  - `tests/test_monitor_agent.py` (11 tests)

#### Packaging

- `pyproject.toml` (PEP 621) — package `hiveguard-security-core`, Python 3.9+,
  zero runtime dependencies, pytest as `[dev]` extra.
- `pip install -e ".[dev]"` works out of the box.

#### Docs

- `README.md` — overview, installation, quick start, runtime enforcement
  table, security invariant examples, architecture tree.
- `SECURITY.md` — responsible disclosure policy, supported versions,
  response timeline.
- `CONTRIBUTING.md` — ground rules, dev setup, PR guidelines, scope.

### Notes

- HiveGuard Security Core is the **open-source skeleton**. The commercial
  autonomous agent implementations — Scout, Analyst, Fixer, WebScout, Bee
  Dance Protocol, Tumbler Vaults, jurisdiction-aware autonomy — ship as
  managed agents via [UBava](https://ubava.ee) and are **not** in this
  repository. The 8 invariants that can't be enforced in a pure-Python
  skeleton (INV-02, 04, 07, 13, 14, 17, 18, 20) are enforced end-to-end in
  the commercial product.

[Unreleased]: https://github.com/HWyn2020/hiveguard-security-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HWyn2020/hiveguard-security-core/releases/tag/v0.1.0
