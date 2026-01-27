"""Generate deterministic drift report: Git docs vs SurrealDB snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DriftResult:
    added: list[str]
    changed: list[str]
    removed: list[str]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_docs(root: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root).as_posix()
        docs[rel] = _sha256_file(file_path)
    return docs


def _load_snapshot(path: Path) -> dict[str, str]:
    data = path.read_text(encoding="utf-8").strip()
    if not data:
        return {}

    records: list[dict] = []
    try:
        parsed = json.loads(data)
        if isinstance(parsed, list):
            records = parsed
        elif isinstance(parsed, dict):
            records = [parsed]
    except json.JSONDecodeError:
        records = [json.loads(line) for line in data.splitlines() if line.strip()]

    mapping: dict[str, str] = {}
    for record in records:
        source = record.get("source") or {}
        path_value = source.get("path") or record.get("source_path")
        hash_value = source.get("sha256") or record.get("source_sha256")
        if path_value and hash_value:
            mapping[str(path_value)] = str(hash_value)
    return mapping


def compute_drift(git_docs: dict[str, str], snapshot: dict[str, str]) -> DriftResult:
    added = sorted([path for path in git_docs if path not in snapshot])
    removed = sorted([path for path in snapshot if path not in git_docs])
    changed = sorted(
        [path for path in git_docs if path in snapshot and git_docs[path] != snapshot[path]]
    )
    return DriftResult(added=added, changed=changed, removed=removed)


def _format_list(paths: Iterable[str], hashes: dict[str, str]) -> str:
    lines = []
    for path in paths:
        lines.append(f"- {path} ({hashes.get(path, 'unknown')[:12]})")
    return "\n".join(lines) if lines else "- None"


def render_report(result: DriftResult, git_docs: dict[str, str], snapshot: dict[str, str]) -> str:
    return "\n".join(
        [
            "# SurrealDB Drift Report",
            "",
            f"Added: {len(result.added)}",
            f"Changed: {len(result.changed)}",
            f"Removed: {len(result.removed)}",
            "",
            "## Added (ingest)",
            _format_list(result.added, git_docs),
            "",
            "## Changed (re-ingest)",
            _format_list(result.changed, git_docs),
            "",
            "## Removed (tombstone)",
            _format_list(result.removed, snapshot),
            "",
            "## Notes",
            "- Deterministic ordering (sorted paths).",
            "- No file contents included.",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SurrealDB drift report.")
    parser.add_argument("--docs-root", type=Path, default=Path("docs"), help="Docs root path")
    parser.add_argument("--snapshot", type=Path, required=True, help="SurrealDB snapshot JSON")
    parser.add_argument("--output", type=Path, default=Path("reports/surrealdb-drift-report.md"))
    args = parser.parse_args()

    git_docs = _iter_docs(args.docs_root)
    snapshot = _load_snapshot(args.snapshot)
    result = compute_drift(git_docs, snapshot)
    report = render_report(result, git_docs, snapshot)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
