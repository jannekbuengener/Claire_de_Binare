"""Unit tests for cross-repo root inventory (#2853)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.mcp import cross_repo_root_inventory as inventory

pytestmark = pytest.mark.unit


def _mini_config(
    *,
    sibling_name: str = "missing-sibling",
    include_config_files: bool = True,
) -> dict:
    config_paths = (
        ["claire-de-binare.mcp.json", "pyproject.toml"]
        if include_config_files
        else ["claire-de-binare.mcp.json"]
    )
    return {
        "schema_version": "1.0",
        "issue_refs": ["#2853"],
        "defaults": {"workspaces_repos_dir_env": "CDB_WORKSPACES_REPOS_TEST"},
        "entries": [
            {
                "key": "working",
                "display_name": "working",
                "required": True,
                "local": {"kind": "repo_root"},
                "github": {
                    "owner": "jannekbuengener",
                    "repo": "Claire_de_Binare",
                },
            },
            {
                "key": "db",
                "display_name": "db",
                "required": True,
                "local": {"relative_path": "tools/surrealdb"},
                "github": {"kind": "same_as_working"},
            },
            {
                "key": "mcp",
                "display_name": "mcp",
                "required": True,
                "local": {"relative_path": "tools/mcp"},
                "github": {"kind": "same_as_working"},
            },
            {
                "key": "config",
                "display_name": "config",
                "required": True,
                "local": {"relative_paths": config_paths},
                "github": {"kind": "same_as_working"},
            },
            {
                "key": "optional_external",
                "display_name": "optional",
                "required": False,
                "local": {"sibling_dir": sibling_name},
                "github": {
                    "owner": "jannekbuengener",
                    "repo": "sample_brain",
                },
            },
        ],
    }


def _bootstrap_mini_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    (tmp_path / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (tmp_path / "tools" / "surrealdb").mkdir(parents=True)
    (tmp_path / "tools" / "mcp").mkdir(parents=True)
    (tmp_path / "claire-de-binare.mcp.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return tmp_path


def test_build_inventory_all_required_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _bootstrap_mini_repo(tmp_path)
    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    monkeypatch.setenv("CDB_WORKSPACES_REPOS_TEST", str(workspaces))

    report = inventory.build_inventory(
        repo,
        config=_mini_config(),
        check_github=False,
    )

    assert len(report.rows) == 5
    keys = {row.key for row in report.rows}
    assert keys == {"working", "db", "mcp", "config", "optional_external"}
    for row in report.rows:
        if row.required:
            assert row.local_status == "OK"
    optional = next(r for r in report.rows if r.key == "optional_external")
    assert optional.local_status == "MISSING"
    assert optional.github_target_status == "SKIPPED"
    assert report.roots_verdict == "pass_with_limits"


def test_missing_required_root_fails_closed(tmp_path: Path) -> None:
    repo = _bootstrap_mini_repo(tmp_path)
    (repo / "tools" / "mcp").rmdir()

    report = inventory.build_inventory(
        repo,
        config=_mini_config(),
        check_github=False,
    )

    mcp_row = next(r for r in report.rows if r.key == "mcp")
    assert mcp_row.local_status == "MISSING"
    assert report.roots_verdict == "fail"
    assert any("mcp" in reason for reason in report.fail_reasons)


def test_config_partial_missing_is_limited_not_ok(tmp_path: Path) -> None:
    repo = _bootstrap_mini_repo(tmp_path)
    (repo / "pyproject.toml").unlink()

    report = inventory.build_inventory(
        repo,
        config=_mini_config(include_config_files=True),
        check_github=False,
    )

    config_row = next(r for r in report.rows if r.key == "config")
    assert config_row.local_status == "LIMITED"
    assert report.roots_verdict == "fail"


def test_local_and_github_fields_are_separate(tmp_path: Path) -> None:
    repo = _bootstrap_mini_repo(tmp_path)

    report = inventory.build_inventory(
        repo,
        config=_mini_config(),
        check_github=False,
    )

    optional = next(r for r in report.rows if r.key == "optional_external")
    assert optional.local_status == "MISSING"
    assert optional.github_slug == "jannekbuengener/sample_brain"
    assert optional.github_target_status == "SKIPPED"


def test_rendered_inventory_has_no_secret_patterns(tmp_path: Path) -> None:
    repo = _bootstrap_mini_repo(tmp_path)
    report = inventory.build_inventory(
        repo,
        config=_mini_config(),
        check_github=False,
    )
    rendered = inventory.format_report(report, "json")
    lowered = rendered.lower()
    assert "password" not in lowered
    assert "api_key" not in lowered
    assert "token" not in lowered or "no secret" in lowered


def test_canonical_config_loads_from_repo() -> None:
    cfg = inventory.load_inventory_config()
    keys = [entry["key"] for entry in cfg["entries"]]
    assert keys == [
        "working",
        "db",
        "mcp",
        "config",
        "traumtaenzer",
        "sample_brain",
        "gpt_mcp_server",
    ]


def test_compute_exit_code() -> None:
    ok = inventory.RootInventoryReport(
        schema_version="1.0",
        timestamp="t",
        issue_refs=[],
        working_repo_root="/w",
        workspaces_repos_dir="/p",
        config_path="/c",
        roots_verdict="pass",
    )
    assert inventory.compute_exit_code(ok) == 0
    fail = inventory.RootInventoryReport(
        schema_version="1.0",
        timestamp="t",
        issue_refs=[],
        working_repo_root="/w",
        workspaces_repos_dir="/p",
        config_path="/c",
        roots_verdict="fail",
    )
    assert inventory.compute_exit_code(fail) == 1
