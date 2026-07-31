"""Static contract for Commit Status versus Check Run sentinel semantics (#4202)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "required-checks-audit.yml"


def test_sentinel_reads_combined_commit_status_and_check_runs_separately() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "/commits/$SHA/status" in text
    assert "/commits/$SHA/check-runs?per_page=100" in text
    assert 'required_type="commit_status"' in text


def test_cdb_local_ci_cannot_pass_from_namesake_check_run() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "status_json" in text
    assert "check_runs_json" in text
    assert "namesake check run is not accepted" in text
