from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from tools.arvp_chain_detector import (
    ChainDetector,
    is_malformed,
    load_events,
    normalize_event_type,
)


def _event(
    id_val: int,
    event_type: str,
    ts_str: str | None = None,
    status: str = "active",
    lineage_hash: str | None = None,
) -> dict:
    return {
        "id": id_val,
        "ts_ms": ts_str or f"2026-06-10T{10 + id_val:02d}:00:00Z",
        "event_type": event_type,
        "status": status,
        "lineage_hash": lineage_hash or f"hash_{id_val}",
    }


# ---------------------------------------------------------------------------
# 1. No events → no_events / complete false
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoEvents:
    def test_empty_events_list(self):
        detector = ChainDetector(events=[])
        assert detector.classify() == "no_events"
        result = detector.detect()
        assert result["complete"] is False
        assert result["chain_status"] == "no_events"
        assert "export_trigger" not in result

    def test_no_events_no_by_type(self):
        detector = ChainDetector()
        assert detector.classify() == "no_events"

    def test_empty_by_type_status(self):
        detector = ChainDetector(events_by_type_status=[])
        assert detector.classify() == "no_events"

    def test_no_events_event_count_none(self):
        result = ChainDetector(events=[]).detect()
        assert result["event_count"] is None

    def test_no_events_missing_all(self):
        result = ChainDetector(events=[]).detect()
        assert result["missing_steps"] == ["SIGNAL", "DECISION", "ORDER", "FILL"]


# ---------------------------------------------------------------------------
# 2. SIGNAL only → partial
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSignalOnly:
    def test_classify_signal_only(self):
        events = [_event(1, "SIGNAL")]
        detector = ChainDetector(events=events)
        assert detector.classify() == "signal_only"

    def test_detect_signal_only_not_complete(self):
        events = [_event(1, "SIGNAL")]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is False
        assert result["chain_status"] == "signal_only"
        assert "export_trigger" not in result

    def test_signal_only_via_aggregated(self):
        detector = ChainDetector(
            events_by_type_status=[
                {"event_type": "SIGNAL", "status": "active", "count": 1}
            ]
        )
        assert detector.classify() == "signal_only"


# ---------------------------------------------------------------------------
# 3. SIGNAL + DECISION → partial
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSignalDecision:
    def test_classify_signal_decision(self):
        events = [_event(1, "SIGNAL"), _event(2, "DECISION")]
        detector = ChainDetector(events=events)
        assert detector.classify() == "signal_decision"

    def test_detect_signal_decision_not_complete(self):
        events = [_event(1, "SIGNAL"), _event(2, "DECISION")]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is False
        assert result["chain_status"] == "signal_decision"
        assert result["missing_steps"] == ["ORDER", "FILL"]

    def test_signal_decision_via_aggregated(self):
        detector = ChainDetector(
            events_by_type_status=[
                {"event_type": "SIGNAL", "status": "active", "count": 1},
                {"event_type": "DECISION", "status": "executed", "count": 1},
            ]
        )
        assert detector.classify() == "signal_decision"


# ---------------------------------------------------------------------------
# 4. SIGNAL + DECISION + ORDER → partial
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSignalDecisionOrder:
    def test_classify_signal_decision_order(self):
        events = [_event(1, "SIGNAL"), _event(2, "DECISION"), _event(3, "ORDER")]
        detector = ChainDetector(events=events)
        assert detector.classify() == "signal_decision_order"

    def test_detect_signal_decision_order_not_complete(self):
        events = [_event(1, "SIGNAL"), _event(2, "DECISION"), _event(3, "ORDER")]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is False
        assert result["chain_status"] == "signal_decision_order"
        assert result["missing_steps"] == ["FILL"]

    def test_signal_decision_order_via_aggregated(self):
        detector = ChainDetector(
            events_by_type_status=[
                {"event_type": "SIGNAL", "status": "active", "count": 1},
                {"event_type": "DECISION", "status": "executed", "count": 1},
                {"event_type": "ORDER", "status": "filled", "count": 1},
            ]
        )
        assert detector.classify() == "signal_decision_order"


# ---------------------------------------------------------------------------
# 5. Full chain → complete_chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCompleteChain:
    def test_classify_complete(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER"),
            _event(4, "FILL"),
        ]
        detector = ChainDetector(events=events)
        assert detector.classify() == "complete_chain"

    def test_detect_complete(self):
        events = [
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(2, "DECISION", "2026-06-10T10:01:00Z"),
            _event(3, "ORDER", "2026-06-10T10:02:00Z"),
            _event(4, "FILL", "2026-06-10T10:03:00Z"),
        ]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is True
        assert result["chain_status"] == "complete_chain"
        assert result["event_count"] == 4
        assert result["event_ids"] == ["1", "2", "3", "4"]
        assert result["first_event_ts"] == "2026-06-10T10:00:00Z"
        assert result["last_event_ts"] == "2026-06-10T10:03:00Z"
        assert result["missing_steps"] == []
        assert "SIGNAL" in result["observed_types"]
        assert "ORDER" in result["observed_types"]
        assert "FILL" in result["observed_types"]

    def test_detect_complete_has_export_trigger(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER"),
            _event(4, "FILL"),
        ]
        result = ChainDetector(events=events).detect()
        trigger = result.get("export_trigger")
        assert trigger is not None
        assert trigger["export_candidate"] is True
        assert trigger["evidence_class"] == "natural_paper_evidence"
        assert len(trigger["next_tools"]) == 4

    def test_complete_no_mutation_flag(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER"),
            _event(4, "FILL"),
        ]
        result = ChainDetector(events=events).detect()
        assert result["no_mutation"] is True


# ---------------------------------------------------------------------------
# 6. ORDER(paper_) wird akzeptiert
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOrderPaperPrefix:
    def test_order_paper_classifies_as_order(self):
        assert normalize_event_type("ORDER(paper_)") == "ORDER"

    def test_order_paper_in_chain(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER(paper_)"),
            _event(4, "FILL"),
        ]
        detector = ChainDetector(events=events)
        assert detector.classify() == "complete_chain"

    def test_order_paper_detect_complete(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER(paper_)"),
            _event(4, "FILL"),
        ]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is True
        assert result["chain_status"] == "complete_chain"
        assert "ORDER" in result["observed_types"]

    def test_order_paper_via_aggregated(self):
        detector = ChainDetector(
            events_by_type_status=[
                {"event_type": "SIGNAL", "status": "active", "count": 1},
                {"event_type": "DECISION", "status": "executed", "count": 1},
                {"event_type": "ORDER(paper_)", "status": "filled", "count": 1},
                {"event_type": "FILL", "status": "confirmed", "count": 1},
            ]
        )
        assert detector.classify() == "complete_chain"


# ---------------------------------------------------------------------------
# 7. Out-of-order events werden korrekt sortiert
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOutOfOrder:
    def test_out_of_order_sorted_in_detect(self):
        events = [
            _event(4, "FILL", "2026-06-10T10:03:00Z"),
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(3, "ORDER", "2026-06-10T10:02:00Z"),
            _event(2, "DECISION", "2026-06-10T10:01:00Z"),
        ]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is True
        assert result["event_ids"] == ["1", "2", "3", "4"]
        assert result["first_event_ts"] == "2026-06-10T10:00:00Z"
        assert result["last_event_ts"] == "2026-06-10T10:03:00Z"

    def test_out_of_order_still_classifies_complete(self):
        events = [
            _event(4, "FILL", "2026-06-10T10:03:00Z"),
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(3, "ORDER", "2026-06-10T10:02:00Z"),
            _event(2, "DECISION", "2026-06-10T10:01:00Z"),
        ]
        detector = ChainDetector(events=events)
        assert detector.classify() == "complete_chain"


# ---------------------------------------------------------------------------
# 8. Duplicate events werden stabil behandelt
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDuplicateEvents:
    def test_exact_duplicate_ids_handled(self):
        events = [
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(2, "DECISION", "2026-06-10T10:01:00Z"),
            _event(3, "ORDER", "2026-06-10T10:02:00Z"),
            _event(4, "FILL", "2026-06-10T10:03:00Z"),
        ]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is True
        assert result["event_count"] == 5
        assert result["event_ids"] == ["1", "2", "3", "4"]

    def test_duplicate_events_different_ids(self):
        events = [
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(5, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(2, "DECISION", "2026-06-10T10:01:00Z"),
            _event(3, "ORDER", "2026-06-10T10:02:00Z"),
            _event(4, "FILL", "2026-06-10T10:03:00Z"),
        ]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is True
        assert result["event_count"] == 5
        assert result["event_ids"] == ["1", "5", "2", "3", "4"]


# ---------------------------------------------------------------------------
# 9. Malformed events → malformed_chain oder limitation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMalformedEvents:
    def test_is_malformed_no_event_type(self):
        assert is_malformed({"id": 1}) is not None

    def test_is_malformed_empty_event_type(self):
        assert is_malformed({"id": 1, "event_type": ""}) is not None

    def test_is_malformed_unknown_type(self):
        assert (
            is_malformed(
                {"id": 1, "event_type": "BOGUS", "ts_ms": "2026-01-01T00:00:00Z"}
            )
            is not None
        )

    def test_is_malformed_missing_ts(self):
        assert is_malformed({"id": 1, "event_type": "SIGNAL"}) is not None

    def test_is_malformed_empty_ts(self):
        assert is_malformed({"id": 1, "event_type": "SIGNAL", "ts_ms": ""}) is not None

    def test_is_malformed_not_a_dict(self):
        assert is_malformed("not a dict") is not None

    def test_malformed_events_classify(self):
        events = [
            {"id": 1, "event_type": "SIGNAL", "ts_ms": "2026-06-10T10:00:00Z"},
            {"id": 2, "event_type": "", "ts_ms": "2026-06-10T10:01:00Z"},
        ]
        detector = ChainDetector(events=events)
        assert detector.classify() == "malformed_chain"

    def test_malformed_events_limitation(self):
        events = [
            {"id": 1, "event_type": "SIGNAL", "ts_ms": "2026-06-10T10:00:00Z"},
            {"id": 2, "event_type": "BAD", "ts_ms": "2026-06-10T10:01:00Z"},
        ]
        result = ChainDetector(events=events).detect()
        assert any("malformed" in lim for lim in result["limitations"])

    def test_not_malformed_unknown_event_type(self):
        detector = ChainDetector(
            events_by_type_status=[
                {"event_type": "UNKNOWN", "status": "active", "count": 1}
            ]
        )
        assert detector.classify() != "malformed_chain"


# ---------------------------------------------------------------------------
# 10. Export trigger nur bei complete_chain true
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportTrigger:
    def test_no_export_on_no_events(self):
        result = ChainDetector(events=[]).detect()
        assert "export_trigger" not in result

    def test_no_export_on_signal_only(self):
        result = ChainDetector(events=[_event(1, "SIGNAL")]).detect()
        assert "export_trigger" not in result

    def test_no_export_on_signal_decision(self):
        events = [_event(1, "SIGNAL"), _event(2, "DECISION")]
        result = ChainDetector(events=events).detect()
        assert "export_trigger" not in result

    def test_no_export_on_signal_decision_order(self):
        events = [_event(1, "SIGNAL"), _event(2, "DECISION"), _event(3, "ORDER")]
        result = ChainDetector(events=events).detect()
        assert "export_trigger" not in result

    def test_export_only_on_complete(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER"),
            _event(4, "FILL"),
        ]
        result = ChainDetector(events=events).detect()
        assert "export_trigger" in result
        assert result["export_trigger"]["export_candidate"] is True
        assert result["export_trigger"]["evidence_class"] == "natural_paper_evidence"

    def test_export_trigger_structure(self):
        events = [
            _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
            _event(4, "FILL", "2026-06-10T10:03:00Z"),
            _event(2, "DECISION", "2026-06-10T10:01:00Z"),
            _event(3, "ORDER", "2026-06-10T10:02:00Z"),
        ]
        result = ChainDetector(events=events).detect()
        trigger = result["export_trigger"]
        assert trigger["suggested_window_start_utc"] == "2026-06-10T10:00:00Z"
        assert trigger["suggested_window_end_utc"] == "2026-06-10T10:03:00Z"
        assert len(trigger["next_tools"]) == 4
        assert "paper_reference_window.v1 export" in trigger["next_tools"]
        assert "replay-vs-paper compare" in trigger["next_tools"]
        assert "simulator calibration" in trigger["next_tools"]
        assert "regime scorecard" in trigger["next_tools"]


# ---------------------------------------------------------------------------
# 11. Supervisor integration — detect_chain returns only complete_chain
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSupervisorIntegration:
    def test_from_probe_result_none(self):
        from tools.arvp_chain_detector import ChainDetector

        probe = {
            "status": "ok",
            "evidence": {
                "latest_event": None,
                "events_since_campaign_start": 0,
                "events_by_type_status": [],
                "campaign_start_utc": "2026-06-10T08:00:00Z",
            },
        }
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "no_events"

    def test_from_probe_result_partial(self):
        probe = {
            "status": "ok",
            "evidence": {
                "latest_event": {"event_type": "SIGNAL"},
                "events_since_campaign_start": 1,
                "events_by_type_status": [
                    {"event_type": "SIGNAL", "status": "active", "count": 1}
                ],
            },
        }
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "signal_only"
        result = detector.detect()
        assert result["complete"] is False

    def test_from_probe_result_complete_with_events(self):
        probe = {
            "status": "ok",
            "evidence": {
                "latest_event": {"event_type": "FILL"},
                "events_since_campaign_start": 4,
                "events_by_type_status": [],
                "events": [
                    _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
                    _event(2, "DECISION", "2026-06-10T10:01:00Z"),
                    _event(3, "ORDER", "2026-06-10T10:02:00Z"),
                    _event(4, "FILL", "2026-06-10T10:03:00Z"),
                ],
            },
        }
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "complete_chain"
        result = detector.detect()
        assert result["complete"] is True
        assert result["export_trigger"]["export_candidate"] is True

    def test_from_probe_result_with_events_and_aggregated(self):
        probe = {
            "status": "ok",
            "evidence": {
                "events_since_campaign_start": 4,
                "events_by_type_status": [
                    {"event_type": "SIGNAL", "status": "active", "count": 1},
                    {"event_type": "DECISION", "status": "executed", "count": 1},
                    {"event_type": "ORDER(paper_)", "status": "filled", "count": 1},
                    {"event_type": "FILL", "status": "confirmed", "count": 1},
                ],
                "events": [
                    _event(1, "SIGNAL", "2026-06-10T10:00:00Z"),
                    _event(2, "DECISION", "2026-06-10T10:01:00Z"),
                    _event(3, "ORDER(paper_)", "2026-06-10T10:02:00Z"),
                    _event(4, "FILL", "2026-06-10T10:03:00Z"),
                ],
            },
        }
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "complete_chain"


# ---------------------------------------------------------------------------
# 12. No secrets/no live boundaries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoSecrets:
    def test_no_live_keywords_in_detector_source(self):
        with open("tools/arvp_chain_detector.py", encoding="utf-8") as f:
            source = f.read()
        for keyword in [
            "Live-Go",
            "Echtgeld-Go",
            "auto-merge",
            "INSERT",
            "UPDATE",
            "DELETE",
        ]:
            assert keyword not in source, f"forbidden keyword found: {keyword}"

    def test_no_live_keywords_in_output(self):
        events = [
            _event(1, "SIGNAL"),
            _event(2, "DECISION"),
            _event(3, "ORDER"),
            _event(4, "FILL"),
        ]
        result = ChainDetector(events=events).detect()
        output = json.dumps(result, default=str)
        for keyword in ["Live-Go", "Echtgeld", "live_trading"]:
            assert keyword not in output

    def test_no_mutation_in_outputs(self):
        for status in [
            "no_events",
            "signal_only",
            "signal_decision",
            "signal_decision_order",
            "complete_chain",
        ]:
            events = [
                _event(1, "SIGNAL"),
            ]
            if status in ("signal_decision", "signal_decision_order", "complete_chain"):
                events.append(_event(2, "DECISION"))
            if status in ("signal_decision_order", "complete_chain"):
                events.append(_event(3, "ORDER"))
            if status == "complete_chain":
                events.append(_event(4, "FILL"))
            result = ChainDetector(events=events).detect()
            assert result["no_mutation"] is True, f"no_mutation false for {status}"


# ---------------------------------------------------------------------------
# load_events edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadEvents:
    def test_load_from_list_json(self):
        events = [_event(1, "SIGNAL")]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(events, f)
            path = f.name
        try:
            loaded = load_events(path)
            assert len(loaded) == 1
            assert loaded[0]["event_type"] == "SIGNAL"
        finally:
            os.unlink(path)

    def test_load_from_probe_output(self):
        data = {
            "correlation_ledger": {
                "status": "ok",
                "evidence": {
                    "events": [_event(1, "SIGNAL"), _event(2, "FILL")],
                },
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            loaded = load_events(path)
            assert len(loaded) == 2
        finally:
            os.unlink(path)

    def test_load_nonexistent_path(self):
        with pytest.raises(FileNotFoundError):
            load_events("/nonexistent/file.json")

    def test_load_empty_file_returns_empty_list(self):
        data = {}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(data, f)
            path = f.name
        try:
            loaded = load_events(path)
            assert loaded == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Edge cases: strict_lineage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStrictLineage:
    def test_strict_lineage_no_hash(self):
        events = [
            _event(1, "SIGNAL", lineage_hash=None),
            _event(2, "DECISION", lineage_hash=None),
            _event(3, "ORDER", lineage_hash=None),
            _event(4, "FILL", lineage_hash=None),
        ]
        result = ChainDetector(events=events, strict_lineage=True).detect()
        assert result["complete"] is True
        assert any("lineage_hash" in lim for lim in result["limitations"])

    def test_strict_lineage_multiple_hashes(self):
        events = [
            _event(1, "SIGNAL", lineage_hash="abc"),
            _event(2, "DECISION", lineage_hash="def"),
            _event(3, "ORDER", lineage_hash="abc"),
            _event(4, "FILL", lineage_hash="abc"),
        ]
        result = ChainDetector(events=events, strict_lineage=True).detect()
        assert result["complete"] is True
        assert any("lineage_hash" in lim for lim in result["limitations"])

    def test_strict_lineage_single_hash(self):
        events = [
            _event(1, "SIGNAL", lineage_hash="abc"),
            _event(2, "DECISION", lineage_hash="abc"),
            _event(3, "ORDER", lineage_hash="abc"),
            _event(4, "FILL", lineage_hash="abc"),
        ]
        result = ChainDetector(events=events, strict_lineage=True).detect()
        assert result["complete"] is True
        lineage_lims = [lim for lim in result["limitations"] if "lineage_hash" in lim]
        assert len(lineage_lims) == 0


# ---------------------------------------------------------------------------
# Edge cases: from_probe_result with empty/missing data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFromProbeResultEdgeCases:
    def test_probe_without_evidence(self):
        probe = {"status": "ok"}
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "no_events"

    def test_probe_with_events_by_type_only(self):
        probe = {
            "status": "ok",
            "evidence": {
                "events_by_type_status": [
                    {"event_type": "SIGNAL", "status": "active", "count": 1},
                    {"event_type": "FILL", "status": "confirmed", "count": 1},
                ],
            },
        }
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "signal_only"

    def test_probe_with_signal_decision_order_by_type_only(self):
        probe = {
            "status": "ok",
            "evidence": {
                "events_by_type_status": [
                    {"event_type": "SIGNAL", "status": "active", "count": 1},
                    {"event_type": "DECISION", "status": "executed", "count": 1},
                    {"event_type": "ORDER", "status": "filled", "count": 1},
                ],
            },
        }
        detector = ChainDetector.from_probe_result(probe)
        assert detector.classify() == "signal_decision_order"
