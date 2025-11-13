#!/usr/bin/env python3
"""Migrate documentation according to a mapping file.

The mapping file may contain either Markdown table rows (| Quelle | Ziel | ...)
or simple "source -> target" lines. Wildcards in the source path are supported
and expand using pathlib.Path.glob relative to --source-root. If the target path
ends with a slash, the matched file or directory name is appended to that
location.
"""

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

TABLE_PREFIX = "|"
ARROW = "->"


def parse_map(map_path: Path) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for raw_line in map_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith(TABLE_PREFIX) and "---" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0].lower() != "quelle":
                src, dst = cells[0], cells[1]
                if src and dst:
                    pairs.append((src, dst))
            continue

        if ARROW in line:
            src, dst = [part.strip() for part in line.split(ARROW, 1)]
            if src and dst:
                pairs.append((src, dst))
    return pairs


def has_wildcard(value: str) -> bool:
    return any(ch in value for ch in "*?[")


def determine_dest(match: Path, dst_spec: str) -> Path:
    dst_path = Path(dst_spec)
    if str(dst_spec).endswith("/") or dst_spec == "":
        return dst_path / match.name
    return dst_path


def iter_tasks(src_root: Path, src_pattern: str, dst_spec: str) -> Iterable[Tuple[str, Path, Path]]:
    if has_wildcard(src_pattern):
        matches = sorted(src_root.glob(src_pattern))
        if not matches:
            yield ("MISS", Path(src_pattern), Path(dst_spec))
        else:
            for match in matches:
                if not match.exists():
                    yield ("MISS", Path(src_pattern), Path(dst_spec))
                    continue
                rel_src = match.relative_to(src_root)
                dest = determine_dest(match, dst_spec)
                yield ("COPY", rel_src, dest)
    else:
        match = src_root / src_pattern
        if not match.exists():
            yield ("MISS", Path(src_pattern), Path(dst_spec))
            return
        rel_src = match.relative_to(src_root)
        dest = determine_dest(match, dst_spec)
        yield ("COPY", rel_src, dest)


def copy_path(src_root: Path, dst_root: Path, rel_src: Path, rel_dest: Path) -> str:
    src = (src_root / rel_src).resolve()
    dest = (dst_root / rel_dest).resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        from shutil import copytree
        copytree(src, dest, dirs_exist_ok=True)
        return f"DIR  {rel_src.as_posix()} -> {rel_dest.as_posix()}"
    else:
        from shutil import copy2
        copy2(src, dest)
        return f"FILE {rel_src.as_posix()} -> {rel_dest.as_posix()}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate documentation files per mapping.")
    parser.add_argument("--map", default="docs/MIGRATION_MAP.md")
    parser.add_argument("--source-root", default="../claire_de_binare")
    parser.add_argument("--target-root", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    map_path = Path(args.map)
    src_root = Path(args.source_root)
    dst_root = Path(args.target_root)

    if not map_path.exists():
        print(f"ERROR: map not found: {map_path}", file=sys.stderr)
        return 2
    if not src_root.exists():
        print(f"ERROR: source root not found: {src_root}", file=sys.stderr)
        return 2

    pairs = parse_map(map_path)
    if not pairs:
        print("WARNING: no mappings resolved")
        return 0

    reports: List[str] = []
    for src_pattern, dst_spec in pairs:
        for action, rel_src, rel_dest in iter_tasks(src_root, src_pattern, dst_spec):
            if action == "MISS":
                reports.append(f"MISS  {src_pattern} -> {dst_spec}")
            elif args.dry_run:
                reports.append(f"EXIST {rel_src.as_posix()} -> {rel_dest.as_posix()}")
            else:
                reports.append(copy_path(src_root, dst_root, rel_src, rel_dest))
    print("\n".join(reports))
    return 0


if __name__ == "__main__":
    sys.exit(main())
