from __future__ import annotations

import importlib
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

PATCHED_HELPERS: tuple[tuple[str, str], ...] = (
    ("tools.evidence_harvester.boot", "_now_utc"),
    ("tools.evidence_harvester.ops_validation", "_now_utc"),
    ("tools.evidence_harvester.snapshot", "utc_now"),
    ("tools.evidence_harvester.validation", "_now_utc"),
    ("tools.evidence_harvester.write_audit", "_now_utc"),
)


def _load(module_name: str) -> ModuleType:
    return importlib.import_module(module_name)


@pytest.mark.unit
@pytest.mark.parametrize(("module_name", "helper_name"), PATCHED_HELPERS)
def test_utc_helper_returns_aware_utc_when_cdb_utcnow_is_naive(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    helper_name: str,
) -> None:
    module = _load(module_name)
    naive_utc = datetime(2026, 6, 20, 18, 44, 13)

    monkeypatch.setattr(module, "cdb_utcnow", lambda: naive_utc)

    result = getattr(module, helper_name)()

    assert result == naive_utc.replace(tzinfo=UTC)
    assert result.tzinfo == UTC


@pytest.mark.unit
@pytest.mark.parametrize(("module_name", "helper_name"), PATCHED_HELPERS)
def test_utc_helper_preserves_aware_utc(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    helper_name: str,
) -> None:
    module = _load(module_name)
    aware_utc = datetime(2026, 6, 20, 18, 44, 13, tzinfo=UTC)

    monkeypatch.setattr(module, "cdb_utcnow", lambda: aware_utc)

    result = getattr(module, helper_name)()

    assert result == aware_utc
    assert result.tzinfo == UTC


@pytest.mark.unit
def test_no_unsafe_cdb_utcnow_astimezone_pattern_remains() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    harvester_dir = repo_root / "tools" / "evidence_harvester"
    unsafe_pattern = "cdb_utcnow().astimezone(UTC)"

    offenders = [
        path.relative_to(repo_root).as_posix()
        for path in sorted(harvester_dir.glob("*.py"))
        if unsafe_pattern in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
