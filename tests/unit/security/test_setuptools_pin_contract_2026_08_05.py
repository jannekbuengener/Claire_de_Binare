"""Contract: setuptools pin floor CVE-2026-59890 (2026-08-05)."""

from __future__ import annotations
from pathlib import Path
import re
import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]
REPO = Path(__file__).resolve().parents[3]
FLOOR = (83, 0, 0)


def test_dockerfiles_pin_setuptools_at_or_above_floor() -> None:
    bad = []
    for path in REPO.rglob("Dockerfile*"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"setuptools==([0-9]+(?:\.[0-9]+)*)", text):
            ver = tuple(int(p) for p in m.group(1).split("."))
            if ver < FLOOR:
                bad.append((str(path.relative_to(REPO)), m.group(1)))
    assert bad == [], f"setuptools pins below 83.0.0: {bad}"


def test_cve_not_in_trivyignore() -> None:
    ignore = REPO / ".trivyignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    assert "CVE-2026-59890" not in text
