"""Tests for check_postgres_driver_compat.py."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from check_postgres_driver_compat import forbid_text, main, require_text


def test_current_repo_postgres_driver_compat_passes() -> None:
    assert main() == 0


def test_require_and_forbid_text_helpers(tmp_path: Path) -> None:
    sample = tmp_path / "requirements.txt"
    sample.write_text("psycopg2-binary==2.9.11\n", encoding="utf-8")

    assert require_text(sample, "psycopg2-binary==2.9.11") is None
    assert forbid_text(sample, "psycopg2-binary==2.9.9") is None
    assert require_text(sample, "psycopg2-binary==2.9.12") is not None
    assert forbid_text(sample, "psycopg2-binary==2.9.11") is not None
