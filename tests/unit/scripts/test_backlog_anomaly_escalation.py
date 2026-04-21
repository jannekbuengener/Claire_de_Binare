from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / ".github" / "scripts" / "backlog_anomaly_escalation.py"

_SPEC = importlib.util.spec_from_file_location("backlog_anomaly_escalation", SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
escalation = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = escalation
_SPEC.loader.exec_module(escalation)


def _anomaly(
    *,
    anomaly_id: str,
    anomaly_type: str,
    confidence: float,
    strength: str,
    escalation_hint: str,
    public_issue_allowed: bool = True,
) -> dict[str, object]:
    return {
        "id": anomaly_id,
        "type": anomaly_type,
        "confidence": confidence,
        "strength": strength,
        "summary": "example",
        "evidence": ["path_missing:.github/workflows/missing.yml"],
        "affected_artifacts": [".github/workflows/missing.yml"],
        "minimum_evidence_met": True,
        "escalation_hint": escalation_hint,
        "public_issue_allowed": public_issue_allowed,
    }


def _artifact(findings: list[dict[str, object]], *, sensitive: bool = False) -> dict[str, object]:
    return {
        "schema_version": "v2",
        "issue": {
            "number": 1795,
            "title": "Backlog curation escalation",
            "url": "https://github.com/jannekbuengener/Claire_de_Binare/issues/1795",
        },
        "fingerprint": "fp-1795",
        "read_budget": {
            "must_read_max": 3,
            "supporting_max": 4,
            "background_max": 2,
            "estimated_tokens": 1200,
        },
        "reuse": {
            "fingerprint": "fp-1795",
            "receipt_marker": "<!-- cdb-backlog-curation-receipt:fp-1795 -->",
            "unchanged_issue_can_reuse": True,
            "strategy": "reuse if unchanged",
        },
        "receipt": {
            "marker": "<!-- cdb-backlog-curation-receipt:fp-1795 -->",
            "status": "curation ready",
            "fingerprint": "fp-1795",
            "top_sources": [
                ".github/scripts/backlog_curation.py",
                ".github/workflows/cdb-backlog-curation.yml",
            ],
            "next_step": "Read must_read first.",
            "artifact_name": "backlog-curation-issue-1795",
            "artifact_ref": "artifacts/backlog-curation/issue-1795.json",
            "body": "receipt",
        },
        "handoff": {
            "must_read": [],
            "supporting": [],
            "background": [],
            "constraints": [],
            "watchouts": [],
            "implementation_targets": [],
        },
        "operator_review_needed": False,
        "safe_for_implementation_start": True,
        "anomalies": {
            "schema_version": "v1",
            "contains_sensitive_signals": sensitive,
            "sensitivity_reasons": ["security label"] if sensitive else [],
            "findings": findings,
        },
    }


def test_classify_strong_broken_reference_as_follow_up_issue() -> None:
    classification, confidence, reason = escalation.classify_anomaly(
        anomaly=_anomaly(
            anomaly_id="abc123",
            anomaly_type="broken_reference",
            confidence=0.93,
            strength="strong",
            escalation_hint="follow_up_candidate",
        ),
        artifact_sensitive=False,
        artifact_sensitive_reasons=[],
    )

    assert classification == "follow_up_issue"
    assert confidence == 0.93
    assert "Strong typed anomaly" in reason


def test_classify_weak_signal_as_report_only() -> None:
    classification, _, reason = escalation.classify_anomaly(
        anomaly=_anomaly(
            anomaly_id="weak1",
            anomaly_type="workflow_doc_drift",
            confidence=0.58,
            strength="weak",
            escalation_hint="report_only",
        ),
        artifact_sensitive=False,
        artifact_sensitive_reasons=[],
    )

    assert classification == "report_only"
    assert "Weak/low-confidence" in reason


def test_classify_medium_signal_as_unclear() -> None:
    classification, _, reason = escalation.classify_anomaly(
        anomaly=_anomaly(
            anomaly_id="med1",
            anomaly_type="architecture_doc_drift",
            confidence=0.8,
            strength="medium",
            escalation_hint="unclear",
        ),
        artifact_sensitive=False,
        artifact_sensitive_reasons=[],
    )

    assert classification == "unclear"
    assert "ambiguous" in reason


def test_sensitive_context_forces_report_only() -> None:
    classification, _, reason = escalation.classify_anomaly(
        anomaly=_anomaly(
            anomaly_id="sec1",
            anomaly_type="broken_reference",
            confidence=0.99,
            strength="strong",
            escalation_hint="follow_up_candidate",
            public_issue_allowed=False,
        ),
        artifact_sensitive=True,
        artifact_sensitive_reasons=["security label"],
    )

    assert classification == "report_only"
    assert "Sensitive/private context" in reason


def test_dedupe_matches_existing_open_issue() -> None:
    marker = escalation.FOLLOWUP_MARKER_TEMPLATE.format(fingerprint="dup123")
    existing = [
        {
            "number": 2001,
            "title": "Backlog anomaly: broken_reference in issue #1795",
            "body": marker + "\nSource issue: #1795",
            "created_at": "2026-04-20T08:00:00Z",
            "html_url": "https://github.com/jannekbuengener/Claire_de_Binare/issues/2001",
        }
    ]

    match, mode = escalation.find_existing_followup(
        open_issues=existing,
        marker=marker,
        source_issue_number=1795,
        anomaly_type="broken_reference",
    )

    assert match is not None
    assert match["number"] == 2001
    assert mode == "marker_match"


def test_ensure_followup_issue_reuses_existing_ticket(monkeypatch: pytest.MonkeyPatch) -> None:
    marker = escalation.FOLLOWUP_MARKER_TEMPLATE.format(fingerprint="dup456")
    open_issues = [
        {
            "number": 2111,
            "title": "Backlog anomaly: broken_reference in issue #1795",
            "body": marker + "\nSource issue: #1795",
            "created_at": "2026-04-20T08:00:00Z",
            "html_url": "https://github.com/jannekbuengener/Claire_de_Binare/issues/2111",
        }
    ]

    def _forbidden_run(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("gh issue create must not run when dedupe matches")

    monkeypatch.setattr(escalation, "run", _forbidden_run)
    result = escalation.ensure_followup_issue(
        repo="jannekbuengener/Claire_de_Binare",
        source_issue={
            "number": 1795,
            "url": "https://github.com/jannekbuengener/Claire_de_Binare/issues/1795",
        },
        anomaly=_anomaly(
            anomaly_id="dup456",
            anomaly_type="broken_reference",
            confidence=0.93,
            strength="strong",
            escalation_hint="follow_up_candidate",
        ),
        decision_reason="Strong typed anomaly passed threshold and escalation hint gates.",
        open_issues=open_issues,
    )

    assert result["action"] == "existing"
    assert result["number"] == 2111


def test_load_artifact_accepts_v2_handoff_extras(tmp_path: Path) -> None:
    artifact = _artifact(
        [
            _anomaly(
                anomaly_id="follow1",
                anomaly_type="broken_reference",
                confidence=0.94,
                strength="strong",
                escalation_hint="follow_up_candidate",
            )
        ]
    )
    artifact_file = tmp_path / "issue-1795.json"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    loaded = escalation.load_artifact(artifact_file)

    assert loaded["schema_version"] == "v2"
    assert loaded["anomalies"]["findings"][0]["id"] == "follow1"


def test_main_dry_run_does_not_emit_issues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = _artifact(
        [
            _anomaly(
                anomaly_id="follow1",
                anomaly_type="broken_reference",
                confidence=0.94,
                strength="strong",
                escalation_hint="follow_up_candidate",
            )
        ]
    )
    artifact_file = tmp_path / "issue-1795.json"
    result_file = tmp_path / "result.json"
    summary_file = tmp_path / "summary.md"
    artifact_file.write_text(json.dumps(artifact), encoding="utf-8")

    called: dict[str, int] = {"ensure": 0}

    def _never_called(**kwargs):  # noqa: ANN003
        called["ensure"] += 1
        return {}

    monkeypatch.setattr(escalation, "ensure_followup_issue", _never_called)
    monkeypatch.setattr(
        escalation,
        "parse_args",
        lambda: Namespace(
            repo="jannekbuengener/Claire_de_Binare",
            artifact_file=artifact_file,
            result_file=result_file,
            summary_file=summary_file,
            publish_mode="dry_run",
            max_followup_issues=1,
        ),
    )

    rc = escalation.main()

    assert rc == 0
    assert called["ensure"] == 0
    result = json.loads(result_file.read_text(encoding="utf-8"))
    assert result["decision_counts"]["follow_up_issue"] == 1
    assert result["issue_events"] == []


def test_backlog_curation_workflow_posts_receipt_and_uses_existing_labels_only() -> None:
    workflow_path = REPO_ROOT / ".github" / "workflows" / "cdb-backlog-curation.yml"
    workflow_text = workflow_path.read_text(encoding="utf-8")
    payload = yaml.safe_load(workflow_text)

    assert payload["permissions"] == {"contents": "read", "issues": "write"}
    step_names = [step["name"] for step in payload["jobs"]["curate"]["steps"]]
    assert "Post issue-scoped curation receipt" in step_names
    assert "context:curate" not in workflow_text
