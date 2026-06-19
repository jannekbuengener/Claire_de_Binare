from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.evidence_harvester.alerts import (
    ALERT_REPORT_SCHEMA_VERSION,
    AlertValidationError,
    alert_report_to_markdown,
    build_alert_report,
    build_issue_draft,
    load_snapshot_fixture,
    main,
)
from tools.evidence_harvester.collector import EvidenceHarvesterCollector
from tools.evidence_harvester.models import CollectorInput
from tools.evidence_harvester.snapshot import build_snapshot


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


def _snapshot_payload() -> dict[str, object]:
    collector_input = CollectorInput.from_mapping(_fixture_payload())
    report = EvidenceHarvesterCollector(stale_after_minutes=60).collect(collector_input)
    snapshot = build_snapshot(report.to_dict(), generated_at_utc="2026-06-19T16:00:00Z")
    return snapshot.to_dict()


@pytest.mark.unit
def test_alert_report_is_deterministic_for_same_snapshot_and_time() -> None:
    snapshot = _snapshot_payload()

    report_a = build_alert_report(
        snapshot,
        evaluated_at_utc="2026-06-19T16:00:00Z",
    ).to_dict()
    report_b = build_alert_report(
        snapshot,
        evaluated_at_utc="2026-06-19T16:00:00Z",
    ).to_dict()

    assert report_a == report_b
    assert report_a["schema_version"] == ALERT_REPORT_SCHEMA_VERSION
    assert report_a["summary"]["highest_severity"] == "critical"


@pytest.mark.unit
def test_alert_report_classifies_required_gaps_and_deduplicates_by_finding_id() -> None:
    snapshot = _snapshot_payload()
    duplicate = dict(snapshot["gap_findings"]["items"][0])
    duplicate["gap_id"] = "gap-999"
    snapshot["gap_findings"]["items"] = tuple(snapshot["gap_findings"]["items"]) + (
        duplicate,
    )

    report = build_alert_report(
        snapshot,
        evaluated_at_utc="2026-06-19T16:00:00Z",
    ).to_dict()
    finding_types = {item["finding_type"] for item in report["findings"]}

    assert report["summary"]["critical_count"] >= 4
    assert "stale_feed" in finding_types
    assert "missing_candles" in finding_types
    assert "missing_regime" in finding_types
    assert "zero_paper_chains" in finding_types
    assert "provenance_contamination" in finding_types
    stale_feed_findings = [
        item for item in report["findings"] if item["finding_type"] == "stale_feed"
    ]
    assert len(stale_feed_findings) == 1
    assert stale_feed_findings[0]["finding_id"].startswith("alert-")


@pytest.mark.unit
def test_alert_report_adds_stale_snapshot_finding_from_evaluation_time() -> None:
    report = build_alert_report(
        _snapshot_payload(),
        evaluated_at_utc="2026-06-19T22:30:00Z",
        stale_snapshot_after_minutes=180,
        critical_snapshot_after_minutes=360,
    ).to_dict()

    stale_snapshot = [
        item for item in report["findings"] if item["finding_type"] == "stale_snapshot"
    ]
    assert report["snapshot_age_minutes"] == 390
    assert stale_snapshot
    assert stale_snapshot[0]["severity"] == "critical"


@pytest.mark.unit
def test_alert_report_rejects_malformed_snapshot() -> None:
    snapshot = _snapshot_payload()
    del snapshot["metadata"]["collector_report_id"]

    with pytest.raises(AlertValidationError, match="metadata malformed"):
        build_alert_report(snapshot)


@pytest.mark.unit
def test_issue_draft_and_markdown_are_plain_text_outputs_only() -> None:
    report = build_alert_report(
        _snapshot_payload(),
        evaluated_at_utc="2026-06-19T16:00:00Z",
    )

    markdown = alert_report_to_markdown(report)
    issue_draft = build_issue_draft(report, issue_number=3350, parent_issue=3345)

    assert markdown.startswith("# Evidence Alert Report\n")
    assert "manual only; no automatic GitHub writes" in markdown
    assert "Manual escalation draft only." in issue_draft
    assert "#3350" in issue_draft
    assert "#3345" in issue_draft


@pytest.mark.unit
def test_cli_writes_alert_report_and_issue_draft(tmp_path: Path) -> None:
    fixture_path = tmp_path / "snapshot.json"
    json_output = tmp_path / "alerts.json"
    markdown_output = tmp_path / "alerts.md"
    issue_output = tmp_path / "issue_draft.md"
    fixture_path.write_text(json.dumps(_snapshot_payload()), encoding="utf-8")

    exit_code = main(
        [
            "--fixture",
            str(fixture_path),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
            "--issue-draft-output",
            str(issue_output),
            "--evaluated-at-utc",
            "2026-06-19T16:00:00Z",
            "--issue-number",
            "3350",
            "--parent-issue",
            "3345",
            "--pretty",
        ]
    )

    assert exit_code == 0
    payload = json.loads(json_output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == ALERT_REPORT_SCHEMA_VERSION
    assert "# Evidence Alert Report\n" in markdown_output.read_text(encoding="utf-8")
    assert "Manual escalation draft only." in issue_output.read_text(encoding="utf-8")


@pytest.mark.unit
def test_load_snapshot_fixture_rejects_non_object_json(tmp_path: Path) -> None:
    fixture_path = tmp_path / "snapshot.json"
    fixture_path.write_text("[]", encoding="utf-8")

    with pytest.raises(AlertValidationError, match="Snapshot fixture JSON root"):
        load_snapshot_fixture(fixture_path)
