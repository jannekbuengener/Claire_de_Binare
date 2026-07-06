"""Operator drill evidence pack contract tests (#3874).

Parent #3872. Fixture-based scoring only — no runtime drill, no secrets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.unit.test_pack._test_pack_contract_helpers import (
    EVIDENCE_README_TEMPLATE,
    FIXTURES_ROOT,
    KILL_SWITCH_CHECKLIST_REPO,
    OPERATOR_DRILL_SCRIPT,
    OPERATOR_ACTION_EVENTS,
    TIMESTAMP_FIELD_NAMES,
    VERDICT_VALUES,
    scan_text_for_secrets,
    score_operator_evidence_pack,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_ROOT / name).read_text(encoding="utf-8"))


def test_evidence_pack_readme_template_exists_with_required_anchors() -> None:
    text = EVIDENCE_README_TEMPLATE.read_text(encoding="utf-8")
    assert "PASS/FAIL" in text
    assert "Date/Time (UTC)" in text
    assert "Operator (if drill)" in text
    assert "sources_manifest.txt" in text
    assert "run_config.json" in text


def test_operator_drill_script_documents_safety_boundaries() -> None:
    text = OPERATOR_DRILL_SCRIPT.read_text(encoding="utf-8")
    assert "experimental" in text.lower() or "secondary helper" in text.lower()
    assert "not the canonical" in text.lower()
    assert "Write-Warning" in text or "console alert" in text.lower()


def test_repo_native_kill_switch_checklist_is_successor_reference() -> None:
    pack_runbook = Path(__file__).resolve().parents[3] / "tools" / "test_pack" / "runbooks" / "kill_switch_checklist.md"
    pack_text = pack_runbook.read_text(encoding="utf-8")
    assert "Deprecated" in pack_text
    assert KILL_SWITCH_CHECKLIST_REPO.is_file()
    repo_text = KILL_SWITCH_CHECKLIST_REPO.read_text(encoding="utf-8")
    assert "8002" in repo_text
    assert "LR-003" not in repo_text or "Avoid stale" in repo_text


def test_complete_evidence_pack_fixture_scores_pass() -> None:
    pack = _load_fixture("operator_evidence_pack_complete.json")
    result = score_operator_evidence_pack(pack)
    assert result.verdict == "PASS"
    assert not result.missing_fields


def test_missing_operator_evidence_fixture_is_not_pass() -> None:
    pack = _load_fixture("operator_evidence_pack_incomplete.json")
    result = score_operator_evidence_pack(pack)
    assert result.verdict == "FAIL"
    assert result.missing_fields


def test_unknown_kill_switch_state_fixture_is_fail_closed() -> None:
    pack = _load_fixture("operator_evidence_pack_unknown_ks.json")
    result = score_operator_evidence_pack(pack)
    assert result.verdict == "FAIL"
    assert "unknown kill-switch state" in " ".join(result.reasons).lower()


def test_warn_semantics_allowed_for_partial_evidence() -> None:
    pack = _load_fixture("operator_evidence_pack_warn.json")
    result = score_operator_evidence_pack(pack)
    assert result.verdict == "WARN"


def test_secret_like_content_fails_no_secret_contract() -> None:
    pack = _load_fixture("operator_evidence_pack_complete.json")
    pack["readme_text"] += "\napi_key=super-secret-value-12345678"
    result = score_operator_evidence_pack(pack)
    assert result.verdict == "FAIL"
    assert scan_text_for_secrets(pack["readme_text"])


def test_pass_fail_verdict_values_are_enumerated() -> None:
    assert "PASS" in VERDICT_VALUES
    assert "WARN" in VERDICT_VALUES
    assert "FAIL" in VERDICT_VALUES


def test_operator_action_events_include_verification_markers() -> None:
    assert "ALERT_TRIGGERED" in OPERATOR_ACTION_EVENTS
    assert "VERIFY_KILL_SWITCH_ACTIVE" in OPERATOR_ACTION_EVENTS


def test_timestamp_field_names_cover_timeline_contract() -> None:
    assert "ts" in TIMESTAMP_FIELD_NAMES
    assert "ts_utc" in TIMESTAMP_FIELD_NAMES
