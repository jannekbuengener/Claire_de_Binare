"""Contract: aiohttp/cryptography pin floors for HIGH CVEs (2026-08-05 campaign).

Guards remediation of:
- CVE-2026-69244 (aiohttp < 3.14.3)
- CVE-2026-69247 (cryptography < 50.0.0)
- CVE-2026-69249 / CVE-2026-69248 (cryptography < 49.0.0; subsumed by 50.0.0)

Static requirements parsing only — no image build, no alert dismissal.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]

AIOHTTP_FLOOR = (3, 14, 3)
CRYPTOGRAPHY_FLOOR = (50, 0, 0)

EXECUTION_REQ = REPO_ROOT / "services" / "execution" / "requirements.txt"
ROOT_REQ = REPO_ROOT / "requirements.txt"
DEV_REQ = REPO_ROOT / "requirements-dev.txt"


def _parse_eq_pin(text: str, name: str) -> tuple[int, ...]:
    m = re.search(rf"(?m)^{re.escape(name)}==([0-9]+(?:\.[0-9]+)*)\s*$", text)
    assert m, f"missing exact pin {name}== in requirements"
    return tuple(int(p) for p in m.group(1).split("."))


def _parse_ge_or_eq_pin(text: str, name: str) -> tuple[int, ...]:
    m = re.search(
        rf"(?m)^{re.escape(name)}(?:==|>=)([0-9]+(?:\.[0-9]+)*)\s*$",
        text,
    )
    assert m, f"missing pin {name} in requirements"
    return tuple(int(p) for p in m.group(1).split("."))


def test_execution_aiohttp_meets_high_cve_floor() -> None:
    text = EXECUTION_REQ.read_text(encoding="utf-8")
    assert _parse_eq_pin(text, "aiohttp") >= AIOHTTP_FLOOR


def test_execution_cryptography_meets_high_cve_floor() -> None:
    text = EXECUTION_REQ.read_text(encoding="utf-8")
    assert _parse_eq_pin(text, "cryptography") >= CRYPTOGRAPHY_FLOOR


def test_root_and_dev_cryptography_meet_high_cve_floor() -> None:
    for path in (ROOT_REQ, DEV_REQ):
        text = path.read_text(encoding="utf-8")
        assert _parse_ge_or_eq_pin(text, "cryptography") >= CRYPTOGRAPHY_FLOOR


def test_root_and_dev_aiohttp_meet_high_cve_floor() -> None:
    for path in (ROOT_REQ, DEV_REQ):
        text = path.read_text(encoding="utf-8")
        assert _parse_ge_or_eq_pin(text, "aiohttp") >= AIOHTTP_FLOOR


def test_cves_not_silenced_in_trivyignore() -> None:
    ignore = REPO_ROOT / ".trivyignore"
    text = ignore.read_text(encoding="utf-8") if ignore.is_file() else ""
    for cve in (
        "CVE-2026-69244",
        "CVE-2026-69247",
        "CVE-2026-69248",
        "CVE-2026-69249",
    ):
        assert cve not in text, f"{cve} must not be ignored"
