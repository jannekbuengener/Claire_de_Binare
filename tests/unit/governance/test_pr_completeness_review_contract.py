"""Contract tests for cdb-pr-completeness-review (#4209)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "config" / "governance" / "pr-acceptance-policy.v1.yaml"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "pr_acceptance_skill_family.v1.schema.json"
SKILL = ROOT / "docs" / "skills" / "cdb-pr-completeness-review" / "SKILL.md"

DIMENSIONS = [
    "Funktionalität",
    "Wiring / Integration",
    "Konfiguration",
    "Persistenz / Zustand",
    "Runtime / Deployment",
    "Tests / Validierung",
    "Dokumentation / Runbooks / Contracts",
    "Operative Readiness / Observability",
]
VERDICTS = [
    "MERGE_CANDIDATE",
    "CURRENT_PR_EXTENSION_REQUIRED",
    "PR_SPLIT_REQUIRED",
    "FOLLOWUP_SLICES_REQUIRED",
    "BLOCKED_MISSING_EVIDENCE",
    "BLOCKED_SCOPE_AMBIGUITY",
    "BLOCKED_VALIDATION_GAP",
    "BLOCKED_UNCLEAR_CLOSURE",
]
DELEGATES = [
    "cdb-integration-wiring-audit",
    "cdb-pr-gap-classifier",
    "cdb-contract-evidence-gatekeeper",
    "cdb-test-first",
    "cdb-shadow-validation",
    "cdb-ci-cd-guard",
    "cdb-drift-reconcile",
]


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_eight_dimensions_fixed_order_policy_schema_skill() -> None:
    policy = _policy()
    schema = _schema()
    text = _skill()
    assert policy["completeness_dimensions"] == DIMENSIONS
    assert len(DIMENSIONS) == 8
    schema_dims = schema["$defs"]["CompletenessDimensionRow"]["properties"][
        "dimension"
    ]["enum"]
    assert schema_dims == DIMENSIONS
    for dim in DIMENSIONS:
        assert f"`{dim}`" in text or dim in text
    # Fixed order: each later dimension appears after the previous in skill text
    positions = [text.index(dim) for dim in DIMENSIONS]
    assert positions == sorted(positions)


def test_verdict_precedence_and_allowed_set() -> None:
    policy = _policy()
    text = _skill()
    assert policy["completeness_verdicts"] == VERDICTS
    for verdict in VERDICTS:
        assert verdict in text
    assert "MUST_FIX_IN_CURRENT_PR" in text
    assert "CURRENT_PR_EXTENSION_REQUIRED" in text
    assert "FOLLOWUP_SLICES_REQUIRED" in text
    assert "PR_SPLIT_REQUIRED" in text
    # Precedence section lists blocking outcomes before MERGE_CANDIDATE outcome
    section = text.split("## Verdict precedence", 1)[1].split("## Hard rules", 1)[0]
    assert section.index("PR_SPLIT_REQUIRED") < section.index("MERGE_CANDIDATE")
    assert section.index("CURRENT_PR_EXTENSION_REQUIRED") < section.index(
        "MERGE_CANDIDATE"
    )
    assert section.index("FOLLOWUP_SLICES_REQUIRED") < section.index("MERGE_CANDIDATE")
    assert policy["completeness_verdict_precedence"][-1] == "MERGE_CANDIDATE"


def test_unknown_and_not_applicable_rules() -> None:
    policy = _policy()
    text = _skill()
    assert policy["dimension_rules"]["UNKNOWN_blocks_MERGE_CANDIDATE"] is True
    assert policy["dimension_rules"]["NOT_APPLICABLE_requires_reason"] is True
    assert "UNKNOWN" in text and "MERGE_CANDIDATE" in text
    assert "NOT_APPLICABLE" in text and "reason" in text
    assert "INVALIDATED_BY_DRIFT" in text or "drift" in text.lower()


def test_must_fix_and_followup_and_split_semantics() -> None:
    text = _skill()
    assert "MUST_FIX_IN_CURRENT_PR" in text
    assert "must not be deferred" in text or "must not" in text
    assert "FOLLOWUP_SLICES_REQUIRED` is not mergeable" in text or (
        "not mergeable" in text
    )
    assert "PR_SPLIT_REQUIRED` precedes" in text or "PR_SPLIT" in text


def test_merge_candidate_only_when_matrix_closed() -> None:
    text = _skill()
    assert "all dimensions `PASS`" in text or "PASS` or justified" in text
    assert "MERGE_CANDIDATE" in text
    assert "Exactly eight dimensions" in text or "eight dimensions" in text.lower()


def test_delegation_to_batch1_and_existing_skills() -> None:
    policy = _policy()
    text = _skill()
    delegates = policy["delegation_matrix"]["cdb-pr-completeness-review"][
        "delegates_to"
    ]
    assert delegates == DELEGATES
    for name in DELEGATES:
        assert name in text
    forbidden = policy["delegation_matrix"]["cdb-pr-completeness-review"]["forbidden"]
    assert "writes" in forbidden
    assert "merge_execution" in forbidden


def test_head_base_drift_invalidates_evidence() -> None:
    policy = _policy()
    text = _skill()
    assert policy["dimension_rules"]["head_or_base_drift_invalidates_evidence"] is True
    assert "drift" in text.lower()
    assert "INVALIDATED_BY_DRIFT" in text or "invalidates" in text.lower()


def test_schema_parity_for_completeness_result() -> None:
    policy = _policy()
    schema = _schema()
    text = _skill()
    verdict_enum = schema["$defs"]["CompletenessReviewResult"]["properties"]["verdict"][
        "enum"
    ]
    assert verdict_enum == policy["completeness_verdicts"]
    dims = schema["$defs"]["CompletenessReviewResult"]["properties"]["dimensions"]
    assert dims["minItems"] == 8
    assert dims["maxItems"] == 8
    assert "cdb-pr-completeness-review" in text
    assert "<!-- cdb-pr-acceptance:v1 -->" in text


def test_boundaries_are_read_only_aggregator() -> None:
    text = _skill()
    for phrase in [
        "No GitHub writes",
        "No implementation",
        "No own routing or CI logic",
        "read-only",
    ]:
        assert phrase in text or phrase.lower() in text.lower()


def test_canonical_header_present() -> None:
    text = _skill()
    assert "Surface: docs (canonical)" in text
    assert "Sync Status: canonical" in text
    assert "cdb-pr-completeness-review" in text
