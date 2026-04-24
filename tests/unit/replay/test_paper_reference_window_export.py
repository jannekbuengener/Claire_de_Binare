"""Unit tests for core/replay/paper_reference_window_export.py (#1907)."""

from __future__ import annotations

import pytest

from core.replay.paper_reference_window_export import (
    PaperReferenceExportError,
    build_export_request,
    export_paper_reference_window,
)


def _req():
    return build_export_request(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=1000,
        end_ts_ms_utc=2000,
        extracted_by="unit-test",
        extracted_at_utc="2026-04-24T00:00:00+00:00",
        source_query_intent="unit-test",
    )


def test_exports_sorted_events_and_requires_paper_order_fill() -> None:
    request = _req()
    rows = [
        {
            "event_pk": "b",
            "correlation_id": "c1",
            "signal_id": "sig1",
            "decision_id": None,
            "order_id": None,
            "fill_id": None,
            "event_type": "SIGNAL",
            "symbol": "BTCUSDT",
            "timestamp_ms": 1500,
            "payload": {"strategy_id": "primary_breakout_v1"},
        },
        {
            "event_pk": "a",
            "correlation_id": "c1",
            "signal_id": "sig1",
            "decision_id": "dec1",
            "order_id": "paper_001",
            "fill_id": None,
            "event_type": "ORDER",
            "symbol": "BTCUSDT",
            "timestamp_ms": 1400,
            "payload": {"strategy_id": "primary_breakout_v1"},
        },
        {
            "event_pk": "c",
            "correlation_id": "c1",
            "signal_id": "sig1",
            "decision_id": "dec1",
            "order_id": "paper_001",
            "fill_id": "fill1",
            "event_type": "FILL",
            "symbol": "BTCUSDT",
            "timestamp_ms": 1600,
            "payload": {"strategy_id": "primary_breakout_v1"},
        },
    ]
    payload = export_paper_reference_window(request=request, rows=rows)
    assert payload["contract_version"] == "arvp_paper_reference_window.v1"
    assert payload["strategy_id"] == "primary_breakout_v1"
    assert payload["symbol"] == "BTCUSDT"
    assert [e["event_pk"] for e in payload["events"]] == ["a", "b", "c"]


def test_fails_closed_when_no_paper_fill() -> None:
    request = _req()
    rows = [
        {
            "event_pk": "a",
            "correlation_id": "c1",
            "signal_id": "sig1",
            "decision_id": "dec1",
            "order_id": "paper_001",
            "fill_id": None,
            "event_type": "ORDER",
            "symbol": "BTCUSDT",
            "timestamp_ms": 1400,
            "payload": {"strategy_id": "primary_breakout_v1"},
        }
    ]
    with pytest.raises(PaperReferenceExportError, match="no FILL"):
        export_paper_reference_window(request=request, rows=rows)


def test_fails_closed_on_strategy_mismatch() -> None:
    request = _req()
    rows = [
        {
            "event_pk": "a",
            "correlation_id": "c1",
            "signal_id": "sig1",
            "decision_id": "dec1",
            "order_id": "paper_001",
            "fill_id": "fill1",
            "event_type": "FILL",
            "symbol": "BTCUSDT",
            "timestamp_ms": 1500,
            "payload": {"strategy_id": "other"},
        }
    ]
    with pytest.raises(PaperReferenceExportError, match="payload\\.strategy_id mismatch"):
        export_paper_reference_window(request=request, rows=rows)

