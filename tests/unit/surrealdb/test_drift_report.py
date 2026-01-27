"""Unit tests for SurrealDB drift report."""
from pathlib import Path

import pytest

from tools.surrealdb.drift_report import compute_drift, render_report


@pytest.mark.unit
def test_drift_report_added_changed_removed(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs"
    docs_root.mkdir()

    file_a = docs_root / "a.md"
    file_b = docs_root / "b.md"
    file_d = docs_root / "d.md"
    file_a.write_text("alpha", encoding="utf-8")
    file_b.write_text("beta", encoding="utf-8")
    file_d.write_text("delta", encoding="utf-8")

    git_docs = {
        "a.md": "hash-a",
        "b.md": "hash-b",
        "d.md": "hash-d",
    }
    snapshot = {
        "a.md": "hash-a",
        "b.md": "hash-old",
        "c.md": "hash-c",
    }

    result = compute_drift(git_docs, snapshot)
    report = render_report(result, git_docs, snapshot)

    assert result.added == ["d.md"]
    assert result.changed == ["b.md"]
    assert result.removed == ["c.md"]
    assert "Added: 1" in report
    assert "Changed: 1" in report
    assert "Removed: 1" in report
