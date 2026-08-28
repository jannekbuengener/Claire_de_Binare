"""Workflow contract guards for Auto Milestone assign-single (#4490)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "auto-milestone.yml"

_ILLEGAL_NULLISH_OR_MIX = re.compile(
    r"\?\?\s*\n?\s*Number\(context\.payload\.client_payload\?\.issue_number \|\| 0\) \|\|"
)


@pytest.mark.unit
def test_assign_single_issue_number_expression_has_legal_nullish_coalescing() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert _ILLEGAL_NULLISH_OR_MIX.search(content) is None
    assert "(Number(context.payload.client_payload?.issue_number || 0) ||" in content
