"""Read-only validator for active onboarding docs integrity.

Validates:
- Relative Markdown links resolve to real files
- Navpack path entries point to real files
- No secret-display commands
- No PROJECT_STATUS.md used as current truth
- Legacy references are explicitly marked as legacy/historical/archive
- Root README remains the GitHub landing candidate

Usage:
    python -m tools.validate_onboarding_docs
    python -m tools.validate_onboarding_docs --verbose

Exit codes:
    0 - all checks PASS
    1 - one or more validation failures

Issue: #3233
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent

ACTIVE_ONBOARDING_SURFACES: list[str] = [
    "README.md",
    "DEVELOPER_ONBOARDING.md",
    "docs/index.md",
    "CONTRIBUTING.md",
    "services/README.md",
    "tests/README.md",
    "tools/README.md",
    "docs/surrealdb/README.md",
    "docs/onboarding/DEVELOPER_VISUAL_START_HERE.md",
    "docs/onboarding/fresh_clone_rehearsal.md",
    "docs/onboarding/repo_brain_context_intelligence.md",
    "docs/onboarding/examples/README.md",
    "docs/onboarding/examples/first_issue_to_pr_flow.md",
    "docs/onboarding/examples/repo_brain_first_use.md",
    "docs/onboarding/templates/agent_prompt_template.md",
    "docs/onboarding/templates/evidence_doc_template.md",
    "docs/onboarding/templates/pr_body_template.md",
    "mcp_navpack_working_repo/ENTRYPOINTS.yaml",
    "mcp_navpack_working_repo/CHEATSHEET.md",
]

NAVPACK_SURFACES: list[str] = [
    "mcp_navpack_working_repo/ENTRYPOINTS.yaml",
    "mcp_navpack_working_repo/CHEATSHEET.md",
]

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

YAML_PATH_RE = re.compile(r'^\s*path:\s*"([^"]+)"')

SECRET_DISPLAY_COMMANDS: list[re.Pattern] = [
    re.compile(
        r"(?i)(?:cat|Get-Content|type)\s+(?:.*[/\\])?(?:REDIS_PASSWORD|POSTGRES_PASSWORD|GRAFANA_PASSWORD)\b"
    ),
    re.compile(r"(?i)(?:cat|Get-Content|type)\s+.*\b\.secrets\b"),
]

PROJECT_STATUS_TRUTH_WORDS: list[re.Pattern] = [
    re.compile(
        r"(?i)PROJECT_STATUS\.md(?!.*(?:historical|legacy|archive|snapshot|context-only))"
    ),
]

LEGACY_PACK_NAMES: list[str] = [
    "ONBOARDING_QUICK_START",
    "ONBOARDING_LINKS",
]

ARCHIVE_MARKERS: list[str] = [
    "historical",
    "legacy",
    "archive",
    "snapshot",
    "context-only",
]


def _is_external_url(link: str) -> bool:
    return link.startswith(("http://", "https://", "mailto:"))


def _is_pure_anchor(link: str) -> bool:
    return link.startswith("#")


def _is_archive_path(link: str) -> bool:
    return link.startswith(("docs/archive/", "knowledge/archive/"))


def _resolve_link(source_file: Path, link: str) -> Path:
    link_clean = link.split("#")[0].split("?")[0]
    if not link_clean:
        return source_file
    return (source_file.parent / link_clean).resolve()


def extract_relative_links(content: str) -> list[str]:
    links: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(content):
        link = match.group(2).strip()
        if not _is_external_url(link) and not _is_pure_anchor(link):
            links.append(link)
    return links


def extract_navpack_paths(content: str) -> list[str]:
    paths: list[str] = []
    for line in content.splitlines():
        match = YAML_PATH_RE.match(line)
        if match:
            paths.append(match.group(1))
    return paths


def check_markdown_links(
    root: Path, source_rel: str, content: str, verbose: bool
) -> list[str]:
    errors: list[str] = []
    source_path = (root / source_rel).resolve()
    links = extract_relative_links(content)
    for link in links:
        if _is_archive_path(link):
            continue
        target = _resolve_link(source_path, link)
        if not target.exists():
            errors.append(
                f"{source_rel}: broken relative link '{link}' -> {target} (not found)"
            )
        elif verbose:
            print(f"  [OK] {source_rel}: '{link}' -> exists", file=sys.stderr)
    return errors


def check_navpack_entries(
    root: Path, source_rel: str, content: str, verbose: bool
) -> list[str]:
    errors: list[str] = []
    paths = extract_navpack_paths(content)
    for path_entry in paths:
        if _is_external_url(path_entry) or path_entry.startswith("#"):
            continue
        target = (root / path_entry.split("#")[0].split("?")[0]).resolve()
        if not target.exists():
            errors.append(
                f"{source_rel}: navpack path '{path_entry}' -> {target} (not found)"
            )
        elif verbose:
            print(
                f"  [OK] {source_rel}: navpack '{path_entry}' -> exists",
                file=sys.stderr,
            )
    return errors


def check_secret_display_commands(source_rel: str, content: str) -> list[str]:
    errors: list[str] = []
    for i, line in enumerate(content.splitlines(), 1):
        for pattern in SECRET_DISPLAY_COMMANDS:
            if pattern.search(line):
                errors.append(
                    f"{source_rel}:{i}: secret-display command pattern found: "
                    f"'{line.strip()}'"
                )
                break
    return errors


def check_project_status_as_truth(source_rel: str, content: str) -> list[str]:
    errors: list[str] = []
    for i, line in enumerate(content.splitlines(), 1):
        for pattern in PROJECT_STATUS_TRUTH_WORDS:
            if pattern.search(line):
                errors.append(
                    f"{source_rel}:{i}: PROJECT_STATUS.md referenced without "
                    f"legacy/historical/archive/snapshot marker: '{line.strip()}'"
                )
                break
    return errors


def check_legacy_pack_references(source_rel: str, content: str) -> list[str]:
    errors: list[str] = []
    for i, line in enumerate(content.splitlines(), 1):
        lower = line.lower()
        for pack in LEGACY_PACK_NAMES:
            if pack.lower() in lower:
                has_marker = any(m in lower for m in ARCHIVE_MARKERS)
                if not has_marker:
                    errors.append(
                        f"{source_rel}:{i}: legacy pack '{pack}' referenced "
                        f"without legacy/historical/archive marker: '{line.strip()}'"
                    )
                break
    return errors


def check_root_readme_is_landing(source_rel: str, content: str) -> list[str]:
    errors: list[str] = []
    if source_rel == "README.md":
        if ".github/README.md" in content and "landing" not in content.lower():
            errors.append(
                f"{source_rel}: .github/README.md referenced but README.md "
                f"may not assert GitHub landing role"
            )
    return errors


def validate_surface(root: Path, rel_path: str, verbose: bool) -> list[str]:
    errors: list[str] = []
    full_path = root / rel_path
    if not full_path.is_file():
        return [f"{rel_path}: active onboarding surface not found"]

    content = full_path.read_text(encoding="utf-8", errors="replace")

    if rel_path.endswith(".md"):
        errors.extend(check_markdown_links(root, rel_path, content, verbose))
        errors.extend(check_secret_display_commands(rel_path, content))
        errors.extend(check_project_status_as_truth(rel_path, content))
        errors.extend(check_legacy_pack_references(rel_path, content))
        errors.extend(check_root_readme_is_landing(rel_path, content))
    elif rel_path in NAVPACK_SURFACES:
        errors.extend(check_navpack_entries(root, rel_path, content, verbose))

    return errors


def validate_all(root: Path | None = None, verbose: bool = False) -> list[str]:
    r = root or REPO_ROOT
    all_errors: list[str] = []

    for surface in ACTIVE_ONBOARDING_SURFACES:
        if verbose:
            print(f"Validating: {surface}", file=sys.stderr)
        errors = validate_surface(r, surface, verbose)
        all_errors.extend(errors)

    return all_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate active onboarding docs integrity (#3233)."
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-check status to stderr",
    )
    args = parser.parse_args(argv)

    errors = validate_all(verbose=args.verbose)

    if errors:
        print("ONBOARDING DOCS VALIDATION FAILED", file=sys.stderr)
        for err in errors:
            print(f"  FAIL: {err}", file=sys.stderr)
        return 1

    print("OK: all active onboarding surfaces pass validation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
