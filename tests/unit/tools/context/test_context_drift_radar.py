"""Unit tests for CDB Context Drift Radar.

#3291
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.context.generate_context_drift_radar import (
    SCHEMA_VERSION,
    RADAR_SCHEMA_VERSION,
    DRIFT_CATEGORIES,
    scan_all,
    scan_canon_pointer_drift,
    scan_ledger_vs_github_drift,
    scan_lr_status_ambiguity,
    scan_stale_architecture_docs,
    scan_stale_onboarding_docs,
    scan_stale_agent_bootloader_instructions,
    scan_workflow_check_drift,
    scan_unknown_high_risk_delta,
    build_stale_claims,
    build_impact_radar,
    build_impact_radar_md,
    _severity_for_category,
    _blocks_brain_apply,
    _find_secret_indicators,
)

UTCNOW = "2026-06-17T12:00:00Z"


def _make_valid_delta() -> dict:
    return {
        "schema_version": "context_refresh_report.v1",
        "generated_at_utc": UTCNOW,
        "base_ref": "origin/main",
        "head_ref": "HEAD",
        "base_commit": "b895444f4ceade80b754e80429838a4b9874cb95",
        "head_commit": "072b740a28586dfd885d80c7bcbc8e82822e2dab",
        "repo": "Claire_de_Binare",
        "open_issues_summary": {
            "total_count": 1,
            "issues": [
                {
                    "number": 3291,
                    "title": "[CONTEXT][DRIFT] Add stale documentation and impact radar",
                    "state": "OPEN",
                    "labels": ["type:docs"],
                    "updated_at": UTCNOW,
                }
            ],
        },
        "open_prs_summary": {
            "total_count": 0,
            "prs": [],
        },
        "changed_canon_paths_if_available": [
            "AGENTS.md",
            "docs/runbooks/CONTROL_REGISTER.md",
        ],
        "limitations": [],
        "safety_boundaries": {
            "lr_status": "NO-GO",
            "board_stage_is_live_go": False,
            "real_money_go": False,
            "productive_db_writes_allowed": False,
            "secrets_in_outputs_allowed": False,
            "trading_state_ingestion_allowed": False,
        },
    }


def _make_valid_validation() -> dict:
    return {
        "schema_version": "validation_report.v1",
        "status": "PASS",
        "validator_used": "tools/context/generate_context_refresh_report.py",
        "blocked_reasons": [],
        "warnings": [],
        "artifact_paths": {
            "context_delta": "/tmp/context_delta.json",
            "context_refresh_summary": "/tmp/context_refresh_summary.md",
        },
        "limitations": [
            "Report-only: no DB writes, no brain apply, no runtime changes.",
            "LR remains NO-GO. No Live-Go. No Echtgeld-Go.",
        ],
    }


def _make_valid_briefing() -> dict:
    return {
        "schema_version": "agent_briefing_seed.v1",
        "generated_at_utc": UTCNOW,
        "source_commit": "072b740a28586dfd885d80c7bcbc8e82822e2dab",
        "stale_claims": [],
        "safety_boundaries": {
            "lr_status": "NO-GO",
            "board_stage_is_live_go": False,
            "real_money_go": False,
            "productive_db_writes_allowed": False,
            "secrets_in_outputs_allowed": False,
            "trading_state_ingestion_allowed": False,
            "brain_apply_allowed": False,
        },
    }


@pytest.fixture
def valid_delta() -> dict:
    return _make_valid_delta()


@pytest.fixture
def valid_validation() -> dict:
    return _make_valid_validation()


@pytest.fixture
def valid_briefing() -> dict:
    return _make_valid_briefing()


def test_valid_input_no_drift_produces_empty_or_pass(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    assert isinstance(claims, list)
    assert "claims" in stale
    assert "summary" in stale
    assert stale["summary"]["blocking_claims"] == 0


def test_ledger_vs_github_drift_detected(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_ledger_vs_github_drift(valid_delta, valid_briefing)
    assert len(claims) >= 1
    assert claims[0]["drift_category"] == "ledger_vs_github_drift"
    assert claims[0]["severity"] == "medium"


def test_lr_status_ambiguity_blocks_brain_apply(
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    bad_delta = dict(_make_valid_delta())
    bad_delta["safety_boundaries"]["lr_status"] = "GO"

    claims = scan_lr_status_ambiguity(bad_delta, valid_validation, valid_briefing)
    assert len(claims) >= 1
    for c in claims:
        assert c["blocks_brain_apply"] is True
        assert c["severity"] == "high"


def test_unknown_high_risk_delta_blocks_brain_apply(
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    bad_delta = dict(_make_valid_delta())
    bad_delta["limitations"] = ["ECHTGELD-GO detected in upstream"]

    claims = scan_unknown_high_risk_delta(bad_delta, valid_briefing)
    assert len(claims) >= 1
    for c in claims:
        assert c["blocks_brain_apply"] is True
        assert c["severity"] == "high"
        assert c["drift_category"] == "unknown_high_risk_delta"


def test_stale_onboarding_docs_classified(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    delta_with_onboarding = dict(_make_valid_delta())
    delta_with_onboarding["changed_canon_paths_if_available"] = [
        "agents/roles/CODEX.md",
    ]

    claims = scan_stale_onboarding_docs(delta_with_onboarding, valid_briefing)
    assert len(claims) >= 1
    for c in claims:
        assert c["drift_category"] == "stale_onboarding_docs"


def test_stale_agent_bootloader_instructions_classified(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    delta_with_boot = dict(_make_valid_delta())
    delta_with_boot["changed_canon_paths_if_available"] = [
        "AGENTS.md",
        "agents/AGENTS.md",
    ]

    claims = scan_stale_agent_bootloader_instructions(delta_with_boot, valid_briefing)
    assert len(claims) >= 1
    for c in claims:
        assert c["drift_category"] == "stale_agent_bootloader_instructions"


def test_workflow_check_drift_classified(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    bad_validation = dict(_make_valid_validation())
    bad_validation["status"] = "BLOCKED"
    bad_validation["blocked_reasons"] = ["Git HEAD resolution failed"]

    claims = scan_workflow_check_drift(bad_validation)
    assert len(claims) >= 1
    for c in claims:
        assert c["drift_category"] == "workflow_check_drift"


def test_recommended_follow_up_issues_report_only(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    issues = radar["recommended_follow_up_issues"]
    assert isinstance(issues, list)
    for issue in issues:
        assert "title" in issue
        assert "reasoning" in issue
        assert "dedupe_hint" in issue
        assert "safety_boundary" in issue


def test_no_auto_github_writes(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    sb = radar["safety_boundaries"]
    assert sb["auto_issue_creation_allowed"] is False


def test_no_secrets_in_output(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    json_str = json.dumps(stale, indent=2, ensure_ascii=False)
    secret_indicators = [
        "api_key",
        "api_secret",
        "REDIS_PASSWORD",
        "POSTGRES_PASSWORD",
        "MEXC_API_KEY",
        "MEXC_API_SECRET",
        "SECRETS_PATH",
        "SMTP_PASSWORD",
        "GRAFANA_PASSWORD",
    ]
    for indicator in secret_indicators:
        assert indicator not in json_str, f"Secret indicator found: {indicator}"

    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar_json = json.dumps(radar, indent=2, ensure_ascii=False)
    for indicator in secret_indicators:
        assert (
            indicator not in radar_json
        ), f"Secret indicator found in radar: {indicator}"


def test_no_live_echtgeld_claims_in_output(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    sb = radar["safety_boundaries"]
    assert sb["lr_status"] == "NO-GO"
    assert sb["real_money_go"] is False
    assert sb["board_stage_is_live_go"] is False

    md = build_impact_radar_md(radar)
    assert "NO-GO" in md
    assert "Echtgeld" not in md or "LR remains NO-GO" in md


def test_deterministic_output_shape(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims1 = scan_all(valid_delta, valid_validation, valid_briefing)
    stale1 = build_stale_claims(
        claims=claims1,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar1 = build_impact_radar(
        stale_claims=stale1,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    claims2 = scan_all(valid_delta, valid_validation, valid_briefing)
    stale2 = build_stale_claims(
        claims=claims2,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar2 = build_impact_radar(
        stale_claims=stale2,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    json1 = json.dumps(radar1, sort_keys=True)
    json2 = json.dumps(radar2, sort_keys=True)
    assert json1 == json2, "Drift radar output is not deterministic"


def test_json_serializable(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    for obj, name in [(stale, "stale_claims"), (radar, "impact_radar")]:
        json_str = json.dumps(obj, indent=2, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict), f"{name} is not serializable"


def test_missing_inputs_degrades() -> None:
    claims = scan_all(None, None, None)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={},
        utc_now=UTCNOW,
        degraded=True,
        limitations=["Both inputs missing"],
    )
    assert stale["degraded"] is True
    assert stale["summary"]["total_claims"] == 0


def test_stale_claims_json_has_required_fields(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    assert "schema_version" in stale
    assert "generated_at_utc" in stale
    assert "source_artifacts" in stale
    assert "claims" in stale
    assert "summary" in stale
    assert "degraded" in stale
    assert "limitations" in stale

    assert stale["schema_version"] == SCHEMA_VERSION

    if stale["claims"]:
        sample = stale["claims"][0]
        assert "claim" in sample
        assert "drift_category" in sample
        assert "severity" in sample
        assert "source_ref" in sample
        assert "current_truth_ref" in sample
        assert "status" in sample
        assert "recommended_action" in sample
        assert "blocks_brain_apply" in sample


def test_impact_radar_md_has_required_sections(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    md = build_impact_radar_md(radar)

    sections = [
        "# Context Drift / Impact Radar",
        "## Source Artifacts",
        "## High-Risk Drift",
        "## Brain Apply Blockers",
        "## Stale Claims",
        "## Canon / Ledger / GitHub Conflicts",
        "## Workflow / Check Drift",
        "## Recommended Follow-up Issues",
        "## Safety Boundaries",
        "## Limitations",
    ]
    for section in sections:
        assert section in md, f"Missing section: {section}"

    assert "NO-GO" in md
    assert "LR remains NO-GO" in md or "lr_status" in md


def test_scan_canon_pointer_drift(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_canon_pointer_drift(valid_delta, valid_briefing)
    assert isinstance(claims, list)
    for c in claims:
        assert c["drift_category"] == "canon_pointer_drift"


def test_scan_stale_architecture_docs(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    delta_with_arch = dict(_make_valid_delta())
    delta_with_arch["changed_canon_paths_if_available"] = [
        "knowledge/CDB_KNOWLEDGE_HUB.md",
    ]

    claims = scan_stale_architecture_docs(delta_with_arch, valid_briefing)
    assert len(claims) >= 1
    for c in claims:
        assert c["drift_category"] == "stale_architecture_docs"


def test_severity_mapping() -> None:
    assert _severity_for_category("lr_status_ambiguity") == "high"
    assert _severity_for_category("unknown_high_risk_delta") == "high"
    assert _severity_for_category("canon_pointer_drift") == "medium"
    assert _severity_for_category("stale_onboarding_docs") == "medium"


def test_blocks_brain_apply_logic() -> None:
    assert _blocks_brain_apply("high", "canon_pointer_drift", "something") is True
    assert _blocks_brain_apply("medium", "lr_status_ambiguity", "something") is True
    assert _blocks_brain_apply("medium", "unknown_high_risk_delta", "something") is True
    assert _blocks_brain_apply("medium", "stale_onboarding_docs", "live-go") is True
    assert (
        _blocks_brain_apply("medium", "stale_onboarding_docs", "documentation change")
        is False
    )


def test_secret_indicator_detection() -> None:
    text = "some text with api_key=123 and password=secret"
    found = _find_secret_indicators(text)
    assert "api_key" in found
    assert "password=" in found

    clean = "no secrets here"
    assert _find_secret_indicators(clean) == []


def test_degraded_mode_no_delta(
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(None, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"validation": "v1"},
        utc_now=UTCNOW,
        degraded=True,
        limitations=["delta not available"],
    )
    assert stale["degraded"] is True
    assert "delta not available" in stale["limitations"]


def test_degraded_mode_no_validation(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, None, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"delta": "v1"},
        utc_now=UTCNOW,
        degraded=True,
        limitations=["validation not available"],
    )
    assert stale["degraded"] is True


def test_blocks_brain_apply_summary(
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    bad_delta = dict(_make_valid_delta())
    bad_delta["safety_boundaries"]["lr_status"] = "GO"

    claims = scan_all(bad_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"delta": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    assert stale["summary"]["blocks_brain_apply"] is True
    assert stale["summary"]["blocking_claims"] >= 1


def test_follow_up_not_auto_created(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    issues = radar["recommended_follow_up_issues"]
    assert isinstance(issues, list)
    for issue in issues:
        assert "dedupe_hint" in issue
        assert "Do not auto-create" not in json.dumps(issue)
    assert radar["safety_boundaries"]["auto_issue_creation_allowed"] is False


def test_drift_categories_enum() -> None:
    expected = [
        "canon_pointer_drift",
        "ledger_vs_github_drift",
        "lr_status_ambiguity",
        "stale_architecture_docs",
        "stale_onboarding_docs",
        "stale_agent_bootloader_instructions",
        "workflow_check_drift",
        "unknown_high_risk_delta",
    ]
    assert DRIFT_CATEGORIES == expected


def test_impact_radar_json_schema(
    valid_delta: dict,
    valid_validation: dict,
    valid_briefing: dict,
) -> None:
    claims = scan_all(valid_delta, valid_validation, valid_briefing)
    stale = build_stale_claims(
        claims=claims,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )
    radar = build_impact_radar(
        stale_claims=stale,
        source_artifacts={"test": "v1"},
        utc_now=UTCNOW,
        degraded=False,
        limitations=[],
    )

    assert radar["schema_version"] == RADAR_SCHEMA_VERSION
    assert "title" in radar
    assert "high_risk_drift" in radar
    assert "brain_apply_blockers" in radar
    assert "brain_apply_blocked" in radar
    assert "stale_claims" in radar
    assert "by_category" in radar
    assert "canon_ledger_github_conflicts" in radar
    assert "workflow_check_drift" in radar
    assert "recommended_follow_up_issues" in radar
    assert "safety_boundaries" in radar
    assert "degraded" in radar
    assert "limitations" in radar


def test_workflow_check_blocked_blocks_brain(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    bad_validation = dict(_make_valid_validation())
    bad_validation["status"] = "BLOCKED"
    bad_validation["blocked_reasons"] = ["Git HEAD resolution failed"]

    claims = scan_workflow_check_drift(bad_validation)
    assert len(claims) >= 1
    for c in claims:
        assert c["blocks_brain_apply"] is True
        assert c["severity"] == "high"


def test_workflow_check_warning_does_not_block(
    valid_delta: dict,
    valid_briefing: dict,
) -> None:
    warn_validation = dict(_make_valid_validation())
    warn_validation["warnings"] = ["No open issues or PRs found"]

    claims = scan_workflow_check_drift(warn_validation)
    assert len(claims) >= 1
    for c in claims:
        assert c["drift_category"] == "workflow_check_drift"
        if c["severity"] == "medium":
            assert c["blocks_brain_apply"] is False
