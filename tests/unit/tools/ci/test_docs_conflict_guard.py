"""Unit tests for docs_conflict_guard path excludes (parity with workflow)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.ci.docs_conflict_guard import EXCLUDE_RE, iter_scan_files

pytestmark = pytest.mark.unit


def test_exclude_re_matches_entire_docs_archive():
    assert EXCLUDE_RE.search("docs/archive/old.md")
    assert EXCLUDE_RE.search("docs/archive/nested/file.yaml")
    assert not EXCLUDE_RE.search("docs/ci/local-status-publisher.md")
    assert not EXCLUDE_RE.search("docs/runbooks/merge_policy_ci_gate.md")


def test_iter_scan_files_skips_docs_archive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "keep.md").write_text("# keep\n", encoding="utf-8")
    archive = tmp_path / "docs" / "archive"
    archive.mkdir()
    (archive / "legacy.md").write_text("<<<<<<< HEAD\n", encoding="utf-8")
    files = iter_scan_files(tmp_path)
    rels = [p.relative_to(tmp_path).as_posix() for p in files]
    assert "docs/keep.md" in rels
    assert "docs/archive/legacy.md" not in rels
