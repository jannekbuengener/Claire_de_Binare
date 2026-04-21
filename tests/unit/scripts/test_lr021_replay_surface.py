"""Fail-closed surface guard for the LR-021 replay smoke canonical entry-points.

Protects against two drift classes that caused real operational failures (Issue #1824):
  1. Missing `workflow_dispatch` in lr021_replay_smoke.yml
     → manual on-demand dispatch fails with HTTP 422
  2. Missing `replay-shadow-run` target in Makefile
     → workflow fails with 'No rule to make target'

Workflow and Makefile entry-point are treated as a coupled surface: the workflow calls
`make replay-shadow-run` directly, so both must be present on main at all times.

Additionally guards the replay smoke summary semantics (Issue #1825): ensures the summary
distinguishes the pipeline step result from the fachliches `gate_status` so operators
cannot mistake a fachliches FAIL for a pipeline failure or an LR-/Live-Freigabe.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "lr021_replay_smoke.yml"
MAKEFILE_PATH = REPO_ROOT / "Makefile"


# ---------------------------------------------------------------------------
# #1824 — workflow_dispatch trigger guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lr021_workflow_has_workflow_dispatch() -> None:
    """lr021_replay_smoke.yml must declare the workflow_dispatch trigger.

    Without this trigger, manual on-demand dispatch fails with HTTP 422.
    This was a real operational failure documented in Issue #1824.
    """
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    raw = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(raw)
    # PyYAML parses the top-level "on:" key as boolean True, not the string "on".
    on_triggers = workflow.get("on") or workflow.get(True) or {}
    assert "workflow_dispatch" in on_triggers, (
        "lr021_replay_smoke.yml is missing the 'workflow_dispatch' trigger. "
        "Manual on-demand dispatch will fail with HTTP 422. See #1824."
    )


# ---------------------------------------------------------------------------
# #1824 — Makefile replay-shadow-run target guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_makefile_has_replay_shadow_run_target() -> None:
    """Makefile must declare replay-shadow-run as a phony target with a recipe.

    Without this target, `make replay-shadow-run` fails with 'No rule to make target'.
    The lr021_replay_smoke.yml workflow calls this target directly.
    This was a real operational failure documented in Issue #1824.
    """
    assert MAKEFILE_PATH.exists(), f"Makefile not found: {MAKEFILE_PATH}"
    content = MAKEFILE_PATH.read_text(encoding="utf-8")

    # Verify .PHONY declaration contains replay-shadow-run
    assert re.search(r"^\.PHONY[^#\n]*\breplay-shadow-run\b", content, re.MULTILINE), (
        "Makefile .PHONY declaration is missing 'replay-shadow-run'. "
        "`make replay-shadow-run` will fail. See #1824."
    )

    # Verify an actual target recipe line (starts at column 0 in a Makefile)
    assert re.search(r"^replay-shadow-run:", content, re.MULTILINE), (
        "Makefile has no actual 'replay-shadow-run:' target recipe line. "
        "`make replay-shadow-run` will fail. See #1824."
    )


# ---------------------------------------------------------------------------
# #1824 — coupling guard: workflow must invoke the canonical Makefile target
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lr021_workflow_calls_replay_shadow_run() -> None:
    """lr021_replay_smoke.yml must invoke `make replay-shadow-run`.

    This test verifies that the workflow and the Makefile entry-point remain coupled.
    If the workflow switches invocation style, the Makefile guard above would become
    orphaned and future Makefile drift would go undetected. See #1824.
    """
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "make replay-shadow-run" in content, (
        "lr021_replay_smoke.yml no longer invokes 'make replay-shadow-run'. "
        "The workflow-to-Makefile coupling is broken. See #1824."
    )


# ---------------------------------------------------------------------------
# #1825 — summary semantic-separation guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_lr021_replay_summary_has_semantic_separation() -> None:
    """Replay smoke summary must clearly separate pipeline step result from gate_status.

    Prevents drift back to a combined summary that causes operators to mistake a
    fachliches gate_status=FAIL for a pipeline failure or an LR-/Live-Freigabe.
    The summary step must contain:
    - An 'Einordnung' note distinguishing gate_status from pipeline step completion
    - A 'fachlich' semantic label making the nature of gate_status explicit
    See #1825.
    """
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    content = WORKFLOW_PATH.read_text(encoding="utf-8")

    # Guard: summary_md must be defined (either as list literal or via "\n".join([...]))
    assert re.search(r"summary_md\s*=", content), (
        "lr021_replay_smoke.yml no longer defines summary_md. "
        "This regression guard cannot verify the generated summary semantics. See #1825."
    )

    assert "Einordnung" in content, (
        "lr021_replay_smoke.yml summary is missing an 'Einordnung' note. "
        "Operators cannot distinguish pipeline step completion from fachliches gate_status. "
        "See #1825."
    )
    assert "fachlich" in content, (
        "lr021_replay_smoke.yml summary is missing a 'fachlich' semantic label on gate_status. "
        "Operators cannot tell whether gate_status reflects a pipeline failure or a "
        "strategy-gate threshold result. See #1825."
    )
