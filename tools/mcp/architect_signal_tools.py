"""MCP adapter layer for Wave-18 architect signals tool.

Issues:
    #2175 — [SURREALDB][CONTEXT][ARCHITECT-MCP] Implement architect signals MCP tool
    Parent: #2170 (Wave-18 anchor)
    Epic: #1976

Adapts the Wave-18-D architect signal service for the MCP tool surface.
The tool is read-only, fail-closed, and carries explicit no-live-go semantics.
No DB access. No SurrealDB SDK. No network. No writes. No auto-fix. No live-go.

Bundle-driven:
    The tool operates exclusively on the in-memory bundle passed as input.
    If no bundle is supplied the tool returns a clean error — it never
    reads from a database, filesystem, or network to fill the gap.
"""

from __future__ import annotations

from typing import Any, Mapping

from tools.surrealdb.architect_signals import (
    GUARDRAILS,
    SIGNAL_SEVERITIES,
    SIGNAL_TYPES,
    ArchitectSignalError,
    scan_architect_signals_v1,
)

TOOL_CDB_CONTEXT_ARCHITECT_SIGNALS = "cdb_context_architect_signals"
SCHEMA_VERSION = "architect-signals-mcp/v1"

_MAX_LIMIT = 500
_DEFAULT_LIMIT = 100
_VALID_SEVERITIES: frozenset[str] = frozenset(SIGNAL_SEVERITIES)
_VALID_SIGNAL_TYPES: frozenset[str] = frozenset(SIGNAL_TYPES)


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


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "tool": TOOL_CDB_CONTEXT_ARCHITECT_SIGNALS,
        "status": "error",
        "error": {"code": code, "message": message},
    }


def _metadata(read_only: bool = True) -> dict[str, Any]:
    return {"source": "in_memory", "read_only": read_only}


# ── Main handler ──────────────────────────────────────────────────────────────


def handle_architect_signals(**kwargs: Any) -> dict[str, Any]:
    """Handle a ``cdb_context_architect_signals`` MCP tool call.

    Required parameters:
        bundle (dict): Input context bundle.

    Optional filter parameters:
        signal_type (str): Return only signals of this type.
        min_severity (str): Return only signals at or above this severity
            (info < watch < blocking).
        limit (int): Maximum number of signals to return (default 100).
        as_of (str): Advisory ISO-8601 UTC timestamp passed to the service.

    Returns a read-only architect signal result. ``metadata.read_only`` is
    always ``True``.
    """
    # ── Validate required bundle ──────────────────────────────────────────────
    bundle = _as_mapping_or_none(kwargs.get("bundle"))
    if bundle is None:
        return _error_response(
            "missing_bundle",
            "bundle is required and must be a JSON object",
        )

    # ── Optional filters ──────────────────────────────────────────────────────
    signal_type = _as_str_or_none(kwargs.get("signal_type"))
    if signal_type is not None and signal_type not in _VALID_SIGNAL_TYPES:
        return _error_response(
            "invalid_signal_type",
            f"signal_type {signal_type!r} is not valid. "
            f"Valid: {', '.join(sorted(_VALID_SIGNAL_TYPES))}",
        )

    min_severity = _as_str_or_none(kwargs.get("min_severity"))
    if min_severity is not None and min_severity not in _VALID_SEVERITIES:
        return _error_response(
            "invalid_severity",
            f"min_severity {min_severity!r} is not valid. "
            f"Valid: {', '.join(sorted(_VALID_SEVERITIES))}",
        )

    raw_limit = kwargs.get("limit", _DEFAULT_LIMIT)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    limit = min(max(limit, 1), _MAX_LIMIT)

    as_of = _as_str_or_none(kwargs.get("as_of"))

    # ── Scan ──────────────────────────────────────────────────────────────────
    try:
        result = scan_architect_signals_v1(bundle, as_of=as_of)
    except ArchitectSignalError as exc:
        return _error_response("signal_error", str(exc))
    except Exception as exc:  # noqa: BLE001 - fail-closed
        return _error_response("internal_error", f"unexpected error: {exc}")

    # ── Filter signals ────────────────────────────────────────────────────────
    _sev_order = {"blocking": 0, "watch": 1, "info": 2}
    signals = list(result.signals)

    if signal_type is not None:
        signals = [s for s in signals if s.signal_type == signal_type]

    if min_severity is not None:
        min_idx = _sev_order.get(min_severity, 2)
        signals = [s for s in signals if _sev_order.get(s.severity, 2) <= min_idx]

    signals = signals[:limit]

    # ── Build response ────────────────────────────────────────────────────────
    return {
        "tool": TOOL_CDB_CONTEXT_ARCHITECT_SIGNALS,
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "scope_id": result.scope_id,
        "scanned_at": result.scanned_at,
        "total_signals": result.total_signals,
        "blocking_count": result.blocking_count,
        "watch_count": result.watch_count,
        "signals": [s.to_dict() for s in signals],
        "guardrails": list(GUARDRAILS),
        "metadata": _metadata(),
    }
