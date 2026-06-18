"""Unit tests for onboarding docs validator (#3233)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools import validate_onboarding_docs as validator

pytestmark = pytest.mark.unit


# --- helpers ---


def _make_file(root: Path, rel: str, content: str = "") -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


# --- link extraction ---


def test_extract_relative_links() -> None:
    content = """
[good](path/to/file.md)
[external](https://example.com)
[anchor](#section)
[mail](mailto:user@example.com)
[relative2](another/file.md)
"""
    links = validator.extract_relative_links(content)
    assert links == ["path/to/file.md", "another/file.md"]


def test_extract_relative_links_empty() -> None:
    assert validator.extract_relative_links("no links here") == []
    assert validator.extract_relative_links("[text]()") == []
    assert validator.extract_relative_links("") == []


# --- navpack path extraction ---


def test_extract_navpack_paths() -> None:
    content = """
schema_version: "1.0"
read_order:
  - id: "01"
    path: "README.md"
  - id: "02"
    path: "docs/index.md"
"""
    paths = validator.extract_navpack_paths(content)
    assert paths == ["README.md", "docs/index.md"]


def test_extract_navpack_paths_empty() -> None:
    assert validator.extract_navpack_paths("no paths here") == []
    assert validator.extract_navpack_paths("") == []


# --- markdown link checks ---


def test_check_markdown_links_all_good(tmp_path: Path) -> None:
    _make_file(tmp_path, "source.md", "[link](target.md)")
    _make_file(tmp_path, "target.md")
    errors = validator.check_markdown_links(
        tmp_path, "source.md", "[link](target.md)", False
    )
    assert errors == []


def test_check_markdown_links_broken(tmp_path: Path) -> None:
    _make_file(tmp_path, "source.md", "[link](missing.md)")
    errors = validator.check_markdown_links(
        tmp_path, "source.md", "[link](missing.md)", False
    )
    assert len(errors) == 1
    assert "missing.md" in errors[0]
    assert "not found" in errors[0]


def test_check_markdown_links_external_ignored(tmp_path: Path) -> None:
    content = "[ext](https://example.com) [mail](mailto:user@test.com)"
    _make_file(tmp_path, "source.md", content)
    errors = validator.check_markdown_links(tmp_path, "source.md", content, False)
    assert errors == []


def test_check_markdown_links_anchor_ignored(tmp_path: Path) -> None:
    content = "[anchor](#section) [other](#subsection)"
    _make_file(tmp_path, "source.md", content)
    errors = validator.check_markdown_links(tmp_path, "source.md", content, False)
    assert errors == []


def test_check_markdown_links_archive_ignored(tmp_path: Path) -> None:
    content = "[archive](docs/archive/old.md)"
    _make_file(tmp_path, "source.md", content)
    errors = validator.check_markdown_links(tmp_path, "source.md", content, False)
    assert errors == []


# --- navpack entry checks ---


def test_check_navpack_entries_all_good(tmp_path: Path) -> None:
    _make_file(tmp_path, "navpack.yaml", '  path: "README.md"')
    _make_file(tmp_path, "README.md")
    errors = validator.check_navpack_entries(
        tmp_path, "navpack.yaml", '  path: "README.md"', False
    )
    assert errors == []


def test_check_navpack_entries_broken(tmp_path: Path) -> None:
    _make_file(tmp_path, "navpack.yaml", '  path: "missing.md"')
    errors = validator.check_navpack_entries(
        tmp_path, "navpack.yaml", '  path: "missing.md"', False
    )
    assert len(errors) == 1
    assert "missing.md" in errors[0]
    assert "not found" in errors[0]


# --- secret display command checks ---


def test_secret_display_commands_cat_password(tmp_path: Path) -> None:
    errors = validator.check_secret_display_commands("test.md", "cat REDIS_PASSWORD")
    assert len(errors) == 1
    assert "REDIS_PASSWORD" in errors[0]


def test_secret_display_commands_get_content_password(tmp_path: Path) -> None:
    errors = validator.check_secret_display_commands(
        "test.md", "Get-Content POSTGRES_PASSWORD"
    )
    assert len(errors) == 1
    assert "POSTGRES_PASSWORD" in errors[0]


def test_secret_display_commands_type_password(tmp_path: Path) -> None:
    errors = validator.check_secret_display_commands("test.md", "type GRAFANA_PASSWORD")
    assert len(errors) == 1
    assert "GRAFANA_PASSWORD" in errors[0]


def test_secret_display_commands_secrets_dir(tmp_path: Path) -> None:
    errors = validator.check_secret_display_commands(
        "test.md", "cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD"
    )
    assert len(errors) == 1
    assert ".secrets" in errors[0]


def test_secret_display_commands_variable_name_allowed(tmp_path: Path) -> None:
    errors = validator.check_secret_display_commands(
        "test.md", "REDIS_PASSWORD env variable"
    )
    assert errors == []


def test_secret_display_commands_no_false_positive(tmp_path: Path) -> None:
    errors = validator.check_secret_display_commands("test.md", "Get-ChildItem .env")
    assert errors == []


# --- PROJECT_STATUS as truth check ---


def test_project_status_as_truth_unmarked(tmp_path: Path) -> None:
    errors = validator.check_project_status_as_truth(
        "test.md", "Active status is in PROJECT_STATUS.md and CURRENT_STATUS.md"
    )
    assert len(errors) == 1
    assert "PROJECT_STATUS.md" in errors[0]


def test_project_status_as_truth_marked_legacy(tmp_path: Path) -> None:
    errors = validator.check_project_status_as_truth(
        "test.md", "PROJECT_STATUS.md is a historical snapshot"
    )
    assert errors == []


def test_project_status_as_truth_marked_archive(tmp_path: Path) -> None:
    errors = validator.check_project_status_as_truth(
        "test.md",
        "PROJECT_STATUS.md (legacy) and knowledge/CURRENT_STATUS.md (archive)",
    )
    assert errors == []


# --- legacy pack reference checks ---


def test_legacy_pack_reference_unmarked(tmp_path: Path) -> None:
    errors = validator.check_legacy_pack_references(
        "test.md", "The onboarding quick start is in ONBOARDING_QUICK_START"
    )
    assert len(errors) == 1
    assert "ONBOARDING_QUICK_START" in errors[0]


def test_legacy_pack_reference_marked(tmp_path: Path) -> None:
    errors = validator.check_legacy_pack_references(
        "test.md", "Legacy ONBOARDING_LINKS was archived"
    )
    assert errors == []


# --- root README landing check ---


def test_root_readme_landing_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "README.md", "landing page")
    content = "landing page"
    errors = validator.check_root_readme_is_landing("README.md", content)
    assert errors == []


def test_root_readme_github_reference_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "README.md", ".github/CONTROL_PLANE.md is the landing")
    content = ".github/CONTROL_PLANE.md is the landing"
    errors = validator.check_root_readme_is_landing("README.md", content)
    assert errors == []


# --- surface validation ---


def test_validate_surface_missing_file(tmp_path: Path) -> None:
    errors = validator.validate_surface(tmp_path, "nonexistent.md", False)
    assert len(errors) == 1
    assert "not found" in errors[0]


def test_validate_surface_markdown_good(tmp_path: Path) -> None:
    _make_file(tmp_path, "README.md", "[doc](index.md)")
    _make_file(tmp_path, "index.md")
    errors = validator.validate_surface(tmp_path, "README.md", False)
    assert errors == []


def test_validate_surface_navpack_good(tmp_path: Path) -> None:
    _make_file(tmp_path, "ENTRYPOINTS.yaml", '  path: "README.md"')
    _make_file(tmp_path, "README.md")
    errors = validator.validate_surface(tmp_path, "ENTRYPOINTS.yaml", False)
    assert errors == []


# --- full validation against real repo ---


def test_validate_all_real_surfaces() -> None:
    """Run validator against real active onboarding surfaces in the repo."""
    errors = validator.validate_all()
    # Must pass with no errors on a well-maintained repo
    assert errors == [], f"Real-surface validation failed:\n" + "\n".join(errors)


# --- main exit codes ---


def test_main_pass() -> None:
    assert validator.main(["--verbose"]) == 0


# --- error cases ---


def test_validate_surface_secret_command(tmp_path: Path) -> None:
    content = "Run: cat REDIS_PASSWORD to see the value"
    _make_file(tmp_path, "test.md", content)
    errors = validator.validate_surface(tmp_path, "test.md", False)
    assert len(errors) >= 1


def test_validate_surface_project_status_unmarked(tmp_path: Path) -> None:
    content = "See PROJECT_STATUS.md for current project state"
    _make_file(tmp_path, "test.md", content)
    errors = validator.validate_surface(tmp_path, "test.md", False)
    assert len(errors) >= 1
