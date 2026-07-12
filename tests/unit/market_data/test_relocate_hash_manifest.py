from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

import pytest

from tools.market_data.relocate_hash_manifest import (
    RelocateHashError,
    compare_manifests,
    create_manifest,
    iter_hash_entries,
    manifest_fingerprint,
)


@pytest.mark.unit
def test_hash_manifest_create_and_compare_pass(tmp_path: Path) -> None:
    root = tmp_path / "data"
    (root / "nested").mkdir(parents=True)
    file_a = root / "nested" / "a.txt"
    file_b = root / "b.txt"
    file_a.write_text("alpha", encoding="utf-8")
    file_b.write_text("beta", encoding="utf-8")
    source_manifest = tmp_path / "source.jsonl"
    dest_manifest = tmp_path / "dest.jsonl"
    create_manifest(root=root, output=source_manifest)
    create_manifest(root=root, output=dest_manifest)
    report_path = tmp_path / "compare.json"
    report = compare_manifests(
        source=source_manifest,
        destination=dest_manifest,
        output=report_path,
    )
    assert report["verdict"] == "PASS"
    assert report["missing"] == []
    assert report["extra"] == []
    assert report["mismatched"] == []


@pytest.mark.unit
def test_hash_manifest_detects_missing_and_extra(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    (source_root / "only_source.txt").write_text("x", encoding="utf-8")
    (dest_root / "only_dest.txt").write_text("y", encoding="utf-8")
    source_manifest = tmp_path / "source.jsonl"
    dest_manifest = tmp_path / "dest.jsonl"
    create_manifest(root=source_root, output=source_manifest)
    create_manifest(root=dest_root, output=dest_manifest)
    report = compare_manifests(
        source=source_manifest,
        destination=dest_manifest,
        output=tmp_path / "compare.json",
    )
    assert report["verdict"] == "FAIL"
    assert report["missing"]
    assert report["extra"]


@pytest.mark.unit
def test_hash_manifest_detects_mismatch(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    dest_root = tmp_path / "dest"
    source_root.mkdir()
    dest_root.mkdir()
    (source_root / "same.txt").write_text("one", encoding="utf-8")
    (dest_root / "same.txt").write_text("two", encoding="utf-8")
    source_manifest = tmp_path / "source.jsonl"
    dest_manifest = tmp_path / "dest.jsonl"
    create_manifest(root=source_root, output=source_manifest)
    create_manifest(root=dest_root, output=dest_manifest)
    report = compare_manifests(
        source=source_manifest,
        destination=dest_manifest,
        output=tmp_path / "compare.json",
    )
    assert report["verdict"] == "FAIL"
    assert report["mismatched"]


@pytest.mark.unit
def test_hash_manifest_reparse_point_blocks(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("symlinks unavailable")
    root = tmp_path / "data"
    root.mkdir()
    real = tmp_path / "real.txt"
    real.write_text("x", encoding="utf-8")
    link = root / "link.txt"
    link.symlink_to(real)
    with pytest.raises(RelocateHashError, match="reparse point"):
        list(iter_hash_entries(root))


@pytest.mark.unit
def test_hash_manifest_deterministic_fingerprint(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    (root / "a.txt").write_text("a", encoding="utf-8")
    entries_a = sorted(iter_hash_entries(root), key=lambda item: item.relative_path)
    entries_b = sorted(iter_hash_entries(root), key=lambda item: item.relative_path)
    assert manifest_fingerprint(entries_a) == manifest_fingerprint(entries_b)


@pytest.mark.unit
def test_hash_manifest_access_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "data"
    root.mkdir()
    blocked = root / "blocked.txt"
    blocked.write_text("x", encoding="utf-8")

    original_stat = Path.stat

    def _fail_stat(self: Path, *args, **kwargs):  # noqa: ANN002, ANN003
        if self == blocked:
            raise OSError("access denied")
        return original_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", _fail_stat)
    with pytest.raises(RelocateHashError, match="access error"):
        list(iter_hash_entries(root))
