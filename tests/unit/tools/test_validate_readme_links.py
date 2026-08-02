"""Unit tests for README link validator (#3994, Area Entry Link Rule #4298)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools import validate_readme_links as readme_validator
from tools.markdown_link_utils import (
    MarkdownLink,
    check_markdown_links,
    extract_markdown_links,
    extract_relative_links,
)

pytestmark = pytest.mark.unit


def _make_file(root: Path, rel: str, content: str = "") -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def _policy(
    tmp_path: Path,
    *,
    hubs: list[dict[str, str]] | None = None,
    enabled: bool = True,
    extra: dict | None = None,
) -> Path:
    resolved_hubs = (
        hubs
        if hubs is not None
        else [
            {"directory": "docs", "entrypoint": "docs/index.md"},
            {"directory": "docs/ci", "entrypoint": "docs/ci/index.md"},
        ]
    )
    for hub in resolved_hubs:
        _make_file(tmp_path, hub["entrypoint"], f"# {hub['directory']}\n")
    data: dict = {
        "default_classification": "active",
        "classification_rules": {
            "archive_snapshot": {
                "path_prefixes": ["docs/archive/", "knowledge/archive/"]
            },
            "fixture_testdata": {"path_prefixes": ["tests/fixtures/", "artifacts/"]},
        },
        "documented_exceptions": [],
        "area_entry_link_rule": {
            "enabled": enabled,
            "established_index_hubs": resolved_hubs,
        },
    }
    if extra:
        data.update(extra)
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def _validate_content(
    tmp_path: Path,
    rel_path: str,
    content: str,
    *,
    hubs: list[dict[str, str]] | None = None,
    enabled: bool = True,
) -> list[str]:
    policy_path = _policy(tmp_path, hubs=hubs, enabled=enabled)
    _make_file(tmp_path, rel_path, content)
    # Ensure common area trees exist for resolution fixtures.
    return readme_validator.validate_surface_file(
        tmp_path,
        rel_path,
        policy_path=policy_path,
    )


# ---------------------------------------------------------------------------
# Existing classification / inventory tests (#3994)
# ---------------------------------------------------------------------------


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
        readme_validator.classify_readme("docs/archive/README.md", policy)
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


def test_validate_all_skips_non_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_path = _policy(tmp_path)
    _make_file(tmp_path, "active/README.md", "[ok](target.md)")
    _make_file(tmp_path, "active/target.md")
    _make_file(tmp_path, "archive/README.md", "[broken](missing.md)")
    # Remap archive classification for this fixture tree.
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "classification_rules": {
                    "archive_snapshot": {"path_prefixes": ["archive/"]},
                },
                "documented_exceptions": [],
                "area_entry_link_rule": {"enabled": True, "established_index_hubs": []},
            }
        ),
        encoding="utf-8",
    )

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
    policy_path = _policy(tmp_path, hubs=[])
    _make_file(tmp_path, "services/README.md", "[bad](missing.md)")

    monkeypatch.setattr(
        readme_validator,
        "discover_tracked_readmes",
        lambda _root: ["services/README.md"],
    )

    errors = readme_validator.validate_all(tmp_path, policy_path)
    assert len(errors) == 1
    assert "broken relative link" in errors[0]


def test_build_inventory_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
                "area_entry_link_rule": {"enabled": True, "established_index_hubs": []},
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
    policy_path = _policy(tmp_path, hubs=[])
    # Ensure area_entry policy loads; explicit surface still checked for broken links.
    data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    data["explicit_active_surfaces"] = {"paths": ["CURRENT_STATUS.md"]}
    policy_path.write_text(yaml.safe_dump(data), encoding="utf-8")
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


def test_extract_markdown_links_includes_label() -> None:
    links = extract_markdown_links("[Services](services/README.md)")
    assert links == [MarkdownLink(label="Services", target="services/README.md")]


# ---------------------------------------------------------------------------
# Area Entry Link Rule — positive cases (#4298)
# ---------------------------------------------------------------------------


def test_area_entry_readme_target_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[Services](services/README.md)",
    )
    assert errors == []


def test_area_entry_visible_folder_text_readme_target_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[`services/`](services/README.md)",
    )
    assert errors == []


def test_area_entry_direct_canon_file_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/meta/REPOSITORY_CANON.md", "# canon")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[Canon](docs/meta/REPOSITORY_CANON.md)",
    )
    assert errors == []


def test_area_entry_direct_yaml_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/navigation/mcp-navpack/ENTRYPOINTS.yaml", "x: 1\n")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[Entrypoints](docs/navigation/mcp-navpack/ENTRYPOINTS.yaml)",
    )
    assert errors == []


def test_area_entry_established_index_hub_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/index.md", "# docs landing")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[Docs](docs/index.md)",
    )
    assert errors == []


def test_area_entry_external_link_ok(tmp_path: Path) -> None:
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[GitHub](https://github.com/jannekbuengener/Claire_de_Binare)",
    )
    assert errors == []


def test_area_entry_pure_anchor_ok(tmp_path: Path) -> None:
    errors = _validate_content(tmp_path, "README.md", "[top](#top)")
    assert errors == []


def test_area_entry_fenced_code_block_example_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# s")
    content = """
# Nav

```markdown
[Beispiel](services/)
```
"""
    errors = _validate_content(tmp_path, "README.md", content)
    assert errors == []


def test_area_entry_unlinked_folder_text_with_readme_link_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    content = """
| Ordner | Dokumentation |
| --- | --- |
| `risk/` | [`README`](services/risk/README.md) |
"""
    errors = _validate_content(tmp_path, "README.md", content)
    assert errors == []


def test_area_entry_deep_relative_readme_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    _make_file(tmp_path, "core/README.md", "# core")
    errors = _validate_content(
        tmp_path,
        "services/risk/README.md",
        "[Core](../../core/README.md)",
    )
    assert errors == []


def test_area_entry_readme_with_anchor_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services\n## usage\n")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[Services](services/README.md#usage)",
    )
    assert errors == []


def test_area_entry_excluded_archive_surface_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy_path = _policy(tmp_path, hubs=[])
    _make_file(tmp_path, "docs/archive/README.md", "[bare](legacy/)")
    _make_file(tmp_path, "docs/archive/legacy/README.md", "# legacy")
    monkeypatch.setattr(
        readme_validator,
        "discover_tracked_readmes",
        lambda _root: ["docs/archive/README.md"],
    )
    errors = readme_validator.validate_all(tmp_path, policy_path)
    assert errors == []


# ---------------------------------------------------------------------------
# Area Entry Link Rule — negative cases (#4298)
# ---------------------------------------------------------------------------


def test_area_entry_bare_folder_with_readme_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services")
    errors = _validate_content(tmp_path, "README.md", "[Services](services/)")
    assert len(errors) == 1
    assert "bare area link 'services/'" in errors[0]
    assert "services/README.md" in errors[0]


def test_area_entry_bare_folder_no_slash_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services")
    errors = _validate_content(tmp_path, "README.md", "[Services](services)")
    assert any("bare area link 'services'" in e for e in errors)


def test_area_entry_dot_slash_folder_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services")
    errors = _validate_content(tmp_path, "README.md", "[Services](./services/)")
    assert any("bare area link './services/'" in e for e in errors)


def test_area_entry_parent_relative_folder_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# services")
    _make_file(tmp_path, "docs/guide/README.md", "[Services](../../services/)")
    errors = _validate_content(
        tmp_path,
        "docs/guide/README.md",
        "[Services](../../services/)",
    )
    assert any("bare area link '../../services/'" in e for e in errors)


def test_area_entry_dual_link_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    content = "[folder](services/risk/) and [readme](services/risk/README.md)"
    errors = _validate_content(tmp_path, "README.md", content)
    assert any("dual area links" in e for e in errors)
    assert any("services/risk" in e for e in errors)


def test_area_entry_dual_link_in_table_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    errors = _validate_content(
        tmp_path,
        "services/README.md",
        """
| Bereich | Dokumentation |
| --- | --- |
| [`risk/`](risk/) | [`README`](risk/README.md) |
""",
    )
    assert any("dual area links" in e for e in errors)


def test_area_entry_bare_index_hub_folder_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/index.md", "# docs")
    _make_file(tmp_path, "docs/ci/index.md", "# ci")
    errors = _validate_content(tmp_path, "README.md", "[CI](docs/ci/)")
    assert any("established index hub" in e for e in errors)
    assert any("docs/ci/index.md" in e for e in errors)


def test_area_entry_invalid_policy_entry_fails_closed(tmp_path: Path) -> None:
    policy_path = tmp_path / "bad.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "area_entry_link_rule": {
                    "enabled": True,
                    "established_index_hubs": [{"directory": "docs"}],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="entrypoint"):
        readme_validator.load_policy(policy_path, root=tmp_path)


def test_area_entry_missing_policy_entrypoint_fails_closed(tmp_path: Path) -> None:
    policy_path = tmp_path / "bad.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "area_entry_link_rule": {
                    "enabled": True,
                    "established_index_hubs": [
                        {"directory": "docs", "entrypoint": "docs/index.md"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not exist"):
        readme_validator.load_policy(policy_path, root=tmp_path)


def test_area_entry_broken_link_still_reported(tmp_path: Path) -> None:
    errors = _validate_content(tmp_path, "README.md", "[x](missing.md)")
    assert any("broken relative link" in e for e in errors)


def test_area_entry_normalized_spellings_same_area(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    content = "[a](services/risk) [b](./services/risk/) [c](services/../services/risk/)"
    errors = _validate_content(tmp_path, "README.md", content)
    bare = [e for e in errors if "bare area link" in e]
    # Multiple spellings normalize to one area; report once with original target.
    assert len(bare) == 1
    assert "services/risk" in bare[0]
    keys = {
        readme_validator.normalize_area_key(tmp_path, "README.md", t)
        for t in ("services/risk", "./services/risk/", "services/../services/risk/")
    }
    assert keys == {"services/risk"}


def test_area_entry_dual_link_with_readme_anchor_fails(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk\n## usage\n")
    content = "[folder](services/risk/) [readme](services/risk/README.md#usage)"
    errors = _validate_content(tmp_path, "README.md", content)
    assert any("dual area links" in e for e in errors)


# ---------------------------------------------------------------------------
# Area Entry Link Rule — boundary cases (#4298)
# ---------------------------------------------------------------------------


def test_area_entry_folder_without_readme_or_index_not_hard_error(
    tmp_path: Path,
) -> None:
    _make_file(tmp_path, "orphan/note.txt", "x")
    errors = _validate_content(tmp_path, "README.md", "[Orphan](orphan/)")
    assert errors == []


def test_area_entry_inline_code_folder_not_a_link(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "See `services/risk/` and [`README`](services/risk/README.md).",
    )
    assert errors == []


def test_area_entry_direct_file_same_folder_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/config.py", "x = 1\n")
    errors = _validate_content(
        tmp_path,
        "services/README.md",
        "[config](config.py)",
    )
    assert errors == []


def test_area_entry_two_distinct_areas_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/risk/README.md", "# risk")
    _make_file(tmp_path, "services/signal/README.md", "# signal")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[R](services/risk/README.md) [S](services/signal/README.md)",
    )
    assert errors == []


def test_area_entry_query_and_anchor_on_readme_ok(tmp_path: Path) -> None:
    _make_file(tmp_path, "services/README.md", "# s")
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[S](services/README.md?x=1#usage)",
    )
    assert errors == []


def test_area_entry_image_link_to_file_ok(tmp_path: Path) -> None:
    # Existing parser matches the [alt](path) portion of image syntax.
    _make_file(tmp_path, "docs/img.png", "png")
    errors = _validate_content(tmp_path, "README.md", "![diagram](docs/img.png)")
    assert errors == []


def test_area_entry_archive_target_from_active_docs_skipped_for_existence(
    tmp_path: Path,
) -> None:
    # Archive targets are skipped by existence check; no area-entry hard error either.
    errors = _validate_content(
        tmp_path,
        "README.md",
        "[hist](docs/archive/old/README.md)",
    )
    assert errors == []


def test_area_entry_duplicate_hub_directory_fails_closed(tmp_path: Path) -> None:
    _make_file(tmp_path, "docs/index.md", "# docs")
    policy_path = tmp_path / "bad.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "area_entry_link_rule": {
                    "enabled": True,
                    "established_index_hubs": [
                        {"directory": "docs", "entrypoint": "docs/index.md"},
                        {"directory": "docs", "entrypoint": "docs/index.md"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        readme_validator.load_policy(policy_path, root=tmp_path)


def test_area_entry_hub_outside_directory_fails_closed(tmp_path: Path) -> None:
    _make_file(tmp_path, "other/index.md", "# other")
    policy_path = tmp_path / "bad.yaml"
    policy_path.write_text(
        yaml.safe_dump(
            {
                "default_classification": "active",
                "area_entry_link_rule": {
                    "enabled": True,
                    "established_index_hubs": [
                        {"directory": "docs", "entrypoint": "other/index.md"},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="outside"):
        readme_validator.load_policy(policy_path, root=tmp_path)
