"""ARVP parallel strategy ledger/evidence isolation contract tests (#3911).

Guards that mixed correlation_ledger windows from PB1 + Donchian publishers
remain separable via strategy_id / bot_id / config_hash qualifiers on export.
No runtime, Docker, or live DB.
"""

from __future__ import annotations

import pytest

from core.replay.paper_reference_window_export import (
    PaperReferenceExportError,
    build_export_request,
    export_paper_reference_window,
)
from tests.unit.arvp import _arvp_parallel_ledger_isolation_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_FIXTURE = helpers.load_parallel_isolation_fixture()
_PB1 = _FIXTURE.strategies["pb1"]
_DONCHIAN = _FIXTURE.strategies["donchian"]


def test_mixed_fixture_declares_distinct_parallel_strategy_context() -> None:
    assert _PB1["strategy_id"] != _DONCHIAN["strategy_id"]
    assert _PB1["bot_id"] != _DONCHIAN["bot_id"]
    assert _PB1["config_hash"] != _DONCHIAN["config_hash"]
    assert _PB1["correlation_id"] != _DONCHIAN["correlation_id"]


def test_pb1_export_with_bot_id_returns_only_pb1_chain() -> None:
    result = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
        bot_id=_PB1["bot_id"],
        config_hash=_PB1["config_hash"],
    )
    helpers.assert_zero_cross_strategy_rows(
        result,
        foreign_correlation_ids={_DONCHIAN["correlation_id"]},
        foreign_strategy_ids={_DONCHIAN["strategy_id"]},
    )
    assert result.payload["strategy_id"] == _PB1["strategy_id"]
    assert helpers.correlation_ids_in_payload(result.payload) == {
        _PB1["correlation_id"]
    }
    assert helpers.count_paper_fills(result.payload) == 1


def test_donchian_export_with_bot_id_returns_only_donchian_chain() -> None:
    result = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_DONCHIAN["strategy_id"],
        bot_id=_DONCHIAN["bot_id"],
        config_hash=_DONCHIAN["config_hash"],
    )
    helpers.assert_zero_cross_strategy_rows(
        result,
        foreign_correlation_ids={_PB1["correlation_id"]},
        foreign_strategy_ids={_PB1["strategy_id"]},
    )
    assert result.payload["strategy_id"] == _DONCHIAN["strategy_id"]
    assert helpers.correlation_ids_in_payload(result.payload) == {
        _DONCHIAN["correlation_id"]
    }
    assert helpers.count_paper_fills(result.payload) == 1


def test_shared_window_does_not_merge_evidence_counts_without_qualifiers() -> None:
    pb1 = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
        bot_id=_PB1["bot_id"],
    )
    donchian = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_DONCHIAN["strategy_id"],
        bot_id=_DONCHIAN["bot_id"],
    )
    assert helpers.count_paper_fills(pb1.payload) == 1
    assert helpers.count_paper_fills(donchian.payload) == 1
    combined_rows = len(pb1.payload["events"]) + len(donchian.payload["events"])
    assert combined_rows == 6
    assert len(_FIXTURE.ledger_rows) == 6


def test_unqualified_export_fails_closed_on_mixed_bot_id_same_strategy() -> None:
    """Same strategy_id + mixed bot_id without qualifier still fails homogeneity guard."""
    rows = [
        row
        for row in helpers.ledger_rows_copy(_FIXTURE)
        if row["correlation_id"] in {_PB1["correlation_id"], _DONCHIAN["correlation_id"]}
    ]
    for row in rows:
        payload = row["payload"]
        payload["strategy_id"] = _PB1["strategy_id"]
        if row["event_type"] == "SIGNAL":
            payload["bot_id"] = (
                _PB1["bot_id"]
                if row["correlation_id"] == _PB1["correlation_id"]
                else _DONCHIAN["bot_id"]
            )
            metadata = payload["metadata"]
            metadata["bot_id"] = payload["bot_id"]
            metadata["config_snapshot"]["bot_id"] = payload["bot_id"]
            metadata["config_snapshot"]["strategy_id"] = _PB1["strategy_id"]
    request = helpers.build_strategy_export_request(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
    )
    with pytest.raises(PaperReferenceExportError, match="mixed bot_id"):
        export_paper_reference_window(request=request, rows=rows)


def test_wrong_bot_id_filter_fails_closed_with_no_matching_anchors() -> None:
    request = helpers.build_strategy_export_request(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
        bot_id=_DONCHIAN["bot_id"],
    )
    with pytest.raises(PaperReferenceExportError, match="no SIGNAL anchors matched"):
        export_paper_reference_window(
            request=request, rows=helpers.ledger_rows_copy(_FIXTURE)
        )


def test_contradictory_bot_id_on_matching_strategy_fails_closed() -> None:
    request = helpers.build_strategy_export_request(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
        bot_id=_DONCHIAN["bot_id"],
        config_hash=_DONCHIAN["config_hash"],
    )
    with pytest.raises(PaperReferenceExportError, match="no SIGNAL anchors matched"):
        export_paper_reference_window(
            request=request, rows=helpers.ledger_rows_copy(_FIXTURE)
        )


def test_cross_strategy_request_with_foreign_bot_id_fails_closed() -> None:
    request = build_export_request(
        strategy_id=_DONCHIAN["strategy_id"],
        symbol=_FIXTURE.symbol,
        start_ts_ms_utc=_FIXTURE.start_ts_ms_utc,
        end_ts_ms_utc=_FIXTURE.end_ts_ms_utc,
        extracted_by="unit-test",
        extracted_at_utc="2026-07-09T00:00:00+00:00",
        source_query_intent="unit-test",
        bot_id=_PB1["bot_id"],
        config_hash=_PB1["config_hash"],
    )
    with pytest.raises(
        PaperReferenceExportError,
        match="no SIGNAL anchors matched|window contains no SIGNAL anchors",
    ):
        export_paper_reference_window(
            request=request, rows=helpers.ledger_rows_copy(_FIXTURE)
        )


def test_export_request_requires_non_empty_strategy_id() -> None:
    """Export request must name strategy_id; empty qualifier is rejected at build time."""
    with pytest.raises(PaperReferenceExportError, match="strategy_id must be a non-empty"):
        build_export_request(
            strategy_id="",
            symbol=_FIXTURE.symbol,
            start_ts_ms_utc=_FIXTURE.start_ts_ms_utc,
            end_ts_ms_utc=_FIXTURE.end_ts_ms_utc,
            extracted_by="unit-test",
            extracted_at_utc="2026-07-09T00:00:00+00:00",
            source_query_intent="unit-test",
        )


def test_bot_id_only_filter_separates_shared_topic_publishers() -> None:
    """Shared Redis `signals` topic: bot_id qualifier isolates per-publisher evidence."""
    pb1 = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
        bot_id=_PB1["bot_id"],
    )
    donchian = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_DONCHIAN["strategy_id"],
        bot_id=_DONCHIAN["bot_id"],
    )
    assert helpers.correlation_ids_in_payload(pb1.payload).isdisjoint(
        helpers.correlation_ids_in_payload(donchian.payload)
    )


def test_config_hash_filter_narrows_to_single_publisher_chain() -> None:
    pb1 = helpers.export_strategy_evidence(
        _FIXTURE,
        strategy_id=_PB1["strategy_id"],
        config_hash=_PB1["config_hash"],
    )
    assert helpers.correlation_ids_in_payload(pb1.payload) == {
        _PB1["correlation_id"]
    }
