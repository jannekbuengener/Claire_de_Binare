"""Contract: Cursor environment Dockerfile COPY sources are in build context (#4360).

test_id: tc_cursor_environment_dockerfile_context_4360
test_type: contract / bauteil
cdb_area: infra/ci / agent-control
rule_ref: .cursor/environment.json build context must include all local COPY/ADD sources
issue_ref: #4360
security_relevant: false
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.agent_control.environment.dockerfile_context import (
    assert_cursor_dockerfile_context_ok,
    check_cursor_dockerfile_context,
    dockerignore_excludes,
    parse_local_copy_sources,
)
from tools.agent_control.paths import REPO_ROOT

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_dockerignore_exact_requirements_dev_match() -> None:
    excluded, pattern = dockerignore_excludes(
        "requirements-dev.txt",
        ["requirements-dev.txt"],
    )
    assert excluded is True
    assert pattern == "requirements-dev.txt"


def test_dockerignore_negation_last_match_wins() -> None:
    excluded, pattern = dockerignore_excludes(
        "requirements-dev.txt",
        ["requirements-dev.txt", "!requirements-dev.txt"],
    )
    assert excluded is False
    assert pattern == "!requirements-dev.txt"


def test_parse_ci_dockerfile_copy_sources() -> None:
    text = (
        "FROM python:3.12-slim-bookworm\n"
        "COPY requirements.txt requirements-dev.txt "
        "requirements-mcp.txt pyproject.toml ./\n"
        "COPY --from=build /venv /venv\n"
        "ADD https://example.com/x.tgz /tmp/\n"
    )
    sources = parse_local_copy_sources(text)
    assert sources == [
        ("COPY", "requirements.txt"),
        ("COPY", "requirements-dev.txt"),
        ("COPY", "requirements-mcp.txt"),
        ("COPY", "pyproject.toml"),
    ]


def test_repo_cursor_environment_dockerfile_context_ok() -> None:
    report = assert_cursor_dockerfile_context_ok(REPO_ROOT)
    assert report.config_path == ".cursor/environment.json"
    assert report.dockerfile_path == "ci/Dockerfile"
    assert report.context_path == "."
    names = {item.source for item in report.sources}
    assert "requirements-dev.txt" in names
    assert all(item.ok for item in report.sources)


def test_regression_excluded_requirements_dev_fails(tmp_path: Path) -> None:
    """Synthetic repo recreates the pre-#4360 failure mode."""
    root = tmp_path / "repo"
    cursor = root / ".cursor"
    cursor.mkdir(parents=True)
    (root / "ci").mkdir()
    (root / "requirements.txt").write_text("x\n", encoding="utf-8")
    (root / "requirements-dev.txt").write_text("y\n", encoding="utf-8")
    (root / "requirements-mcp.txt").write_text("z\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='t'\n", encoding="utf-8")
    (root / "ci" / "Dockerfile").write_text(
        "FROM python:3.12-slim-bookworm\n"
        "COPY requirements.txt requirements-dev.txt "
        "requirements-mcp.txt pyproject.toml ./\n",
        encoding="utf-8",
    )
    (root / ".dockerignore").write_text(
        "# Requirements (install from specific file, not all)\n"
        "requirements-dev.txt\n",
        encoding="utf-8",
    )
    (cursor / "environment.json").write_text(
        json.dumps(
            {
                "build": {"dockerfile": "../ci/Dockerfile", "context": ".."},
                "install": "python -m pip install -r requirements-dev.txt",
                "agentCanUpdateSnapshot": False,
            }
        ),
        encoding="utf-8",
    )

    report = check_cursor_dockerfile_context(root)
    assert report.ok is False
    failed = {item.source: item for item in report.failures}
    assert "requirements-dev.txt" in failed
    assert failed["requirements-dev.txt"].excluded_by_dockerignore is True
    assert failed["requirements-dev.txt"].matching_pattern == "requirements-dev.txt"
