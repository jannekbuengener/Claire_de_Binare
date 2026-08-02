"""Shared Markdown relative-link helpers for docs validators.

Used by:
- tools.validate_onboarding_docs (#3233)
- tools.validate_readme_links (#3994, #4037, #4298)

Issues: #3994, #4037, #4298
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
FENCED_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)


@dataclass(frozen=True)
class MarkdownLink:
    """One Markdown link outside fenced code blocks."""

    label: str
    target: str


def strip_fenced_code_blocks(content: str) -> str:
    """Remove fenced code blocks before navigation link extraction."""
    return FENCED_CODE_BLOCK_RE.sub("", content)


def is_external_url(link: str) -> bool:
    return link.startswith(("http://", "https://", "mailto:"))


def is_pure_anchor(link: str) -> bool:
    return link.startswith("#")


def is_archive_link_target(link: str) -> bool:
    """Skip existence checks for links into archive trees."""
    return link.startswith(("docs/archive/", "knowledge/archive/"))


def strip_link_fragments(link: str) -> str:
    """Remove query/anchor portions used only for path resolution."""
    return link.split("#", 1)[0].split("?", 1)[0]


def resolve_relative_link(source_file: Path, link: str) -> Path:
    link_clean = strip_link_fragments(link)
    if not link_clean:
        return source_file
    return (source_file.parent / link_clean).resolve()


def extract_markdown_links(content: str) -> list[MarkdownLink]:
    """Extract relative and absolute Markdown links (label + target).

    External URLs and pure anchors are included; callers filter as needed.
    Fenced code blocks are ignored.
    """
    links: list[MarkdownLink] = []
    for match in MARKDOWN_LINK_RE.finditer(strip_fenced_code_blocks(content)):
        label = match.group(1)
        target = match.group(2).strip()
        if target:
            links.append(MarkdownLink(label=label, target=target))
    return links


def extract_relative_links(content: str) -> list[str]:
    """Backward-compatible target-only extraction for relative links."""
    return [
        link.target
        for link in extract_markdown_links(content)
        if not is_external_url(link.target) and not is_pure_anchor(link.target)
    ]


def repo_relative_posix(root: Path, path: Path) -> str | None:
    """Return POSIX path relative to root, or None if outside the repository."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


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
