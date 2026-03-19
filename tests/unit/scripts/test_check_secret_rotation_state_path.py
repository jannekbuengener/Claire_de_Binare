"""Tests for check_secret_rotation_state_path.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts" / "governance"))

from check_secret_rotation_state_path import forbid_markers, main, require_markers


def test_current_repo_secret_rotation_state_path_passes() -> None:
    assert main() == 0


def test_marker_helpers_report_missing_and_forbidden_markers(tmp_path: Path) -> None:
    sample = tmp_path / "Rotate-Secrets.ps1"
    sample.write_text(
        "Rotation state: $SECRETS_PATH/.rotation_state.json\n"
        "Using old state path as fallback\n",
        encoding="utf-8",
    )

    missing = require_markers(
        sample,
        [
            "Rotation state: $SECRETS_PATH/.rotation_state.json",
            "Move-Item $oldStatePath $script:STATE_PATH -Force",
        ],
    )
    forbidden = forbid_markers(sample, ["Using old state path as fallback"])

    assert len(missing) == 1
    assert "Move-Item $oldStatePath $script:STATE_PATH -Force" in missing[0]
    assert len(forbidden) == 1
    assert "Using old state path as fallback" in forbidden[0]
