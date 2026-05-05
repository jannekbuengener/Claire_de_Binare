"""Decision Replay Builder v1 — side-effect-free domain component.

Issue:
    #2119 — [SURREALDB][CONTEXT][REPLAY] Implement decision replay v1
    Parent: #2115 (Wave-14)
    Epic: #1976

Dependencies (local, read-only):
    - #2118 Decision History Query v1: tools/surrealdb/decision_history_query.py
    - #2012 Decision Replay Query Contract: docs/surrealdb/decision_replay_query_contract.md

Scope:
    Build a minimal, deterministic Decision Replay output from in-memory decision
    events. No DB access. No SurrealDB SDK. No MCP. No networking. No writes.

Guardrails:
    - Replay explains only. No approval semantics. No Live-Go. No Echtgeld-Go.
    - Human-GO is surfaced as data only (non-authorizing).
    - Evidence/Claim resolver is intentionally not implemented here (#2116/#2117).
      Missing refs remain visible as unresolved refs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from core.utils.clock import utcnow
from tools.surrealdb.decision_history_query import (
    DecisionHistoryQueryRequest,
    query_decision_history_v1,
)

SCHEMA_VERSION = "decision-replay-query/v1"

SUPPORTED_MODES = frozenset(
    {
        "replay_by_decision_id",
        "replay_current_for_topic",
        "replay_superseded_for_topic",
        # Optional modes (kept minimal, still v1):
        "replay_by_scope",
        "replay_by_artifact",
        "replay_by_status",
    }
)


class DecisionReplayError(ValueError):
    """Raised when replay inputs are invalid or unsafe."""


@dataclass(frozen=True)
class DecisionReplayRequest:
    mode: str
    decision_id: str | None = None
    topic: str | None = None
    scope: str | None = None
    artifact: str | None = None
    status: str | None = None
    date_range: dict[str, Any] | None = None
    limit: int = 50


def _utc_now_iso() -> str:
    return utcnow().isoformat()


def _validate_request(req: DecisionReplayRequest) -> None:
    if req.mode not in SUPPORTED_MODES:
        raise DecisionReplayError(f"unsupported mode: {req.mode}")
    if req.limit < 1 or req.limit > 500:
        raise DecisionReplayError("limit must be within 1..500")

    required: dict[str, str] = {
        "replay_by_decision_id": "decision_id",
        "replay_current_for_topic": "topic",
        "replay_superseded_for_topic": "topic",
        "replay_by_scope": "scope",
        "replay_by_artifact": "artifact",
        "replay_by_status": "status",
    }
    required_field = required.get(req.mode)
    if required_field:
        value = getattr(req, required_field)
        if not isinstance(value, str) or not value.strip():
            raise DecisionReplayError(f"{req.mode} requires {required_field}")

    # date_range is contract-level optional and best-effort. Validate shape only.
    if req.date_range is not None and not isinstance(req.date_range, dict):
        raise DecisionReplayError("date_range must be an object when provided")


def _bucket_for_decision_id(history_result: Mapping[str, Any], decision_id: str) -> str:
    if any(d.get("decision_id") == decision_id for d in history_result.get("invalidated_decisions", [])):
        return "invalidated"
    if any(d.get("decision_id") == decision_id for d in history_result.get("superseded_decisions", [])):
        return "superseded"
    if any(d.get("decision_id") == decision_id for d in history_result.get("current_decisions", [])):
        return "current"
    return "unknown"


def _select_decision(history_result: Mapping[str, Any], decision_id: str | None) -> Mapping[str, Any] | None:
    if not decision_id:
        return None
    for d in history_result.get("matched_decisions", []):
        if d.get("decision_id") == decision_id:
            return d
    for bucket in ("current_decisions", "superseded_decisions", "invalidated_decisions"):
        for d in history_result.get(bucket, []):
            if d.get("decision_id") == decision_id:
                return d
    return None


def _decision_summary(decision: Mapping[str, Any] | None) -> dict[str, Any]:
    if not decision:
        return {
            "decision_id": None,
            "title": "",
            "status": "unknown",
            "scope": "",
            "topics": [],
            "created_at": None,
            "agent": "",
            "human_go": {"present": False, "value": False, "note": None},
            "uncertainty": None,
        }
    human_go_value = bool(decision.get("human_go", False))
    human_go_note = decision.get("human_go_note")
    return {
        "decision_id": decision.get("decision_id"),
        "title": decision.get("title") or "",
        "status": decision.get("status") or "unknown",
        "scope": decision.get("scope") or "",
        "topics": list(decision.get("topics") or []),
        "created_at": decision.get("created_at"),
        "agent": decision.get("agent") or "",
        "human_go": {
            "present": bool(human_go_value or human_go_note),
            "value": human_go_value,
            "note": human_go_note,
        },
        "uncertainty": decision.get("uncertainty"),
    }


def _build_refs_chain(
    refs: list[str],
    known_ids: set[str] | None,
    summaries: Mapping[str, Any] | None,
) -> dict[str, Any]:
    resolved: list[Any] = []
    unresolved: list[str] = []

    if summaries is not None:
        for ref in refs:
            if ref in summaries:
                resolved.append({"id": ref, "summary": summaries[ref]})
            else:
                unresolved.append(ref)
        return {"refs": refs, "resolved": resolved, "unresolved": unresolved}

    if known_ids is not None:
        unresolved = [r for r in refs if r not in known_ids]
    return {"refs": refs, "resolved": resolved, "unresolved": unresolved}


def _supersession_chain_from_decision_chain(decision_chain: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for node in decision_chain:
        from_id = node.get("decision_id")
        to_id = node.get("superseded_by")
        if isinstance(from_id, str) and from_id and isinstance(to_id, str) and to_id:
            chain.append({"from": from_id, "to": to_id, "relation": "supersedes"})
    return chain


def build_decision_replay_v1(
    decision_events: Iterable[Mapping[str, Any]],
    request: DecisionReplayRequest,
    *,
    known_evidence_ids: set[str] | None = None,
    known_claim_ids: set[str] | None = None,
    evidence_summaries: Mapping[str, Any] | None = None,
    claim_summaries: Mapping[str, Any] | None = None,
    stop_conditions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a minimal Decision Replay v1 response (agent-readable)."""
    _validate_request(request)

    warnings: list[str] = []

    history_mode_map: dict[str, str] = {
        "replay_by_decision_id": "by_decision_id",
        "replay_current_for_topic": "current_for_topic",
        "replay_superseded_for_topic": "superseded_for_topic",
        "replay_by_scope": "by_scope",
        "replay_by_artifact": "by_artifact",
        "replay_by_status": "by_status",
    }
    history_mode = history_mode_map[request.mode]

    history_request = DecisionHistoryQueryRequest(
        mode=history_mode,
        decision_id=request.decision_id,
        topic=request.topic,
        scope=request.scope,
        artifact=request.artifact,
        issue=None,
        status=request.status,
        limit=max(1, min(200, request.limit)),
    )

    history_result = query_decision_history_v1(
        decision_events,
        history_request,
        known_evidence_ids=known_evidence_ids,
        known_claim_ids=known_claim_ids,
    )

    # Identify primary decision target
    primary_decision_id: str | None = None
    if request.mode == "replay_by_decision_id":
        primary_decision_id = request.decision_id
    elif request.mode == "replay_current_for_topic":
        current = history_result.get("current_decisions", [])
        if current:
            primary_decision_id = current[-1].get("decision_id")
    elif request.mode == "replay_superseded_for_topic":
        superseded = history_result.get("superseded_decisions", [])
        if superseded:
            primary_decision_id = superseded[-1].get("decision_id")

    primary_decision = _select_decision(history_result, primary_decision_id)
    if request.mode == "replay_by_decision_id" and primary_decision is None:
        warnings.append("missing_decision")

    decision_summary = _decision_summary(primary_decision)

    # Current status per contract
    bucket = (
        _bucket_for_decision_id(history_result, primary_decision_id)
        if primary_decision_id
        else "unknown"
    )
    current_for_topic_id: str | None = None
    if request.topic:
        # For topic queries, take the last current decision deterministically.
        current = history_result.get("current_decisions", [])
        if current:
            current_for_topic_id = current[-1].get("decision_id")

    current_status = {
        "bucket": bucket,
        "current_decision_id": current_for_topic_id,
        "as_of": _utc_now_iso(),
    }

    decision_chain = history_result.get("decision_chain", [])
    if not decision_chain and primary_decision:
        # For replay_by_decision_id, the history query does not include a chain.
        # Best-effort: derive chain from the first topic, if present.
        topics = primary_decision.get("topics", [])
        if isinstance(topics, list) and topics and isinstance(topics[0], str) and topics[0].strip():
            topic_for_chain = topics[0].strip()
            chain_result = query_decision_history_v1(
                decision_events,
                DecisionHistoryQueryRequest(mode="by_topic", topic=topic_for_chain, limit=200),
                known_evidence_ids=known_evidence_ids,
                known_claim_ids=known_claim_ids,
            )
            decision_chain = chain_result.get("decision_chain", []) or []

    if request.topic and not decision_chain:
        warnings.append("broken_supersession_chain")

    supersession_chain = _supersession_chain_from_decision_chain(decision_chain)

    evidence_refs = history_result.get("evidence_refs", [])
    claim_refs = history_result.get("claim_refs", [])

    evidence_chain = _build_refs_chain(evidence_refs, known_evidence_ids, evidence_summaries)
    claim_chain = _build_refs_chain(claim_refs, known_claim_ids, claim_summaries)

    if evidence_chain.get("unresolved"):
        warnings.append("unresolved_evidence_refs_present")
    if claim_chain.get("unresolved"):
        warnings.append("unresolved_claim_refs_present")

    uncertainty = list(history_result.get("uncertainty", []))
    if evidence_chain.get("unresolved") or claim_chain.get("unresolved"):
        uncertainty.append(
            {
                "decision_id": primary_decision_id,
                "uncertainty": "unresolved evidence/claim refs present (resolver out of scope)",
            }
        )

    approval_semantics = {
        "history_only": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Replay explains only. This output does not grant approval and does not "
            "authorize live capital."
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
            "status": request.status,
            "date_range": request.date_range,
            "limit": request.limit,
        },
        "decision_summary": decision_summary,
        "current_status": current_status,
        "old_decisions": list(history_result.get("superseded_decisions", [])),
        "current_decisions": list(history_result.get("current_decisions", [])),
        "superseded_decisions": list(history_result.get("superseded_decisions", [])),
        "invalidated_decisions": list(history_result.get("invalidated_decisions", [])),
        "decision_chain": decision_chain,
        "evidence_chain": evidence_chain,
        "claim_chain": claim_chain,
        "supersession_chain": supersession_chain,
        "uncertainty": uncertainty,
        "stop_conditions": list(stop_conditions or []),
        "human_go": list(history_result.get("human_go", [])),
        "warnings": sorted(set(warnings + list(history_result.get("warnings", [])))),
        "approval_semantics": approval_semantics,
    }
