"""Tests for canonical_docs_rag_adapter.py."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

import canonical_docs_rag_adapter as adapter


def make_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "Claire_de_Binare"
    (repository / "knowledge" / "governance").mkdir(parents=True)
    (repository / "agents").mkdir(parents=True)
    (repository / "docs" / "meta").mkdir(parents=True)
    (repository / "docs" / "meta" / "REPOSITORY_CANON.md").write_text(
        "# Claire de Binare repository\n", encoding="utf-8"
    )
    (repository / "knowledge" / "governance" / "policy.md").write_text(
        "# Policy\nFirst section.\n## Controls\nSecond section.\n",
        encoding="utf-8",
    )
    (repository / "agents" / "AGENTS.md").write_text(
        "# Agents\nAgent charter.\n", encoding="utf-8"
    )
    return repository


def test_build_chunks_collects_canonical_docs_content(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)

    chunks = adapter.build_chunks(repository, max_chars=40)

    assert chunks
    assert any(
        chunk.metadata["repository_path"] == "docs/meta/REPOSITORY_CANON.md" for chunk in chunks
    )
    assert any(chunk.metadata["source_kind"] == "knowledge" for chunk in chunks)


def test_export_jsonl_writes_serialized_chunks(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    chunks = adapter.build_chunks(repository, max_chars=80)
    output = tmp_path / "export" / "canonical_docs.jsonl"

    adapter.export_jsonl(chunks, output)

    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    payload = json.loads(lines[0])
    assert payload["metadata"]["source_repo"] == "Claire_de_Binare"


def test_optional_framework_exports_use_lazy_imports(
    monkeypatch, tmp_path: Path
) -> None:
    repository = make_repository(tmp_path)
    chunks = adapter.build_chunks(repository, max_chars=120)

    class FakeDocument:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def fake_import_module(name: str):
        if name == "langchain_core.documents":
            return SimpleNamespace(Document=FakeDocument)
        if name == "llama_index.core":
            return SimpleNamespace(Document=FakeDocument)
        raise ModuleNotFoundError(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    langchain_docs = adapter.to_langchain_documents(chunks)
    llamaindex_docs = adapter.to_llamaindex_documents(chunks)

    assert langchain_docs and isinstance(langchain_docs[0], FakeDocument)
    assert "page_content" in langchain_docs[0].kwargs
    assert llamaindex_docs and isinstance(llamaindex_docs[0], FakeDocument)
    assert "text" in llamaindex_docs[0].kwargs


def test_main_export_jsonl_succeeds_with_explicit_repository(tmp_path: Path) -> None:
    repository = make_repository(tmp_path)
    output = tmp_path / "export.jsonl"

    exit_code = adapter.main(
        [
            "--repository",
            str(repository),
            "export-jsonl",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert output.is_file()
