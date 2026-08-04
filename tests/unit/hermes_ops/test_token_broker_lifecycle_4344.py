"""Token broker systemd lifecycle contract (#4289 / PR #4344)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ci.publisher.app_auth import AuthenticationError
from tools.hermes_ops.profile_users import (
    FORBIDDEN_TOKEN_CONSUMERS,
    assert_token_consumer_allowed,
    token_file_path,
)
from tools.hermes_ops.systemd_contract import validate_broker_unit
from tools.hermes_ops.token_broker import (
    assert_app_compatible_for_hermes_write,
    metadata_only,
    resolve_hermes_app_id,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

UNIT = Path("infrastructure/hermes/systemd/hermes-github-token.service")


def test_broker_unit_remain_after_exit_keeps_token_until_stop() -> None:
    """Oneshot mint must stay active so /run token survives until systemctl stop."""
    text = UNIT.read_text(encoding="utf-8")
    assert "Type=oneshot" in text
    assert "RemainAfterExit=yes" in text
    assert "ExecStart=" in text and "mint-token" in text
    assert "--token-file /run/hermes/cdb-engineer/token" in text
    assert "ExecStopPost=+/bin/rm -f /run/hermes/cdb-engineer/token" in text
    assert "ExecStartPost=+/bin/chown hermes-cdb-engineer:hermes-cdb-engineer" in text
    assert validate_broker_unit() == []


def test_broker_validator_requires_remain_after_exit(tmp_path: Path) -> None:
    raw = UNIT.read_text(encoding="utf-8").replace("RemainAfterExit=yes\n", "")
    bad = tmp_path / "hermes-github-token.service"
    bad.write_text(raw, encoding="utf-8")
    errors = validate_broker_unit(bad)
    assert any("RemainAfterExit=yes" in e for e in errors)


def test_broker_validator_requires_exec_stop_post_token_rm(tmp_path: Path) -> None:
    raw = UNIT.read_text(encoding="utf-8").replace(
        "ExecStopPost=+/bin/rm -f /run/hermes/cdb-engineer/token\n",
        "",
    )
    bad = tmp_path / "hermes-github-token.service"
    bad.write_text(raw, encoding="utf-8")
    errors = validate_broker_unit(bad)
    assert any("ExecStopPost=" in e for e in errors)


def test_token_path_available_only_to_engineer_consumer() -> None:
    assert token_file_path() == "/run/hermes/cdb-engineer/token"
    assert_token_consumer_allowed("hermes-cdb-engineer")
    assert "hermes-jannek-assistant" in FORBIDDEN_TOKEN_CONSUMERS
    with pytest.raises(PermissionError):
        assert_token_consumer_allowed("hermes-jannek-assistant")


def test_app_id_4410232_still_rejected_for_hermes_mint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_GH_APP_ID", "4410232")
    with pytest.raises(AuthenticationError, match="4410232"):
        resolve_hermes_app_id()
    with pytest.raises(AuthenticationError, match="4410232"):
        assert_app_compatible_for_hermes_write(app_id=4410232)


def test_metadata_and_unit_never_embed_live_token_values() -> None:
    preview = metadata_only("cdb-engineer")
    blob = str(preview)
    assert "ghs_" not in blob
    assert "eyJ" not in blob
    unit = UNIT.read_text(encoding="utf-8")
    assert "ghs_" not in unit
    assert "BEGIN " not in unit
    # Journal must carry redacted marker path only via mint CLI contract.
    assert preview.get("token_file") == "/run/hermes/cdb-engineer/token"
    assert preview.get("reuse_cdb_local_ci_app") is False
