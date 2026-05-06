"""MCP adapter layer for Wave-15 contradiction scan tool.

Issues:
    #2148 — [SURREALDB][CONTEXT][CONTRADICTION-MCP] Implement contradiction MCP tool
    Parent: #2145 (Wave-15)
    Epic: #1976

Adapts the Wave-15 contradiction scan domain service for the MCP tool surface.
The tool is read-only, fail-closed, and carries explicit no-live-go semantics.
No DB access. No SurrealDB SDK. No network. No writes. No auto-fix. No live-go.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from tools.surrealdb.contradiction_scan import (
    ContradictionFinding,
    ContradictionScanError,
    EvidenceRef,
    SourceRef,
    scan_contradictions_v1,
)

TOOL_CDB_CONTEXT_CONTRADICTIONS = "cdb_context_contradictions"

_MAX_RECOMMENDED_READS = 20


@dataclass(frozen=True)
class _ToolRequest:
    tool: str
    parameters: Mapping[str, Any]


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def _as_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _metadata(*, source: str = "in_memory", query_time_ms: int = 0) -> dict[str, Any]:
    return {
        "query_time_ms": query_time_ms,
        "source": source,
        "read_only": True,
    }


def _error_response(
    tool: str,
    *,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool": tool,
        "status": "error",
        "error": {"code": code, "message": message},
        "metadata": _metadata(),
    }
    if details:
        payload["error"]["details"] = dict(details)
    return payload


def _parse_tool_request(
    request: Mapping[str, Any],
    *,
    expected_tool: str,
) -> _ToolRequest | dict[str, Any]:
    tool = request.get("tool")
    if tool is None:
        tool = expected_tool
    if tool != expected_tool:
        return _error_response(
            expected_tool,
            code="invalid_tool",
            message=f"expected tool {expected_tool!r}, got {tool!r}",
        )
    parameters = _as_mapping(request.get("parameters")) or request
    return _ToolRequest(tool=expected_tool, parameters=parameters)


def _source_ref_to_dict(src: SourceRef) -> dict[str, Any]:
    return {
        "ref_id": src.ref_id,
        "ref_type": src.ref_type,
        "path": src.path,
        "description": src.description,
    }


def _evidence_ref_to_dict(ev: EvidenceRef) -> dict[str, Any]:
    return {
        "evidence_id": ev.evidence_id,
        "evidence_type": ev.evidence_type,
        "strength": ev.strength,
        "description": ev.description,
    }


def _finding_to_dict(f: ContradictionFinding) -> dict[str, Any]:
    return {
        "contradiction_id": f.contradiction_id,
        "contradiction_type": f.contradiction_type,
        "source_a_ref": _source_ref_to_dict(f.source_a_ref),
        "source_b_ref": _source_ref_to_dict(f.source_b_ref),
        "claim_refs": list(f.claim_refs),
        "evidence_refs": [_evidence_ref_to_dict(ev) for ev in f.evidence_refs],
        "severity": f.severity,
        "confidence": f.confidence,
        "detected_by": f.detected_by,
        "detected_at": f.detected_at,
        "status": f.status,
        "recommended_action": f.recommended_action,
        "blocking": f.blocking,
    }


def _derive_recommended_next_reads(
    findings: Sequence[ContradictionFinding],
    limit: int = _MAX_RECOMMENDED_READS,
) -> list[str]:
    """Derive a deduplicated, priority-sorted list of recommended next reads.

    Priority:
        1. Paths/refs from blocking findings (source_a_ref.path, source_b_ref.path,
           claim_refs)
        2. Evidence IDs from blocking findings
        3. Paths/refs from non-blocking findings
        4. Evidence IDs from non-blocking findings

    Returns at most `limit` non-empty, deduplicated strings.
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(ref: str | None) -> None:
        if ref and ref.strip() and ref not in seen:
            seen.add(ref)
            result.append(ref)

    # Priority 1 & 2: blocking findings first
    for f in findings:
        if not f.blocking:
            continue
        _add(f.source_a_ref.path)
        _add(f.source_b_ref.path)
        for cr in f.claim_refs:
            _add(cr)
        for er in f.evidence_refs:
            _add(er.evidence_id)

    # Priority 3 & 4: non-blocking findings
    for f in findings:
        if f.blocking:
            continue
        _add(f.source_a_ref.path)
        _add(f.source_b_ref.path)
        for cr in f.claim_refs:
            _add(cr)
        for er in f.evidence_refs:
            _add(er.evidence_id)

    return result[:limit]


def handle_cdb_context_contradictions(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: detect contradictions over in-memory records.

    Tool: cdb_context_contradictions
    Read-only, fail-closed, no writes, no DB/network/GitHub access.
    Detection is signal, not action permission. No live-go.

    Input:
        records (required): dict of in-memory input bundles keyed by domain
            (e.g. doc_claims, code_symbols, decisions, claims, evidence_records, etc.)
        scope (optional): scope context identifier for output traceability
        artifact (optional): artifact identifier for output traceability
        decision (optional): decision identifier for output traceability
        claim (optional): claim identifier for output traceability
        overrides (optional): dict[contradiction_id → "false_positive"|"accepted_risk"]
        include_non_blocking (optional, default True): include non-blocking findings
        types (optional): list[str] — filter to these contradiction_type values
        limit (optional): int — max number of findings to return
        format (optional): "json" — reserved, no effect (always returns dict)

    Output:
        tool, status, scope, artifact, decision, claim,
        total_findings, blocking_count, findings, recommended_next_reads,
        guardrails, no_live_go, no_write, metadata
    """
    parsed = _parse_tool_request(request, expected_tool=TOOL_CDB_CONTEXT_CONTRADICTIONS)
    if isinstance(parsed, dict):
        return parsed

    params = parsed.parameters

    # records — required, must be a Mapping
    raw_records = params.get("records")
    records = _as_mapping(raw_records)
    if records is None:
        return _error_response(
            TOOL_CDB_CONTEXT_CONTRADICTIONS,
            code="missing_records",
            message=(
                "records is required (object/dict of in-memory input bundles) "
                "for the contradiction scan adapter. Supply a records object with "
                "domain-specific keys (e.g. doc_claims, code_symbols, decisions, "
                "claims, evidence_records, etc.)."
            ),
        )

    # Optional traceability parameters (passed through to output, not used for filtering)
    scope = _as_str_or_none(params.get("scope"))
    artifact = _as_str_or_none(params.get("artifact"))
    decision = _as_str_or_none(params.get("decision"))
    claim = _as_str_or_none(params.get("claim"))

    # overrides: dict[contradiction_id → override_status]
    raw_overrides = params.get("overrides")
    overrides: dict[str, str] | None = None
    if raw_overrides is not None:
        mapped = _as_mapping(raw_overrides)
        if mapped is not None:
            overrides = {
                str(k): str(v)
                for k, v in mapped.items()
                if isinstance(k, str) and isinstance(v, str)
            }

    include_non_blocking: bool = bool(params.get("include_non_blocking", True))

    raw_types = params.get("types")
    types_filter: list[str] | None = None
    if isinstance(raw_types, list):
        types_filter = [str(t) for t in raw_types if isinstance(t, str) and t.strip()]
        if not types_filter:
            types_filter = None

    raw_limit = params.get("limit")
    findings_limit: int | None = None
    if raw_limit is not None:
        try:
            findings_limit = max(1, int(raw_limit))
        except (TypeError, ValueError):
            findings_limit = None

    # Run the contradiction scan — read-only, no writes, no network
    try:
        scan_result = scan_contradictions_v1(records, overrides)
    except ContradictionScanError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_CONTRADICTIONS,
            code="scan_error",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            TOOL_CDB_CONTEXT_CONTRADICTIONS,
            code="execution_error",
            message=str(exc),
        )

    # Post-scan filtering
    findings = list(scan_result.findings)

    if types_filter is not None:
        findings = [f for f in findings if f.contradiction_type in types_filter]

    if not include_non_blocking:
        findings = [f for f in findings if f.blocking]

    # Compute blocking_count and recommended_next_reads from the full filtered
    # set BEFORE applying limit so that callers always get the true scan result
    # even when output is capped.
    blocking_count = sum(1 for f in findings if f.blocking)
    total_findings_before_limit = len(findings)
    # Derive recommended_next_reads from all filtered findings (pre-limit) so
    # that blocking paths are never dropped from the read list by a cap.
    recommended_next_reads = _derive_recommended_next_reads(findings)

    truncated = False
    if findings_limit is not None:
        truncated = len(findings) > findings_limit
        findings = findings[:findings_limit]

    guardrails = [
        "Detection is signal, not action permission.",
        "No write. No DB access. No network. No GitHub access.",
        "No auto-fix. No live-go. No real-money scope.",
        "Blocking findings are visible but grant no action authority.",
        (
            "LR status remains NO-GO for live trading "
            "(SSOT: docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)."
        ),
        "Board stage (trade-capable) is orthogonal to live readiness.",
    ]

    return {
        "tool": TOOL_CDB_CONTEXT_CONTRADICTIONS,
        "status": "ok",
        "scope": scope,
        "artifact": artifact,
        "decision": decision,
        "claim": claim,
        "total_findings": total_findings_before_limit,
        "returned_findings": len(findings),
        "blocking_count": blocking_count,
        "truncated": truncated,
        "findings": [_finding_to_dict(f) for f in findings],
        "recommended_next_reads": recommended_next_reads,
        "guardrails": guardrails,
        "no_live_go": True,
        "no_write": True,
        "metadata": _metadata(),
    }
