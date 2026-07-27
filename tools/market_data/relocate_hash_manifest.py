"""Streaming SHA256 manifests for market_data relocation (#4004)."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.market_data.historical_common import (
    HistoricalProbeError,
    sha256_file,
    utc_now_iso,
    write_json,
)

CHUNK_SIZE = 1024 * 1024


class RelocateHashError(HistoricalProbeError):
    """Hash manifest creation or comparison failed."""


@dataclass(frozen=True, slots=True)
class HashEntry:
    relative_path: str
    size_bytes: int
    sha256: str
    last_write_utc: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "last_write_utc": self.last_write_utc,
        }


def _is_reparse_point(path: Path) -> bool:
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def _ensure_traversable(path: Path) -> None:
    """Reject reparse points; map access failures to RelocateHashError (#4166)."""
    try:
        if _is_reparse_point(path):
            raise RelocateHashError(f"reparse point encountered: {path}")
    except OSError as exc:
        raise RelocateHashError(f"access error: {path}") from exc


def _normalize_relative(root: Path, file_path: Path) -> str:
    rel = file_path.relative_to(root).as_posix()
    return rel


def iter_hash_entries(root: Path) -> Iterator[HashEntry]:
    root = root.resolve()
    if not root.is_dir():
        raise RelocateHashError(f"root is not a directory: {root}")
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)
        _ensure_traversable(current)
        pruned: list[str] = []
        for name in dirnames:
            child = current / name
            _ensure_traversable(child)
            pruned.append(name)
        dirnames[:] = pruned
        for name in sorted(filenames):
            file_path = current / name
            _ensure_traversable(file_path)
            try:
                stat_result = file_path.stat()
            except OSError as exc:
                raise RelocateHashError(f"access error: {file_path}") from exc
            last_write = datetime.fromtimestamp(
                stat_result.st_mtime, tz=UTC
            ).isoformat()
            try:
                file_sha256 = sha256_file(file_path)
            except OSError as exc:
                raise RelocateHashError(f"access error: {file_path}") from exc
            yield HashEntry(
                relative_path=_normalize_relative(root, file_path),
                size_bytes=stat_result.st_size,
                sha256=file_sha256,
                last_write_utc=last_write,
            )


def manifest_fingerprint(entries: list[HashEntry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        line = json.dumps(entry.to_dict(), sort_keys=True, separators=(",", ":"))
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def create_manifest(*, root: Path, output: Path) -> dict[str, Any]:
    entries = sorted(iter_hash_entries(root), key=lambda item: item.relative_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    with output.open("w", encoding="utf-8") as handle:
        for entry in entries:
            total_bytes += entry.size_bytes
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")
    summary = {
        "root": str(root.resolve()),
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "manifest_fingerprint": manifest_fingerprint(entries),
        "created_at_utc": utc_now_iso(),
    }
    return summary


def _load_manifest(path: Path) -> list[HashEntry]:
    entries: list[HashEntry] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RelocateHashError(f"invalid jsonl at {path}:{line_no}") from exc
            entries.append(
                HashEntry(
                    relative_path=str(payload["relative_path"]),
                    size_bytes=int(payload["size_bytes"]),
                    sha256=str(payload["sha256"]),
                    last_write_utc=payload.get("last_write_utc"),
                )
            )
    return entries


def compare_manifests(
    *,
    source: Path,
    destination: Path,
    output: Path,
) -> dict[str, Any]:
    source_entries = _load_manifest(source)
    dest_entries = _load_manifest(destination)
    source_map = {entry.relative_path: entry for entry in source_entries}
    dest_map = {entry.relative_path: entry for entry in dest_entries}
    source_paths = set(source_map)
    dest_paths = set(dest_map)
    missing = sorted(source_paths - dest_paths)
    extra = sorted(dest_paths - source_paths)
    mismatched: list[dict[str, str]] = []
    metadata_mismatched: list[dict[str, Any]] = []
    for rel in sorted(source_paths & dest_paths):
        s_entry = source_map[rel]
        d_entry = dest_map[rel]
        if s_entry.sha256 != d_entry.sha256:
            mismatched.append(
                {
                    "relative_path": rel,
                    "source_sha256": s_entry.sha256,
                    "dest_sha256": d_entry.sha256,
                }
            )
        elif s_entry.size_bytes != d_entry.size_bytes:
            metadata_mismatched.append(
                {
                    "relative_path": rel,
                    "source_size_bytes": s_entry.size_bytes,
                    "destination_size_bytes": d_entry.size_bytes,
                }
            )
    source_bytes = sum(entry.size_bytes for entry in source_entries)
    destination_bytes = sum(entry.size_bytes for entry in dest_entries)
    verdict = "PASS"
    if missing or extra or mismatched or metadata_mismatched:
        verdict = "FAIL"
    if source_entries and len(source_entries) != len(dest_entries):
        verdict = "FAIL"
    if source_bytes != destination_bytes:
        verdict = "FAIL"
    report = {
        "source_file_count": len(source_entries),
        "destination_file_count": len(dest_entries),
        "source_bytes": source_bytes,
        "destination_bytes": destination_bytes,
        "missing": missing,
        "extra": extra,
        "mismatched": mismatched,
        "metadata_mismatched": metadata_mismatched,
        "source_manifest_fingerprint": manifest_fingerprint(source_entries),
        "destination_manifest_fingerprint": manifest_fingerprint(dest_entries),
        "verdict": verdict,
        "compared_at_utc": utc_now_iso(),
    }
    write_json(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Relocation hash manifests (#4004)")
    sub = parser.add_subparsers(dest="command", required=True)

    create_parser = sub.add_parser("create")
    create_parser.add_argument("--root", required=True)
    create_parser.add_argument("--output", required=True)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--source", required=True)
    compare_parser.add_argument("--destination", required=True)
    compare_parser.add_argument("--output", required=True)

    args = parser.parse_args()
    try:
        if args.command == "create":
            summary = create_manifest(root=Path(args.root), output=Path(args.output))
            print(json.dumps(summary, indent=2))
            return 0
        if args.command == "compare":
            report = compare_manifests(
                source=Path(args.source),
                destination=Path(args.destination),
                output=Path(args.output),
            )
            print(json.dumps({"verdict": report["verdict"]}, indent=2))
            return 0 if report["verdict"] == "PASS" else 2
    except RelocateHashError as exc:
        print(f"HASH_MANIFEST_ERROR: {exc}", file=sys.stderr)
        return 3
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
