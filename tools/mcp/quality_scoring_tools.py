"""MCP adapter layer for Wave-18 quality scoring tool.

Issues:
    #2173 — [SURREALDB][CONTEXT][QUALITY-MCP] Implement quality score MCP tool
    Parent: #2170 (Wave-18 anchor)
    Epic: #1976

Adapts the Wave-18-A knowledge quality scoring domain service for the MCP tool
surface. The tool is read-only, fail-closed, and carries explicit no-live-go
semantics. No DB access. No SurrealDB SDK. No network. No writes. No auto-fix.
No live-go.

Bundle-driven:
    The tool operates exclusively on the in-memory bundle passed as input.
    If no bundle is supplied the tool returns a clean error — it never
    reads from a database, filesystem, or network to fill the gap.
"""

from __future__ import annotations

from typing import Any, Mapping

from tools.surrealdb.quality_scoring import (
    GRADES,
    GUARDRAILS,
    SCORE_DIMENSIONS,
    QualityScoringError,
    score_knowledge_quality_v1,
)

TOOL_CDB_CONTEXT_QUALITY_SCORE = "cdb_context_quality_score"
SCHEMA_VERSION = "quality-score-mcp/v1"

_MAX_LIMIT = 500
_DEFAULT_LIMIT = 100
_VALID_GRADES: frozenset[str] = frozenset(GRADES)
_VALID_DIMENSIONS: frozenset[str] = frozenset(SCORE_DIMENSIONS)


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
        "tool": TOOL_CDB_CONTEXT_QUALITY_SCORE,
        "status": "error",
        "error": {"code": code, "message": message},
    }


def _metadata(read_only: bool = True) -> dict[str, Any]:
    return {"source": "in_memory", "read_only": read_only}


# ── Main handler ──────────────────────────────────────────────────────────────


def handle_quality_score(**kwargs: Any) -> dict[str, Any]:
    """Handle a ``cdb_context_quality_score`` MCP tool call.

    Required parameters:
        bundle (dict): Input quality bundle.

    Optional filter parameters:
        dimension (str): Show only a single score dimension.
        min_grade (str): Filter dimensions to those at or below this grade.
        limit (int): Maximum number of dimensions to return (default 100).
        as_of (str): Advisory ISO-8601 UTC timestamp passed to the scorer.

    Returns a read-only quality score result. ``metadata.read_only`` is
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
    dimension = _as_str_or_none(kwargs.get("dimension"))
    if dimension is not None and dimension not in _VALID_DIMENSIONS:
        return _error_response(
            "invalid_dimension",
            f"dimension {dimension!r} is not valid. "
            f"Valid: {', '.join(sorted(_VALID_DIMENSIONS))}",
        )

    min_grade = _as_str_or_none(kwargs.get("min_grade"))
    if min_grade is not None and min_grade not in _VALID_GRADES:
        return _error_response(
            "invalid_grade",
            f"min_grade {min_grade!r} is not valid. Valid: {', '.join(sorted(_VALID_GRADES))}",
        )

    raw_limit = kwargs.get("limit", _DEFAULT_LIMIT)
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        limit = _DEFAULT_LIMIT
    limit = min(max(limit, 1), _MAX_LIMIT)

    as_of = _as_str_or_none(kwargs.get("as_of"))

    # ── Score ─────────────────────────────────────────────────────────────────
    try:
        result = score_knowledge_quality_v1(bundle, as_of=as_of)
    except QualityScoringError as exc:
        return _error_response("scoring_error", str(exc))
    except Exception as exc:  # noqa: BLE001 - fail-closed
        return _error_response("internal_error", f"unexpected error: {exc}")

    # ── Filter dimensions ─────────────────────────────────────────────────────
    _grade_order = {"blocking": 0, "watch": 1, "weak": 2, "good": 3}
    dims = list(result.dimensions)

    if dimension is not None:
        dims = [d for d in dims if d.dimension == dimension]

    if min_grade is not None:
        min_idx = _grade_order.get(min_grade, 3)
        dims = [d for d in dims if _grade_order.get(d.grade, 3) <= min_idx]

    dims = dims[:limit]

    # ── Build response ────────────────────────────────────────────────────────
    return {
        "tool": TOOL_CDB_CONTEXT_QUALITY_SCORE,
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "scope_id": result.scope_id,
        "level": result.level,
        "scored_at": result.scored_at,
        "overall_score": result.overall_score,
        "overall_grade": result.overall_grade,
        "blocking_dimensions": list(result.blocking_dimensions),
        "watch_dimensions": list(result.watch_dimensions),
        "recommended_next_reads": list(result.recommended_next_reads),
        "dimensions": [d.to_dict() for d in dims],
        "guardrails": list(GUARDRAILS),
        "metadata": _metadata(),
    }
