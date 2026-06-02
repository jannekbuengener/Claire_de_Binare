"""Decision Replay Builder v1/v2 — side-effect-free domain component.

Issue:
    #2119 — [SURREALDB][CONTEXT][REPLAY] Implement decision replay v1
    #2800 — [PHASE-2][SURREALDB][SLICE-4] Evidence-aware decision replay v2
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
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

import re

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow
from tools.surrealdb.decision_history_query import (
    DecisionHistoryQueryRequest,
    query_decision_history_v1,
)

SCHEMA_VERSION = "decision-replay-query/v1"
SCHEMA_VERSION_V2 = "decision-replay-query/v2"

_SENSITIVE_KEY_RE = re.compile(
    r"(token|secret|password|api[_-]?key|credential|private[_-]?key)",
    re.IGNORECASE,
)

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
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _normalize_date_range(date_range: dict[str, Any] | None) -> dict[str, datetime] | None:
    if date_range is None:
        return None

    if not date_range:
        return {}

    at_raw = date_range.get("at")
    from_raw = date_range.get("from")
    to_raw = date_range.get("to")

    if at_raw is not None and (from_raw is not None or to_raw is not None):
        raise DecisionReplayError("date_range.at is mutually exclusive with date_range.from/to")

    normalized: dict[str, datetime] = {}
    if at_raw is not None:
        at_dt = _parse_datetime(at_raw)
        if at_dt is None:
            raise DecisionReplayError("date_range.at must be a valid ISO8601 timestamp")
        normalized["to"] = at_dt
        return normalized

    if from_raw is not None:
        from_dt = _parse_datetime(from_raw)
        if from_dt is None:
            raise DecisionReplayError("date_range.from must be a valid ISO8601 timestamp")
        normalized["from"] = from_dt
    if to_raw is not None:
        to_dt = _parse_datetime(to_raw)
        if to_dt is None:
            raise DecisionReplayError("date_range.to must be a valid ISO8601 timestamp")
        normalized["to"] = to_dt
    if "from" in normalized and "to" in normalized and normalized["from"] > normalized["to"]:
        raise DecisionReplayError("date_range.from must be <= date_range.to")
    return normalized


def _filter_events_by_date_range(
    decision_events: Iterable[Mapping[str, Any]],
    date_range: dict[str, datetime] | None,
) -> list[Mapping[str, Any]]:
    events = list(decision_events)
    if date_range is None:
        return events

    start = date_range.get("from")
    end = date_range.get("to")
    filtered: list[Mapping[str, Any]] = []
    for raw in events:
        created_at = _parse_datetime(raw.get("created_at"))
        if start is not None and (created_at is None or created_at < start):
            continue
        if end is not None and (created_at is None or created_at > end):
            continue
        filtered.append(raw)
    return filtered


def _sanitize_decision(decision: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in decision.items() if not str(key).startswith("_")}


def _sanitize_decisions(decisions: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [_sanitize_decision(decision) for decision in decisions]


def _effective_bucket(decision: Mapping[str, Any], visible_ids: set[str]) -> str:
    status = str(decision.get("status") or "").strip().lower()
    invalidated_by = decision.get("invalidated_by")
    superseded_by = decision.get("superseded_by")

    if isinstance(invalidated_by, str) and invalidated_by:
        return "invalidated" if invalidated_by in visible_ids else "current"
    if isinstance(superseded_by, str) and superseded_by:
        return "superseded" if superseded_by in visible_ids else "current"
    if status == "invalidated":
        return "invalidated"
    if status == "superseded":
        return "superseded"
    return "current"


def _rebucket_decisions(
    decisions: Iterable[Mapping[str, Any]], visible_ids: set[str]
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {"current": [], "superseded": [], "invalidated": []}
    for decision in decisions:
        sanitized = _sanitize_decision(decision)
        buckets[_effective_bucket(sanitized, visible_ids)].append(sanitized)
    return buckets


def _decision_event_meta(decision_events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    meta: list[dict[str, Any]] = []
    for raw in decision_events:
        if not isinstance(raw, Mapping):
            continue
        decision_id = raw.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id.strip():
            continue
        topics = raw.get("topics")
        topic_values: list[str] = []
        if isinstance(topics, list):
            topic_values.extend(str(topic).strip() for topic in topics if isinstance(topic, str) and topic.strip())
        topic_single = raw.get("topic")
        if isinstance(topic_single, str) and topic_single.strip():
            topic_values.append(topic_single.strip())
        meta.append(
            {
                "decision_id": decision_id.strip(),
                "topics": sorted(set(topic_values)),
                "superseded_by": raw.get("superseded_by") if isinstance(raw.get("superseded_by"), str) else None,
                "created_at": _parse_datetime(raw.get("created_at")),
            }
        )
    return meta


def _warnings_for_supersession(
    full_events: Iterable[Mapping[str, Any]],
    filtered_events: Iterable[Mapping[str, Any]],
    topics: Iterable[str],
) -> list[str]:
    relevant_topics = {topic.strip() for topic in topics if isinstance(topic, str) and topic.strip()}
    if not relevant_topics:
        return []

    full_meta = _decision_event_meta(full_events)
    filtered_meta = _decision_event_meta(filtered_events)
    full_relevant = [item for item in full_meta if relevant_topics.intersection(item.get("topics", []))]
    filtered_relevant = [item for item in filtered_meta if relevant_topics.intersection(item.get("topics", []))]
    full_ids = {item["decision_id"] for item in full_relevant}
    filtered_ids = {item["decision_id"] for item in filtered_relevant}

    warnings: list[str] = []
    for item in filtered_relevant:
        target = item.get("superseded_by")
        if not isinstance(target, str) or not target:
            continue
        if target not in full_ids:
            warnings.append("broken_supersession_chain")
        elif target not in filtered_ids:
            warnings.extend(["broken_supersession_chain", "date_range_out_of_history"])
    return warnings


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
    normalized_date_range = _normalize_date_range(request.date_range)
    full_events = list(decision_events)
    filtered_events = _filter_events_by_date_range(full_events, normalized_date_range)

    history_mode_map: dict[str, str] = {
        "replay_by_decision_id": "by_decision_id",
        "replay_current_for_topic": "current_for_topic",
        "replay_superseded_for_topic": "superseded_for_topic",
        "replay_by_scope": "by_scope",
        "replay_by_artifact": "by_artifact",
        "replay_by_status": "by_status",
    }
    history_mode = history_mode_map[request.mode]
    if normalized_date_range and history_mode in {"current_for_topic", "superseded_for_topic"}:
        history_mode = "by_topic"

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
        filtered_events,
        history_request,
        known_evidence_ids=known_evidence_ids,
        known_claim_ids=known_claim_ids,
    )

    all_visible_ids = {
        str(raw.get("decision_id"))
        for raw in filtered_events
        if isinstance(raw, Mapping) and isinstance(raw.get("decision_id"), str)
    }

    rebucketed_matched = _rebucket_decisions(history_result.get("matched_decisions", []), all_visible_ids)

    # Identify primary decision target
    primary_decision_id: str | None = None
    if request.mode == "replay_by_decision_id":
        primary_decision_id = request.decision_id
    elif request.mode == "replay_current_for_topic":
        current = rebucketed_matched.get("current", [])
        if current:
            primary_decision_id = current[-1].get("decision_id")
    elif request.mode == "replay_superseded_for_topic":
        superseded = rebucketed_matched.get("superseded", [])
        if superseded:
            primary_decision_id = superseded[-1].get("decision_id")

    primary_decision = _select_decision(history_result, primary_decision_id)
    if request.mode == "replay_by_decision_id" and primary_decision is None:
        warnings.append("missing_decision")

    decision_summary = _decision_summary(primary_decision)

    relevant_topics: list[str] = []
    if isinstance(request.topic, str) and request.topic.strip():
        relevant_topics = [request.topic.strip()]
    elif primary_decision is not None:
        relevant_topics = [topic for topic in primary_decision.get("topics", []) if isinstance(topic, str) and topic.strip()]

    # Current status per contract
    bucket = (
        _effective_bucket(primary_decision, all_visible_ids) if primary_decision is not None else _bucket_for_decision_id(history_result, primary_decision_id)
        if primary_decision_id
        else "unknown"
    )
    current_for_topic_id: str | None = None
    if request.topic:
        current = rebucketed_matched.get("current", [])
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

    warnings.extend(_warnings_for_supersession(full_events, filtered_events, relevant_topics))

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
        "old_decisions": list(rebucketed_matched.get("superseded", [])),
        "current_decisions": list(rebucketed_matched.get("current", [])),
        "superseded_decisions": list(rebucketed_matched.get("superseded", [])),
        "invalidated_decisions": list(rebucketed_matched.get("invalidated", [])),
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


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key))


def _redact_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return _redact_mapping(value)
    if isinstance(value, list):
        return [_redact_value(key, item) for item in value]
    return value


def _redact_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in raw.items():
        if str(key).startswith("_"):
            continue
        redacted[str(key)] = _redact_value(str(key), value)
    return redacted


def _index_evidence_records(
    evidence_records: Iterable[Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if evidence_records is None:
        return {}
    index: dict[str, dict[str, Any]] = {}
    for raw in evidence_records:
        if not isinstance(raw, Mapping):
            continue
        evidence_id = raw.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            continue
        sanitized = _redact_mapping(_sanitize_decision(raw))
        sanitized.pop("_created_at_dt", None)
        index[evidence_id.strip()] = sanitized
    return index


def _resolved_from_v1_chain(evidence_chain: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    resolved_by_id: dict[str, dict[str, Any]] = {}
    for item in evidence_chain.get("resolved", []):
        if not isinstance(item, Mapping):
            continue
        ref = item.get("id")
        if isinstance(ref, str) and ref.strip():
            resolved_by_id[ref.strip()] = dict(item)
    return resolved_by_id


def _evidence_resolution_status(
    refs: list[str],
    unresolved: list[str],
    resolved_count: int,
    *,
    inputs_provided: bool,
) -> str:
    if not refs:
        return "none"
    if not inputs_provided:
        return "refs_only"
    if unresolved:
        return "partial" if resolved_count else "refs_only"
    if resolved_count >= len(refs):
        return "full"
    return "partial"


def _build_evidence_enrichment_v2(
    base: Mapping[str, Any],
    *,
    evidence_records: Iterable[Mapping[str, Any]] | None = None,
    evidence_summaries: Mapping[str, Any] | None = None,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
    str,
    list[str],
]:
    evidence_chain = base.get("evidence_chain") or {}
    refs = sorted(
        {
            str(ref).strip()
            for ref in evidence_chain.get("refs", [])
            if isinstance(ref, str) and ref.strip()
        }
    )
    v1_unresolved = {
        str(ref).strip()
        for ref in evidence_chain.get("unresolved", [])
        if isinstance(ref, str) and ref.strip()
    }
    v1_resolved = _resolved_from_v1_chain(evidence_chain)
    record_index = _index_evidence_records(evidence_records)

    inputs_provided = evidence_summaries is not None or bool(record_index)
    evidence_links: list[dict[str, Any]] = []
    resolved_evidence: list[dict[str, Any]] = []
    unresolved: list[str] = []
    evidence_warnings: list[str] = []

    if refs and not inputs_provided:
        evidence_warnings.append("evidence_resolution_inputs_not_provided")

    for ref in refs:
        link_status = "unresolved"
        if ref in v1_resolved:
            entry = _redact_mapping(v1_resolved[ref])
            entry["resolution_source"] = "summary"
            entry["authorization_implied"] = False
            resolved_evidence.append(entry)
            link_status = "summary_resolved"
        elif ref in record_index:
            resolved_evidence.append(
                {
                    "id": ref,
                    "resolution_source": "record",
                    "authorization_implied": False,
                    "evidence": record_index[ref],
                }
            )
            link_status = "record_resolved"
        else:
            unresolved.append(ref)
            link_status = "unresolved"
        evidence_links.append({"id": ref, "link_status": link_status})

    unresolved = sorted(set(unresolved) | v1_unresolved)
    resolved_ids = {
        item.get("id")
        for item in resolved_evidence
        if isinstance(item.get("id"), str) and item.get("id")
    }
    unresolved = sorted(ref for ref in unresolved if ref not in resolved_ids)

    if unresolved:
        evidence_warnings.append("unresolved_evidence_refs_present")
    if refs and unresolved and inputs_provided:
        evidence_warnings.append("evidence_resolution_partial")

    status = _evidence_resolution_status(
        refs,
        unresolved,
        len(resolved_evidence),
        inputs_provided=inputs_provided,
    )
    return evidence_links, resolved_evidence, unresolved, status, evidence_warnings


def _resolved_evidence_ids(resolved_evidence: Iterable[Mapping[str, Any]]) -> list[str]:
    ids: list[str] = []
    for item in resolved_evidence:
        if not isinstance(item, Mapping):
            continue
        ref = item.get("id")
        if isinstance(ref, str) and ref.strip():
            ids.append(ref.strip())
            continue
        evidence = item.get("evidence")
        if isinstance(evidence, Mapping):
            evidence_id = evidence.get("evidence_id")
            if isinstance(evidence_id, str) and evidence_id.strip():
                ids.append(evidence_id.strip())
    return sorted(set(ids))


def _decision_chain_hash_payload(
    base: Mapping[str, Any],
    *,
    unresolved_evidence_refs: list[str],
    resolved_evidence_ids: list[str],
    evidence_resolution_status: str,
) -> dict[str, Any]:
    evidence_chain = base.get("evidence_chain") or {}
    claim_chain = base.get("claim_chain") or {}
    return {
        "decision_chain": list(base.get("decision_chain") or []),
        "supersession_chain": list(base.get("supersession_chain") or []),
        "evidence_refs": sorted(
            str(ref).strip()
            for ref in evidence_chain.get("refs", [])
            if isinstance(ref, str) and ref.strip()
        ),
        "claim_refs": sorted(
            str(ref).strip()
            for ref in claim_chain.get("refs", [])
            if isinstance(ref, str) and ref.strip()
        ),
        "unresolved_evidence_refs": sorted(unresolved_evidence_refs),
        "resolved_evidence_ids": sorted(resolved_evidence_ids),
        "evidence_resolution_status": evidence_resolution_status,
        "unresolved_claim_refs": sorted(
            str(ref).strip()
            for ref in claim_chain.get("unresolved", [])
            if isinstance(ref, str) and ref.strip()
        ),
    }


def _build_replay_explainability_v2(
    base: Mapping[str, Any],
    *,
    evidence_resolution_status: str,
    unresolved_evidence_refs: list[str],
    evidence_warnings: list[str],
) -> dict[str, Any]:
    query = base.get("query") or {}
    decision_summary = base.get("decision_summary") or {}
    evidence_chain = base.get("evidence_chain") or {}
    refs = evidence_chain.get("refs", [])
    limitations: list[str] = []
    if evidence_resolution_status in {"refs_only", "partial"}:
        limitations.append(
            "Evidence refs are visible; full resolution requires optional "
            "evidence_summaries or in-memory evidence_records."
        )
    if unresolved_evidence_refs:
        limitations.append(
            "Unresolved evidence refs remain unverified and do not imply approval."
        )
    if evidence_warnings:
        limitations.append("See evidence_warnings and warnings for operator detail.")

    approval = base.get("approval_semantics") or {}
    return {
        "mode": query.get("mode"),
        "primary_decision_id": decision_summary.get("decision_id"),
        "evidence_resolution_status": evidence_resolution_status,
        "evidence_ref_count": len(refs) if isinstance(refs, list) else 0,
        "unresolved_evidence_count": len(unresolved_evidence_refs),
        "decision_chain_length": len(base.get("decision_chain") or []),
        "limitations": limitations,
        "authorization_note": approval.get("note"),
        "history_only": approval.get("history_only", True),
    }


def build_decision_replay_v2(
    decision_events: Iterable[Mapping[str, Any]],
    request: DecisionReplayRequest,
    *,
    known_evidence_ids: set[str] | None = None,
    known_claim_ids: set[str] | None = None,
    evidence_summaries: Mapping[str, Any] | None = None,
    claim_summaries: Mapping[str, Any] | None = None,
    evidence_records: Iterable[Mapping[str, Any]] | None = None,
    claim_records: Iterable[Mapping[str, Any]] | None = None,
    stop_conditions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build Decision Replay v2: v1 semantics plus evidence enrichment and chain hash."""
    _ = claim_records  # reserved for future claim-record enrichment; v1 claim_chain unchanged
    base = build_decision_replay_v1(
        decision_events,
        request,
        known_evidence_ids=known_evidence_ids,
        known_claim_ids=known_claim_ids,
        evidence_summaries=evidence_summaries,
        claim_summaries=claim_summaries,
        stop_conditions=stop_conditions,
    )
    (
        evidence_links,
        resolved_evidence,
        unresolved_evidence_refs,
        evidence_resolution_status,
        evidence_warnings,
    ) = _build_evidence_enrichment_v2(
        base,
        evidence_records=evidence_records,
        evidence_summaries=evidence_summaries,
    )

    enriched = dict(base)
    enriched["schema_version"] = SCHEMA_VERSION_V2
    enriched["evidence_links"] = evidence_links
    enriched["resolved_evidence"] = resolved_evidence
    enriched["unresolved_evidence_refs"] = unresolved_evidence_refs
    enriched["evidence_resolution_status"] = evidence_resolution_status
    enriched["evidence_warnings"] = sorted(set(evidence_warnings))
    enriched["decision_chain_hash"] = canonical_hash(
        _decision_chain_hash_payload(
            base,
            unresolved_evidence_refs=unresolved_evidence_refs,
            resolved_evidence_ids=_resolved_evidence_ids(resolved_evidence),
            evidence_resolution_status=evidence_resolution_status,
        )
    )
    enriched["replay_explainability"] = _build_replay_explainability_v2(
        base,
        evidence_resolution_status=evidence_resolution_status,
        unresolved_evidence_refs=unresolved_evidence_refs,
        evidence_warnings=enriched["evidence_warnings"],
    )
    enriched["warnings"] = sorted(
        set(enriched.get("warnings", [])) | set(enriched["evidence_warnings"])
    )
    return enriched
