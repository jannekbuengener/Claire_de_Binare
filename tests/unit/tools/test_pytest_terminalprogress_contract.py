from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_pytest_config_disables_terminalprogress_on_windows() -> None:
    config = (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")

    assert "-p no:terminalprogress" in config
