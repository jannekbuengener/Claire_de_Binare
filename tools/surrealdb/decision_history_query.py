"""Decision History Query v1 — side-effect-free domain component.

Issue:
    #2118 — [SURREALDB][CONTEXT][DECISION] Implement decision history query v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Scope:
    Implements a minimal, deterministic decision-history query slice that works
    purely on in-memory decision-event records. No DB access. No SurrealDB SDK.
    No MCP. No networking. No writes.

Guardrails:
    - Retrieval/explanation only: never implies approval, live-go, or authority.
    - Human-GO fields are surfaced as data only (non-authorizing).
    - Evidence/Claim lookup is intentionally *not* implemented here (#2116/#2117).
      Missing refs remain visible via unresolved_* output.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "decision-history-query/v1"

SUPPORTED_MODES = frozenset(
    {
        "by_decision_id",
        "by_topic",
        "by_scope",
        "by_artifact",
        "by_issue",
        "by_status",
        "current_for_topic",
        "superseded_for_topic",
    }
)


class DecisionHistoryQueryError(ValueError):
    """Raised when query inputs are invalid or unsafe."""


@dataclass(frozen=True)
class DecisionHistoryQueryRequest:
    """Query request for decision history v1."""

    mode: str
    decision_id: str | None = None
    topic: str | None = None
    scope: str | None = None
    artifact: str | None = None
    issue: str | None = None
    status: str | None = None
    limit: int = 200


def _parse_datetime(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc) if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text:
        return None
    # Accept ISO-8601; tolerate trailing Z.
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    return str(value).strip() or None


def _normalize_decision(raw: Mapping[str, Any]) -> dict[str, Any]:
    decision_id = _as_str(raw.get("decision_id"))
    if not decision_id:
        raise DecisionHistoryQueryError("decision record missing decision_id")

    created_at = _parse_datetime(raw.get("created_at"))
    status = _as_str(raw.get("status")) or "unknown"
    scope = _as_str(raw.get("scope")) or ""

    superseded_by = _as_str(raw.get("superseded_by"))
    invalidated_by = _as_str(raw.get("invalidated_by"))
    uncertainty = _as_str(raw.get("uncertainty"))

    evidence_refs = [str(x) for x in _as_list(raw.get("evidence_refs")) if _as_str(x)]
    claim_refs = [str(x) for x in _as_list(raw.get("claim_refs")) if _as_str(x)]
    affected_artifacts = [str(x) for x in _as_list(raw.get("affected_artifacts")) if _as_str(x)]

    topics: list[str] = []
    if _as_str(raw.get("topic")):
        topics.append(str(raw["topic"]).strip())
    topics.extend([str(x) for x in _as_list(raw.get("topics")) if _as_str(x)])

    issue_refs = [str(x) for x in _as_list(raw.get("issue_refs")) if _as_str(x)]

    human_go = bool(raw.get("human_go", False))
    human_go_note = _as_str(raw.get("human_go_note"))

    return {
        "decision_id": decision_id,
        "title": _as_str(raw.get("title")) or "",
        "question": _as_str(raw.get("question")) or "",
        "answer": _as_str(raw.get("answer")) or "",
        "decision_type": _as_str(raw.get("decision_type")) or "",
        "status": status,
        "scope": scope,
        "topics": sorted(set(t for t in topics if t)),
        "issue_refs": sorted(set(i for i in issue_refs if i)),
        "evidence_refs": sorted(set(evidence_refs)),
        "claim_refs": sorted(set(claim_refs)),
        "affected_artifacts": sorted(set(affected_artifacts)),
        "agent": _as_str(raw.get("agent")) or "",
        "human_go": human_go,
        "human_go_note": human_go_note,
        "superseded_by": superseded_by,
        "invalidated_by": invalidated_by,
        "uncertainty": uncertainty,
        "comment": _as_str(raw.get("comment")) or "",
        "created_at": created_at.isoformat() if created_at else None,
        "_created_at_dt": created_at,
    }


def _decision_sort_key(decision: Mapping[str, Any]) -> tuple[int, str, str]:
    dt: datetime | None = decision.get("_created_at_dt")
    # Missing timestamps sort last but deterministically.
    if dt is None:
        return (1, "", str(decision.get("decision_id", "")))
    return (0, dt.isoformat(), str(decision.get("decision_id", "")))


def _classify_bucket(decision: Mapping[str, Any]) -> str:
    status = str(decision.get("status", "")).strip().lower()
    if decision.get("invalidated_by") or status == "invalidated":
        return "invalidated"
    if decision.get("superseded_by") or status == "superseded":
        return "superseded"
    return "current"


def _validate_request(req: DecisionHistoryQueryRequest) -> None:
    if req.mode not in SUPPORTED_MODES:
        raise DecisionHistoryQueryError(f"unsupported mode: {req.mode}")
    if req.limit < 1 or req.limit > 10_000:
        raise DecisionHistoryQueryError("limit must be within 1..10000")

    required: dict[str, str] = {
        "by_decision_id": "decision_id",
        "by_topic": "topic",
        "by_scope": "scope",
        "by_artifact": "artifact",
        "by_issue": "issue",
        "by_status": "status",
        "current_for_topic": "topic",
        "superseded_for_topic": "topic",
    }
    required_field = required.get(req.mode)
    if required_field and not _as_str(getattr(req, required_field)):
        raise DecisionHistoryQueryError(f"{req.mode} requires {required_field}")


def _match(decision: Mapping[str, Any], req: DecisionHistoryQueryRequest) -> bool:
    if req.mode == "by_decision_id":
        return decision.get("decision_id") == req.decision_id
    if req.mode in {"by_topic", "current_for_topic", "superseded_for_topic"}:
        topic = (req.topic or "").strip()
        return topic in set(decision.get("topics", []))
    if req.mode == "by_scope":
        scope = (req.scope or "").strip()
        if not scope:
            return False
        return scope in str(decision.get("scope", ""))
    if req.mode == "by_artifact":
        artifact = (req.artifact or "").strip()
        return artifact in set(decision.get("affected_artifacts", []))
    if req.mode == "by_issue":
        issue = (req.issue or "").strip()
        return issue in set(decision.get("issue_refs", []))
    if req.mode == "by_status":
        status = (req.status or "").strip().lower()
        return str(decision.get("status", "")).strip().lower() == status
    return False


def _build_chain_for_topic(
    decisions: Sequence[Mapping[str, Any]], topic: str
) -> list[dict[str, Any]]:
    topic_decisions = [d for d in decisions if topic in set(d.get("topics", []))]
    by_id: dict[str, Mapping[str, Any]] = {d["decision_id"]: d for d in topic_decisions}

    # Pick roots deterministically: candidates that are not referenced as superseded_by targets.
    referenced: set[str] = set()
    for d in topic_decisions:
        target = d.get("superseded_by")
        if isinstance(target, str) and target:
            referenced.add(target)

    roots = sorted((d for d in topic_decisions if d["decision_id"] not in referenced), key=_decision_sort_key)
    chain: list[dict[str, Any]] = []
    visited: set[str] = set()

    for root in roots:
        current = root
        while True:
            did = current["decision_id"]
            if did in visited:
                break
            visited.add(did)
            bucket = _classify_bucket(current)
            chain.append(
                {
                    "decision_id": did,
                    "bucket": bucket,
                    "created_at": current.get("created_at"),
                    "superseded_by": current.get("superseded_by"),
                    "invalidated_by": current.get("invalidated_by"),
                }
            )
            next_id = current.get("superseded_by")
            if not isinstance(next_id, str) or not next_id or next_id not in by_id:
                break
            current = by_id[next_id]

    # Append any disconnected nodes deterministically.
    for d in sorted(topic_decisions, key=_decision_sort_key):
        if d["decision_id"] in visited:
            continue
        chain.append(
            {
                "decision_id": d["decision_id"],
                "bucket": _classify_bucket(d),
                "created_at": d.get("created_at"),
                "superseded_by": d.get("superseded_by"),
                "invalidated_by": d.get("invalidated_by"),
            }
        )
    return chain


def query_decision_history_v1(
    decision_events: Iterable[Mapping[str, Any]],
    request: DecisionHistoryQueryRequest,
    *,
    known_evidence_ids: set[str] | None = None,
    known_claim_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Query decision history over in-memory decision-event records.

    The function is deterministic and side-effect-free.
    """
    _validate_request(request)

    warnings: list[str] = []

    normalized: list[dict[str, Any]] = []
    for raw in decision_events:
        if not isinstance(raw, Mapping):
            continue
        normalized.append(_normalize_decision(raw))

    # Deterministic stable ordering
    normalized_sorted = sorted(normalized, key=_decision_sort_key)

    matched = [d for d in normalized_sorted if _match(d, request)]
    if request.mode == "current_for_topic":
        matched = [d for d in matched if _classify_bucket(d) == "current"]
    if request.mode == "superseded_for_topic":
        matched = [d for d in matched if _classify_bucket(d) == "superseded"]

    if not matched:
        warnings.append("no_decisions_matched")

    # Enforce limit deterministically
    matched = matched[: request.limit]

    buckets: dict[str, list[dict[str, Any]]] = {"current": [], "superseded": [], "invalidated": []}
    for d in matched:
        buckets[_classify_bucket(d)].append(d)

    # Aggregate refs
    evidence_refs: list[str] = sorted({e for d in matched for e in d.get("evidence_refs", [])})
    claim_refs: list[str] = sorted({c for d in matched for c in d.get("claim_refs", [])})

    unresolved_evidence_refs: list[str] = []
    if known_evidence_ids is not None:
        unresolved_evidence_refs = sorted([e for e in evidence_refs if e not in known_evidence_ids])
        if unresolved_evidence_refs:
            warnings.append("unresolved_evidence_refs_present")

    unresolved_claim_refs: list[str] = []
    if known_claim_ids is not None:
        unresolved_claim_refs = sorted([c for c in claim_refs if c not in known_claim_ids])
        if unresolved_claim_refs:
            warnings.append("unresolved_claim_refs_present")

    uncertainty = [
        {"decision_id": d["decision_id"], "uncertainty": d["uncertainty"]}
        for d in matched
        if d.get("uncertainty")
    ]

    human_go = [
        {
            "decision_id": d["decision_id"],
            "human_go": bool(d.get("human_go", False)),
            "note": d.get("human_go_note"),
        }
        for d in matched
        if d.get("human_go") or d.get("human_go_note")
    ]

    decision_chain: list[dict[str, Any]] = []
    if request.mode in {"by_topic", "current_for_topic", "superseded_for_topic"} and request.topic:
        decision_chain = _build_chain_for_topic(normalized_sorted, request.topic.strip())
        if not decision_chain:
            warnings.append("no_chain_for_topic")

    # Approval semantics are explicit and non-ambiguous.
    approval_semantics = {
        "history_only": True,
        "no_approval": True,
        "no_live_go": True,
        "note": (
            "Decision history retrieval only. This output does not grant approval, "
            "does not authorize live trading, and must not be interpreted as Human-GO."
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "query": {
            "mode": request.mode,
            "decision_id": request.decision_id,
            "topic": request.topic,
            "scope": request.scope,
            "artifact": request.artifact,
            "issue": request.issue,
            "status": request.status,
            "limit": request.limit,
        },
        "mode": request.mode,
        "matched_decisions": [d for d in matched],
        "current_decisions": [d for d in buckets["current"]],
        "superseded_decisions": [d for d in buckets["superseded"]],
        "invalidated_decisions": [d for d in buckets["invalidated"]],
        "decision_chain": decision_chain,
        "evidence_refs": evidence_refs,
        "claim_refs": claim_refs,
        "unresolved_evidence_refs": unresolved_evidence_refs,
        "unresolved_claim_refs": unresolved_claim_refs,
        "uncertainty": uncertainty,
        "human_go": human_go,
        "warnings": sorted(set(warnings)),
        "approval_semantics": approval_semantics,
    }
