from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.evidence_harvester.collector import EvidenceHarvesterCollector
from tools.evidence_harvester.models import CollectorInput
from tools.evidence_harvester.snapshot import (
    SAFETY_BANNER,
    SNAPSHOT_SCHEMA_VERSION,
    SnapshotValidationError,
    build_snapshot,
    main,
    snapshot_to_markdown,
)


def _fixture_payload() -> dict[str, object]:
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


def _collector_report_dict() -> dict[str, object]:
    collector_input = CollectorInput.from_mapping(_fixture_payload())
    return (
        EvidenceHarvesterCollector(stale_after_minutes=60)
        .collect(collector_input)
        .to_dict()
    )


@pytest.mark.unit
def test_snapshot_is_deterministic_for_same_report_and_time() -> None:
    report = _collector_report_dict()
    snapshot_a = build_snapshot(report, generated_at_utc="2026-06-19T16:00:00Z")
    snapshot_b = build_snapshot(report, generated_at_utc="2026-06-19T16:00:00Z")

    assert snapshot_a.to_dict() == snapshot_b.to_dict()
    assert snapshot_a.to_dict()["metadata"]["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert (
        snapshot_a.to_dict()["metadata"]["generated_at_utc"] == "2026-06-19T16:00:00Z"
    )
    assert snapshot_a.to_dict()["metadata"]["collector_report_hash"].startswith(
        "sha256:"
    )


@pytest.mark.unit
def test_snapshot_json_and_markdown_share_same_normalized_object() -> None:
    snapshot = build_snapshot(
        _collector_report_dict(),
        generated_at_utc="2026-06-19T16:00:00Z",
    )

    payload = snapshot.to_dict()
    markdown = snapshot_to_markdown(snapshot)

    assert set(payload) >= {
        "metadata",
        "status",
        "coverage",
        "provenance",
        "paper_chains",
        "gap_findings",
        "safety",
        "next_action_hints",
    }
    assert payload["coverage"]["candles"]["coverage_pct"] == 0.9
    assert payload["coverage"]["regimes"]["coverage_pct"] == 0.0
    assert payload["paper_chains"]["complete_chain_count_total"] == 0
    assert payload["provenance"]["status"] == "blocked"
    assert payload["safety"]["banner"] == SAFETY_BANNER
    assert "## Status" in markdown
    assert "## Coverage Summary" in markdown
    assert "## Paper Chain Summary" in markdown
    assert "## Provenance" in markdown
    assert "## Gap Findings" in markdown
    assert "## Safety Boundaries" in markdown
    assert "## Next Action Hints" in markdown
    assert SAFETY_BANNER in markdown


@pytest.mark.unit
def test_snapshot_rejects_invalid_source_mode() -> None:
    report = _collector_report_dict()
    report["source_mode"] = "live_runtime"

    with pytest.raises(
        SnapshotValidationError,
        match=r"collector_report.source_mode must be one of fixture\|future_readonly",
    ):
        build_snapshot(report, generated_at_utc="2026-06-19T16:00:00Z")


@pytest.mark.unit
def test_snapshot_rejects_malformed_collector_report() -> None:
    report = _collector_report_dict()
    del report["summary"]

    with pytest.raises(SnapshotValidationError, match="collector_report malformed"):
        build_snapshot(report, generated_at_utc="2026-06-19T16:00:00Z")


@pytest.mark.unit
def test_snapshot_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    fixture_path = tmp_path / "collector_report.json"
    json_output = tmp_path / "snapshot.json"
    markdown_output = tmp_path / "snapshot.md"
    fixture_path.write_text(json.dumps(_collector_report_dict()), encoding="utf-8")

    exit_code = main(
        [
            "--fixture",
            str(fixture_path),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
            "--generated-at-utc",
            "2026-06-19T16:00:00Z",
            "--pretty",
        ]
    )

    assert exit_code == 0
    snapshot_payload = json.loads(json_output.read_text(encoding="utf-8"))
    markdown_text = markdown_output.read_text(encoding="utf-8")
    assert snapshot_payload["metadata"]["generated_at_utc"] == "2026-06-19T16:00:00Z"
    assert snapshot_payload["status"]["overall_status"] == "blocked"
    assert markdown_text.startswith("# Daily Evidence Snapshot\n")
    assert "Collector report hash:" in markdown_text
