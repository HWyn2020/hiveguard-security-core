# Security Policy

HiveGuard Security Core is a framework for *building* secure autonomous AI agents. Security is the product. If you find a weakness, we want to hear from you.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security problems.**

Email **security@ubava.ee** (or **info@ubava.ee** if the security address is unavailable) with:

- A clear description of the issue
- The affected module(s) and version
- Reproduction steps or a proof-of-concept if possible
- Your assessment of impact (confidentiality / integrity / availability)
- Whether you want public credit after the fix lands

We will acknowledge receipt within **72 hours**. If you do not hear back in that window, follow up — do not assume the report was received.

## Scope

### In scope

Anything in this repository — the public `hiveguard-security-core` framework:

- `framework/agents/base_agent.py` — base class, health server, graceful shutdown, memory wipe
- `framework/lifecycle/states.py` — state machine + transition table
- `framework/security/invariants.py` — the 20-invariant spec
- `framework/security/enforcement.py` — runtime enforcement decorators (`@enforces`, `sanitize_input`, `validated_urls`, etc.)
- `framework/types/` — type definitions
- `examples/echo_agent.py`, `examples/monitor_agent.py`

Examples of in-scope findings:

- Framework invariants that can be bypassed without raising `InvariantViolation`
- Decorator stacks that silently drop violations
- `safe_url()` false negatives (URLs that should be blocked but aren't)
- `sanitize_input()` depth or escape-sequence bypasses
- Memory leaks that survive `stop()` with `@memory_wiped_on_exit`
- Any exploit that lets an attacker bypass the 20-invariant contract

### Out of scope

- **The commercial HiveGuard agents** (Scout, Analyst, Fixer, WebScout) available via [ubava.ee](https://ubava.ee) — these have their own private disclosure channel. Contact **security@ubava.ee** and we will route the report to the right team.
- **The UBava Relay** — reports about the privacy relay, VHH air-lock, PII cascade, or Docker cascade infrastructure should also go to **security@ubava.ee**.
- **Dependencies** — we have zero runtime dependencies. Dev-only dependencies (pytest) should be reported upstream to the respective project.
- **Attacks that require local machine compromise** already (root on the machine running the framework).
- **Social engineering or physical attacks.**

## Response Timeline

After acknowledging your report, we aim to:

| Milestone | Target |
|---|---|
| Initial assessment + severity triage | within 7 days |
| Remediation plan shared with reporter | within 14 days |
| Fix merged to `main` | within 30 days (critical) / 90 days (non-critical) |
| Coordinated disclosure | at fix release, or 90 days after report, whichever is sooner |

We practice **coordinated disclosure**: we ask reporters not to publish details until a fix is live, and in exchange we commit to a concrete timeline.

## Supported Versions

This is an early-stage framework. During the `0.x` series, only the **latest minor release** receives security fixes.

| Version | Supported |
|---|---|
| 0.1.x | ✅ |
| older | ❌ |

When `1.0.0` ships, the previous major version will continue to receive critical security fixes for six months.

## Acknowledgments

Reporters who follow responsible disclosure will be credited in the commit that fixes the issue and in the release notes, unless they request anonymity.

## Relationship to the Commercial Product

HiveGuard Security Core is the **open-source spec and runtime enforcement layer**. The 20 invariants in `framework/security/invariants.py` describe the security contract every HiveGuard agent — open or commercial — must satisfy.

The commercial agents behind the UBava Relay enforce the *full* spec end-to-end, including the 8 invariants that can't be verified in a pure-Python framework skeleton (jurisdiction-aware autonomy, inter-agent authentication, BDP integrity, etc.). If your research touches those commercial components, the same **security@ubava.ee** address reaches the team that owns them.

---

Thank you for helping us keep autonomous agents safe. 🐝
