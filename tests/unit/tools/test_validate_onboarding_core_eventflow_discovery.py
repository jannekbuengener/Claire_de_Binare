"""Regression tests for core-eventflow onboarding discovery (#4116)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import validate_onboarding_docs as validator

pytestmark = pytest.mark.unit


def _make_file(root: Path, rel: str, content: str = "") -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def test_discover_core_eventflow_surfaces_finds_all_pack_pages(tmp_path: Path) -> None:
    pack = "docs/onboarding/core-eventflows"
    for name in ("README.md", "alpha.md", "beta.md"):
        _make_file(tmp_path, f"{pack}/{name}")

    assert validator.discover_core_eventflow_surfaces(tmp_path) == [
        f"{pack}/README.md",
        f"{pack}/alpha.md",
        f"{pack}/beta.md",
    ]


def test_validate_all_discovers_new_broken_core_eventflow_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack = "docs/onboarding/core-eventflows"
    _make_file(tmp_path, f"{pack}/new_flow.md", "[broken](../../../missing.md)")
    monkeypatch.setattr(validator, "ACTIVE_ONBOARDING_SURFACES", [])

    errors = validator.validate_all(root=tmp_path)

    assert len(errors) == 1
    assert f"{pack}/new_flow.md" in errors[0]
    assert "missing.md" in errors[0]
