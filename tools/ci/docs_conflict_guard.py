"""Docs Conflict Guard — merge conflict marker scan.

Extracted from .github/workflows/docs-conflict-guard.yml for local reuse.
Workflow YAML is intentionally unchanged in Phase 1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

EXTENSIONS = {".md", ".yaml", ".yml", ".json"}
SCAN_ROOTS = ("agents", "knowledge", "docs", ".github")
# Match docs-conflict-guard.yml: exclude entire docs/archive/ and .git.
EXCLUDE_RE = re.compile(r"(^|[/\\])(docs[/\\]archive|\.git)([/\\]|$)")
PATTERNS = (
    re.compile(r"^\s*<<<<<<<.*$"),
    re.compile(r"^\s*=======$"),
    re.compile(r"^\s*>>>>>>>.*$"),
)


def iter_scan_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = repo_root / root_name
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in EXTENSIONS:
                    files.append(path)
    for path in repo_root.iterdir():
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            files.append(path)
    unique: dict[str, Path] = {}
    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        if EXCLUDE_RE.search(rel):
            continue
        unique[rel] = path
    return [unique[k] for k in sorted(unique)]


def find_conflict_markers(repo_root: Path) -> list[tuple[str, int, str]]:
    hits: list[tuple[str, int, str]] = []
    for path in iter_scan_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.match(line):
                    rel = path.relative_to(repo_root).as_posix()
                    hits.append((rel, idx, line.strip()))
                    break
    return hits


def main(argv: list[str] | None = None) -> int:
    del argv  # unused; CLI compatible with python -m
    repo_root = Path(__file__).resolve().parents[2]
    hits = find_conflict_markers(repo_root)
    if hits:
        print("Merge conflict markers found:")
        for rel, line_no, line in hits:
            print(f"{rel}:{line_no}: {line}")
        print("Merge conflict markers detected in tracked docs files.", file=sys.stderr)
        return 1
    print("OK: no merge conflict markers found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
