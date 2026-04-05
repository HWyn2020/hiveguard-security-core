"""
HiveGuard Security Invariants

20 security properties every HiveGuard agent must satisfy.
Use as a checklist when building your agents.
"""

SECURITY_INVARIANTS = [
    "INV-01: Agents MUST NOT call LLM APIs directly. All calls route through the designated entry point.",
    "INV-02: PII MUST be tokenized before leaving the client infrastructure.",
    "INV-03: Agent memory MUST be wiped on shutdown.",
    "INV-04: Inter-agent communication MUST be authenticated and encrypted.",
    "INV-05: Task queues MUST be bounded to prevent memory exhaustion.",
    "INV-06: Agent decisions MUST be logged for audit.",
    "INV-07: Agents MUST NOT escalate privileges beyond their assigned role.",
    "INV-08: Health endpoints MUST NOT expose sensitive data.",
    "INV-09: Graceful shutdown MUST handle SIGTERM within 10 seconds.",
    "INV-10: Agent credentials MUST be wiped from process environment on shutdown.",
    "INV-11: All user input MUST be sanitized before processing.",
    "INV-12: Agents MUST validate URL targets (no SSRF, no internal IPs).",
    "INV-13: Decision memory MUST be integrity-protected.",
    "INV-14: Cross-agent data access MUST be scoped to the owning agent.",
    "INV-15: Failed operations MUST fail closed, not fail open.",
    "INV-16: Rate limiting MUST be enforced on all external calls.",
    "INV-17: Agents MUST NOT store PII in any persistent storage.",
    "INV-18: Container restart MUST NOT reset security policies.",
    "INV-19: All cryptographic operations MUST use approved algorithms.",
    "INV-20: Agents MUST respect jurisdiction-aware autonomy constraints.",
]


def check_invariant(invariant_id: str) -> str:
    for inv in SECURITY_INVARIANTS:
        if inv.startswith(invariant_id):
            return inv
    raise ValueError(f"Unknown invariant: {invariant_id}")


def list_invariants() -> list:
    return SECURITY_INVARIANTS.copy()
