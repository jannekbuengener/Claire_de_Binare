"""Unit tests for README link validator (#3994)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools import validate_readme_links as readme_validator
from tools.markdown_link_utils import check_markdown_links, extract_relative_links

pytestmark = pytest.mark.unit


def _make_file(root: Path, rel: str, content: str = "") -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def test_classify_readme_active_by_default() -> None:
    policy = {
        "default_classification": "active",
        "classification_rules": {
            "archive_snapshot": {"path_prefixes": ["docs/archive/"]},
        },
        "documented_exceptions": [],
    }
    assert readme_validator.classify_readme("services/README.md", policy) == "active"


def test_classify_readme_archive_prefix() -> None:
    policy = {
        "default_classification": "active",
        "classification_rules": {
            "archive_snapshot": {"path_prefixes": ["docs/archive/"]},
        },
        "documented_exceptions": [],
    }
    assert (
        readme_validator.classify_readme(
            "docs/archive/README.md", policy
        )
        == "archive_snapshot"
    )


def test_classify_readme_documented_exception() -> None:
    policy = {
        "default_classification": "active",
        "classification_rules": {},
        "documented_exceptions": [
            {
                "path": "custom/README.md",
                "classification": "fixture_testdata",
            }
        ],
    }
    assert (
        readme_validator.classify_readme("custom/README.md", policy)
        == "fixture_testdata"
    )


def test_validate_all_skips_non_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "classification_rules": {
                    "archive_snapshot": {"path_prefixes": ["archive/"]},
                },
                "documented_exceptions": [],
            }
        ),
        encoding="utf-8",
    )
    _make_file(tmp_path, "active/README.md", "[ok](target.md)")
    _make_file(tmp_path, "active/target.md")
    _make_file(tmp_path, "archive/README.md", "[broken](missing.md)")

    monkeypatch.setattr(
        readme_validator,
        "discover_tracked_readmes",
        lambda _root: ["active/README.md", "archive/README.md"],
    )

    errors = readme_validator.validate_all(tmp_path, policy_path)
    assert errors == []


def test_validate_all_fails_on_broken_active_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump({"default_classification": "active"}),
        encoding="utf-8",
    )
    _make_file(tmp_path, "services/README.md", "[bad](missing.md)")

    monkeypatch.setattr(
        readme_validator,
        "discover_tracked_readmes",
        lambda _root: ["services/README.md"],
    )

    errors = readme_validator.validate_all(tmp_path, policy_path)
    assert len(errors) == 1
    assert "broken relative link" in errors[0]


def test_build_inventory_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "classification_rules": {
                    "fixture_testdata": {"path_prefixes": ["tests/fixtures/"]},
                },
                "explicit_active_surfaces": {
                    "paths": ["CURRENT_STATUS.md"],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        readme_validator,
        "discover_tracked_readmes",
        lambda _root: ["README.md", "tests/fixtures/x/README.md"],
    )

    inv = readme_validator.build_inventory(tmp_path, policy_path)
    assert inv["total_readmes"] == 2
    assert inv["total"] == 3
    assert inv["explicit_active_surfaces"] == ["CURRENT_STATUS.md"]
    assert inv["by_classification"]["active"] == 1
    assert inv["by_classification"]["fixture_testdata"] == 1


def test_validate_all_checks_explicit_active_surfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "explicit_active_surfaces": {"paths": ["CURRENT_STATUS.md"]},
            }
        ),
        encoding="utf-8",
    )
    _make_file(tmp_path, "CURRENT_STATUS.md", "[broken](missing.md)")
    monkeypatch.setattr(
        readme_validator,
        "discover_tracked_readmes",
        lambda _root: [],
    )

    errors = readme_validator.validate_all(tmp_path, policy_path)
    assert len(errors) == 1
    assert "CURRENT_STATUS.md" in errors[0]


def test_explicit_active_surfaces_empty_when_omitted() -> None:
    assert readme_validator.explicit_active_surfaces({}) == []


def test_shared_extract_relative_links() -> None:
    content = "[ok](a.md) [ext](https://x) [anc](#x)"
    assert extract_relative_links(content) == ["a.md"]


def test_shared_check_markdown_links_broken(tmp_path: Path) -> None:
    _make_file(tmp_path, "README.md", "[x](nope.md)")
    errors = check_markdown_links(tmp_path, "README.md", "[x](nope.md)", False)
    assert len(errors) == 1


def test_extract_relative_links_ignores_fenced_code_blocks() -> None:
    content = """
[nav](good.md)

```markdown
[ignored](missing-in-codeblock.md)
```
"""
    assert extract_relative_links(content) == ["good.md"]


def test_check_markdown_links_nested_depth(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/onboarding/parent.md", "[glossary](cdb_glossary.md)")
    _make_file(tmp_path, "docs/onboarding/cdb_glossary.md")
    errors = check_markdown_links(
        tmp_path,
        "docs/onboarding/parent.md",
        "[glossary](cdb_glossary.md)",
        False,
    )
    assert errors == []


def test_check_markdown_links_with_fragment(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/onboarding/cdb_glossary.md", "[lr](#lr)")
    errors = check_markdown_links(
        tmp_path,
        "docs/onboarding/cdb_glossary.md",
        "[lr](#lr)",
        False,
    )
    assert errors == []
