"""Pin-check and mint CLI contracts (#4289)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.hermes_ops.__main__ import main

pytestmark = [pytest.mark.unit]


def test_pin_check_require_pinned_passes_with_filled_pin(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True
    assert out["missing_fields"] == []
    assert out["git_ref"]


def test_pin_check_empty_pin_fails_require_pinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    pin_dir = tmp_path / "infrastructure" / "hermes"
    pin_dir.mkdir(parents=True)
    (pin_dir / "VERSION_PIN.yaml").write_text(
        'schema_version: cdb.hermes.version_pin/v1\nhermes:\n  git_ref: ""\n'
        '  git_commit: ""\n  install_script_sha256: ""\n  install_url: ""\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["ok"] is False
    assert "hermes.git_ref" in out["missing_fields"]


def test_mint_token_live_requires_token_file(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # dry-run ok without token-file
    code = main(["mint-token", "--profile", "cdb-engineer", "--dry-run"])
    assert code == 0
    _ = capsys.readouterr()
    # live without token-file must fail closed (no stdout token)
    code = main(["mint-token", "--profile", "cdb-engineer"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["error"] == "token_file_required"
    assert "token" not in out or out.get("token") in (None, "[REDACTED]")
