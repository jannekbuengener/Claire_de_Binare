"""Unit tests for local Context Query config initialization (#2687)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.surrealdb import local_query_config_init as init

pytestmark = pytest.mark.unit


def _write_example(root: Path) -> Path:
    source = Path("infrastructure/config/surrealdb/context_query.local.example.yaml")
    config_dir = root / "infrastructure/config/surrealdb"
    config_dir.mkdir(parents=True)
    target = config_dir / "context_query.local.example.yaml"
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_init_creates_gitignored_local_config_from_example(tmp_path: Path) -> None:
    _write_example(tmp_path)

    result = init.init_local_query_config(repo_root=tmp_path)

    target = tmp_path / init.DEFAULT_TARGET
    assert result == f"created: {init.DEFAULT_TARGET}"
    assert target.is_file()
    assert "super-secret-password" not in target.read_text(encoding="utf-8")


def test_init_is_idempotent_when_local_config_exists(tmp_path: Path) -> None:
    example = _write_example(tmp_path)
    target = tmp_path / init.DEFAULT_TARGET
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")

    result = init.init_local_query_config(repo_root=tmp_path)

    assert result == f"exists: {init.DEFAULT_TARGET}"


def test_init_fails_when_example_is_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        init.init_local_query_config(repo_root=tmp_path)


def test_main_returns_ok_for_created_config(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_example(tmp_path)

    assert init.main(["--repo-root", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "[OK] created:" in output
    assert "SURREAL_PASS" not in output
