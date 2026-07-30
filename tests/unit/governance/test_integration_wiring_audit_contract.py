"""Contract tests for cdb-integration-wiring-audit (#4207)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "config" / "governance" / "pr-acceptance-policy.v1.yaml"
SKILL = ROOT / "docs" / "skills" / "cdb-integration-wiring-audit" / "SKILL.md"

AXES = [
    "Entry Point",
    "Registration / Discovery",
    "Configuration",
    "Dataflow",
    "Persistence",
    "Runtime",
    "Failure Path",
    "Observability",
    "Documentation",
    "Legacy / Bypass Risk",
]
ROW_FIELDS = [
    "dimension",
    "applicability",
    "state",
    "evidence_ids",
    "gap_ids",
    "affected_claim",
    "current_pr_fix_required",
    "reason",
]
PRECEDENCE = [
    "UNREACHABLE_IMPLEMENTATION",
    "BLOCKED_UNCLEAR_INTEGRATION",
    "WIRING_REQUIRED_IN_CURRENT_PR",
    "WIRING_FOLLOWUP_ALLOWED",
    "WIRED_AND_REACHABLE",
]


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_ten_wiring_axes_in_policy_and_skill() -> None:
    policy = _policy()
    text = _skill()
    assert policy["wiring_axes"] == AXES
    assert len(AXES) == 10
    for axis in AXES:
        assert axis in text


def test_row_contract_and_not_applicable_reason() -> None:
    text = _skill()
    for field in ROW_FIELDS:
        assert f"`{field}`" in text or field in text
    assert "NOT_APPLICABLE` requires a non-empty `reason`" in text or (
        "NOT_APPLICABLE requires a non-empty" in text
    )
    assert "UNKNOWN" in text and "MERGE_CANDIDATE" in text
    assert _policy()["dimension_rules"]["NOT_APPLICABLE_requires_reason"] is True


def test_verdict_precedence_unreachable_and_unknown() -> None:
    policy = _policy()
    text = _skill()
    assert policy["wiring_verdict_precedence"] == PRECEDENCE
    for verdict in PRECEDENCE:
        assert verdict in text
    assert "UNREACHABLE_IMPLEMENTATION" in text
    assert "BLOCKED_UNCLEAR_INTEGRATION" in text
    assert "required surface is `UNKNOWN`" in text or "UNKNOWN" in text


def test_boundaries_are_read_only() -> None:
    text = _skill()
    for phrase in [
        "No writes",
        "No second routing engine",
        "No CI decision logic",
        "No issue creation",
        "No implementation work",
    ]:
        assert phrase in text


def test_canonical_header_present() -> None:
    text = _skill()
    assert "Surface: docs (canonical)" in text
    assert "Sync Status: canonical" in text
    assert "cdb-integration-wiring-audit" in text
