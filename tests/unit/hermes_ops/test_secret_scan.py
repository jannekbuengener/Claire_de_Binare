"""Secret leak scanner tests for Hermes repo surfaces (#4289)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.hermes_ops.secret_scan import Finding, scan_paths

pytestmark = [pytest.mark.unit]


def test_hermes_surfaces_have_no_secret_findings() -> None:
    findings = scan_paths()
    assert findings == [], findings


def test_scanner_detects_pem_and_token_in_temp(tmp_path: Path) -> None:
    dirty = tmp_path / "leak.yaml"
    dirty.write_text(
        "token: ghp_abcdefghijklmnopqrstuvwxyz0123456789\n"
        "-----BEGIN PRIVATE KEY-----\nABCD\n-----END PRIVATE KEY-----\n",
        encoding="utf-8",
    )
    findings = scan_paths((dirty,))
    kinds = {f.kind for f in findings}
    assert "secret_pattern" in kinds
    assert all(isinstance(f, Finding) for f in findings)
