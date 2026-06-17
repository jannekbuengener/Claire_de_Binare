"""Unit tests for onboarding simulation runner.

Issue: #3273
"""

from __future__ import annotations

import json
import re

import pytest

from tools.onboarding_simulation import (
    FORBIDDEN_OUTPUT_PATTERNS,
    VERDICT_ENUM,
    _build_bootloader_plan,
    _build_context_brain_note,
    _build_final_verdict,
    _build_hold_conditions,
    _build_live_truth_plan,
    _build_pr_lock_simulation,
    _normalize_mode,
    _normalize_role,
    _validate_output_safe,
    render_simulation,
    render_simulation_json,
)


class TestNormalizeRole:
    def test_agent(self) -> None:
        assert _normalize_role("agent") == "agent"

    def test_developer(self) -> None:
        assert _normalize_role("developer") == "developer"

    def test_dev_alias(self) -> None:
        assert _normalize_role("dev") == "developer"

    def test_docs(self) -> None:
        assert _normalize_role("docs") == "docs"

    def test_docs_maintainer_alias(self) -> None:
        assert _normalize_role("docs-maintainer") == "docs"

    def test_validation(self) -> None:
        assert _normalize_role("validation") == "validation"

    def test_evidence_alias(self) -> None:
        assert _normalize_role("evidence") == "validation"

    def test_unknown_role_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported role"):
            _normalize_role("nonexistent")


class TestNormalizeMode:
    def test_first_issue_dry_run(self) -> None:
        assert _normalize_mode("first-issue-dry-run") == "first-issue-dry-run"

    def test_check_only(self) -> None:
        assert _normalize_mode("check-only") == "check-only"

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="unsupported mode"):
            _normalize_mode("live")


class TestBuildFinalVerdict:
    def test_agent_first_issue_ready(self) -> None:
        assert _build_final_verdict("agent", "first-issue-dry-run") == "READY_FOR_REAL_FIRST_ISSUE"

    def test_developer_first_issue_ready(self) -> None:
        assert _build_final_verdict("developer", "first-issue-dry-run") == "READY_FOR_REAL_FIRST_ISSUE"

    def test_check_only_hold(self) -> None:
        assert _build_final_verdict("agent", "check-only") == "HOLD_ONBOARDING_GAP"

    def test_check_only_hold_developer(self) -> None:
        assert _build_final_verdict("developer", "check-only") == "HOLD_ONBOARDING_GAP"


class TestRenderSimulationDefaults:
    def test_contains_onboarding_start(self) -> None:
        output = render_simulation()
        assert "ONBOARDING_START" in output

    def test_contains_mode(self) -> None:
        output = render_simulation()
        assert "mode: first-issue-dry-run" in output

    def test_contains_default_role_agent(self) -> None:
        output = render_simulation()
        assert "role: Agent" in output

    def test_contains_writes_disabled(self) -> None:
        output = render_simulation()
        assert "writes: disabled" in output

    def test_contains_github_writes_disabled(self) -> None:
        output = render_simulation()
        assert "github_writes: disabled" in output

    def test_contains_lr_no_go(self) -> None:
        output = render_simulation()
        assert "lr: NO-GO" in output

    def test_contains_final_verdict(self) -> None:
        output = render_simulation()
        assert "Final Verdict: READY_FOR_REAL_FIRST_ISSUE" in output

    def test_contains_bootloader_section(self) -> None:
        output = render_simulation()
        assert "Bootloader Plan:" in output

    def test_contains_live_truth_section(self) -> None:
        output = render_simulation()
        assert "Live Truth Plan:" in output

    def test_contains_tour_section(self) -> None:
        output = render_simulation()
        assert "Tour Path:" in output

    def test_contains_doctor_validator_section(self) -> None:
        output = render_simulation()
        assert "Doctor / Validator Plan:" in output

    def test_contains_first_issue_dry_run_section(self) -> None:
        output = render_simulation()
        assert "First-Issue Dry Run:" in output

    def test_contains_pr_lock_section(self) -> None:
        output = render_simulation()
        assert "PR / LOCK Simulation:" in output

    def test_contains_hold_conditions_section(self) -> None:
        output = render_simulation()
        assert "HOLD Conditions:" in output

    def test_contains_context_brain_section(self) -> None:
        output = render_simulation()
        assert "Context Brain Note:" in output

    def test_contains_safety_lr(self) -> None:
        output = render_simulation()
        assert "LR remains NO-GO" in output

    def test_contains_safety_trade_capable(self) -> None:
        output = render_simulation()
        assert "trade-capable is not Live-Go" in output

    def test_contains_safety_echtgeld(self) -> None:
        output = render_simulation()
        assert "Echtgeld-Go" in output

    def test_contains_safety_read_only(self) -> None:
        output = render_simulation()
        assert "read-only" in output


class TestRenderSimulationByRole:
    def test_developer_role(self) -> None:
        output = render_simulation(role="developer")
        assert "role: Developer" in output
        assert "DEVELOPER_ONBOARDING.md" in output

    def test_agent_role(self) -> None:
        output = render_simulation(role="agent")
        assert "role: Agent" in output
        assert "CODEX.md" in output

    def test_docs_role(self) -> None:
        output = render_simulation(role="docs")
        assert "role: Docs Maintainer" in output

    def test_validation_role(self) -> None:
        output = render_simulation(role="validation")
        assert "role: Validation / Evidence" in output


class TestRenderSimulationByMode:
    def test_check_only_mode(self) -> None:
        output = render_simulation(mode="check-only")
        assert "mode: check-only" in output
        assert "HOLD_ONBOARDING_GAP" in output

    def test_first_issue_dry_run_mode(self) -> None:
        output = render_simulation(mode="first-issue-dry-run")
        assert "READY_FOR_REAL_FIRST_ISSUE" in output


class TestRenderSimulationJson:
    def test_valid_json(self) -> None:
        output = render_simulation_json()
        data = json.loads(output)
        assert isinstance(data, dict)

    def test_json_contains_role(self) -> None:
        output = render_simulation_json()
        data = json.loads(output)
        assert "role" in data
        assert data["role"] == "Agent"

    def test_json_contains_mode(self) -> None:
        output = render_simulation_json()
        data = json.loads(output)
        assert data["mode"] == "first-issue-dry-run"

    def test_json_contains_verdict(self) -> None:
        output = render_simulation_json()
        data = json.loads(output)
        assert data["verdict"] == "READY_FOR_REAL_FIRST_ISSUE"

    def test_json_contains_sections(self) -> None:
        output = render_simulation_json()
        data = json.loads(output)
        assert "sections" in data
        assert "bootloader" in data["sections"]
        assert "live_truth" in data["sections"]
        assert "context_brain" in data["sections"]

    def test_json_developer_role(self) -> None:
        output = render_simulation_json(role="developer")
        data = json.loads(output)
        assert data["role"] == "Developer"
        assert data["verdict"] == "READY_FOR_REAL_FIRST_ISSUE"

    def test_json_check_only_mode(self) -> None:
        output = render_simulation_json(mode="check-only")
        data = json.loads(output)
        assert data["verdict"] == "HOLD_ONBOARDING_GAP"


class TestVerdictEnum:
    def test_ready_for_real_first_issue(self) -> None:
        assert "READY_FOR_REAL_FIRST_ISSUE" in VERDICT_ENUM

    def test_hold_onboarding_gap(self) -> None:
        assert "HOLD_ONBOARDING_GAP" in VERDICT_ENUM

    def test_blocked_bootloader(self) -> None:
        assert "BLOCKED_BOOTLOADER" in VERDICT_ENUM

    def test_blocked_live_truth(self) -> None:
        assert "BLOCKED_LIVE_TRUTH" in VERDICT_ENUM

    def test_blocked_governance(self) -> None:
        assert "BLOCKED_GOVERNANCE" in VERDICT_ENUM

    def test_enum_length(self) -> None:
        assert len(VERDICT_ENUM) == 5


class TestBuildBootloaderPlan:
    def test_contains_read_order(self) -> None:
        lines = _build_bootloader_plan("agent")
        text = "\n".join(lines)
        assert "AGENTS.md" in text
        assert "agents/AGENTS.md" in text
        assert "OPEN_CODE_AGENTS.md" in text

    def test_contains_context_brain_preflight(self) -> None:
        lines = _build_bootloader_plan("agent")
        text = "\n".join(lines)
        assert "context_brain_attempted" in text

    def test_agent_has_codex(self) -> None:
        lines = _build_bootloader_plan("agent")
        text = "\n".join(lines)
        assert "CODEX.md" in text

    def test_developer_no_codex(self) -> None:
        lines = _build_bootloader_plan("developer")
        text = "\n".join(lines)
        assert "CODEX.md" not in text


class TestBuildLiveTruthPlan:
    def test_contains_github_live(self) -> None:
        lines = _build_live_truth_plan()
        text = "\n".join(lines)
        assert "GitHub live" in text

    def test_contains_ledger_note(self) -> None:
        lines = _build_live_truth_plan()
        text = "\n".join(lines)
        assert "CURRENT_STATUS.md" in text
        assert "context only" in text

    def test_contains_lr_ssot(self) -> None:
        lines = _build_live_truth_plan()
        text = "\n".join(lines)
        assert "LR-AUDIT-STATUS" in text


class TestBuildHoldConditions:
    def test_contains_context_brain_fail(self) -> None:
        lines = _build_hold_conditions()
        text = "\n".join(lines)
        assert "Context Brain Preflight fails" in text

    def test_contains_scope_growth(self) -> None:
        lines = _build_hold_conditions()
        text = "\n".join(lines)
        assert "scope growth" in text

    def test_contains_secrets_boundary(self) -> None:
        lines = _build_hold_conditions()
        text = "\n".join(lines)
        assert "Secrets" in text

    def test_contains_dirty_worktree(self) -> None:
        lines = _build_hold_conditions()
        text = "\n".join(lines)
        assert "Worktree dirty" in text


class TestBuildContextBrainNote:
    def test_contains_attempted_true(self) -> None:
        lines = _build_context_brain_note()
        text = "\n".join(lines)
        assert "context_brain_attempted=true" in text

    def test_contains_fallback_reason(self) -> None:
        lines = _build_context_brain_note()
        text = "\n".join(lines)
        assert "repo_fallback_reason=tool_blocked" in text

    def test_contains_no_db_backed_claims(self) -> None:
        lines = _build_context_brain_note()
        text = "\n".join(lines)
        assert "DB-backed claims" in text


class TestBuildPrLockSimulation:
    def test_contains_lock_comment(self) -> None:
        lines = _build_pr_lock_simulation()
        text = "\n".join(lines)
        assert "LOCK" in text

    def test_contains_required_checks(self) -> None:
        lines = _build_pr_lock_simulation()
        text = "\n".join(lines)
        assert "ci" in text
        assert "policy-gate" in text

    def test_contains_squash_merge(self) -> None:
        lines = _build_pr_lock_simulation()
        text = "\n".join(lines)
        assert "Squash-merge" in text


class TestValidateOutputSafe:
    def test_clean_output_passes(self) -> None:
        _validate_output_safe("safe output without secrets")

    def test_token_assignment_rejected(self) -> None:
        with pytest.raises(ValueError, match="potential secret leak"):
            _validate_output_safe("token: abc123secretkey")

    def test_api_key_assignment_rejected(self) -> None:
        with pytest.raises(ValueError, match="potential secret leak"):
            _validate_output_safe("api_key=sk-live-abcdef")

    def test_github_token_pattern_rejected(self) -> None:
        with pytest.raises(ValueError, match="potential secret leak"):
            _validate_output_safe("ghp_abcdefghijklmnopqrstuvwxyz123456")

    def test_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="potential secret leak"):
            _validate_output_safe("check https://example.com/secret")


class TestSimulationOutputContract:
    def test_contains_all_required_sections(self) -> None:
        output = render_simulation()
        required_prefixes = [
            "ONBOARDING_START",
            "Context Brain Note:",
            "Bootloader Plan:",
            "Live Truth Plan:",
            "Tour Path:",
            "Doctor / Validator Plan:",
            "First-Issue Dry Run:",
            "PR / LOCK Simulation:",
            "HOLD Conditions:",
            "Final Verdict:",
        ]
        for prefix in required_prefixes:
            assert prefix in output, f"Missing required section: {prefix}"

    def test_verdict_is_valid_enum(self) -> None:
        output = render_simulation()
        verdict_line = [line for line in output.split("\n") if "Final Verdict:" in line][0]
        verdict = verdict_line.split(": ", 1)[1].strip()
        assert verdict in VERDICT_ENUM, f"Verdict '{verdict}' not in VERDICT_ENUM"


class TestForbiddenPatternsInOutput:
    def test_no_urls_in_rendered_output(self) -> None:
        output = render_simulation()
        url_pattern = re.compile(r"https?://[^\s\"']+")
        assert not url_pattern.search(output), "Output contains URLs"

    def test_no_token_patterns_in_rendered_output(self) -> None:
        output = render_simulation()
        for pattern in FORBIDDEN_OUTPUT_PATTERNS:
            assert not pattern.search(output), f"Output matches forbidden pattern: {pattern.pattern}"
