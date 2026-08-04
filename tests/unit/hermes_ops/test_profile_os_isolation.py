"""OS profile UID isolation + token delivery contracts (#4289 B2.0)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.hermes_ops.profile_users import (
    FORBIDDEN_TOKEN_CONSUMERS,
    PEM_HOST_PATH,
    PROFILE_LINUX_USERS,
    SHARED_INSTALL_USER,
    TOKEN_RUNTIME_DIR,
    assert_token_consumer_allowed,
    expected_dashboard_user_line,
    linux_user_for_profile,
    profile_home,
    profile_log_dir,
    token_file_path,
)
from tools.hermes_ops.systemd_contract import validate_broker_unit, validate_unit
from tools.hermes_ops.token_broker import (
    assert_app_compatible_for_hermes_write,
    assert_token_file_path_allowed,
    mint_profile_token,
)
from ci.publisher.app_auth import AuthenticationError

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_profiles_map_to_distinct_linux_users() -> None:
    users = {linux_user_for_profile(p) for p in ("jannek-assistant", "cdb-engineer")}
    assert users == {"hermes-jannek-assistant", "hermes-cdb-engineer"}
    assert SHARED_INSTALL_USER not in users
    assert (
        PROFILE_LINUX_USERS["jannek-assistant"] != PROFILE_LINUX_USERS["cdb-engineer"]
    )


def test_dashboard_unit_uses_per_instance_user_not_shared_hermes() -> None:
    errors = validate_unit()
    assert errors == [], errors
    text = Path("infrastructure/hermes/systemd/hermes-dashboard@.service").read_text(
        encoding="utf-8"
    )
    assert "User=hermes-%i" in text
    assert "Group=hermes-%i" in text
    assert "User=hermes\n" not in text.replace("User=hermes-%i", "")
    assert "Group=hermes\n" not in text.replace("Group=hermes-%i", "")
    assert "/var/log/hermes/%i" in text
    for profile in ("jannek-assistant", "cdb-engineer"):
        assert expected_dashboard_user_line(profile) == "User=hermes-%i"


def test_broker_unit_is_root_oneshot_with_isolated_runtime_dir() -> None:
    errors = validate_broker_unit()
    assert errors == [], errors
    text = Path("infrastructure/hermes/systemd/hermes-github-token.service").read_text(
        encoding="utf-8"
    )
    assert "Type=oneshot" in text
    assert "RemainAfterExit=yes" in text
    assert "ExecStopPost=+/bin/rm -f /run/hermes/cdb-engineer/token" in text
    assert "ExecStartPost=+/bin/chown -R hermes-cdb-engineer:hermes-cdb-engineer" in text
    assert "ProtectSystem=" not in text
    assert not any(
        line.strip() == "NoNewPrivileges=true" for line in text.splitlines()
    )
    assert "User=root" in text
    assert TOKEN_RUNTIME_DIR in text or "RuntimeDirectory=hermes/cdb-engineer" in text
    assert PEM_HOST_PATH in text or "cdb-hermes-engineer.pem" in text


def test_token_path_contract() -> None:
    assert token_file_path() == f"{TOKEN_RUNTIME_DIR}/token"
    assert_token_file_path_allowed(token_file_path())
    with pytest.raises(AuthenticationError):
        assert_token_file_path_allowed("/var/lib/hermes/profiles/cdb-engineer/token")
    with pytest.raises(AuthenticationError):
        assert_token_file_path_allowed("/tmp/hermes.token")


def test_forbidden_token_consumers() -> None:
    assert "hermes-jannek-assistant" in FORBIDDEN_TOKEN_CONSUMERS
    assert "hermes" in FORBIDDEN_TOKEN_CONSUMERS
    with pytest.raises(PermissionError):
        assert_token_consumer_allowed("hermes-jannek-assistant")
    with pytest.raises(PermissionError):
        assert_token_consumer_allowed("hermes")
    assert_token_consumer_allowed("hermes-cdb-engineer")


def test_other_profile_cannot_mint_token() -> None:
    with pytest.raises(AuthenticationError):
        mint_profile_token("jannek-assistant", dry_run=True)


def test_app_4410232_rejected_in_direct_python_call() -> None:
    with pytest.raises(AuthenticationError, match="4410232"):
        assert_app_compatible_for_hermes_write(app_id=4410232)


def test_profile_paths_are_partitioned() -> None:
    assert profile_home("cdb-engineer") == "/var/lib/hermes/profiles/cdb-engineer"
    assert profile_log_dir("jannek-assistant") == "/var/log/hermes/jannek-assistant"
    assert profile_home("cdb-engineer") != profile_home("jannek-assistant")


def test_migrate_script_creates_dedicated_users() -> None:
    text = Path("infrastructure/hermes/hetzner/migrate-profile-uids.sh").read_text(
        encoding="utf-8"
    )
    assert "hermes-cdb-engineer" in text
    assert "hermes-jannek-assistant" in text
    assert "useradd" in text
    assert "/usr/sbin/nologin" in text or "nologin" in text
    assert "chown" in text
    assert "HOLD_PROFILE_OS_ISOLATION" in text or "fail" in text.lower()


def test_bootstrap_uses_per_profile_linux_users() -> None:
    text = Path("infrastructure/hermes/hetzner/bootstrap.sh").read_text(
        encoding="utf-8"
    )
    assert "hermes-cdb-engineer" in text
    assert "hermes-jannek-assistant" in text
    assert "User=hermes-%i" in Path(
        "infrastructure/hermes/systemd/hermes-dashboard@.service"
    ).read_text(encoding="utf-8")


def test_bootstrap_mirrors_migrate_traverse_perms_for_dedicated_uids() -> None:
    """Greenfield bootstrap must encode live B2.0 traverse fixes (not migrate-only)."""
    bootstrap = Path("infrastructure/hermes/hetzner/bootstrap.sh").read_text(
        encoding="utf-8"
    )
    migrate = Path("infrastructure/hermes/hetzner/migrate-profile-uids.sh").read_text(
        encoding="utf-8"
    )
    cloud_init = Path("infrastructure/hermes/hetzner/cloud-init.yaml").read_text(
        encoding="utf-8"
    )
    assert "apply_dedicated_uid_traverse_perms" in bootstrap
    assert 'chmod 0751 "${HERMES_BASE}"' in bootstrap
    assert "chmod 0751 /home/hermes" in bootstrap
    assert "find" in bootstrap and "a+rx" in bootstrap
    assert "/home/hermes/.local/share/uv" in bootstrap
    assert 'chmod 0751 "${HERMES_BASE}"' in migrate
    assert "chmod 0751" in cloud_init
    assert "chmod 0750 /opt/hermes /var/lib/hermes" not in cloud_init
