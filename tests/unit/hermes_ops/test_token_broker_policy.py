"""Token broker + capability policy tests (#4289)."""

from __future__ import annotations

import pytest

from ci.publisher.app_auth import AuthenticationError
from tools.hermes_ops.policy import (
    assert_action_allowed,
    omnipotent_combination_forbidden,
)
from tools.hermes_ops.token_broker import (
    build_mint_body,
    metadata_only,
    mint_profile_token,
)

pytestmark = [pytest.mark.unit]


def test_cdb_engineer_mint_dry_run_metadata() -> None:
    token, meta = mint_profile_token("cdb-engineer", dry_run=True)
    assert token is None
    assert meta.repositories == ("Claire_de_Binare",)  # pragma: allowlist secret
    assert meta.permissions.get("contents") == "write"
    assert "checks" not in meta.permissions
    preview = metadata_only("cdb-engineer")
    assert preview["reuses_auth_lineage"] == ["4170", "4195"]


def test_jannek_assistant_cannot_mint() -> None:
    with pytest.raises(AuthenticationError):
        build_mint_body("jannek-assistant")


def test_forbidden_actions_denied_for_engineer() -> None:
    for action in (
        "publish_cdb_local_ci",
        "admin_merge",
        "force_push",
        "edit_branch_protection",
        "live_trade",
    ):
        verdict = assert_action_allowed("cdb-engineer", action)
        assert verdict.ok is False, action


def test_personal_windows_shell_denied() -> None:
    verdict = assert_action_allowed("jannek-assistant", "windows_shell")
    assert verdict.ok is False


def test_omnipotent_combination_guard() -> None:
    assert omnipotent_combination_forbidden({"personal_memory", "github_admin"})
    assert not omnipotent_combination_forbidden({"personal_memory"})
