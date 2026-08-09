"""Regression contract for the Fast-CI MCP dependency closure (#4434)."""

from __future__ import annotations

import pytest

from pathlib import Path

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]


def _pinned_requirements() -> dict[str, str]:
    requirements = REPO_ROOT / "requirements-mcp.txt"
    return {
        name: version
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if "==" in line and not line.lstrip().startswith("#")
        for name, version in [line.split("==", maxsplit=1)]
    }


def test_mcp_fast_ci_dependency_closure_pins_pydantic_core_pair() -> None:
    requirements = _pinned_requirements()

    assert requirements["mcp"] == "1.28.1"
    assert requirements["mcp-server-time"] == "2026.7.10"
    assert requirements["pydantic"] == "2.13.4"
    assert requirements["pydantic-core"] == "2.46.4"
