"""Validate relative Markdown links on active documentation surfaces.

Discovers tracked README.md files via git, classifies them with rule-based
policy, and fail-closed validates all `active` README surfaces offline.
Also validates explicit non-README canon entry points listed in policy
(`explicit_active_surfaces`, #3995) with the same link engine.

Area Entry Link Rule (#4298): fail-closed on bare folder area links when a
local README or established index hub exists, and on dual folder+README links.

Usage:
    python -m tools.validate_readme_links
    python -m tools.validate_readme_links --verbose
    python -m tools.validate_readme_links --inventory

Exit codes:
    0 - all active surface link checks PASS
    1 - one or more validation failures

Issues: #3994, #3995, #4037, #4298
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from tools.markdown_link_utils import (
    MarkdownLink,
    check_markdown_links,
    extract_markdown_links,
    is_archive_link_target,
    is_external_url,
    is_pure_anchor,
    repo_relative_posix,
    resolve_relative_link,
    strip_link_fragments,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "tests/fixtures/readme_link_policy.yaml"

README_NAME = "README.md"
INDEX_NAME = "index.md"


def discover_tracked_readmes(root: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "--", "README.md", "**/README.md"],
        cwd=root,
        text=True,
    )
    return sorted(set(line.strip() for line in output.splitlines() if line.strip()))


def _normalize_policy_path(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/")


def _validate_area_entry_policy(root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize area_entry_link_rule; fail closed on bad config."""
    block = policy.get("area_entry_link_rule")
    if block is None:
        return {"enabled": False, "hubs": {}}
    if not isinstance(block, dict):
        raise ValueError("area_entry_link_rule must be a mapping")

    enabled = block.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("area_entry_link_rule.enabled must be a boolean")

    hubs_raw = block.get("established_index_hubs") or []
    if not isinstance(hubs_raw, list):
        raise ValueError("area_entry_link_rule.established_index_hubs must be a list")

    hubs: dict[str, str] = {}
    for idx, entry in enumerate(hubs_raw):
        if not isinstance(entry, dict):
            raise ValueError(
                f"area_entry_link_rule.established_index_hubs[{idx}] must be a mapping"
            )
        directory = entry.get("directory")
        entrypoint = entry.get("entrypoint")
        if not directory or not isinstance(directory, str):
            raise ValueError(
                f"area_entry_link_rule.established_index_hubs[{idx}] missing directory"
            )
        if not entrypoint or not isinstance(entrypoint, str):
            raise ValueError(
                f"area_entry_link_rule.established_index_hubs[{idx}] missing entrypoint"
            )
        if "://" in directory or "://" in entrypoint:
            raise ValueError(
                f"area_entry_link_rule hub paths must be repository-relative "
                f"(got directory={directory!r}, entrypoint={entrypoint!r})"
            )
        if Path(directory).is_absolute() or Path(entrypoint).is_absolute():
            raise ValueError(
                "area_entry_link_rule hub paths must not be absolute filesystem paths"
            )

        dir_key = _normalize_policy_path(directory)
        entry_key = _normalize_policy_path(entrypoint)
        if dir_key in hubs:
            raise ValueError(
                f"area_entry_link_rule duplicate directory entry: {dir_key}"
            )
        if not (
            entry_key == f"{dir_key}/{INDEX_NAME}"
            or entry_key.startswith(f"{dir_key}/")
        ):
            raise ValueError(
                f"area_entry_link_rule entrypoint '{entry_key}' is outside "
                f"directory '{dir_key}'"
            )

        entry_path = root / entry_key
        if not entry_path.is_file():
            raise ValueError(
                f"area_entry_link_rule entrypoint '{entry_key}' does not exist"
            )
        hubs[dir_key] = entry_key

    return {"enabled": enabled, "hubs": hubs}


def load_policy(policy_path: Path, root: Path | None = None) -> dict[str, Any]:
    data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid policy YAML: {policy_path}")
    scan_root = root if root is not None else REPO_ROOT
    data["_area_entry"] = _validate_area_entry_policy(scan_root, data)
    return data


def _match_prefix(rel_path: str, prefix: str) -> bool:
    return rel_path == prefix or rel_path.startswith(prefix)


def classify_readme(rel_path: str, policy: dict[str, Any]) -> str:
    for entry in policy.get("documented_exceptions", []) or []:
        if entry.get("path") == rel_path:
            return str(entry.get("classification", "documented_exception"))

    rules = policy.get("classification_rules", {}) or {}
    for classification, rule_block in rules.items():
        prefixes = (rule_block or {}).get("path_prefixes", []) or []
        for prefix in prefixes:
            if _match_prefix(rel_path, prefix):
                return classification

    return str(policy.get("default_classification", "active"))


def explicit_active_surfaces(policy: dict[str, Any]) -> list[str]:
    block = policy.get("explicit_active_surfaces") or {}
    paths = block.get("paths") or []
    return sorted({str(p).strip() for p in paths if str(p).strip()})


def normalize_area_key(root: Path, source_rel: str, link_target: str) -> str | None:
    """Normalize a relative link target to a repository-relative area directory key."""
    if is_external_url(link_target) or is_pure_anchor(link_target):
        return None
    if is_archive_link_target(link_target):
        return None

    source_path = (root / source_rel).resolve()
    resolved = resolve_relative_link(source_path, link_target)
    rel = repo_relative_posix(root, resolved)
    if rel is None:
        return None

    clean = strip_link_fragments(link_target)
    # If the link path (before resolve) ends with README.md / index.md, area is parent.
    path_part = clean.replace("\\", "/")
    base_name = Path(path_part).name.lower()
    if base_name in {README_NAME.lower(), INDEX_NAME.lower()}:
        parent = Path(rel).parent
        if str(parent) == ".":
            return ""
        return parent.as_posix()

    if resolved.is_dir():
        return rel
    if resolved.is_file():
        # Direct non-entry file link — not an area key for dual-link grouping,
        # unless it is README/index (handled above via path name).
        return None

    # Target missing: still classify by path shape for dual-link / bare checks.
    if path_part.endswith("/") or "." not in Path(path_part).name:
        return rel
    return None


def _preferred_area_entrypoint(
    root: Path,
    area_key: str,
    hubs: dict[str, str],
) -> str | None:
    if area_key in hubs:
        return hubs[area_key]
    readme = f"{area_key}/{README_NAME}" if area_key else README_NAME
    if (root / readme).is_file():
        return readme
    return None


def _classify_area_link(
    root: Path,
    source_rel: str,
    link: MarkdownLink,
    hubs: dict[str, str],
) -> tuple[str | None, str | None]:
    """Return (area_key, kind) where kind is bare|readme|index|None."""
    target = link.target
    if (
        is_external_url(target)
        or is_pure_anchor(target)
        or is_archive_link_target(target)
    ):
        return None, None

    source_path = (root / source_rel).resolve()
    resolved = resolve_relative_link(source_path, target)
    rel = repo_relative_posix(root, resolved)
    if rel is None:
        return None, None

    path_part = strip_link_fragments(target).replace("\\", "/")
    base_name = Path(path_part).name.lower()

    if base_name == README_NAME.lower():
        area = normalize_area_key(root, source_rel, target)
        return area, "readme"
    if base_name == INDEX_NAME.lower():
        area = normalize_area_key(root, source_rel, target)
        if area is not None and area in hubs and hubs[area] == rel:
            return area, "index"
        # Non-hub index.md is a direct file link, not area dual-link fodder.
        return None, None

    looks_like_dir = path_part.endswith("/") or "." not in Path(path_part).name
    if resolved.is_dir() or (not resolved.exists() and looks_like_dir):
        return rel, "bare"

    return None, None


def check_area_entry_links(
    root: Path,
    source_rel: str,
    content: str,
    policy: dict[str, Any],
) -> list[str]:
    area_cfg = policy.get("_area_entry") or {"enabled": False, "hubs": {}}
    if not area_cfg.get("enabled"):
        return []

    hubs: dict[str, str] = area_cfg.get("hubs") or {}
    errors: list[str] = []
    relative_links = [
        link
        for link in extract_markdown_links(content)
        if not is_external_url(link.target) and not is_pure_anchor(link.target)
    ]

    # Dual-link aggregation: bare vs readme/index for same area.
    by_area: dict[str, dict[str, list[str]]] = {}
    bare_reported: set[str] = set()

    for link in relative_links:
        if is_archive_link_target(link.target):
            continue

        area_key, kind = _classify_area_link(root, source_rel, link, hubs)
        if area_key is None or kind is None:
            continue

        bucket = by_area.setdefault(area_key, {"bare": [], "entry": []})
        if kind == "bare":
            bucket["bare"].append(link.target)
            preferred = _preferred_area_entrypoint(root, area_key, hubs)
            if preferred and area_key not in bare_reported:
                bare_reported.add(area_key)
                if area_key in hubs:
                    errors.append(
                        f"{source_rel}: bare area link '{link.target}' targets an "
                        f"established index hub; use '{preferred}'"
                    )
                else:
                    errors.append(
                        f"{source_rel}: bare area link '{link.target}' targets "
                        f"directory '{area_key}'; use '{preferred}'"
                    )
        else:
            bucket["entry"].append(link.target)

    for area_key, groups in sorted(by_area.items()):
        bare_targets = groups["bare"]
        entry_targets = groups["entry"]
        if bare_targets and entry_targets:
            errors.append(
                f"{source_rel}: dual area links for '{area_key}': "
                f"'{bare_targets[0]}' and '{entry_targets[0]}'; "
                f"keep only the README or index target"
            )

    return errors


def validate_surface_file(
    root: Path,
    rel_path: str,
    *,
    verbose: bool = False,
    surface_kind: str = "active",
    policy_path: Path | None = None,
    policy: dict[str, Any] | None = None,
) -> list[str]:
    full_path = root / rel_path
    if not full_path.is_file():
        return [f"{rel_path}: tracked surface missing on disk"]

    if verbose:
        print(f"Validating ({surface_kind}): {rel_path}", file=sys.stderr)

    content = full_path.read_text(encoding="utf-8", errors="replace")
    errors = check_markdown_links(root, rel_path, content, verbose)

    active_policy = policy
    if active_policy is None and policy_path is not None:
        active_policy = load_policy(policy_path, root=root)
    if active_policy is not None:
        errors.extend(check_area_entry_links(root, rel_path, content, active_policy))

    return errors


def build_inventory(root: Path, policy_path: Path | None = None) -> dict[str, Any]:
    policy = load_policy(policy_path or DEFAULT_POLICY_PATH, root=root)
    readmes = discover_tracked_readmes(root)
    by_class: dict[str, list[str]] = {}
    for rel in readmes:
        cls = classify_readme(rel, policy)
        by_class.setdefault(cls, []).append(rel)

    explicit = explicit_active_surfaces(policy)
    area_cfg = policy.get("_area_entry") or {}

    return {
        "total_readmes": len(readmes),
        "total": len(readmes) + len(explicit),
        "explicit_active_surfaces": explicit,
        "by_classification": {k: len(v) for k, v in sorted(by_class.items())},
        "paths_by_classification": by_class,
        "policy_path": str((policy_path or DEFAULT_POLICY_PATH).relative_to(root)),
        "area_entry_link_rule": {
            "enabled": bool(area_cfg.get("enabled")),
            "established_index_hubs": [
                {"directory": d, "entrypoint": e}
                for d, e in sorted((area_cfg.get("hubs") or {}).items())
            ],
        },
    }


def validate_all(
    root: Path | None = None,
    policy_path: Path | None = None,
    verbose: bool = False,
) -> list[str]:
    r = root or REPO_ROOT
    policy = load_policy(policy_path or DEFAULT_POLICY_PATH, root=r)
    all_errors: list[str] = []

    for rel_path in discover_tracked_readmes(r):
        classification = classify_readme(rel_path, policy)
        if classification != "active":
            if verbose:
                print(
                    f"Skipping ({classification}): {rel_path}",
                    file=sys.stderr,
                )
            continue

        all_errors.extend(
            validate_surface_file(
                r,
                rel_path,
                verbose=verbose,
                surface_kind="active",
                policy=policy,
            )
        )

    for rel_path in explicit_active_surfaces(policy):
        all_errors.extend(
            validate_surface_file(
                r,
                rel_path,
                verbose=verbose,
                surface_kind="canon_entry_point",
                policy=policy,
            )
        )

    return all_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate relative links and Area Entry Link Rule on active "
            "README/canon surfaces (#3994/#4298)."
        )
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-file status to stderr",
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Print classification inventory and exit 0",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to readme_link_policy.yaml",
    )
    args = parser.parse_args(argv)

    if args.inventory:
        inv = build_inventory(REPO_ROOT, args.policy)
        print(yaml.safe_dump(inv, sort_keys=False))
        return 0

    errors = validate_all(REPO_ROOT, args.policy, args.verbose)

    if errors:
        print("README LINK VALIDATION FAILED", file=sys.stderr)
        for err in errors:
            print(f"  FAIL: {err}", file=sys.stderr)
        return 1

    print(
        "OK: all active README and explicit canon entry surfaces pass "
        "link and area-entry validation"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
