"""Export a comparison-grade ARVP paper reference window from correlation_ledger (#1907).

This module is intentionally narrow:
  - input: DB rows from public.correlation_ledger within an explicit window
  - output: arvp_paper_reference_window.v1 payload compatible with #1902 compare

Design rules:
  - Fail-closed: missing/invalid required fields -> PaperReferenceExportError.
  - Explicit: strategy_id is taken from payload.strategy_id (not inferred).
  - Paper qualification: requires at least one ORDER and one FILL whose order_id
    is prefixed with "paper_".
  - Deterministic ordering: events are sorted by (timestamp_ms, event_pk).

Non-goals:
  - Changing correlation_ledger schema or write behavior
  - Heuristic chain repair
  - Any "evidence-valid" policy verdict beyond contract checks
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from core.utils.clock import utcnow
from typing import Any, Mapping, Sequence

_CONTRACT_VERSION = "arvp_paper_reference_window.v1"
_SOURCE_TABLE = "public.correlation_ledger"
_PAPER_PREFIX = "paper_"

_ALLOWED_EVENT_TYPES = {"SIGNAL", "DECISION", "ORDER", "FILL"}


class PaperReferenceExportError(ValueError):
    """Raised when correlation_ledger rows cannot form a comparison-grade window."""


def _require_non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperReferenceExportError(f"{name} must be a non-empty string")
    return value.strip()


def _require_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise PaperReferenceExportError(f"{name} must be an int")
    return value


def _require_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperReferenceExportError(f"{name} must be a JSON object")
    return value


@dataclass(frozen=True, slots=True)
class ExportRequest:
    strategy_id: str
    symbol: str
    start_ts_ms_utc: int
    end_ts_ms_utc: int
    extracted_by: str
    extracted_at_utc: str
    source_query_intent: str


def build_export_request(
    *,
    strategy_id: str,
    symbol: str,
    start_ts_ms_utc: int,
    end_ts_ms_utc: int,
    extracted_by: str,
    source_query_intent: str,
    extracted_at_utc: str | None = None,
) -> ExportRequest:
    strategy_id = _require_non_empty_string(strategy_id, "strategy_id")
    symbol = _require_non_empty_string(symbol, "symbol").upper()
    start_ts_ms_utc = int(start_ts_ms_utc)
    end_ts_ms_utc = int(end_ts_ms_utc)
    if start_ts_ms_utc <= 0 or end_ts_ms_utc <= 0 or end_ts_ms_utc <= start_ts_ms_utc:
        raise PaperReferenceExportError("start_ts_ms_utc and end_ts_ms_utc must define a positive window")
    extracted_by = _require_non_empty_string(extracted_by, "extracted_by")
    source_query_intent = _require_non_empty_string(source_query_intent, "source_query_intent")
    if extracted_at_utc is None:
        dt = utcnow()
        if dt.tzinfo is None:
            extracted_at_utc = dt.replace(tzinfo=timezone.utc).isoformat()
        else:
            extracted_at_utc = dt.astimezone(timezone.utc).isoformat()
    else:
        extracted_at_utc = _require_non_empty_string(extracted_at_utc, "extracted_at_utc")
    return ExportRequest(
        strategy_id=strategy_id,
        symbol=symbol,
        start_ts_ms_utc=start_ts_ms_utc,
        end_ts_ms_utc=end_ts_ms_utc,
        extracted_by=extracted_by,
        extracted_at_utc=extracted_at_utc,
        source_query_intent=source_query_intent,
    )


def export_paper_reference_window(
    *,
    request: ExportRequest,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Transform correlation_ledger rows into an arvp_paper_reference_window.v1 payload."""
    if not isinstance(rows, Sequence):
        raise PaperReferenceExportError("rows must be a sequence")
    if not rows:
        raise PaperReferenceExportError("rows must be non-empty")

    events: list[dict[str, Any]] = []
    saw_paper_order = False
    saw_paper_fill = False

    for idx, raw in enumerate(rows):
        row = _require_mapping(raw, f"rows[{idx}]")
        event_pk = _require_non_empty_string(row.get("event_pk"), "event_pk")
        correlation_id = _require_non_empty_string(row.get("correlation_id"), "correlation_id")
        event_type = _require_non_empty_string(row.get("event_type"), "event_type").upper()
        if event_type not in _ALLOWED_EVENT_TYPES:
            raise PaperReferenceExportError(f"event_type must be one of {_ALLOWED_EVENT_TYPES}, got {event_type!r}")
        symbol = _require_non_empty_string(row.get("symbol"), "symbol").upper()
        if symbol != request.symbol:
            raise PaperReferenceExportError(f"symbol mismatch in row: expected {request.symbol!r}, got {symbol!r}")
        timestamp_ms = _require_int(row.get("timestamp_ms"), "timestamp_ms")
        if timestamp_ms < request.start_ts_ms_utc or timestamp_ms > request.end_ts_ms_utc:
            raise PaperReferenceExportError("timestamp_ms out of requested window")

        payload = row.get("payload")
        payload = {} if payload is None else _require_mapping(payload, "payload")
        payload_strategy = _require_non_empty_string(payload.get("strategy_id"), "payload.strategy_id")
        if payload_strategy != request.strategy_id:
            raise PaperReferenceExportError(
                f"payload.strategy_id mismatch: expected {request.strategy_id!r}, got {payload_strategy!r}"
            )

        ev: dict[str, Any] = {
            "event_pk": event_pk,
            "correlation_id": correlation_id,
            "event_type": event_type,
            "symbol": symbol,
            "timestamp_ms": timestamp_ms,
            "payload": dict(payload),
        }
        # Optional chain fields (contract requires presence for certain event types, but
        # correlation_ledger allows nulls; we fail-closed when missing for those types).
        for name in ("signal_id", "decision_id", "order_id", "fill_id"):
            val = row.get(name)
            if isinstance(val, str) and val.strip():
                ev[name] = val.strip()

        if event_type == "SIGNAL":
            if "signal_id" not in ev:
                raise PaperReferenceExportError("SIGNAL event missing signal_id")
        elif event_type == "DECISION":
            if "signal_id" not in ev or "decision_id" not in ev:
                raise PaperReferenceExportError("DECISION event missing signal_id/decision_id")
        elif event_type == "ORDER":
            if "signal_id" not in ev or "decision_id" not in ev or "order_id" not in ev:
                raise PaperReferenceExportError("ORDER event missing signal_id/decision_id/order_id")
            if str(ev["order_id"]).startswith(_PAPER_PREFIX):
                saw_paper_order = True
        elif event_type == "FILL":
            if (
                "signal_id" not in ev
                or "decision_id" not in ev
                or "order_id" not in ev
                or "fill_id" not in ev
            ):
                raise PaperReferenceExportError("FILL event missing signal_id/decision_id/order_id/fill_id")
            if str(ev["order_id"]).startswith(_PAPER_PREFIX):
                saw_paper_fill = True

        events.append(ev)

    if not saw_paper_order:
        raise PaperReferenceExportError("paper qualification failed: no ORDER with paper_ prefix")
    if not saw_paper_fill:
        raise PaperReferenceExportError("paper qualification failed: no FILL with paper_ prefix")

    events.sort(key=lambda e: (int(e["timestamp_ms"]), str(e["event_pk"])))

    return {
        "contract_version": _CONTRACT_VERSION,
        "strategy_id": request.strategy_id,
        "symbol": request.symbol,
        "start_ts_ms_utc": request.start_ts_ms_utc,
        "end_ts_ms_utc": request.end_ts_ms_utc,
        "source_table": _SOURCE_TABLE,
        "source_query_intent": request.source_query_intent,
        "extracted_at_utc": request.extracted_at_utc,
        "extracted_by": request.extracted_by,
        "events": events,
    }




