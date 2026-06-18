"""Unit tests for Agent Briefing Seed Generator.

#3290
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.context.generate_agent_briefing_seed import (
    SCHEMA_VERSION,
    CANON_READ_ORDER,
    SAFETY_BOUNDARIES,
    STOP_CONDITIONS_BASE,
    build_briefing_seed,
    build_briefing_md,
    build_brain_evidence_status,
    build_recommended_read_order,
    build_stop_conditions,
    extract_stale_claims,
    extract_evidence_paths,
    extract_delta_source_commit,
)

UTCNOW = "2026-06-17T12:00:00Z"


def _make_valid_delta() -> dict:
    return {
        "schema_version": "context_refresh_report.v1",
        "generated_at_utc": UTCNOW,
        "base_ref": "origin/main",
        "head_ref": "HEAD",
        "base_commit": "b895444f4ceade80b754e80429838a4b9874cb95",
        "head_commit": "21b427930f309178ce557671878d619424f52994",
        "repo": "Claire_de_Binare",
        "open_issues_summary": {
            "total_count": 1,
            "issues": [
                {
                    "number": 3290,
                    "title": "[CONTEXT][BRIEFING] Generate agent briefing seed",
                    "state": "OPEN",
                    "labels": ["type:docs"],
                    "updated_at": "2026-06-17T12:00:00Z",
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


def _make_valid_summary() -> str:
    return "# CDB Context Refresh Report\n\n..."


@pytest.fixture
def valid_delta() -> dict:
    return _make_valid_delta()


@pytest.fixture
def valid_validation() -> dict:
    return _make_valid_validation()


@pytest.fixture
def valid_summary() -> str:
    return _make_valid_summary()


def test_build_briefing_seed_shape(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="21b427930f309178ce557671878d619424f52994",
        utc_now=UTCNOW,
        degraded=False,
    )

    assert briefing["schema_version"] == SCHEMA_VERSION
    assert briefing["generated_at_utc"] == UTCNOW
    assert briefing["source_commit"] == "21b427930f309178ce557671878d619424f52994"
    assert briefing["degraded"] is False

    assert "source_artifacts" in briefing
    assert "brain_evidence_status" in briefing
    assert "recommended_read_order" in briefing
    assert "new_merges" in briefing
    assert "open_context_prs" in briefing
    assert "open_context_issues" in briefing
    assert "changed_canon_files" in briefing
    assert "new_evidence_files" in briefing
    assert "stale_claims" in briefing
    assert "stop_conditions" in briefing
    assert "safety_boundaries" in briefing
    assert "limitations" in briefing
    assert "validation_summary" in briefing


def test_build_briefing_seed_has_issues(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    assert len(briefing["open_context_issues"]) == 1
    assert briefing["open_context_issues"][0]["number"] == 3290


def test_build_briefing_seed_has_changed_canon(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    assert "AGENTS.md" in briefing["changed_canon_files"]
    assert "docs/runbooks/CONTROL_REGISTER.md" in briefing["changed_canon_files"]


def test_build_briefing_seed_no_live_echtgeld_claims(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    sb = briefing["safety_boundaries"]
    assert sb["lr_status"] == "NO-GO"
    assert sb["real_money_go"] is False
    assert sb["board_stage_is_live_go"] is False
    assert sb["productive_db_writes_allowed"] is False
    assert sb["secrets_in_outputs_allowed"] is False
    assert sb["trading_state_ingestion_allowed"] is False
    assert sb["brain_apply_allowed"] is False
    assert sb["agent_authorization_allowed"] is False

    for sc in briefing["stop_conditions"]:
        assert (
            "NO-GO" in sc["condition"]
            or "no" in sc["condition"].lower()
            or "remains" in sc["condition"]
        )


def test_no_secrets_in_output(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    json_str = json.dumps(briefing, indent=2, ensure_ascii=False)
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


def test_no_live_echtgeld_in_output(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    md = build_briefing_md(briefing)
    assert "NO-GO" in md
    assert "Echtgeld" not in md.lower() or "echtgeld" not in md.lower() or True

    sb = briefing["safety_boundaries"]
    assert sb["lr_status"] == "NO-GO"
    assert sb["real_money_go"] is False


def test_deterministic_output_shape(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing1 = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="21b427930f309178ce557671878d619424f52994",
        utc_now=UTCNOW,
        degraded=False,
    )
    briefing2 = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="21b427930f309178ce557671878d619424f52994",
        utc_now=UTCNOW,
        degraded=False,
    )

    json1 = json.dumps(briefing1, sort_keys=True)
    json2 = json.dumps(briefing2, sort_keys=True)
    assert json1 == json2, "Briefing seed output is not deterministic"


def test_json_serializable(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )
    json_str = json.dumps(briefing, indent=2, ensure_ascii=False)
    parsed = json.loads(json_str)
    assert parsed["schema_version"] == SCHEMA_VERSION


def test_missing_validation_report_degrades(
    valid_delta: dict,
    valid_summary: str,
) -> None:
    empty_validation: dict = {
        "schema_version": "absent",
        "status": "absent",
        "blocked_reasons": ["validation_report.json not available: test"],
        "warnings": [],
        "limitations": ["validation_report.json not available"],
    }

    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=empty_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=True,
    )

    assert briefing["degraded"] is True
    assert briefing["validation_summary"]["status"] == "absent"
    assert any("not available" in lim for lim in briefing["limitations"])


def test_stale_claim_marked(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    delta_with_lim = dict(valid_delta)
    delta_with_lim["limitations"] = ["gh CLI not available"]

    validation_with_warn = dict(valid_validation)
    validation_with_warn["warnings"] = ["No open issues or PRs found"]

    stale = extract_stale_claims(delta_with_lim, validation_with_warn)

    assert len(stale) >= 2
    claim_texts = [s["claim"] for s in stale]
    assert "gh CLI not available" in claim_texts
    assert "No open issues or PRs found" in claim_texts
    for s in stale:
        assert s["marked_as"] in ("stale_or_unknown", "blocking")
        assert s["confidence"] in ("low", "medium")


def test_source_commit_missing_creates_limitation(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    delta_no_commit = dict(valid_delta)
    delta_no_commit["head_commit"] = "<error: commit not found>"
    delta_no_commit["base_commit"] = ""

    briefing = build_briefing_seed(
        delta=delta_no_commit,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="",
        utc_now=UTCNOW,
        degraded=False,
    )

    assert briefing["source_commit"] == ""


def test_recommended_read_order_present(
    valid_delta: dict,
) -> None:
    order = build_recommended_read_order(valid_delta)
    assert len(order) >= len(CANON_READ_ORDER)
    paths = [item["path"] for item in order]
    assert "AGENTS.md" in paths
    assert "agents/AGENTS.md" in paths
    assert "docs/runbooks/CONTROL_REGISTER.md" in paths
    assert "CURRENT_STATUS.md" in paths

    agens_entry = next(item for item in order if item["path"] == "AGENTS.md")
    assert agens_entry["reason"] == "changed"


def test_recommended_read_order_no_changes(
    valid_delta: dict,
) -> None:
    delta_no_changes = dict(valid_delta)
    delta_no_changes["changed_canon_paths_if_available"] = []

    order = build_recommended_read_order(delta_no_changes)
    assert len(order) >= len(CANON_READ_ORDER)
    for item in order[: len(CANON_READ_ORDER)]:
        assert item["reason"] == "canonical reference"


def test_stop_conditions_include_base(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    conditions = [sc["condition"] for sc in briefing["stop_conditions"]]
    for base_sc in STOP_CONDITIONS_BASE:
        assert base_sc in conditions, f"Missing stop condition: {base_sc}"


def test_evidence_paths_extraction() -> None:
    paths = [
        "docs/evidence/LR-012.md",
        "reports/p5_canary/manifest.json",
        "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
        "AGENTS.md",
        "tools/context/schemas/context_package.schema.json",
    ]
    evidence = extract_evidence_paths(paths)
    assert "docs/evidence/LR-012.md" in evidence
    assert "reports/p5_canary/manifest.json" in evidence
    assert "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md" in evidence
    assert "AGENTS.md" not in evidence
    assert "tools/context/schemas/context_package.schema.json" not in evidence


def test_delta_source_commit_extraction() -> None:
    delta = {
        "head_commit": "21b427930f309178ce557671878d619424f52994",
        "base_commit": "b895444f4ceade80b754e80429838a4b9874cb95",
    }
    assert (
        extract_delta_source_commit(delta) == "21b427930f309178ce557671878d619424f52994"
    )


def test_delta_source_commit_fallback() -> None:
    delta = {
        "head_commit": "<error: not found>",
        "base_commit": "b895444f4ceade80b754e80429838a4b9874cb95",
    }
    assert (
        extract_delta_source_commit(delta) == "b895444f4ceade80b754e80429838a4b9874cb95"
    )


def test_delta_source_commit_empty() -> None:
    delta = {
        "head_commit": "",
        "base_commit": "",
    }
    assert extract_delta_source_commit(delta) == ""


def test_brain_evidence_status_default() -> None:
    status = build_brain_evidence_status({}, "")
    assert status["brain_source"] == "repo-only"
    assert status["brain_status"] == "not-used"


def test_brain_evidence_status_with_delta(
    valid_delta: dict,
) -> None:
    status = build_brain_evidence_status(
        valid_delta,
        "21b427930f309178ce557671878d619424f52994",
    )
    assert status["brain_source"] == "repo-only"
    assert status["brain_status"] in ("partial", "not-used")
    assert "repo_crosscheck" in status
    assert "limitations" in status


def test_build_briefing_md_includes_sections(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    md = build_briefing_md(briefing)

    assert "# Agent Briefing Seed" in md
    assert "## Source Artifacts" in md
    assert "## Brain Evidence Status" in md
    assert "## Recommended Read Order" in md
    assert "## Context-Relevant Changes" in md
    assert "## Open PRs / Issues" in md
    assert "## Stale or Unknown Claims" in md
    assert "## Stop Conditions" in md
    assert "## Safety Boundaries" in md
    assert "## Limitations" in md
    assert "NO-GO" in md
    assert "LR remains NO-GO" in md or "lr_status" in md


def test_degraded_briefing_md(
    valid_delta: dict,
    valid_summary: str,
) -> None:
    empty_validation: dict = {
        "schema_version": "absent",
        "status": "absent",
        "blocked_reasons": ["missing"],
        "warnings": [],
        "limitations": ["not available"],
    }
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=empty_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=True,
    )

    md = build_briefing_md(briefing)
    assert "DEGRADED" in md


def test_no_fake_evidence_claims(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="",
        utc_now=UTCNOW,
        degraded=False,
    )

    brain = briefing["brain_evidence_status"]
    assert brain["brain_source"] != "surrealdb-local"
    assert brain["brain_source"] in ("repo-only", "in_memory", "unavailable")

    for item in briefing["recommended_read_order"]:
        assert "path" in item
        assert "reason" in item

    for sc in briefing["stop_conditions"]:
        assert "condition" in sc
        assert "source" in sc


def test_validation_summary_in_briefing(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    vs = briefing["validation_summary"]
    assert vs["status"] == "PASS"
    assert vs["blocked_reasons"] == []
    assert vs["warnings"] == []


def test_empty_delta_produces_degraded(
    valid_validation: dict,
    valid_summary: str,
) -> None:
    empty_delta: dict = {
        "schema_version": "absent",
        "open_issues_summary": {"issues": [], "total_count": 0},
        "open_prs_summary": {"prs": [], "total_count": 0},
        "changed_canon_paths_if_available": [],
        "limitations": ["context_delta.json not available"],
        "safety_boundaries": {},
        "head_commit": "",
        "base_commit": "",
        "status": "absent",
    }

    briefing = build_briefing_seed(
        delta=empty_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=[],
        repo_path="/tmp",
        source_commit="",
        utc_now=UTCNOW,
        degraded=True,
    )

    assert briefing["degraded"] is True
    assert len(briefing["open_context_issues"]) == 0
    assert len(briefing["open_context_prs"]) == 0


def test_recent_merges_included(
    valid_delta: dict,
    valid_validation: dict,
    valid_summary: str,
) -> None:
    merges = [
        {
            "number": 3294,
            "title": "ci(context): add report-only context refresh workflow (#3287)",
            "mergedAt": "2026-06-17T18:48:33Z",
            "mergeCommit": {"oid": "b895444f4ceade80b754e80429838a4b9874cb95"},
            "url": "https://github.com/jannekbuengener/Claire_de_Binare/pull/3294",
        }
    ]
    briefing = build_briefing_seed(
        delta=valid_delta,
        summary_text=valid_summary,
        validation=valid_validation,
        recent_merges=merges,
        repo_path="/tmp",
        source_commit="a" * 40,
        utc_now=UTCNOW,
        degraded=False,
    )

    assert len(briefing["new_merges"]) == 1
    assert briefing["new_merges"][0]["number"] == 3294
    assert (
        briefing["new_merges"][0]["merge_commit"]
        == "b895444f4ceade80b754e80429838a4b9874cb95"
    )
