"""MCP adapter layer for Wave-16-C stale context tool.

Issues:
    #2157 — [SURREALDB][CONTEXT][STALE-MCP] Implement stale context MCP tool
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Adapts the Wave-16-A stale knowledge scan domain service for the MCP tool
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

from tools.surrealdb.stale_knowledge_scan import (
    GUARDRAILS,
    SEVERITY_LEVELS,
    STALE_TYPES,
    StaleFinding,
    StaleKnowledgeScanError,
    scan_stale_knowledge_v1,
)

TOOL_CDB_CONTEXT_STALE = "cdb_context_stale"
SCHEMA_VERSION = "stale-context-mcp/v1"

# Maximum limit accepted; requests above this are silently capped.
_MAX_LIMIT = 500
_DEFAULT_LIMIT = 100

# Supported scope values and their corresponding stale_type subsets.
# "all" means no stale_type restriction.
_SCOPE_TO_STALE_TYPES: dict[str, frozenset[str]] = {
    "all": frozenset(STALE_TYPES),
    "artifact": frozenset({"source_hash_changed", "source_deleted"}),
    "decision": frozenset({"decision_superseded"}),
    "evidence": frozenset({"evidence_expired"}),
    "memory": frozenset({"memory_ttl_expired"}),
    "edge": frozenset({"dependency_edge_no_longer_observed"}),
    "package": frozenset({"stale_context_package"}),
    "briefing": frozenset({"stale_briefing"}),
}

_VALID_SCOPES: frozenset[str] = frozenset(_SCOPE_TO_STALE_TYPES.keys())
_VALID_SEVERITIES: frozenset[str] = frozenset(SEVERITY_LEVELS)


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


def _severity_summary(findings: Sequence[StaleFinding]) -> dict[str, int]:
    summary: dict[str, int] = {level: 0 for level in SEVERITY_LEVELS}
    for f in findings:
        if f.severity in summary:
            summary[f.severity] += 1
    return summary


def _stale_type_summary(findings: Sequence[StaleFinding]) -> dict[str, int]:
    summary: dict[str, int] = {t: 0 for t in sorted(STALE_TYPES)}
    for f in findings:
        if f.stale_type in summary:
            summary[f.stale_type] += 1
    return summary


def _collect_source_refs(findings: Sequence[StaleFinding]) -> list[str]:
    """Return a deduplicated, ordered list of source_refs across findings."""
    seen: set[str] = set()
    result: list[str] = []
    for f in findings:
        for ref in f.source_refs:
            if ref and ref not in seen:
                seen.add(ref)
                result.append(ref)
    return result


def _collect_recommended_refresh(findings: Sequence[StaleFinding]) -> list[str]:
    """Return a deduplicated, first-seen-order recommended_refresh list."""
    seen: set[str] = set()
    result: list[str] = []
    for f in findings:
        if f.recommended_refresh and f.recommended_refresh not in seen:
            seen.add(f.recommended_refresh)
            result.append(f.recommended_refresh)
    return result


# ── Handler ───────────────────────────────────────────────────────────────────


def handle_cdb_context_stale(request: Mapping[str, Any]) -> dict[str, Any]:
    """MCP handler: detect stale context findings over in-memory bundle.

    Tool: cdb_context_stale
    Read-only, fail-closed, no writes, no DB/network/GitHub access.
    Bundle-driven: a bundle must be supplied — no live reads.
    Detection is signal, not action permission. No live-go.

    Input:
        bundle (required): object — scan input bundle (domain records)
        scope (optional): str — one of all|artifact|decision|memory|edge|package|briefing
        target_ref (optional): str — exact target_ref to filter findings
        stale_type (optional): str — exact stale_type to filter findings
        severity (optional): str — one of info|warning|blocking
        include_guardrails (optional, default True): bool
        limit (optional, default 100, max 500): int
        as_of (optional): ISO-8601 UTC str; also read from bundle["meta"]["as_of"]

    Output:
        tool, schema_version, status, summary (total_count, blocking_count,
        severity_summary, stale_type_summary, truncated), findings,
        recommended_refresh, source_refs, guardrails (if include_guardrails),
        as_of, metadata
    """
    # Normalise: if request arrives as plain kwargs dict (from bridge **kwargs),
    # the tool key may be absent — treat the whole dict as parameters.
    tool_key = request.get("tool")
    if tool_key is not None and tool_key != TOOL_CDB_CONTEXT_STALE:
        return _error_response(
            TOOL_CDB_CONTEXT_STALE,
            code="invalid_tool",
            message=f"expected tool {TOOL_CDB_CONTEXT_STALE!r}, got {tool_key!r}",
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
            TOOL_CDB_CONTEXT_STALE,
            code="missing_bundle",
            message=(
                "bundle is required (object/dict of scan input records). "
                "This tool is read-only and bundle-driven — it never reads "
                "from a database, filesystem, or network. "
                "Supply a bundle with domain keys (sources, decisions, "
                "evidence_records, memory_records, dependency_edges, "
                "context_packages, briefings)."
            ),
        )

    # ── Optional: scope ───────────────────────────────────────────────────────
    raw_scope = params.get("scope", "all")
    scope = _as_str_or_none(raw_scope) or "all"
    if scope not in _VALID_SCOPES:
        return _error_response(
            TOOL_CDB_CONTEXT_STALE,
            code="invalid_scope",
            message=(
                f"scope must be one of {sorted(_VALID_SCOPES)}, got {scope!r}"
            ),
        )

    # ── Optional: stale_type filter ───────────────────────────────────────────
    raw_stale_type = params.get("stale_type")
    stale_type_filter = _as_str_or_none(raw_stale_type)
    if stale_type_filter is not None and stale_type_filter not in STALE_TYPES:
        return _error_response(
            TOOL_CDB_CONTEXT_STALE,
            code="invalid_stale_type",
            message=(
                f"stale_type must be one of {sorted(STALE_TYPES)}, "
                f"got {stale_type_filter!r}"
            ),
        )

    # ── Optional: severity filter ─────────────────────────────────────────────
    raw_severity = params.get("severity")
    severity_filter = _as_str_or_none(raw_severity)
    if severity_filter is not None and severity_filter not in _VALID_SEVERITIES:
        return _error_response(
            TOOL_CDB_CONTEXT_STALE,
            code="invalid_severity",
            message=(
                f"severity must be one of {sorted(_VALID_SEVERITIES)}, "
                f"got {severity_filter!r}"
            ),
        )

    # ── Optional: target_ref filter ───────────────────────────────────────────
    target_ref_filter = _as_str_or_none(params.get("target_ref"))

    # ── Optional: include_guardrails ─────────────────────────────────────────
    raw_guardrails = params.get("include_guardrails", True)
    include_guardrails: bool = bool(raw_guardrails) if isinstance(raw_guardrails, bool) else True

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
        scan_result = scan_stale_knowledge_v1(bundle, as_of=raw_as_of)
    except StaleKnowledgeScanError as exc:
        return _error_response(
            TOOL_CDB_CONTEXT_STALE,
            code="invalid_bundle",
            message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(
            TOOL_CDB_CONTEXT_STALE,
            code="scan_error",
            message=f"Scan failed unexpectedly: {type(exc).__name__}",
        )

    # ── Apply post-scan filters ───────────────────────────────────────────────
    allowed_stale_types = _SCOPE_TO_STALE_TYPES[scope]

    filtered: list[StaleFinding] = []
    for f in scan_result.findings:
        # scope / stale_type whitelist
        if f.stale_type not in allowed_stale_types:
            continue
        # explicit stale_type filter
        if stale_type_filter is not None and f.stale_type != stale_type_filter:
            continue
        # severity filter
        if severity_filter is not None and f.severity != severity_filter:
            continue
        # target_ref filter
        if target_ref_filter is not None and f.target_ref != target_ref_filter:
            continue
        filtered.append(f)

    # ── Summary (post-filter, pre-limit) ─────────────────────────────────────
    total_count = len(filtered)
    blocking_count = sum(1 for f in filtered if f.blocking)
    sev_summary = _severity_summary(filtered)
    st_summary = _stale_type_summary(filtered)

    # ── Apply limit ───────────────────────────────────────────────────────────
    truncated = len(filtered) > limit
    findings_page = filtered[:limit]

    # ── Collect cross-cutting fields from paged findings only ────────────────
    # Metadata is derived from findings_page so callers receive refs only for
    # the items they actually see — not for items filtered out by limit.
    recommended_refresh = _collect_recommended_refresh(findings_page)
    source_refs = _collect_source_refs(findings_page)

    # ── Build response ────────────────────────────────────────────────────────
    response: dict[str, Any] = {
        "tool": TOOL_CDB_CONTEXT_STALE,
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "summary": {
            "total_count": total_count,
            "blocking_count": blocking_count,
            "truncated": truncated,
            "severity_summary": sev_summary,
            "stale_type_summary": st_summary,
        },
        "findings": [f.to_dict() for f in findings_page],
        "recommended_refresh": recommended_refresh,
        "source_refs": source_refs,
        "as_of": scan_result.as_of,
        "metadata": _metadata(),
    }

    if include_guardrails:
        response["guardrails"] = list(GUARDRAILS)

    return response
