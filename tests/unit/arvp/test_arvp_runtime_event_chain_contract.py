"""Fixture-based ARVP runtime event-chain contract tests (#3821).

Paper runtime chain SIGNAL → DECISION → ORDER → FILL via ChainDetector.
No Docker, network, DB, exchange, or live GitHub.
"""

from __future__ import annotations

import json

import pytest

from tools.arvp_chain_detector import ChainDetector, normalize_event_type

from tests.unit.arvp._arvp_event_chain_helpers import (
    assert_chain_detector_source_boundaries,
    assert_no_live_keywords_in_output,
    detect_chain_from_fixture,
    load_event_chain_fixture,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_PARTIAL_FIXTURES = (
    ("signal_only.json", "signal_only"),
    ("signal_decision.json", "signal_decision"),
    ("signal_decision_order.json", "signal_decision_order"),
)


def test_complete_chain_with_order_paper_prefix_promotes_export_trigger() -> None:
    result = detect_chain_from_fixture("complete_chain_paper_order.json")
    assert result["complete"] is True
    assert result["chain_status"] == "complete_chain"
    assert "ORDER" in result["observed_types"]
    assert result["export_trigger"]["export_candidate"] is True
    assert result["export_trigger"]["evidence_class"] == "natural_paper_evidence"
    assert result["no_mutation"] is True
    assert_no_live_keywords_in_output(result)


@pytest.mark.parametrize("fixture_name,expected_status", _PARTIAL_FIXTURES)
def test_partial_chains_never_promote_to_complete(
    fixture_name: str, expected_status: str
) -> None:
    result = detect_chain_from_fixture(fixture_name)
    assert result["complete"] is False
    assert result["chain_status"] == expected_status
    assert "export_trigger" not in result


def test_malformed_events_fail_closed_without_complete_chain() -> None:
    result = detect_chain_from_fixture("malformed_missing_ts.json")
    assert result["complete"] is False
    assert result["chain_status"] == "malformed_chain"
    assert "export_trigger" not in result
    assert any("malformed" in lim for lim in result["limitations"])


def test_order_paper_prefix_normalizes_to_order_type() -> None:
    assert normalize_event_type("ORDER(paper_)") == "ORDER"
    events = load_event_chain_fixture("complete_chain_paper_order.json")
    paper_orders = [e for e in events if "ORDER(paper_)" in e.get("event_type", "")]
    assert len(paper_orders) == 1
    detector = ChainDetector(events=events)
    assert detector.classify() == "complete_chain"


def test_probe_result_partial_chain_does_not_export() -> None:
    probe = {
        "status": "ok",
        "evidence": {
            "events_since_campaign_start": 2,
            "events_by_type_status": [
                {"event_type": "SIGNAL", "status": "active", "count": 1},
                {"event_type": "DECISION", "status": "executed", "count": 1},
            ],
            "events": load_event_chain_fixture("signal_decision.json"),
        },
    }
    result = ChainDetector.from_probe_result(probe).detect()
    assert result["complete"] is False
    assert result["chain_status"] == "signal_decision"
    assert "export_trigger" not in result


def test_chain_detector_source_has_no_secret_or_mutation_keywords() -> None:
    assert_chain_detector_source_boundaries()


def test_all_fixture_outputs_serialize_without_live_go_keywords() -> None:
    for name in (
        "complete_chain_paper_order.json",
        "signal_only.json",
        "signal_decision.json",
        "signal_decision_order.json",
        "malformed_missing_ts.json",
    ):
        assert_no_live_keywords_in_output(detect_chain_from_fixture(name))


def test_complete_chain_event_ids_are_deterministic() -> None:
    first = detect_chain_from_fixture("complete_chain_paper_order.json")
    second = detect_chain_from_fixture("complete_chain_paper_order.json")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
