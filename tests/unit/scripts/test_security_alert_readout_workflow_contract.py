"""Workflow contract guards for security-alert-readout issue automation (#2289)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "security-alert-readout.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_manual_issue_automation_live_input_defaults_false() -> None:
    workflow = _load_workflow()
    on_triggers = workflow.get("on") or workflow.get(True) or {}
    workflow_dispatch = on_triggers.get("workflow_dispatch") or {}
    inputs = workflow_dispatch.get("inputs") or {}
    live_input = inputs.get("issue_automation_live") or {}
    assert str(live_input.get("default")).lower() == "false"


@pytest.mark.unit
def test_issue_automation_scheduled_runs_default_to_live_mode() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'LIVE_MODE="true"' in content
    assert 'if [[ "${GITHUB_EVENT_NAME}" == "workflow_dispatch" ]]; then' in content
    assert "LIVE_MODE=\"${{ inputs.issue_automation_live || 'false' }}\"" in content


@pytest.mark.unit
def test_issue_automation_exports_summary_json_to_outputs() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "automation_summary_json" in content
    assert "AUTOMATION_SUMMARY_JSON=" in content
    assert "issue-automation counters: created=" in content
    assert "|| true" in content
    assert (
        '\'{"mode":"skipped","created":0,"deduped":0,"skipped":0,"capped":0,"failed":0,"created_issues":[]}\''
        in content
    )


@pytest.mark.unit
def test_comment_epic_does_not_use_fragile_issue_links_python_one_liner() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'issue_links="$(python3 -c' not in content
    assert 'refs=[(f"#' not in content


@pytest.mark.unit
def test_comment_epic_uses_robust_multiline_issue_links_renderer() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert 'issue_links="$(SUMMARY_JSON="${summary_json}" python3 -c "' in content
    assert "created_issues = payload.get('created_issues')" in content
    assert "print('; '.join(refs))" in content
