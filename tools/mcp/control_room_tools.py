"""MCP adapter layer for Wave-19 visual control room view builder tool.

Issues:
    #2180 — [SURREALDB][CONTEXT][CONTROL-ROOM] Implement control room view builder v1
    Parent: #2179 (Wave-19 anchor)
    Epic: #1976

Adapts the Wave-19 Visual Control Room View Builder domain service for the MCP
tool surface. The tool is read-only, fail-closed, and carries explicit no-live-go
semantics. No DB access. No SurrealDB SDK. No network. No writes. No auto-fix.
No live-go. No trading console. No runtime control.

Bundle-driven:
    The tool operates exclusively on the in-memory bundle passed as input.
    If no bundle is supplied the tool returns a clean error — it never
    reads from a database, filesystem, or network to fill the gap.
"""

from __future__ import annotations

from typing import Any, Mapping

from tools.surrealdb.control_room_view_builder import (
    EXPORT_FORMATS,
    GUARDRAILS,
    VIEW_TYPES,
    ControlRoomError,
    build_all_views_v1,
    build_control_room_view_v1,
)

TOOL_CDB_CONTROL_ROOM_VIEW = "cdb_control_room_view"
SCHEMA_VERSION = "control-room-view-mcp/v1"


# ── Internal helpers ──────────────────────────────────────────────────────────


def _metadata() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "guardrails": list(GUARDRAILS),
        "supported_view_types": sorted(VIEW_TYPES),
        "export_formats": list(EXPORT_FORMATS),
    }


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "tool": TOOL_CDB_CONTROL_ROOM_VIEW,
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "error_code": code,
        "message": message,
        "guardrails": list(GUARDRAILS),
        "metadata": _metadata(),
    }


def _as_str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


# ── Public handler ────────────────────────────────────────────────────────────


def handle_control_room_view(
    bundle: Mapping[str, Any] | None = None,
    view_type: str | None = None,
    filters: Mapping[str, Any] | None = None,
    as_of: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """MCP handler for cdb_control_room_view.

    Args:
        bundle:     In-memory context bundle (required).
        view_type:  Optional — one of VIEW_TYPES.  If omitted, all 9 views are built.
        filters:    Optional filter map (key → value).
        as_of:      Optional ISO-8601 timestamp for deterministic test output.

    Returns:
        Dict with status='ok' and view(s), or status='error'.
    """
    # ── Input validation ──────────────────────────────────────────────────────
    if bundle is None:
        return _error_response(
            "missing_bundle",
            "bundle is required. Pass an in-memory context bundle as input.",
        )
    if not isinstance(bundle, Mapping):
        return _error_response("invalid_bundle", "bundle must be a Mapping (dict).")

    resolved_as_of = _as_str_or_none(as_of or kwargs.get("as_of"))

    resolved_filters: dict[str, Any] = {}
    if filters and isinstance(filters, Mapping):
        resolved_filters = dict(filters)

    resolved_view_type = _as_str_or_none(view_type or kwargs.get("view_type"))

    # ── Build view(s) ─────────────────────────────────────────────────────────
    try:
        if resolved_view_type is not None:
            view = build_control_room_view_v1(
                view_type=resolved_view_type,
                bundle=bundle,
                filters=resolved_filters,
                as_of=resolved_as_of,
            )
            return {
                "tool": TOOL_CDB_CONTROL_ROOM_VIEW,
                "schema_version": SCHEMA_VERSION,
                "status": "ok",
                "view_type": resolved_view_type,
                "view": view.to_dict(),
                "guardrails": list(GUARDRAILS),
                "metadata": _metadata(),
            }
        else:
            views = build_all_views_v1(
                bundle=bundle,
                filters=resolved_filters,
                as_of=resolved_as_of,
            )
            return {
                "tool": TOOL_CDB_CONTROL_ROOM_VIEW,
                "schema_version": SCHEMA_VERSION,
                "status": "ok",
                "view_type": "all",
                "views": [v.to_dict() for v in views],
                "view_count": len(views),
                "guardrails": list(GUARDRAILS),
                "metadata": _metadata(),
            }

    except ControlRoomError as exc:
        return _error_response("builder_error", str(exc))
    except Exception as exc:  # noqa: BLE001 - fail-closed
        return _error_response("internal_error", f"unexpected error: {exc}")
