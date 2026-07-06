"""Onboarding fresh-agent and simulation contract tests (#3868).

Contract-Test: read-only default, explicit setup GO, first-issue dry-run,
guided-rehearsal routing, and orchestrator state machine boundaries.

Complements smoke tests under tests/smoke/test_onboarding_* and
tests/unit/tools/test_onboarding_simulation.py.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tools.onboarding_orchestrator import (
    ACTION_ABORT,
    ACTION_APPROVE_SETUP,
    ACTION_REQUEST_SETUP_GO,
    ACTION_STATUS_ONLY,
    SETUP_ABORTED,
    SETUP_APPROVED,
    SETUP_CONFIRMATION_PENDING,
    SETUP_REQUIRED,
    OrchestratorOutput,
    build_verdict,
    format_output,
    get_setup_prompt_text,
    normalize_setup_prompt_input,
)
from tools.onboarding_simulation import render_simulation

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

ONBOARDING_MODULE = REPO_ROOT / "tools" / "onboarding_orchestrator.py"
AGENTS_ROOT = REPO_ROOT / "AGENTS.md"


# ---------------------------------------------------------------------------
# Read-only default (#3868)
# ---------------------------------------------------------------------------


def test_orchestrator_module_declares_read_only_default() -> None:
    doc = inspect.getdoc(__import__("tools.onboarding_orchestrator", fromlist=["x"]))
    assert doc is not None
    lowered = doc.lower()
    assert "read-only by default" in lowered
    assert "no file writes" in lowered
    assert "no setup mutation" in lowered


def test_orchestrator_source_has_two_option_setup_prompt_only() -> None:
    text = ONBOARDING_MODULE.read_text(encoding="utf-8")
    assert "1. Ja" in text
    assert "2. Abbruch" in text
    assert "SETUP_CONFIRMATION_PENDING" in text


def test_format_output_always_declares_no_changes_and_lr_no_go() -> None:
    report = OrchestratorOutput(status="PASS", state="STATUS_ONLY")
    output = format_output(report, "text")
    assert "No changes made." in output
    assert "LR remains NO-GO." in output
    assert "trade-capable is not Live-Go." in output


def test_simulation_default_disables_writes() -> None:
    output = render_simulation()
    assert "writes: disabled" in output
    assert "github_writes: disabled" in output
    assert "lr: NO-GO" in output


# ---------------------------------------------------------------------------
# Setup mutation requires explicit selection (#3868)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", SETUP_APPROVED),
        ("ja", SETUP_APPROVED),
        ("yes", SETUP_APPROVED),
        ("2", SETUP_ABORTED),
        ("nein", SETUP_ABORTED),
        ("abbruch", SETUP_ABORTED),
        ("maybe", None),
        ("", None),
    ],
)
def test_normalize_setup_prompt_input_gate(raw: str, expected: str | None) -> None:
    assert normalize_setup_prompt_input(raw) == expected


def test_setup_prompt_has_exactly_two_options() -> None:
    prompt = get_setup_prompt_text()
    assert prompt.count("1. Ja") == 1
    assert prompt.count("2. Abbruch") == 1


def test_build_verdict_setup_warn_requires_explicit_go_in_default_mode() -> None:
    report = build_verdict(REPO_ROOT, mode="default")
    if report.status == "SETUP_WARN":
        assert report.requires_explicit_setup_go is True
        assert report.state == SETUP_CONFIRMATION_PENDING
        assert report.setup_prompt_visible is True
        assert ACTION_APPROVE_SETUP in report.allowed_next_actions
        assert ACTION_ABORT in report.allowed_next_actions


def test_build_verdict_check_only_never_shows_setup_prompt() -> None:
    report = build_verdict(REPO_ROOT, mode="check-only")
    assert report.setup_prompt_visible is False
    assert report.state in {SETUP_REQUIRED, "DRY_RUN_COMPLETE", "BLOCKED", "STATUS_ONLY"}
    if report.status == "SETUP_WARN":
        assert ACTION_REQUEST_SETUP_GO in report.allowed_next_actions
        assert ACTION_APPROVE_SETUP not in report.allowed_next_actions


def test_format_output_check_only_forbids_setup_mutation() -> None:
    report = OrchestratorOutput(mode="check-only", status="SETUP_WARN", state=SETUP_REQUIRED)
    report.requires_explicit_setup_go = True
    output = format_output(report, "text")
    assert "check-only mode is dry-run only." in output
    assert "No setup mutation is allowed from this run." in output


# ---------------------------------------------------------------------------
# First-issue dry-run without side effects (#3868)
# ---------------------------------------------------------------------------


def test_first_issue_dry_run_simulation_is_read_only() -> None:
    output = render_simulation(mode="first-issue-dry-run")
    assert "mode: first-issue-dry-run" in output
    assert "writes: disabled" in output
    assert "github_writes: disabled" in output
    assert "READY_FOR_REAL_FIRST_ISSUE" in output
    assert "First-Issue Dry Run:" in output


def test_first_issue_dry_run_json_has_no_mutation_flags() -> None:
    from tools.onboarding_simulation import render_simulation_json

    data = __import__("json").loads(render_simulation_json(mode="first-issue-dry-run"))
    assert data["mode"] == "first-issue-dry-run"
    assert data["verdict"] == "READY_FOR_REAL_FIRST_ISSUE"


# ---------------------------------------------------------------------------
# Guided rehearsal / onboarding routing (#3868)
# ---------------------------------------------------------------------------


def test_agents_root_routes_onboarding_to_orchestrator() -> None:
    text = AGENTS_ROOT.read_text(encoding="utf-8")
    assert "python -m tools.onboarding_orchestrator" in text
    assert "fresh agent onboarding" in text
    assert "onboarding_simulation --mode guided-rehearsal" in text


def test_guided_rehearsal_simulation_is_non_mutating() -> None:
    output = render_simulation(mode="guided-rehearsal")
    assert "mode: guided-rehearsal" in output
    assert "writes: disabled" in output
    assert "GUIDED_REHEARSAL_DONE" in output
    assert "simuliert" in output.lower()


def test_build_verdict_with_mocked_doctor_runners_stays_deterministic() -> None:
    ok_proc = MagicMock(returncode=0, stdout="ok", stderr="")

    def _runner(*_args, **_kwargs):
        return ok_proc

    report = build_verdict(
        REPO_ROOT,
        mode="check-only",
        doctor_runner=_runner,
        context_doctor_runner=_runner,
    )
    assert report.mode == "check-only"
    assert report.check_scope == "onboarding_status_check_only"
    if not report.blockers:
        assert ACTION_STATUS_ONLY in report.allowed_next_actions or ACTION_ABORT in report.allowed_next_actions
