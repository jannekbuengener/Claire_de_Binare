from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.evidence_harvester.collector import EvidenceHarvesterCollector, main
from tools.evidence_harvester.models import CollectorInput, CollectorValidationError


def _fixture_payload() -> dict:
    return {
        "evidence_class": "pipeline_test_evidence",
        "evidence_class_version": "1.0",
        "produced_by": "pytest",
        "produced_at_utc": "2026-06-19T12:00:00Z",
        "source_mode": "fixture",
        "allowed_provenance_sources": ["mexc", "paper_runner"],
        "stale_after_minutes": 60,
        "candle_coverages": [
            {
                "symbol": "BTCUSDT",
                "venue": "mexc",
                "timeframe": "1m",
                "first_ts_utc": "2026-06-19T10:00:00Z",
                "last_ts_utc": "2026-06-19T10:19:00Z",
                "observed_count": 18,
                "expected_count": 20,
            }
        ],
        "regime_coverages": [
            {
                "symbol": "BTCUSDT",
                "venue": "regime_service",
                "timeframe": "1m",
                "first_ts_utc": "2026-06-19T10:00:00Z",
                "last_ts_utc": "2026-06-19T10:19:00Z",
                "observed_count": 0,
                "expected_count": 20,
                "regime_distribution": {},
            }
        ],
        "paper_chain_coverages": [
            {
                "symbol": "BTCUSDT",
                "venue": "paper_runner",
                "timeframe": "1m",
                "observation_window_hours": 2.0,
                "signal_count": 0,
                "decision_count": 0,
                "order_count": 0,
                "fill_count": 0,
                "complete_chain_count": 0,
                "partial_chain_count": 0,
            }
        ],
        "provenance_observations": [
            {"source": "mexc", "observed_count": 18, "contaminated": False},
            {"source": "replay_runner", "observed_count": 2, "contaminated": True},
        ],
    }


@pytest.mark.unit
def test_collector_report_is_deterministic_for_same_fixture() -> None:
    collector_input = CollectorInput.from_mapping(_fixture_payload())
    collector = EvidenceHarvesterCollector(stale_after_minutes=60)

    report_a = collector.collect(collector_input).to_dict()
    report_b = collector.collect(collector_input).to_dict()

    assert report_a == report_b
    assert report_a["summary"]["overall_status"] == "blocked"
    assert report_a["raw_evidence"]["observed_input_count"] == 5


@pytest.mark.unit
def test_collector_report_distinguishes_raw_and_derived_evidence() -> None:
    collector_input = CollectorInput.from_mapping(_fixture_payload())
    report = EvidenceHarvesterCollector(stale_after_minutes=60).collect(collector_input)
    payload = report.to_dict()

    assert payload["raw_evidence"]["candle_input_count"] == 1
    assert len(payload["candle_coverages"]) == 1
    assert payload["candle_coverages"][0]["coverage_pct"] == 0.9
    assert len(payload["gap_findings"]) >= 4
    gap_types = {item["gap_type"] for item in payload["gap_findings"]}
    assert "missing_candles" in gap_types
    assert "missing_regime" in gap_types
    assert "zero_paper_chains" in gap_types
    assert "provenance_contamination" in gap_types


@pytest.mark.unit
def test_collector_rejects_unknown_evidence_class() -> None:
    payload = _fixture_payload()
    payload["evidence_class"] = "not_real"

    with pytest.raises(CollectorValidationError, match="unknown evidence_class"):
        CollectorInput.from_mapping(payload)


@pytest.mark.unit
@pytest.mark.parametrize(
    "field,value,match",
    [
        ("observed_count", -1, "non-negative"),
        ("expected_count", 0, "must be > 0"),
        ("last_ts_utc", "not-a-time", "ISO-8601 UTC timestamp"),
    ],
)
def test_collector_rejects_invalid_counts_and_timestamps(
    field: str, value: object, match: str
) -> None:
    payload = _fixture_payload()
    payload["candle_coverages"][0][field] = value

    with pytest.raises(CollectorValidationError, match=match):
        CollectorInput.from_mapping(payload)


@pytest.mark.unit
def test_cli_fixture_mode_writes_json_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fixture_path = tmp_path / "collector_input.json"
    output_path = tmp_path / "collector_report.json"
    fixture_path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    exit_code = main(
        [
            "--fixture",
            str(fixture_path),
            "--output",
            str(output_path),
            "--pretty",
        ]
    )

    assert exit_code == 0
    assert output_path.exists()
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["summary"]["overall_status"] == "blocked"
    captured = capsys.readouterr()
    assert captured.out == ""
