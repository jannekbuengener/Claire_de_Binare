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


def _optional_non_empty_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PaperReferenceExportError(f"{name} must be a string when provided")
    stripped = value.strip()
    if not stripped:
        raise PaperReferenceExportError(f"{name} must be non-empty when provided")
    return stripped


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip()


def _require_signal_metadata(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = payload.get("metadata")
    return _require_mapping(metadata, "payload.metadata")


def _resolve_signal_bot_id(payload: Mapping[str, Any]) -> str:
    payload_bot_id = _optional_string(payload.get("bot_id"))
    if payload_bot_id:
        return payload_bot_id

    metadata = _require_signal_metadata(payload)
    metadata_bot_id = _optional_string(metadata.get("bot_id"))
    if metadata_bot_id:
        return metadata_bot_id

    config_snapshot = _require_mapping(
        metadata.get("config_snapshot"), "payload.metadata.config_snapshot"
    )
    snapshot_bot_id = config_snapshot.get("bot_id")
    if not isinstance(snapshot_bot_id, str):
        raise PaperReferenceExportError(
            "payload.metadata.config_snapshot.bot_id must be a string"
        )
    return snapshot_bot_id.strip()


def _resolve_signal_config_hash(payload: Mapping[str, Any]) -> str:
    metadata = _require_signal_metadata(payload)
    return _require_non_empty_string(
        metadata.get("config_hash"), "payload.metadata.config_hash"
    )


@dataclass(frozen=True, slots=True)
class SignalAnchor:
    correlation_id: str
    signal_id: str
    bot_id: str
    config_hash: str


@dataclass(frozen=True, slots=True)
class ExportRequest:
    strategy_id: str
    symbol: str
    start_ts_ms_utc: int
    end_ts_ms_utc: int
    extracted_by: str
    extracted_at_utc: str
    source_query_intent: str
    bot_id: str | None = None
    config_hash: str | None = None


def build_export_request(
    *,
    strategy_id: str,
    symbol: str,
    start_ts_ms_utc: int,
    end_ts_ms_utc: int,
    extracted_by: str,
    source_query_intent: str,
    extracted_at_utc: str | None = None,
    bot_id: str | None = None,
    config_hash: str | None = None,
) -> ExportRequest:
    strategy_id = _require_non_empty_string(strategy_id, "strategy_id")
    symbol = _require_non_empty_string(symbol, "symbol").upper()
    start_ts_ms_utc = int(start_ts_ms_utc)
    end_ts_ms_utc = int(end_ts_ms_utc)
    if start_ts_ms_utc <= 0 or end_ts_ms_utc <= 0 or end_ts_ms_utc <= start_ts_ms_utc:
        raise PaperReferenceExportError(
            "start_ts_ms_utc and end_ts_ms_utc must define a positive window"
        )
    extracted_by = _require_non_empty_string(extracted_by, "extracted_by")
    source_query_intent = _require_non_empty_string(
        source_query_intent, "source_query_intent"
    )
    bot_id = _optional_non_empty_string(bot_id, "bot_id")
    config_hash = _optional_non_empty_string(config_hash, "config_hash")
    if extracted_at_utc is None:
        dt = utcnow()
        if dt.tzinfo is None:
            extracted_at_utc = dt.replace(tzinfo=timezone.utc).isoformat()
        else:
            extracted_at_utc = dt.astimezone(timezone.utc).isoformat()
    else:
        extracted_at_utc = _require_non_empty_string(
            extracted_at_utc, "extracted_at_utc"
        )
    return ExportRequest(
        strategy_id=strategy_id,
        symbol=symbol,
        start_ts_ms_utc=start_ts_ms_utc,
        end_ts_ms_utc=end_ts_ms_utc,
        extracted_by=extracted_by,
        extracted_at_utc=extracted_at_utc,
        source_query_intent=source_query_intent,
        bot_id=bot_id,
        config_hash=config_hash,
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

    all_events: list[dict[str, Any]] = []
    signal_anchors: dict[str, SignalAnchor] = {}

    for idx, raw in enumerate(rows):
        row = _require_mapping(raw, f"rows[{idx}]")
        event_pk = _require_non_empty_string(row.get("event_pk"), "event_pk")
        correlation_id = _require_non_empty_string(
            row.get("correlation_id"), "correlation_id"
        )
        event_type = _require_non_empty_string(
            row.get("event_type"), "event_type"
        ).upper()
        if event_type not in _ALLOWED_EVENT_TYPES:
            raise PaperReferenceExportError(
                f"event_type must be one of {_ALLOWED_EVENT_TYPES}, got {event_type!r}"
            )
        symbol = _require_non_empty_string(row.get("symbol"), "symbol").upper()
        if symbol != request.symbol:
            raise PaperReferenceExportError(
                f"symbol mismatch in row: expected {request.symbol!r}, got {symbol!r}"
            )
        timestamp_ms = _require_int(row.get("timestamp_ms"), "timestamp_ms")
        if (
            timestamp_ms < request.start_ts_ms_utc
            or timestamp_ms > request.end_ts_ms_utc
        ):
            raise PaperReferenceExportError("timestamp_ms out of requested window")

        payload = row.get("payload")
        payload = {} if payload is None else _require_mapping(payload, "payload")
        payload_strategy = _require_non_empty_string(
            payload.get("strategy_id"), "payload.strategy_id"
        )
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
            anchor = SignalAnchor(
                correlation_id=correlation_id,
                signal_id=str(ev["signal_id"]),
                bot_id=_resolve_signal_bot_id(payload),
                config_hash=_resolve_signal_config_hash(payload),
            )
            existing = signal_anchors.get(correlation_id)
            if existing is not None:
                raise PaperReferenceExportError(
                    f"correlation_id {correlation_id!r} has multiple SIGNAL anchors"
                )
            signal_anchors[correlation_id] = anchor
        elif event_type == "DECISION":
            if "signal_id" not in ev or "decision_id" not in ev:
                raise PaperReferenceExportError(
                    "DECISION event missing signal_id/decision_id"
                )
        elif event_type == "ORDER":
            if "signal_id" not in ev or "decision_id" not in ev or "order_id" not in ev:
                raise PaperReferenceExportError(
                    "ORDER event missing signal_id/decision_id/order_id"
                )
        elif event_type == "FILL":
            if (
                "signal_id" not in ev
                or "decision_id" not in ev
                or "order_id" not in ev
                or "fill_id" not in ev
            ):
                raise PaperReferenceExportError(
                    "FILL event missing signal_id/decision_id/order_id/fill_id"
                )

        all_events.append(ev)

    if not signal_anchors:
        raise PaperReferenceExportError(
            "chain-integrity failed: window contains no SIGNAL anchors"
        )

    for ev in all_events:
        if ev["event_type"] == "SIGNAL":
            continue
        correlation_id = str(ev["correlation_id"])
        anchor = signal_anchors.get(correlation_id)
        if anchor is None:
            raise PaperReferenceExportError(
                f"chain-integrity failed: missing SIGNAL anchor for correlation_id {correlation_id!r}"
            )
        event_signal_id = _require_non_empty_string(
            ev.get("signal_id"), f"events[{correlation_id}].signal_id"
        )
        if event_signal_id != anchor.signal_id:
            raise PaperReferenceExportError(
                "chain-integrity failed: event signal_id does not match SIGNAL anchor "
                f"for correlation_id {correlation_id!r}"
            )

    selected_correlation_ids: set[str] = set()
    for correlation_id, anchor in signal_anchors.items():
        if request.bot_id is not None and anchor.bot_id != request.bot_id:
            continue
        if (
            request.config_hash is not None
            and anchor.config_hash != request.config_hash
        ):
            continue
        selected_correlation_ids.add(correlation_id)

    if request.bot_id is not None or request.config_hash is not None:
        if not selected_correlation_ids:
            raise PaperReferenceExportError(
                "no SIGNAL anchors matched requested bot_id/config_hash filters"
            )
    else:
        selected_correlation_ids = set(signal_anchors)

    events: list[dict[str, Any]] = []
    saw_paper_order = False
    saw_paper_fill = False
    selected_bot_ids: set[str] = set()
    selected_config_hashes: set[str] = set()

    for correlation_id in selected_correlation_ids:
        anchor = signal_anchors[correlation_id]
        selected_bot_ids.add(anchor.bot_id)
        selected_config_hashes.add(anchor.config_hash)

    for ev in all_events:
        correlation_id = str(ev["correlation_id"])
        if correlation_id not in selected_correlation_ids:
            continue

        if ev["event_type"] == "ORDER" and str(ev["order_id"]).startswith(
            _PAPER_PREFIX
        ):
            saw_paper_order = True
        if ev["event_type"] == "FILL" and str(ev["order_id"]).startswith(_PAPER_PREFIX):
            saw_paper_fill = True

        events.append(ev)

    if len(selected_bot_ids) != 1:
        raise PaperReferenceExportError(
            "homogeneity guard failed: mixed bot_id across SIGNAL anchors in export window"
        )
    if len(selected_config_hashes) != 1:
        raise PaperReferenceExportError(
            "homogeneity guard failed: mixed metadata.config_hash across SIGNAL anchors in export window"
        )

    if not saw_paper_order:
        raise PaperReferenceExportError(
            "paper qualification failed: no ORDER with paper_ prefix"
        )
    if not saw_paper_fill:
        raise PaperReferenceExportError(
            "paper qualification failed: no FILL with paper_ prefix"
        )

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
