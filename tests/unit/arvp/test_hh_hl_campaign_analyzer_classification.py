"""Unit tests for durable hh_hl analyzer classification (#4374).

test_id: tc_hh_hl_durable_classifier_001
test_type: Bauteil-Test / Schutz-Test
cdb_area: arvp_campaign
issue_ref: #4374
live_relevant: false
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.arvp_vacation.hh_hl_campaign_analyzer import (
    REASON_INCONCLUSIVE_STABILITY_ABSENT,
    REASON_INCONCLUSIVE_THRESHOLD_POLICY_ABSENT,
    REASON_REJECTED_UNIFORM_NEGATIVE_SIGN,
    build_hh_hl_analyzer_profile,
    build_threshold_policy,
    build_uniform_negative_sign_reject_policy_draft,
    classify_hh_hl_campaign,
)
from tools.arvp_vacation.hh_hl_window_stability import build_window_stability

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLASSIFICATION_SCHEMA = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "cdb_hh_hl_analyzer_classification.v1.schema.json"
)
POLICY_SCHEMA = (
    PROJECT_ROOT
    / "docs"
    / "contracts"
    / "cdb_hh_hl_classifier_threshold_policy.v1.schema.json"
)


def _fp(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _bindings(**overrides):
    base = {
        "campaign_id": "arvp-hh-hl-continuation-4374-prep-v1",
        "issue": 4374,
        "authorization_fingerprint": _fp("auth"),
        "execution_sha": "79b150d452a6bebddc5a8f1b0db39c77ebbfe1c3",
        "manifest_fingerprint": _fp("manifest"),
        "run_plan_fingerprint": _fp("run_plan"),
        "dataset_selection_sha256": _fp("dataset_sel"),
        "dataset_content_fingerprint_digest": _fp("dataset_content"),
        "physical_parameter_set_fingerprint": _fp("params"),
        "campaign_summary_fingerprint": _fp("summary"),
        "source_run_count": 3,
    }
    base.update(overrides)
    return base


def _window(window_id: str, *, net_pnl: float, expectancy: float, trades: int = 10):
    return {
        "window_id": window_id,
        "result": {
            "net_pnl_quote": net_pnl,
            "expectancy_r": expectancy,
            "max_drawdown_r": 0.5,
            "fees_total_quote": 10.0,
            "closed_trades_total": trades,
            "gate_result": {"status": "NOT_RANKING_READY"},
        },
    }


def _stability_all_negative():
    return build_window_stability(
        bindings=_bindings(),
        window_records=[
            _window("w_a", net_pnl=-100.0, expectancy=-0.01),
            _window("w_b", net_pnl=-200.0, expectancy=-0.02),
            _window("w_c", net_pnl=-50.0, expectancy=-0.005),
        ],
    )


def _profile():
    return build_hh_hl_analyzer_profile(
        expected_run_keys=["k1", "k2", "k3"],
    )


@pytest.fixture(scope="module")
def classification_validator() -> Draft202012Validator:
    return Draft202012Validator(
        json.loads(CLASSIFICATION_SCHEMA.read_text(encoding="utf-8"))
    )


@pytest.fixture(scope="module")
def policy_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(POLICY_SCHEMA.read_text(encoding="utf-8")))


@pytest.mark.unit
def test_missing_stability_never_promising(classification_validator):
    result = classify_hh_hl_campaign(
        analyzer_profile=_profile(),
        reproduction_pass=True,
        window_stability=None,
    )
    assert result["classification"] == "INCONCLUSIVE"
    assert result["reason_code"] == REASON_INCONCLUSIVE_STABILITY_ABSENT
    assert result["classification"] != "PROMISING"
    classification_validator.validate(result)


@pytest.mark.unit
def test_classifier_requires_bound_stability_artifact(classification_validator):
    result = classify_hh_hl_campaign(
        analyzer_profile=_profile(),
        reproduction_pass=True,
        window_stability=None,
        threshold_policy=build_uniform_negative_sign_reject_policy_draft(),
    )
    assert result["reason_code"] == REASON_INCONCLUSIVE_STABILITY_ABSENT
    assert result["input_fingerprints"]["window_stability_fingerprint"] is None
    classification_validator.validate(result)


@pytest.mark.unit
def test_stability_without_policy_inconclusive(classification_validator):
    result = classify_hh_hl_campaign(
        analyzer_profile=_profile(),
        reproduction_pass=True,
        window_stability=_stability_all_negative(),
        threshold_policy=None,
    )
    assert result["classification"] == "INCONCLUSIVE"
    assert result["reason_code"] == REASON_INCONCLUSIVE_THRESHOLD_POLICY_ABSENT
    assert result["window_stability_present"] is True
    classification_validator.validate(result)


@pytest.mark.unit
def test_policy_fingerprint_bound_into_classification(
    classification_validator, policy_validator
):
    policy = build_threshold_policy(
        policy_id="uniform_negative_sign_reject_v1",
        policy_status="OWNER_RATIFIED",
        issue=4374,
        rejected_rules=build_uniform_negative_sign_reject_policy_draft()[
            "rejected_rules"
        ],
        promising_rules=[],
        owner_ratified_at_utc="2026-08-08T00:00:00Z",
        owner_github_login="jannekbuengener",
    )
    policy_validator.validate(policy)
    result = classify_hh_hl_campaign(
        analyzer_profile=_profile(),
        reproduction_pass=True,
        window_stability=_stability_all_negative(),
        threshold_policy=policy,
        campaign_summary_fingerprint=_fp("summary"),
        reproduction_summary_fingerprint=_fp("repro"),
    )
    assert result["policy_fingerprint"] == policy["policy_fingerprint"]
    assert (
        result["input_fingerprints"]["threshold_policy_fingerprint"]
        == policy["policy_fingerprint"]
    )
    assert result["classification"] == "REJECTED"
    assert result["reason_code"] == REASON_REJECTED_UNIFORM_NEGATIVE_SIGN
    classification_validator.validate(result)


@pytest.mark.unit
def test_same_inputs_and_policy_same_verdict_fingerprint():
    policy = build_threshold_policy(
        policy_id="uniform_negative_sign_reject_v1",
        policy_status="OWNER_RATIFIED",
        issue=4374,
        rejected_rules=build_uniform_negative_sign_reject_policy_draft()[
            "rejected_rules"
        ],
        promising_rules=[],
        owner_ratified_at_utc="2026-08-08T00:00:00Z",
        owner_github_login="jannekbuengener",
    )
    stability = _stability_all_negative()
    profile = _profile()
    a = classify_hh_hl_campaign(
        analyzer_profile=profile,
        reproduction_pass=True,
        window_stability=stability,
        threshold_policy=policy,
    )
    b = classify_hh_hl_campaign(
        analyzer_profile=copy.deepcopy(profile),
        reproduction_pass=True,
        window_stability=copy.deepcopy(stability),
        threshold_policy=copy.deepcopy(policy),
    )
    assert a == b
    assert a["classification_fingerprint"] == b["classification_fingerprint"]


@pytest.mark.unit
def test_draft_policy_does_not_reject():
    policy = build_uniform_negative_sign_reject_policy_draft()
    assert policy["policy_status"] == "DRAFT"
    result = classify_hh_hl_campaign(
        analyzer_profile=_profile(),
        reproduction_pass=True,
        window_stability=_stability_all_negative(),
        threshold_policy=policy,
    )
    assert result["classification"] == "INCONCLUSIVE"
    assert "NOT_RATIFIED" in result["reason_code"]


@pytest.mark.unit
def test_reproduction_not_pass_blocked():
    result = classify_hh_hl_campaign(
        analyzer_profile=_profile(),
        reproduction_pass=False,
        window_stability=_stability_all_negative(),
    )
    assert result["classification"] == "BLOCKED"
