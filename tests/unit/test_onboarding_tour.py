"""Unit tests for onboarding tour (#3249)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from tools import onboarding_doctor
from tools import onboarding_tour

pytestmark = pytest.mark.unit


def test_render_tour_default_contains_core_surfaces() -> None:
    output = onboarding_tour.render_tour()

    assert "Role: General" in output
    assert "LR remains NO-GO." in output
    assert "Board stage trade-capable is not Live-Go." in output
    assert "No Echtgeld-Go." in output
    assert "docs/onboarding/cdb_glossary.md" in output
    assert "docs/onboarding/fresh_clone_rehearsal.md" in output
    assert ".\\tools\\cdb.ps1 onboarding doctor" in output
    assert "docs/onboarding/first_issue_sandbox.md" in output
    assert "docs/onboarding/examples/first_issue_to_pr_flow.md" not in output


@pytest.mark.parametrize(
    ("role", "expected_title", "expected_surface"),
    [
        ("developer", "Role: Developer", "DEVELOPER_ONBOARDING.md"),
        ("agent", "Role: Agent", "agents/OPEN_CODE_AGENTS.md"),
        ("docs", "Role: Docs Maintainer", "tools/README.md"),
        (
            "validation",
            "Role: Validation / Evidence",
            "docs/onboarding/templates/evidence_doc_template.md",
        ),
        (
            "evidence",
            "Role: Validation / Evidence",
            "docs/onboarding/templates/evidence_doc_template.md",
        ),
    ],
)
def test_render_tour_role_paths(
    role: str, expected_title: str, expected_surface: str
) -> None:
    output = onboarding_tour.render_tour(role)

    assert expected_title in output
    assert expected_surface in output


def test_render_tour_output_has_no_forbidden_patterns() -> None:
    for role in (None, "developer", "agent", "docs", "validation", "evidence"):
        output = onboarding_tour.render_tour(role)
        for pattern in onboarding_doctor.FORBIDDEN_OUTPUT_PATTERNS:
            assert not pattern.search(output), pattern.pattern


def test_main_rejects_unknown_role() -> None:
    with pytest.raises(SystemExit) as exc_info:
        onboarding_tour.main(["--role", "runtime"])

    assert exc_info.value.code == 2


def test_main_prints_agent_tour(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = onboarding_tour.main(["--role", "agent"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Role: Agent" in captured.out
    assert "AGENTS.md" in captured.out


def test_cdb_front_door_includes_onboarding_tour() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    content = (repo_root / "tools" / "cdb.ps1").read_text(encoding="utf-8")

    assert ".\\tools\\cdb.ps1 onboarding tour" in content
    assert "'onboarding tour' { 'tools\\onboarding_tour.py' }" in content


def test_direct_script_execution_works() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "tools/onboarding_tour.py", "--role", "docs"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Role: Docs Maintainer" in result.stdout
