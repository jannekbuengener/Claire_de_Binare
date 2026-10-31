"""Claire-owned policies that must stay outside Agent Brain.

Agent Brain supplies context/evidence. Claire remains product/runtime authority
for trading, live readiness, and Echtgeld boundaries.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode

# Claire safety posture for #13 — never grant live/trading authority via cutover.
CLAIRE_CONSUMER_GUARDRAILS: tuple[str, ...] = (
    "Agent Brain output is orientation/evidence only.",
    "LR remains NO-GO; no Live-Go.",
    "No Echtgeld-Go.",
    "No productive Agent Memory writes via this consumer path.",
    "No automatic trading, order, or risk action from brain responses.",
)

_FORBIDDEN_LIVE_SCOPES = frozenset(
    {
        "live",
        "live-trade",
        "echtgeld",
        "real-money",
        "production-trade",
    }
)


def assert_claire_consumer_policy(
    *,
    target_scope: str,
    tags: Sequence[str] | None = None,
    allow_memory_writes: bool = False,
) -> dict[str, Any]:
    """Fail closed on Claire-specific unsafe scopes; return policy envelope."""
    scope = (target_scope or "").strip().lower()
    tag_set = {str(t).strip().lower() for t in (tags or ()) if str(t).strip()}
    hits = sorted((_FORBIDDEN_LIVE_SCOPES & ({scope} | tag_set)))
    if hits:
        raise ConsumerError(
            ConsumerErrorCode.POLICY_BLOCKED,
            "Claire policy blocks live/echtgeld consumer use in #13",
            details={"blocked": hits},
        )
    if allow_memory_writes:
        raise ConsumerError(
            ConsumerErrorCode.POLICY_BLOCKED,
            "productive memory writes are out of scope for #13",
            details={"allow_memory_writes": True},
        )
    return {
        "policy_owner": "claire_de_binare",
        "guardrails": list(CLAIRE_CONSUMER_GUARDRAILS),
        "target_scope": target_scope,
        "memory_writes": False,
        "live_or_echtgeld": False,
    }


def attach_claire_policy(
    payload: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    """Attach Claire policy metadata without mutating Agent Brain core shapes."""
    out = dict(payload)
    out["claire_policy"] = dict(policy)
    return out


__all__ = [
    "CLAIRE_CONSUMER_GUARDRAILS",
    "assert_claire_consumer_policy",
    "attach_claire_policy",
]
