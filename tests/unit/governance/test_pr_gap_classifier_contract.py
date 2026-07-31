"""Contract tests for cdb-pr-gap-classifier (#4208)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "config" / "governance" / "pr-acceptance-policy.v1.yaml"
SKILL = ROOT / "docs" / "skills" / "cdb-pr-gap-classifier" / "SKILL.md"

GAP_CLASSES = [
    "MUST_FIX_IN_CURRENT_PR",
    "FOLLOWUP_AFTER_MERGE",
    "SEPARATE_DEDICATED_PR",
    "PARKED_NOT_ACTIVE",
    "NOT_A_REAL_GAP",
]
OUTPUT_FIELDS = [
    "gap_id",
    "classification",
    "summary",
    "affected_claim",
    "current_pr_fix_required",
    "separate_issue_required",
    "suggested_issue_target",
    "why_not_now",
    "evidence_ids",
    "dedupe_result",
]


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_exactly_five_gap_classes() -> None:
    policy = _policy()
    text = _skill()
    assert policy["gap_classes"] == GAP_CLASSES
    assert len(GAP_CLASSES) == 5
    for gap_class in GAP_CLASSES:
        assert gap_class in text
    assert "Exactly five gap classes" in text


def test_required_output_fields() -> None:
    text = _skill()
    for field in OUTPUT_FIELDS:
        assert f"`{field}`" in text


def test_insufficient_evidence_blocks_class() -> None:
    text = _skill()
    assert "BLOCKED_INSUFFICIENT_EVIDENCE" in text
    assert "classification=null" in text or "**no** class" in text
    assert "BLOCKED_INSUFFICIENT_EVIDENCE" in _policy()["gap_classification_status"]


def test_dedupe_does_not_change_class() -> None:
    text = _skill()
    assert "does **not** change the fachliche class" in text
    assert "does not discover findings" in text
    assert "does not create issues" in text


def test_must_fix_and_separate_rules() -> None:
    text = _skill()
    assert "MUST_FIX_IN_CURRENT_PR" in text
    assert "SEPARATE_DEDICATED_PR" in text
    assert "FOLLOWUP_AFTER_MERGE" in text
    assert "PARKED_NOT_ACTIVE" in text
    assert "NOT_A_REAL_GAP" in text


def _classify(
    *,
    evidence_ok: bool,
    current_claim_false: bool,
    separate_scope: bool,
    hardening_only: bool,
    parked: bool,
    false_positive: bool,
    dedupe_issue: int | None,
) -> dict:
    """Minimal deterministic classifier mirror for contract coverage."""
    if not evidence_ok:
        return {
            "classification_status": "BLOCKED_INSUFFICIENT_EVIDENCE",
            "classification": None,
            "dedupe_result": {
                "matched_existing": dedupe_issue is not None,
                "existing_issue": dedupe_issue,
            },
        }
    if current_claim_false:
        classification = "MUST_FIX_IN_CURRENT_PR"
    elif separate_scope:
        classification = "SEPARATE_DEDICATED_PR"
    elif hardening_only:
        classification = "FOLLOWUP_AFTER_MERGE"
    elif parked:
        classification = "PARKED_NOT_ACTIVE"
    elif false_positive:
        classification = "NOT_A_REAL_GAP"
    else:
        raise AssertionError("unclassified fixture")
    # Dedupe must not mutate class.
    return {
        "classification_status": "CLASSIFIED",
        "classification": classification,
        "dedupe_result": {
            "matched_existing": dedupe_issue is not None,
            "existing_issue": dedupe_issue,
        },
    }


def test_helper_enforces_single_class_and_stable_dedupe() -> None:
    base = _classify(
        evidence_ok=True,
        current_claim_false=True,
        separate_scope=False,
        hardening_only=False,
        parked=False,
        false_positive=False,
        dedupe_issue=None,
    )
    deduped = _classify(
        evidence_ok=True,
        current_claim_false=True,
        separate_scope=False,
        hardening_only=False,
        parked=False,
        false_positive=False,
        dedupe_issue=4184,
    )
    assert base["classification"] == "MUST_FIX_IN_CURRENT_PR"
    assert deduped["classification"] == base["classification"]
    assert deduped["dedupe_result"]["existing_issue"] == 4184
    blocked = _classify(
        evidence_ok=False,
        current_claim_false=False,
        separate_scope=False,
        hardening_only=False,
        parked=False,
        false_positive=False,
        dedupe_issue=99,
    )
    assert blocked["classification"] is None
    assert blocked["classification_status"] == "BLOCKED_INSUFFICIENT_EVIDENCE"
