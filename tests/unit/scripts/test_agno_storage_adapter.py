"""Tests for agno_storage_adapter.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from agno_storage_adapter import AgnoStorageAdapter, main, normalize_key


def test_init_creates_manifest_and_bucket_dirs(tmp_path: Path) -> None:
    adapter = AgnoStorageAdapter(root=tmp_path / "agno")

    adapter.ensure_layout()

    assert adapter.manifest_path.is_file()
    assert (adapter.root / "memory").is_dir()
    assert (adapter.root / "knowledge").is_dir()
    manifest = json.loads(adapter.manifest_path.read_text(encoding="utf-8"))
    assert manifest["adapter"] == "cdb-agno-filesystem"
    assert manifest["scope"] == ["memory", "knowledge"]


def test_put_get_and_list_round_trip(tmp_path: Path) -> None:
    adapter = AgnoStorageAdapter(root=tmp_path / "agno")

    adapter.put("memory", "Daily Note", "remember this", {"source": "unit"})
    adapter.put("knowledge", "runbook/redis", "restart redis", {"owner": "ops"})

    memory_record = adapter.get("memory", "Daily Note")
    assert memory_record["key"] == "Daily-Note"
    assert memory_record["content"] == "remember this"
    assert memory_record["metadata"]["source"] == "unit"

    listed = adapter.list()
    assert len(listed) == 2
    assert {item["kind"] for item in listed} == {"memory", "knowledge"}


def test_cli_rejects_unsupported_scope_and_normalizes_keys(tmp_path: Path) -> None:
    assert normalize_key("Runbook / Redis") == "Runbook-Redis"

    exit_code = main(
        [
            "--root",
            str(tmp_path / "agno"),
            "put",
            "--kind",
            "memory",
            "--key",
            "ops note",
            "--content",
            "check redis",
            "--metadata-json",
            '{"tag":"ops"}',
        ]
    )
    assert exit_code == 0

    adapter = AgnoStorageAdapter(root=(tmp_path / "agno").resolve())
    listed = adapter.list("memory")
    assert listed[0]["key"] == "ops-note"
