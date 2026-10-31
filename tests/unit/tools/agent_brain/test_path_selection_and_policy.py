"""Unit tests for Claire Agent Brain path selection and Claire-owned policy."""

from __future__ import annotations

import pytest

from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.path_selection import (
    ConsumerPath,
    resolve_consumer_path,
    select_consumer_path,
)
from tools.agent_brain.policy import assert_claire_consumer_policy

pytestmark = pytest.mark.unit


def test_default_path_is_legacy() -> None:
    path = resolve_consumer_path(config={"consumer_path": "legacy"}, env={})
    assert path is ConsumerPath.LEGACY


def test_env_override_selects_agent_brain() -> None:
    path = resolve_consumer_path(
        config={"consumer_path": "legacy"},
        env={"CDB_AGENT_BRAIN_CONSUMER_PATH": "agent_brain"},
    )
    assert path is ConsumerPath.AGENT_BRAIN


def test_explicit_rollback_to_legacy() -> None:
    assert select_consumer_path(desired="legacy") is ConsumerPath.LEGACY


def test_unknown_path_fail_closed() -> None:
    with pytest.raises(ConsumerError) as exc:
        resolve_consumer_path(explicit="dual_run")
    assert exc.value.code is ConsumerErrorCode.UNSUPPORTED_PATH


def test_claire_policy_blocks_live_scope() -> None:
    with pytest.raises(ConsumerError) as exc:
        assert_claire_consumer_policy(target_scope="echtgeld")
    assert exc.value.code is ConsumerErrorCode.POLICY_BLOCKED


def test_claire_policy_blocks_memory_writes() -> None:
    with pytest.raises(ConsumerError) as exc:
        assert_claire_consumer_policy(target_scope="issue:13", allow_memory_writes=True)
    assert exc.value.code is ConsumerErrorCode.POLICY_BLOCKED


def test_select_agent_brain_rejects_live_flag_in_config() -> None:
    with pytest.raises(ConsumerError) as exc:
        select_consumer_path(
            desired="agent_brain",
            config={"allow_live_or_echtgeld": True},
        )
    assert exc.value.code is ConsumerErrorCode.POLICY_BLOCKED
