"""Regression contract for the Fast-CI MCP dependency closure (#4434)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.stages import mcp_dependency_closure

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

    assert requirements["mcp"] == "2.1.1"
    assert "mcp-server-time" not in requirements
    assert requirements["pydantic"] == "2.14.0b1"
    assert requirements["pydantic-core"] == "2.48.0"


def test_mcp_dependency_closure_rejects_an_incompatible_active_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        mcp_dependency_closure.importlib.metadata,
        "version",
        lambda name: "2.0.0",
    )

    with pytest.raises(ValueError, match="MCP_SDK_VERSION_MISMATCH"):
        mcp_dependency_closure._validate_mcp_sdk(REPO_ROOT)


def test_mcp_dependency_closure_accepts_the_pinned_sdk() -> None:
    expected, active = mcp_dependency_closure._validate_mcp_sdk(REPO_ROOT)

    assert expected == "2.1.1"
    assert active == expected
