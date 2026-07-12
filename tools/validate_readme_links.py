"""Validate relative Markdown links on active documentation surfaces.

Discovers tracked README.md files via git, classifies them with rule-based
policy, and fail-closed validates all `active` README surfaces offline.
Also validates explicit non-README canon entry points listed in policy
(`explicit_active_surfaces`, #3995) with the same link engine.

Usage:
    python -m tools.validate_readme_links
    python -m tools.validate_readme_links --verbose
    python -m tools.validate_readme_links --inventory

Exit codes:
    0 - all active surface link checks PASS
    1 - one or more validation failures

Issues: #3994 (README discovery), #3995 (explicit canon entry points)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from tools.markdown_link_utils import check_markdown_links

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "tests/fixtures/readme_link_policy.yaml"


def discover_tracked_readmes(root: Path) -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "--", "README.md", "**/README.md"],
        cwd=root,
        text=True,
    )
    return sorted(set(line.strip() for line in output.splitlines() if line.strip()))


def load_policy(policy_path: Path) -> dict[str, Any]:
    data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Invalid policy YAML: {policy_path}")
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


def validate_surface_file(
    root: Path,
    rel_path: str,
    *,
    verbose: bool = False,
    surface_kind: str = "active",
) -> list[str]:
    full_path = root / rel_path
    if not full_path.is_file():
        return [f"{rel_path}: tracked surface missing on disk"]

    if verbose:
        print(f"Validating ({surface_kind}): {rel_path}", file=sys.stderr)

    content = full_path.read_text(encoding="utf-8", errors="replace")
    return check_markdown_links(root, rel_path, content, verbose)


def build_inventory(root: Path, policy_path: Path | None = None) -> dict[str, Any]:
    policy = load_policy(policy_path or DEFAULT_POLICY_PATH)
    readmes = discover_tracked_readmes(root)
    by_class: dict[str, list[str]] = {}
    for rel in readmes:
        cls = classify_readme(rel, policy)
        by_class.setdefault(cls, []).append(rel)

    explicit = explicit_active_surfaces(policy)

    return {
        "total_readmes": len(readmes),
        "total": len(readmes) + len(explicit),
        "explicit_active_surfaces": explicit,
        "by_classification": {k: len(v) for k, v in sorted(by_class.items())},
        "paths_by_classification": by_class,
        "policy_path": str((policy_path or DEFAULT_POLICY_PATH).relative_to(root)),
    }


def validate_all(
    root: Path | None = None,
    policy_path: Path | None = None,
    verbose: bool = False,
) -> list[str]:
    r = root or REPO_ROOT
    policy = load_policy(policy_path or DEFAULT_POLICY_PATH)
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
            validate_surface_file(r, rel_path, verbose=verbose, surface_kind="active")
        )

    for rel_path in explicit_active_surfaces(policy):
        all_errors.extend(
            validate_surface_file(
                r,
                rel_path,
                verbose=verbose,
                surface_kind="canon_entry_point",
            )
        )

    return all_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate relative links in active tracked README.md files (#3994)."
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

    print("OK: all active README and explicit canon entry surfaces pass link validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
