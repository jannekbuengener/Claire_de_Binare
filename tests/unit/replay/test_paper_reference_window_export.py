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


def _signal_payload(
    *,
    strategy_id: str = "primary_breakout_v1",
    bot_id: str = "bot-a",
    config_hash: str = "cfg-a",
) -> dict:
    return {
        "strategy_id": strategy_id,
        "bot_id": bot_id,
        "metadata": {
            "bot_id": bot_id,
            "config_hash": config_hash,
            "config_snapshot": {
                "strategy_id": strategy_id,
                "bot_id": bot_id,
            },
        },
    }


def _signal_row(
    *,
    event_pk: str,
    correlation_id: str,
    signal_id: str,
    timestamp_ms: int,
    strategy_id: str = "primary_breakout_v1",
    bot_id: str = "bot-a",
    config_hash: str = "cfg-a",
) -> dict:
    return {
        "event_pk": event_pk,
        "correlation_id": correlation_id,
        "signal_id": signal_id,
        "decision_id": None,
        "order_id": None,
        "fill_id": None,
        "event_type": "SIGNAL",
        "symbol": "BTCUSDT",
        "timestamp_ms": timestamp_ms,
        "payload": _signal_payload(
            strategy_id=strategy_id,
            bot_id=bot_id,
            config_hash=config_hash,
        ),
    }


def _order_row(
    *,
    event_pk: str,
    correlation_id: str,
    signal_id: str,
    decision_id: str,
    order_id: str,
    timestamp_ms: int,
    strategy_id: str = "primary_breakout_v1",
) -> dict:
    return {
        "event_pk": event_pk,
        "correlation_id": correlation_id,
        "signal_id": signal_id,
        "decision_id": decision_id,
        "order_id": order_id,
        "fill_id": None,
        "event_type": "ORDER",
        "symbol": "BTCUSDT",
        "timestamp_ms": timestamp_ms,
        "payload": {"strategy_id": strategy_id},
    }


def _fill_row(
    *,
    event_pk: str,
    correlation_id: str,
    signal_id: str,
    decision_id: str,
    order_id: str,
    fill_id: str,
    timestamp_ms: int,
    strategy_id: str = "primary_breakout_v1",
) -> dict:
    return {
        "event_pk": event_pk,
        "correlation_id": correlation_id,
        "signal_id": signal_id,
        "decision_id": decision_id,
        "order_id": order_id,
        "fill_id": fill_id,
        "event_type": "FILL",
        "symbol": "BTCUSDT",
        "timestamp_ms": timestamp_ms,
        "payload": {"strategy_id": strategy_id},
    }


def test_exports_sorted_events_and_requires_paper_order_fill() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="b",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
        _order_row(
            event_pk="a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1400,
        ),
        _fill_row(
            event_pk="c",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1600,
        ),
    ]
    payload = export_paper_reference_window(request=request, rows=rows)
    assert payload["contract_version"] == "arvp_paper_reference_window.v1"
    assert payload["strategy_id"] == "primary_breakout_v1"
    assert payload["symbol"] == "BTCUSDT"
    assert [e["event_pk"] for e in payload["events"]] == ["a", "b", "c"]


def test_fails_closed_when_no_paper_fill() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1300,
        ),
        _order_row(
            event_pk="a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1400,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="no FILL"):
        export_paper_reference_window(request=request, rows=rows)


def _decision_row(
    *,
    event_pk: str,
    correlation_id: str,
    signal_id: str,
    decision_id: str,
    timestamp_ms: int,
    strategy_id: str | None = "SENTINEL_NO_STRATEGY",
) -> dict:
    payload: dict = {
        "decision_id": decision_id,
        "signal_id": signal_id,
        "regime_id": "HIGH_VOL_CHAOTIC",
        "contract_version": "1.0",
    }
    if strategy_id != "SENTINEL_NO_STRATEGY":
        payload["strategy_id"] = strategy_id
    return {
        "event_pk": event_pk,
        "correlation_id": correlation_id,
        "signal_id": signal_id,
        "decision_id": decision_id,
        "order_id": None,
        "fill_id": None,
        "event_type": "DECISION",
        "symbol": "BTCUSDT",
        "timestamp_ms": timestamp_ms,
        "payload": payload,
    }


def test_decision_without_payload_strategy_id_resolves_from_signal_anchor() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
        ),
        _decision_row(
            event_pk="dec-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            timestamp_ms=1200,
        ),
        _order_row(
            event_pk="ord-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1300,
        ),
        _fill_row(
            event_pk="fill-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1400,
        ),
    ]
    payload = export_paper_reference_window(request=request, rows=rows)
    assert payload["strategy_id"] == "primary_breakout_v1"
    events_by_type = {e["event_type"]: e for e in payload["events"]}
    assert events_by_type["DECISION"]["payload"]["strategy_id"] == "primary_breakout_v1"


def test_decision_rows_all_missing_strategy_id_resolved_from_signal() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
        ),
        _decision_row(
            event_pk="dec-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            timestamp_ms=1200,
        ),
        _decision_row(
            event_pk="dec-1b",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1b",
            timestamp_ms=1250,
        ),
        _order_row(
            event_pk="ord-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1300,
        ),
        _fill_row(
            event_pk="fill-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1400,
        ),
    ]
    payload = export_paper_reference_window(request=request, rows=rows)
    assert payload["strategy_id"] == "primary_breakout_v1"
    for ev in payload["events"]:
        if ev["event_type"] == "DECISION":
            assert ev["payload"]["strategy_id"] == "primary_breakout_v1"


def test_mixed_strategy_chain_rejected_even_when_signal_anchor_resolves() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
        ),
        _decision_row(
            event_pk="dec-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            timestamp_ms=1200,
        ),
        _order_row(
            event_pk="ord-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1300,
            strategy_id="other_strategy",
        ),
        _fill_row(
            event_pk="fill-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1400,
        ),
    ]
    with pytest.raises(
        PaperReferenceExportError, match="payload\\.strategy_id mismatch"
    ):
        export_paper_reference_window(request=request, rows=rows)


def test_chain_no_signal_anchor_cannot_resolve_strategy() -> None:
    request = _req()
    rows = [
        _decision_row(
            event_pk="dec-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            timestamp_ms=1200,
        ),
        _order_row(
            event_pk="ord-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1300,
        ),
        _fill_row(
            event_pk="fill-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1400,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="no SIGNAL anchors"):
        export_paper_reference_window(request=request, rows=rows)


def test_decision_with_explicit_strategy_id_matching_request_accepted() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
        ),
        _decision_row(
            event_pk="dec-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            timestamp_ms=1200,
            strategy_id="primary_breakout_v1",
        ),
        _order_row(
            event_pk="ord-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1300,
        ),
        _fill_row(
            event_pk="fill-1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1400,
        ),
    ]
    payload = export_paper_reference_window(request=request, rows=rows)
    assert payload["strategy_id"] == "primary_breakout_v1"


def test_fails_closed_on_strategy_mismatch() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1400,
        ),
        _fill_row(
            event_pk="a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1500,
            strategy_id="other",
        ),
    ]
    with pytest.raises(
        PaperReferenceExportError, match="payload\\.strategy_id mismatch"
    ):
        export_paper_reference_window(request=request, rows=rows)


def test_fails_closed_on_mixed_config_hash() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
            config_hash="cfg-a",
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
        _signal_row(
            event_pk="sig-b",
            correlation_id="c2",
            signal_id="sig2",
            timestamp_ms=1400,
            config_hash="cfg-b",
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="mixed metadata\\.config_hash"):
        export_paper_reference_window(request=request, rows=rows)


def test_fails_closed_on_mixed_bot_id() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
            bot_id="bot-a",
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
        _signal_row(
            event_pk="sig-b",
            correlation_id="c2",
            signal_id="sig2",
            timestamp_ms=1400,
            bot_id="bot-b",
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="mixed bot_id"):
        export_paper_reference_window(request=request, rows=rows)


def test_fails_closed_when_signal_config_hash_missing() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
    ]
    rows[0]["payload"]["metadata"].pop("config_hash")

    with pytest.raises(
        PaperReferenceExportError, match="payload\\.metadata\\.config_hash"
    ):
        export_paper_reference_window(request=request, rows=rows)


def test_fails_closed_when_order_chain_has_no_signal_anchor() -> None:
    request = _req()
    rows = [
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="no SIGNAL anchors"):
        export_paper_reference_window(request=request, rows=rows)


def test_fails_closed_when_chain_signal_id_mismatches_anchor() -> None:
    request = _req()
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig-X",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="does not match SIGNAL anchor"):
        export_paper_reference_window(request=request, rows=rows)


def test_filters_export_by_config_hash_and_bot_id() -> None:
    request = build_export_request(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=1000,
        end_ts_ms_utc=2000,
        extracted_by="unit-test",
        extracted_at_utc="2026-04-24T00:00:00+00:00",
        source_query_intent="unit-test",
        bot_id="bot-a",
        config_hash="cfg-a",
    )
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
            bot_id="bot-a",
            config_hash="cfg-a",
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
        _signal_row(
            event_pk="sig-b",
            correlation_id="c2",
            signal_id="sig2",
            timestamp_ms=1400,
            bot_id="bot-b",
            config_hash="cfg-b",
        ),
    ]

    payload = export_paper_reference_window(request=request, rows=rows)

    assert [event["correlation_id"] for event in payload["events"]] == [
        "c1",
        "c1",
        "c1",
    ]


def test_filters_export_by_bot_id_only() -> None:
    request = build_export_request(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=1000,
        end_ts_ms_utc=2000,
        extracted_by="unit-test",
        extracted_at_utc="2026-04-24T00:00:00+00:00",
        source_query_intent="unit-test",
        bot_id="bot-a",
    )
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
            bot_id="bot-a",
            config_hash="cfg-a",
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
        _signal_row(
            event_pk="sig-b",
            correlation_id="c2",
            signal_id="sig2",
            timestamp_ms=1400,
            bot_id="bot-b",
            config_hash="cfg-a",
        ),
    ]

    payload = export_paper_reference_window(request=request, rows=rows)

    assert [event["correlation_id"] for event in payload["events"]] == [
        "c1",
        "c1",
        "c1",
    ]
    assert [event["event_type"] for event in payload["events"]] == [
        "SIGNAL",
        "ORDER",
        "FILL",
    ]


def test_filters_export_by_trimmed_config_snapshot_bot_id_fallback() -> None:
    request = build_export_request(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=1000,
        end_ts_ms_utc=2000,
        extracted_by="unit-test",
        extracted_at_utc="2026-04-24T00:00:00+00:00",
        source_query_intent="unit-test",
        bot_id="bot-a",
    )
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
            bot_id="bot-a",
            config_hash="cfg-a",
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
        _signal_row(
            event_pk="sig-b",
            correlation_id="c2",
            signal_id="sig2",
            timestamp_ms=1400,
            bot_id="bot-b",
            config_hash="cfg-a",
        ),
    ]
    rows[0]["payload"].pop("bot_id")
    rows[0]["payload"]["metadata"].pop("bot_id")
    rows[0]["payload"]["metadata"]["config_snapshot"]["bot_id"] = "  bot-a  "

    payload = export_paper_reference_window(request=request, rows=rows)

    assert [event["correlation_id"] for event in payload["events"]] == [
        "c1",
        "c1",
        "c1",
    ]
    assert [event["event_type"] for event in payload["events"]] == [
        "SIGNAL",
        "ORDER",
        "FILL",
    ]


def test_filters_export_by_config_hash_only() -> None:
    request = build_export_request(
        strategy_id="primary_breakout_v1",
        symbol="BTCUSDT",
        start_ts_ms_utc=1000,
        end_ts_ms_utc=2000,
        extracted_by="unit-test",
        extracted_at_utc="2026-04-24T00:00:00+00:00",
        source_query_intent="unit-test",
        config_hash="cfg-a",
    )
    rows = [
        _signal_row(
            event_pk="sig-a",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1100,
            bot_id="bot-a",
            config_hash="cfg-a",
        ),
        _order_row(
            event_pk="ord-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1200,
        ),
        _fill_row(
            event_pk="fill-a",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1300,
        ),
        _signal_row(
            event_pk="sig-b",
            correlation_id="c2",
            signal_id="sig2",
            timestamp_ms=1400,
            bot_id="bot-a",
            config_hash="cfg-b",
        ),
    ]

    payload = export_paper_reference_window(request=request, rows=rows)

    assert [event["correlation_id"] for event in payload["events"]] == [
        "c1",
        "c1",
        "c1",
    ]
    assert [event["event_type"] for event in payload["events"]] == [
        "SIGNAL",
        "ORDER",
        "FILL",
    ]


# ---------------------------------------------------------------------------
# Causal context events (#3058)
# ---------------------------------------------------------------------------


def test_exports_causal_context_events_when_provided() -> None:
    """causal_context_rows populate causal_context_events array with metadata."""
    request = _req()
    rows = [
        _signal_row(
            event_pk="in-signal",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
        _order_row(
            event_pk="in-order",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1600,
        ),
        _fill_row(
            event_pk="in-fill",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1700,
        ),
    ]
    causal = [
        _signal_row(
            event_pk="causal-sig-1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=500,  # outside window [1000, 2000]
        ),
    ]
    payload = export_paper_reference_window(
        request=request, rows=rows, causal_context_rows=causal
    )

    assert "causal_context_events" in payload
    assert len(payload["causal_context_events"]) == 1
    ce = payload["causal_context_events"][0]
    assert ce["event_type"] == "SIGNAL"
    assert ce["in_window"] is False
    assert ce["context_scope"] == "pre_window_causal"
    assert ce["signal_id"] == "sig1"
    assert "causal_for_event_ids" in ce
    # Still 1 in-window SIGNAL (pilot: 0 in-window + 1 causal = 1 total)
    assert len(payload["events"]) == 3


def test_causal_context_main_events_unchanged() -> None:
    """causal_context_rows do not affect main events list."""
    request = _req()
    rows = [
        _signal_row(
            event_pk="s1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
        _order_row(
            event_pk="o1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1600,
        ),
        _fill_row(
            event_pk="f1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1700,
        ),
    ]
    # Build causal row with timestamp outside window
    causal = [
        _signal_row(
            event_pk="causal-s1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=500,
        ),
    ]
    no_causal = export_paper_reference_window(request=request, rows=rows)
    with_causal = export_paper_reference_window(
        request=request, rows=rows, causal_context_rows=causal
    )
    assert no_causal["events"] == with_causal["events"]
    assert no_causal["causal_context_events"] == []
    assert len(with_causal["causal_context_events"]) == 1


def test_causal_context_signal_inside_window_fails_closed() -> None:
    """causal_context_rows must be outside window bounds."""
    request = _req()
    rows = [
        _signal_row(
            event_pk="s1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
        _order_row(
            event_pk="o1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1600,
        ),
        _fill_row(
            event_pk="f1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1700,
        ),
    ]
    # signal at 1500 is inside window [1000, 2000]
    causal_inside = [
        _signal_row(
            event_pk="bad",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="is inside window"):
        export_paper_reference_window(
            request=request, rows=rows, causal_context_rows=causal_inside
        )


def test_causal_context_unmatched_signal_id_fails_closed() -> None:
    """causal SIGNAL must have signal_id matching in-window ORDER/FILL."""
    request = _req()
    rows = [
        _signal_row(
            event_pk="s1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
        _order_row(
            event_pk="o1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1600,
        ),
        _fill_row(
            event_pk="f1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1700,
        ),
    ]
    causal_unmatched = [
        _signal_row(
            event_pk="unmatched",
            correlation_id="c2",
            signal_id="sig-orphan",
            timestamp_ms=500,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="has no matching ORDER/FILL"):
        export_paper_reference_window(
            request=request, rows=rows, causal_context_rows=causal_unmatched
        )


def test_causal_context_non_signal_type_fails_closed() -> None:
    """causal_context_rows must be SIGNAL events."""
    request = _req()
    rows = [
        _signal_row(
            event_pk="s1",
            correlation_id="c1",
            signal_id="sig1",
            timestamp_ms=1500,
        ),
        _order_row(
            event_pk="o1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            timestamp_ms=1600,
        ),
        _fill_row(
            event_pk="f1",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_001",
            fill_id="fill1",
            timestamp_ms=1700,
        ),
    ]
    causal_bad_type = [
        _order_row(
            event_pk="bad-type",
            correlation_id="c1",
            signal_id="sig1",
            decision_id="dec1",
            order_id="paper_999",
            timestamp_ms=500,
        ),
    ]
    with pytest.raises(PaperReferenceExportError, match="SIGNAL"):
        export_paper_reference_window(
            request=request, rows=rows, causal_context_rows=causal_bad_type
        )
