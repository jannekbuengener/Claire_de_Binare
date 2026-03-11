"""Tests for docs_hub_rag_adapter.py."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

import docs_hub_rag_adapter as adapter


def make_docs_hub(tmp_path: Path) -> Path:
    docs_hub = tmp_path / "Claire_de_Binare_Docs"
    (docs_hub / "knowledge" / "governance").mkdir(parents=True)
    (docs_hub / "agents").mkdir(parents=True)
    (docs_hub / "meta").mkdir(parents=True)
    (docs_hub / "DOCS_HUB_INDEX.md").write_text(
        "# Canon\n## Governance\ncontent\n", encoding="utf-8"
    )
    (docs_hub / "index.yaml").write_text(
        "metadata:\n  version: '1.0'\n", encoding="utf-8"
    )
    (docs_hub / "cdb_docs_index.yaml").write_text(
        "metadata:\n  version: '1.0'\n", encoding="utf-8"
    )
    (docs_hub / "knowledge" / "governance" / "policy.md").write_text(
        "# Policy\nFirst section.\n## Controls\nSecond section.\n",
        encoding="utf-8",
    )
    (docs_hub / "agents" / "AGENTS.md").write_text(
        "# Agents\nAgent charter.\n", encoding="utf-8"
    )
    (docs_hub / "meta" / "status.yaml").write_text(
        "status: canonical\n", encoding="utf-8"
    )
    return docs_hub


def test_build_chunks_collects_docs_hub_content(tmp_path: Path) -> None:
    docs_hub = make_docs_hub(tmp_path)

    chunks = adapter.build_chunks(docs_hub, max_chars=40)

    assert chunks
    assert any(
        chunk.metadata["docs_hub_path"] == "DOCS_HUB_INDEX.md" for chunk in chunks
    )
    assert any(chunk.metadata["source_kind"] == "knowledge" for chunk in chunks)


def test_export_jsonl_writes_serialized_chunks(tmp_path: Path) -> None:
    docs_hub = make_docs_hub(tmp_path)
    chunks = adapter.build_chunks(docs_hub, max_chars=80)
    output = tmp_path / "export" / "docs_hub.jsonl"

    adapter.export_jsonl(chunks, output)

    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert lines
    payload = json.loads(lines[0])
    assert payload["metadata"]["source_repo"] == "Claire_de_Binare_Docs"


def test_optional_framework_exports_use_lazy_imports(
    monkeypatch, tmp_path: Path
) -> None:
    docs_hub = make_docs_hub(tmp_path)
    chunks = adapter.build_chunks(docs_hub, max_chars=120)

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


def test_main_export_jsonl_succeeds_with_explicit_docs_hub(tmp_path: Path) -> None:
    docs_hub = make_docs_hub(tmp_path)
    output = tmp_path / "export.jsonl"

    exit_code = adapter.main(
        [
            "--docs-hub",
            str(docs_hub),
            "export-jsonl",
            "--out",
            str(output),
        ]
    )

    assert exit_code == 0
    assert output.is_file()
