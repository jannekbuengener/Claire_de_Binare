"""Workflow contract guards for CDB Context Refresh Report (#4506)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "cdb-context-refresh-report.yml"


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_generate_step_sets_pythonpath_for_core_import() -> None:
    workflow = _load_workflow()
    steps = workflow["jobs"]["context-refresh"]["steps"]
    generate = next(step for step in steps if step.get("id") == "generate")
    env = generate.get("env") or {}
    assert env.get("PYTHONPATH") == "${{ github.workspace }}"
    assert "generate_context_refresh_report.py" in generate["run"]
