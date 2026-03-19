#!/usr/bin/env python3
"""Optional filesystem-backed Agno storage adapter for memory and knowledge only.

This helper is intentionally narrow:
- no default runtime wiring
- no mandatory Agno dependency
- only `memory` and `knowledge` buckets

It provides a small local storage layout that external Agno-side tooling can use
explicitly when maintainers want a repo-adjacent persistence path without
touching the default Graphiti-based memory overlay.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

VALID_KINDS = ("memory", "knowledge")
DEFAULT_STORAGE_ROOT = Path(".cdb_local/agno_storage")
MANIFEST_NAME = "manifest.json"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def detect_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "infrastructure" / "compose" / "memory.yml").is_file():
            return candidate
    return Path.cwd()


def normalize_key(key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", key.strip()).strip("-._")
    if not normalized:
        raise ValueError("key must contain at least one filesystem-safe character")
    return normalized


def validate_kind(kind: str) -> str:
    if kind not in VALID_KINDS:
        raise ValueError(
            f"unsupported kind '{kind}'; expected one of: {', '.join(VALID_KINDS)}"
        )
    return kind


@dataclass(slots=True)
class AgnoStorageAdapter:
    root: Path

    @classmethod
    def from_env(cls, explicit_root: str | None = None) -> "AgnoStorageAdapter":
        if explicit_root:
            root = Path(explicit_root)
        else:
            configured = os.getenv("AGNO_STORAGE_ROOT")
            base = (
                Path(configured)
                if configured
                else detect_repo_root() / DEFAULT_STORAGE_ROOT
            )
            root = base
        return cls(root=root.resolve())

    @property
    def manifest_path(self) -> Path:
        return self.root / MANIFEST_NAME

    def kind_dir(self, kind: str) -> Path:
        return self.root / validate_kind(kind)

    def record_path(self, kind: str, key: str) -> Path:
        return self.kind_dir(kind) / f"{normalize_key(key)}.json"

    def ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for kind in VALID_KINDS:
            self.kind_dir(kind).mkdir(parents=True, exist_ok=True)

        manifest = {
            "adapter": "cdb-agno-filesystem",
            "scope": list(VALID_KINDS),
            "storage_root": str(self.root),
            "version": 1,
            "updated_at": utc_now_iso(),
        }
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    def put(
        self, kind: str, key: str, content: str, metadata: dict[str, Any] | None = None
    ) -> Path:
        self.ensure_layout()
        record = {
            "kind": validate_kind(kind),
            "key": normalize_key(key),
            "content": content,
            "metadata": metadata or {},
            "updated_at": utc_now_iso(),
        }
        destination = self.record_path(kind, key)
        destination.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        return destination

    def get(self, kind: str, key: str) -> dict[str, Any]:
        record_path = self.record_path(kind, key)
        if not record_path.is_file():
            raise FileNotFoundError(f"record not found: {record_path}")
        return json.loads(record_path.read_text(encoding="utf-8"))

    def list(self, kind: str | None = None) -> list[dict[str, Any]]:
        kinds = [validate_kind(kind)] if kind else list(VALID_KINDS)
        records: list[dict[str, Any]] = []
        for bucket in kinds:
            directory = self.kind_dir(bucket)
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                payload = json.loads(path.read_text(encoding="utf-8"))
                records.append(
                    {
                        "kind": payload["kind"],
                        "key": payload["key"],
                        "path": str(path),
                        "updated_at": payload.get("updated_at"),
                    }
                )
        return records


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Optional Agno storage helper (memory + knowledge only)"
    )
    parser.add_argument(
        "--root",
        help="Storage root directory (default: AGNO_STORAGE_ROOT or .cdb_local/agno_storage)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create storage layout and manifest")

    put_parser = subparsers.add_parser("put", help="Write a memory or knowledge record")
    put_parser.add_argument("--kind", required=True, choices=VALID_KINDS)
    put_parser.add_argument("--key", required=True)
    group = put_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--content", help="Inline content")
    group.add_argument("--content-file", help="Read content from file")
    put_parser.add_argument("--metadata-json", help="Optional JSON object for metadata")

    get_parser = subparsers.add_parser("get", help="Read a stored record")
    get_parser.add_argument("--kind", required=True, choices=VALID_KINDS)
    get_parser.add_argument("--key", required=True)

    list_parser = subparsers.add_parser("list", help="List stored records")
    list_parser.add_argument(
        "--kind", choices=VALID_KINDS, help="Limit listing to one bucket"
    )

    return parser


def load_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    decoded = json.loads(raw)
    if not isinstance(decoded, dict):
        raise ValueError("--metadata-json must decode to a JSON object")
    return decoded


def load_content(inline_content: str | None, content_file: str | None) -> str:
    if inline_content is not None:
        return inline_content
    assert content_file is not None
    return Path(content_file).read_text(encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    adapter = AgnoStorageAdapter.from_env(explicit_root=args.root)

    try:
        if args.command == "init":
            adapter.ensure_layout()
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "root": str(adapter.root),
                        "manifest": str(adapter.manifest_path),
                    },
                    indent=2,
                )
            )
            return 0

        if args.command == "put":
            metadata = load_metadata(args.metadata_json)
            content = load_content(args.content, args.content_file)
            destination = adapter.put(
                kind=args.kind, key=args.key, content=content, metadata=metadata
            )
            print(json.dumps({"status": "ok", "path": str(destination)}, indent=2))
            return 0

        if args.command == "get":
            print(json.dumps(adapter.get(kind=args.kind, key=args.key), indent=2))
            return 0

        if args.command == "list":
            print(json.dumps(adapter.list(kind=args.kind), indent=2))
            return 0

        parser.error(f"unsupported command: {args.command}")
        return 2
    except Exception as exc:  # pragma: no cover - CLI surface
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
