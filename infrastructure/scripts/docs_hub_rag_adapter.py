#!/usr/bin/env python3
"""Optional canonical docs RAG adapter for LangChain and LlamaIndex.

This helper is intentionally narrow:
- canonical docs only
- optional framework imports
- no default runtime wiring

It can:
- collect canonical docs files from the working repo or the local archive snapshot
- split them into small RAG-friendly chunks
- export the chunks as JSONL
- optionally render LangChain or LlamaIndex document objects when those
  packages are explicitly installed and requested
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_INCLUDE_DIRS = ("knowledge", "agents", "meta")
ROOT_INDEX_FILES = ("DOCS_HUB_INDEX.md", "index.yaml", "cdb_docs_index.yaml")
SUPPORTED_SUFFIXES = (".md", ".yaml", ".yml", ".json")
DEFAULT_MAX_CHARS = 1800
LOCAL_ROOT_INDEX_FILES = ("docs/meta/WORKING_REPO_CANON.md",)


@dataclass(slots=True)
class RagChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


def detect_working_repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / ".git").exists() and (candidate / "infrastructure").exists():
            return candidate
    return Path.cwd()


def is_valid_docs_hub(path: Path) -> bool:
    return (
        path.exists()
        and (path / "DOCS_HUB_INDEX.md").is_file()
        and (path / "knowledge").is_dir()
        and (path / "agents").is_dir()
    )


def is_valid_local_docs_workspace(path: Path) -> bool:
    return (
        path.exists()
        and (path / "docs" / "meta" / "WORKING_REPO_CANON.md").is_file()
        and (path / "knowledge").is_dir()
        and (path / "agents").is_dir()
    )


def is_valid_docs_source(path: Path) -> bool:
    return is_valid_local_docs_workspace(path) or is_valid_docs_hub(path)


def resolve_docs_hub_path(explicit_path: str | None = None) -> Path:
    if explicit_path:
        path = Path(explicit_path).resolve()
        if is_valid_docs_source(path):
            return path
        raise FileNotFoundError(f"invalid docs workspace path: {explicit_path}")

    env_path = os.getenv("DOCS_HUB_PATH")
    if env_path:
        path = Path(env_path).resolve()
        if is_valid_docs_source(path):
            return path

    working_repo = detect_working_repo_root()
    if is_valid_local_docs_workspace(working_repo):
        return working_repo.resolve()

    snapshot = working_repo / "docs" / "archive" / "docs_hub_snapshot"
    if is_valid_docs_hub(snapshot):
        return snapshot.resolve()

    raise FileNotFoundError(
        "could not locate canonical docs workspace; set DOCS_HUB_PATH, "
        "use --docs-hub, or restore the local docs_hub_snapshot archive"
    )


def iter_docs_hub_files(
    docs_hub_path: Path, include_dirs: Sequence[str] = DEFAULT_INCLUDE_DIRS
) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    root_index_files = (
        LOCAL_ROOT_INDEX_FILES
        if is_valid_local_docs_workspace(docs_hub_path)
        else ROOT_INDEX_FILES
    )

    for filename in root_index_files:
        candidate = docs_hub_path / filename
        if candidate.is_file() and candidate not in seen:
            files.append(candidate)
            seen.add(candidate)

    for relative_dir in include_dirs:
        base = docs_hub_path / relative_dir
        if not base.is_dir() and relative_dir == "meta":
            base = docs_hub_path / "docs" / "meta"
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if (
                path.is_file()
                and path.suffix.lower() in SUPPORTED_SUFFIXES
                and path not in seen
            ):
                files.append(path)
                seen.add(path)

    return files


def split_text(text: str, max_chars: int) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    sections = re.split(r"(?m)(?=^#{1,6}\s+)", stripped)
    base_chunks = [section.strip() for section in sections if section.strip()] or [
        stripped
    ]
    chunks: list[str] = []

    for section in base_chunks:
        if len(section) <= max_chars:
            chunks.append(section)
            continue

        start = 0
        step = max_chars
        while start < len(section):
            chunks.append(section[start : start + step].strip())
            start += step

    return [chunk for chunk in chunks if chunk]


def build_chunks(
    docs_hub_path: Path,
    include_dirs: Sequence[str] = DEFAULT_INCLUDE_DIRS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> list[RagChunk]:
    chunks: list[RagChunk] = []
    for file_path in iter_docs_hub_files(docs_hub_path, include_dirs):
        relative_path = file_path.relative_to(docs_hub_path).as_posix()
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        parts = split_text(text, max_chars=max_chars)
        for index, part in enumerate(parts):
            chunks.append(
                RagChunk(
                    chunk_id=f"{relative_path}#{index}",
                    text=part,
                    metadata={
                        "docs_hub_path": relative_path,
                        "source_repo": docs_hub_path.name,
                        "source_kind": relative_path.split("/", 1)[0],
                        "chunk_index": index,
                    },
                )
            )
    return chunks


def export_jsonl(chunks: Iterable[RagChunk], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    return output_path


def import_langchain_document() -> type[Any]:
    for module_name in ("langchain_core.documents", "langchain.schema"):
        try:
            module = importlib.import_module(module_name)
            return getattr(module, "Document")
        except ModuleNotFoundError:
            continue
    raise RuntimeError(
        "LangChain adapter requested but no compatible package is installed "
        "(expected langchain_core or langchain)"
    )


def import_llamaindex_document() -> type[Any]:
    try:
        module = importlib.import_module("llama_index.core")
        return getattr(module, "Document")
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "LlamaIndex adapter requested but llama_index is not installed"
        ) from exc


def to_langchain_documents(chunks: Sequence[RagChunk]) -> list[Any]:
    document_type = import_langchain_document()
    return [
        document_type(page_content=chunk.text, metadata=chunk.metadata)
        for chunk in chunks
    ]


def to_llamaindex_documents(chunks: Sequence[RagChunk]) -> list[Any]:
    document_type = import_llamaindex_document()
    return [
        document_type(text=chunk.text, metadata=chunk.metadata, doc_id=chunk.chunk_id)
        for chunk in chunks
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Optional canonical docs RAG adapter")
    parser.add_argument("--docs-hub", help="Explicit docs workspace path")
    parser.add_argument(
        "--include-dir",
        action="append",
        dest="include_dirs",
        help="Docs subdirectory to include (default: knowledge, agents, meta)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help=f"Maximum characters per chunk (default: {DEFAULT_MAX_CHARS})",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    preview_parser = subparsers.add_parser("preview", help="Preview collected chunks")
    preview_parser.add_argument(
        "--adapter",
        choices=("jsonl", "langchain", "llamaindex"),
        default="jsonl",
        help="Optional adapter surface to instantiate",
    )
    preview_parser.add_argument(
        "--limit", type=int, default=5, help="Preview item limit"
    )

    export_parser = subparsers.add_parser("export-jsonl", help="Export chunks as JSONL")
    export_parser.add_argument("--out", required=True, help="Output JSONL path")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    include_dirs = tuple(args.include_dirs or DEFAULT_INCLUDE_DIRS)

    try:
        docs_hub_path = resolve_docs_hub_path(args.docs_hub)
        chunks = build_chunks(
            docs_hub_path=docs_hub_path,
            include_dirs=include_dirs,
            max_chars=args.max_chars,
        )

        if args.command == "preview":
            if args.adapter == "langchain":
                rendered = to_langchain_documents(chunks)
                print(
                    json.dumps(
                        {
                            "adapter": "langchain",
                            "count": len(rendered),
                            "preview_metadata": [
                                chunks[i].metadata
                                for i in range(min(args.limit, len(chunks)))
                            ],
                        },
                        indent=2,
                    )
                )
                return 0

            if args.adapter == "llamaindex":
                rendered = to_llamaindex_documents(chunks)
                print(
                    json.dumps(
                        {
                            "adapter": "llamaindex",
                            "count": len(rendered),
                            "preview_metadata": [
                                chunks[i].metadata
                                for i in range(min(args.limit, len(chunks)))
                            ],
                        },
                        indent=2,
                    )
                )
                return 0

            preview = [asdict(chunk) for chunk in chunks[: args.limit]]
            print(
                json.dumps(
                    {
                        "adapter": "jsonl",
                        "docs_hub": str(docs_hub_path),
                        "count": len(chunks),
                        "preview": preview,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0

        if args.command == "export-jsonl":
            output = export_jsonl(chunks, Path(args.out))
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "docs_hub": str(docs_hub_path),
                        "count": len(chunks),
                        "output": str(output.resolve()),
                    },
                    indent=2,
                )
            )
            return 0

        parser.error(f"unsupported command: {args.command}")
        return 2
    except Exception as exc:  # pragma: no cover - CLI surface
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
