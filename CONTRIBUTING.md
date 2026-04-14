# Contributing to HiveGuard Security Core

Thanks for wanting to help. HiveGuard is a small, opinionated framework — we want it to stay that way, so there are a few ground rules before you open a PR.

## What this repo is

This repo is the **public security core framework** — the MIT-licensed skeleton that defines what a secure autonomous agent must look like. It contains:

- A base agent class (`framework/agents/base_agent.py`)
- An 8-state lifecycle machine (`framework/lifecycle/states.py`)
- The 20-invariant security spec (`framework/security/invariants.py`)
- Runtime enforcement decorators (`framework/security/enforcement.py`)
- Core type definitions (`framework/types/`)
- Two example agents (`examples/`)
- A pytest test suite (`tests/`)

It contains **zero runtime dependencies** and targets Python 3.9+.

## What this repo is NOT

The commercial HiveGuard agent implementations — Scout, Analyst, Fixer, WebScout — are **not** in this repo and never will be. The Bee Dance Protocol, Tumbler Vaults, jurisdiction engine, and the full agent intelligence live in a private repository and ship as managed agents via [ubava.ee](https://ubava.ee).

**Contributions that attempt to re-implement those proprietary components are out of scope** and will be politely declined. If you want to build *your own* intelligence layer on top of this framework, great — that's exactly what the skeleton is for. Just don't try to make this repo into a competitor to the commercial product.

## Ground rules

1. **No runtime dependencies.** Pure Python stdlib only. `[dev]` extras may pull pytest; nothing else.
2. **Tests are mandatory.** Every new decorator, every new helper, every new lifecycle transition — add real pytest coverage. We enforce `pytest -v` green in CI (coming soon).
3. **Don't break the 20-invariant spec.** The invariant list in `framework/security/invariants.py` is a contract with downstream users. Adding a 21st invariant is a discussion, not a PR. Removing one is a breaking change.
4. **No proprietary code dumps.** If you've seen the commercial HiveGuard internals, don't port them here. We both know.
5. **Python 3.9+ compatibility.** Use `from __future__ import annotations` for forward references rather than quoting strings.
6. **Type hints everywhere.** New code must be type-hinted. `Any` is allowed as a last resort.
7. **Docstrings on public API.** Every public function, class, and decorator gets a short docstring explaining *what* and *why*. Reference the invariant ID where applicable.

## Development setup

```bash
git clone https://github.com/HWyn2020/hiveguard-security-core
cd hiveguard-security-core
pip install -e ".[dev]"
pytest -v
```

Editable install means your changes are picked up immediately without reinstalling.

## Running the tests

```bash
# Full suite
pytest -v

# Just the enforcement layer
pytest tests/test_enforcement.py -v

# Just a single test class
pytest tests/test_lifecycle.py::TestValidTransitions -v

# Run the example agents
python -m examples.echo_agent
python -m examples.monitor_agent
```

The entire suite should run in well under a second. If a test takes more than ~100ms, something is probably wrong.

## Opening a PR

1. **One concern per PR.** A bug fix and a new feature don't belong in the same pull request.
2. **Write the test first.** Or at least write it. Failing PRs without new test coverage get bounced.
3. **Keep the diff small.** 200 lines is a normal PR. 2,000 lines is a red flag.
4. **Describe the invariant you're touching.** If your change affects INV-XX behavior, say so in the PR body.
5. **Update the README** if you add a public API.
6. **Be ready to iterate.** Reviewers will ask for changes. That's the process.

## Reporting security issues

Do **not** open a public issue for security problems. See [SECURITY.md](SECURITY.md) for the private disclosure process.

## Code style

- PEP 8, 4-space indents
- Line length: ~100 characters soft limit, 120 hard limit
- Double quotes for strings by default
- Imports sorted: stdlib, third-party, local (we only have stdlib + local)
- No linter is enforced in CI yet — just be reasonable

## Questions?

- **Framework questions:** Open a GitHub discussion or issue
- **Commercial / managed agents / pricing:** [ubava.ee](https://ubava.ee)
- **Security disclosures:** security@ubava.ee

Thanks for helping us build a safer autonomous-agent ecosystem. 🐝
