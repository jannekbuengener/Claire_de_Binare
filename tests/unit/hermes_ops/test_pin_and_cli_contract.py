"""Pin-check and mint CLI contracts (#4289 / #4327)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.hermes_ops.__main__ import main

pytestmark = [pytest.mark.unit]

_COMMIT = "cc4cab2f592e60a197e796506de9168f74baf3ea"
_SHA = "ab3e6ae1a1bda828941df8911ae44ed5de68412805124f338f157aa0360eb660"
_BOUND_URL = (
    f"https://raw.githubusercontent.com/NousResearch/hermes-agent/"
    f"{_COMMIT}/scripts/install.sh"
)


def _write_pin(tmp_path: Path, hermes_block: str) -> None:
    pin_dir = tmp_path / "infrastructure" / "hermes"
    pin_dir.mkdir(parents=True)
    (pin_dir / "VERSION_PIN.yaml").write_text(
        "schema_version: cdb.hermes.version_pin/v1\n" f"hermes:\n{hermes_block}",
        encoding="utf-8",
    )


def test_pin_check_require_pinned_passes_with_filled_pin(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True
    assert out["missing_fields"] == []
    assert out["contract_errors"] == []
    assert out["git_ref"]
    assert out["install_url"].startswith("https://")
    assert _COMMIT in out["install_url"]
    assert out["install_url"].endswith("/scripts/install.sh")


def test_pin_check_empty_pin_fails_require_pinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_pin(
        tmp_path,
        '  git_ref: ""\n'
        '  git_commit: ""\n'
        '  install_script_sha256: ""\n'
        '  install_url: ""\n',
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["ok"] is False
    assert "hermes.git_ref" in out["missing_fields"]


def test_pin_check_rejects_floating_cdn_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_pin(
        tmp_path,
        f'  git_ref: "v2026.7.30"\n'
        f'  git_commit: "{_COMMIT}"\n'
        f'  install_script_sha256: "{_SHA}"\n'
        '  install_url: "https://hermes-agent.nousresearch.com/install.sh"\n',
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert out["ok"] is False
    assert "hermes.install_url_floating_cdn_forbidden" in out["contract_errors"]


def test_pin_check_rejects_url_commit_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    other = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    _write_pin(
        tmp_path,
        f'  git_ref: "v2026.7.30"\n'
        f'  git_commit: "{_COMMIT}"\n'
        f'  install_script_sha256: "{_SHA}"\n'
        f'  install_url: "https://raw.githubusercontent.com/NousResearch/'
        f'hermes-agent/{other}/scripts/install.sh"\n',
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "hermes.install_url_missing_git_commit" in out["contract_errors"]


def test_pin_check_rejects_malformed_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_pin(
        tmp_path,
        f'  git_ref: "v2026.7.30"\n'
        f'  git_commit: "{_COMMIT}"\n'
        '  install_script_sha256: "not-a-sha"\n'
        f'  install_url: "{_BOUND_URL}"\n',
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "hermes.install_script_sha256_malformed" in out["contract_errors"]


def test_pin_check_rejects_malformed_git_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_pin(
        tmp_path,
        '  git_ref: "v2026.7.30"\n'
        '  git_commit: "deadbeef"\n'
        f'  install_script_sha256: "{_SHA}"\n'
        f'  install_url: "{_BOUND_URL}"\n',
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "hermes.git_commit_malformed" in out["contract_errors"]


def test_pin_check_accepts_commit_bound_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_pin(
        tmp_path,
        f'  git_ref: "v2026.7.30"\n'
        f'  git_commit: "{_COMMIT}"\n'
        f'  install_script_sha256: "{_SHA}"\n'
        f'  install_url: "{_BOUND_URL}"\n',
    )
    monkeypatch.chdir(tmp_path)
    code = main(["pin-check", "--require-pinned"])
    out = json.loads(capsys.readouterr().out)
    assert code == 0
    assert out["ok"] is True
    assert out["contract_errors"] == []
    assert out["install_url"] == _BOUND_URL


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
