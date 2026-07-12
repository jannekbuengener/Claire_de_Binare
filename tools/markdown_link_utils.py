"""Shared Markdown relative-link helpers for docs validators.

Used by:
- tools.validate_onboarding_docs (#3233)
- tools.validate_readme_links (#3994)

Issue: #3994
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def is_external_url(link: str) -> bool:
    return link.startswith(("http://", "https://", "mailto:"))


def is_pure_anchor(link: str) -> bool:
    return link.startswith("#")


def is_archive_link_target(link: str) -> bool:
    """Skip existence checks for links into archive trees."""
    return link.startswith(("docs/archive/", "knowledge/archive/"))


def resolve_relative_link(source_file: Path, link: str) -> Path:
    link_clean = link.split("#")[0].split("?")[0]
    if not link_clean:
        return source_file
    return (source_file.parent / link_clean).resolve()


def extract_relative_links(content: str) -> list[str]:
    links: list[str] = []
    for match in MARKDOWN_LINK_RE.finditer(content):
        link = match.group(2).strip()
        if not is_external_url(link) and not is_pure_anchor(link):
            links.append(link)
    return links


def check_markdown_links(
    root: Path,
    source_rel: str,
    content: str,
    verbose: bool = False,
) -> list[str]:
    errors: list[str] = []
    source_path = (root / source_rel).resolve()
    for link in extract_relative_links(content):
        if is_archive_link_target(link):
            continue
        target = resolve_relative_link(source_path, link)
        if not target.exists():
            errors.append(
                f"{source_rel}: broken relative link '{link}' -> {target} (not found)"
            )
        elif verbose:
            print(f"  [OK] {source_rel}: '{link}' -> exists", file=sys.stderr)
    return errors
