"""MCP adapter layer for Wave-17-C scope drift tool.

Issues:
    #2165 — [SURREALDB][CONTEXT][SCOPE-MCP] Implement scope drift MCP tool
    Parent: #2162 (Wave-17 anchor)
    Epic: #1976

Adapts the Wave-17-A scope drift firewall domain service for the MCP tool
surface. The tool is read-only, fail-closed, and carries explicit no-live-go
semantics. No DB access. No SurrealDB SDK. No network. No writes. No auto-fix.
No live-go.

Bundle-driven:
    The tool operates exclusively on the in-memory bundle passed as input.
    If no bundle is supplied the tool returns a clean error — it never
    reads from a database, filesystem, or network to fill the gap.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from tools.surrealdb.scope_drift_blocking import build_blocking_output
from tools.surrealdb.scope_drift_firewall import (
    DRIFT_TYPES,
    GUARDRAILS,
    SEVERITY_LEVELS,
    ScopeDriftFinding,
    ScopeDriftFirewallError,
    scan_scope_drift_v1,
)

TOOL_CDB_CONTEXT_SCOPE_DRIFT = "cdb_context_scope_drift"
SCHEMA_VERSION = "scope-drift-mcp/v1"

# Maximum limit accepted; requests above this are silently capped.
_MAX_LIMIT = 500
_DEFAULT_LIMIT = 100

_VALID_SEVERITIES: frozenset[str] = frozenset(SEVERITY_LEVELS)
_VALID_SCOPE_TYPES: frozenset[str] = frozenset(DRIFT_TYPES)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _as_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _as_mapping_or_none(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def _error_response(
    tool: str,
    *,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "tool": tool,
        "status": "error",
        "error": {"code": code, "message": message},
    }


def _metadata(*, source: str = "in_memory", read_only: bool = True) -> dict[str, Any]:
    return {
        "source": source,
        "read_only": read_only,
    }


def _severity_summary(findings: Sequence[ScopeDriftFinding]) -> dict[str, int]:
    summary: dict[str, int] = {level: 0 for level in SEVERITY_LEVELS}
    for f in findings:
        if f.severity in summary:
            summary[f.severity] += 1
    return summary


def _drift_type_summary(findings: Sequence[ScopeDriftFinding]) -> dict[str, int]:
    summary: dict[str, int] = {t: 0 for t in sorted(DRIFT_TYPES)}
    for f in findings:
        if f.drift_type in summary:
            summary[f.drift_type] += 1
    return summary


# ── Handler ───────────────────────────────────────────────────────────────────


def handle_cdb_context_scope_drift(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: detect scope drift findings over in-memory bundle.

    Tool: cdb_context_scope_drift
    Read-only, fail-closed, no writes, no DB/network/GitHub access.
    Bundle-driven: a bundle must be supplied — no live reads.
    Detection is signal, not action permission. No live-go.

    Input:
        bundle (required): object — scan input bundle (declared_scope, touched_artifacts, etc.)
        severity (optional): str — one of info|warning|blocking
        scope_type (optional): str — one of the 9 canonical drift types
        target_ref (optional): str — filter to findings whose affected_artifacts contains this ref
        blocking (optional): bool — true: only blocking findings; false: only non-blocking
        limit (optional, default 100, max 500): int
        as_of (optional): ISO-8601 UTC str; also read from bundle["meta"]["as_of"]

    Output:
        tool, schema_version, status, summary (total_count, blocking_count,
        severity_summary, drift_type_summary, truncated, filters_applied),
        findings, guardrails, scan_status, scanned_at, metadata
    """
    # Normalise: if request arrives as plain kwargs dict (from bridge **kwargs),
    # the tool key may be absent — treat the whole dict as parameters.
    tool_key = request.get("tool")
    if tool_key is not None and tool_key != TOOL_CDB_CONTEXT_SCOPE_DRIFT:
        return _error_response(
            TOOL_CDB_CONTEXT_SCOPE_DRIFT,
            code="invalid_tool",
            message=f"expected tool {TOOL_CDB_CONTEXT_SCOPE_DRIFT!r}, got {tool_key!r}",
        )

    # Resolve parameters: if a "parameters" wrapper is present, unwrap it.
    raw_params = request.get("parameters")
    if isinstance(raw_params, Mapping):
        params: Mapping[str, Any] = raw_params
    else:
        params = request

    # ── Required: bundle ──────────────────────────────────────────────────────
    raw_bundle = params.get("bundle")
    bundle = _as_mapping_or_none(raw_bundle)
    if bundle is None:
        return _error_response(
            TOOL_CDB_CONTEXT_SCOPE_DRIFT,
            code="missing_bundle",
            message=(
                "bundle is required (object/dict of scan input records). "
                "This tool is read-only and bundle-driven — it never reads "
                "from a database, filesystem, or network. "
                "Supply a bundle with domain keys (declared_scope, touched_artifacts, "
                "issue_refs, generated_findings, forbidden_surfaces)."
            ),
        )

    # ── Optional: severity filter ─────────────────────────────────────────────
    raw_severity = params.get("severity")
    severity_filter = _as_str_or_none(raw_severity)
    if severity_filter is not None and severity_filter not in _VALID_SEVERITIES:
        return _error_response(
            TOOL_CDB_CONTEXT_SCOPE_DRIFT,
            code="invalid_severity",
            message=(
                f"severity must be one of {sorted(_VALID_SEVERITIES)}, "
                f"got {severity_filter!r}"
            ),
        )

    # ── Optional: scope_type filter ───────────────────────────────────────────
    raw_scope_type = params.get("scope_type")
    scope_type_filter = _as_str_or_none(raw_scope_type)
    if scope_type_filter is not None and scope_type_filter not in _VALID_SCOPE_TYPES:
        return _error_response(
            TOOL_CDB_CONTEXT_SCOPE_DRIFT,
            code="invalid_scope_type",
            message=(
                f"scope_type must be one of {sorted(_VALID_SCOPE_TYPES)}, "
                f"got {scope_type_filter!r}"
            ),
        )

    # ── Optional: target_ref filter ───────────────────────────────────────────
    target_ref_filter = _as_str_or_none(params.get("target_ref"))

    # ── Optional: blocking filter ─────────────────────────────────────────────
    raw_blocking = params.get("blocking")
    blocking_filter: bool | None = None
    if raw_blocking is not None:
        if isinstance(raw_blocking, bool):
            blocking_filter = raw_blocking
        else:
            s = str(raw_blocking).strip().lower()
            if s == "true":
                blocking_filter = True
            elif s == "false":
                blocking_filter = False
            # else: unrecognised value — ignore (treat as absent)

    # ── Optional: limit ───────────────────────────────────────────────────────
    raw_limit = params.get("limit", _DEFAULT_LIMIT)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    limit = max(1, min(limit, _MAX_LIMIT))

    # ── Optional: as_of ───────────────────────────────────────────────────────
    # Priority: explicit param > bundle["meta"]["as_of"] > None (service default)
    raw_as_of = _as_str_or_none(params.get("as_of"))
    if raw_as_of is None:
        meta = bundle.get("meta")
        if isinstance(meta, Mapping):
            raw_as_of = _as_str_or_none(meta.get("as_of"))

    # ── Run scan ─────────────────────────────────────────────────────────────
    try:
        scan_result = scan_scope_drift_v1(bundle, as_of=raw_as_of)
    except ScopeDriftFirewallError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_SCOPE_DRIFT,
            code="invalid_bundle",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            TOOL_CDB_CONTEXT_SCOPE_DRIFT,
            code="scan_error",
            message=f"Scan failed unexpectedly: {type(exc).__name__}",
        )

    # ── Apply post-scan filters ───────────────────────────────────────────────
    filtered: list[ScopeDriftFinding] = []
    for f in scan_result.findings:
        # severity filter
        if severity_filter is not None and f.severity != severity_filter:
            continue
        # scope_type filter (maps to drift_type field)
        if scope_type_filter is not None and f.drift_type != scope_type_filter:
            continue
        # target_ref filter: membership in affected_artifacts
        if target_ref_filter is not None and target_ref_filter not in f.affected_artifacts:
            continue
        # blocking filter: maps to human_go_required
        if blocking_filter is not None and f.human_go_required != blocking_filter:
            continue
        filtered.append(f)

    # ── Summary (post-filter, pre-limit) ─────────────────────────────────────
    total_count = len(filtered)
    blocking_count = sum(1 for f in filtered if f.human_go_required)
    sev_summary = _severity_summary(filtered)
    dt_summary = _drift_type_summary(filtered)

    # Build filters_applied for traceability
    filters_applied: dict[str, Any] = {}
    if severity_filter is not None:
        filters_applied["severity"] = severity_filter
    if scope_type_filter is not None:
        filters_applied["scope_type"] = scope_type_filter
    if target_ref_filter is not None:
        filters_applied["target_ref"] = target_ref_filter
    if blocking_filter is not None:
        filters_applied["blocking"] = blocking_filter

    # ── Apply limit ───────────────────────────────────────────────────────────
    truncated = len(filtered) > limit
    findings_page = filtered[:limit]

    # ── Build response ────────────────────────────────────────────────────────
    return {
        "tool": TOOL_CDB_CONTEXT_SCOPE_DRIFT,
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "summary": {
            "total_count": total_count,
            "blocking_count": blocking_count,
            "truncated": truncated,
            "severity_summary": sev_summary,
            "drift_type_summary": dt_summary,
            "filters_applied": filters_applied,
        },
        "findings": [f.to_dict() for f in findings_page],
        "guardrails": list(GUARDRAILS),
        "scan_status": scan_result.status,
        "scanned_at": scan_result.scanned_at,
        "metadata": _metadata(),
        "blocking_output": build_blocking_output(scan_result) if scan_result.blocking_count > 0 else None,
    }
