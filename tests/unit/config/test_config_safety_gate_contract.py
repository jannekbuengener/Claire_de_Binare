"""Config, feature flags and live-trading safety gate contract tests (#3837).

No live secrets, no deployment changes, no Live-Go derivation from config alone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.config.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
    FeatureFlagState,
    is_feature_enabled,
)
from core.config.trading_mode import TradingMode, get_trading_mode, validate_trading_mode
from services.signal.service import _build_config_hash, _build_runtime_config_snapshot
from services.signal.config import SignalConfig

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_LR_AUDIT = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "live-readiness"
    / "LR-AUDIT-STATUS-2026-03-05.md"
)


def test_default_trading_mode_is_paper_without_live_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRADING_MODE", raising=False)
    monkeypatch.delenv("LIVE_TRADING_CONFIRMED", raising=False)
    assert get_trading_mode(require_confirmation=True) == TradingMode.PAPER


def test_live_mode_requires_explicit_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADING_MODE", "live")
    monkeypatch.delenv("LIVE_TRADING_CONFIRMED", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        get_trading_mode(require_confirmation=True)
    assert exc_info.value.code == 1


def test_invalid_trading_mode_env_fails_safe_to_paper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRADING_MODE", "definitely_not_a_mode")
    assert get_trading_mode(require_confirmation=False) == TradingMode.PAPER


def test_live_mode_never_implied_from_paper_config_validation() -> None:
    assert validate_trading_mode(TradingMode.PAPER) is True
    assert TradingMode.PAPER.is_safe is True
    assert TradingMode.PAPER.requires_confirmation is False


def test_lr_audit_status_remains_no_go_in_canon() -> None:
    body = _LR_AUDIT.read_text(encoding="utf-8")
    assert "NO-GO" in body
    assert "Live-Go" not in body or "kein Live-Go" in body or "NO-GO" in body


def test_feature_flag_unknown_defaults_disabled(tmp_path: Path) -> None:
    config_path = tmp_path / "feature_flags.json"
    config_path.write_text("{}", encoding="utf-8")
    manager = FeatureFlagManager(config_path=str(config_path))
    assert manager.is_enabled("nonexistent_flag") is False
    assert is_feature_enabled("nonexistent_flag") is False


def test_feature_flag_respects_environment_gate(tmp_path: Path) -> None:
    config_path = tmp_path / "feature_flags.json"
    config_path.write_text(
        json.dumps(
            {
                "shadow_only": {
                    "state": "enabled",
                    "description": "shadow path",
                    "environments": ["staging"],
                }
            }
        ),
        encoding="utf-8",
    )
    manager = FeatureFlagManager(config_path=str(config_path))
    manager.environment = "development"
    assert manager.is_enabled("shadow_only") is False
    manager.environment = "staging"
    assert manager.is_enabled("shadow_only") is True


def test_feature_flag_rollout_is_deterministic_for_user_id(tmp_path: Path) -> None:
    config_path = tmp_path / "feature_flags.json"
    config_path.write_text(
        json.dumps(
            {
                "gradual": {
                    "state": "rollout",
                    "description": "rollout",
                    "rollout_percentage": 50.0,
                    "environments": ["development"],
                }
            }
        ),
        encoding="utf-8",
    )
    manager = FeatureFlagManager(config_path=str(config_path))
    first = manager.is_enabled("gradual", user_id="user-abc")
    second = manager.is_enabled("gradual", user_id="user-abc")
    assert first == second


def test_config_hash_stable_for_identical_runtime_snapshot() -> None:
    config = SignalConfig()
    snapshot = _build_runtime_config_snapshot(config)
    assert _build_config_hash(snapshot) == _build_config_hash(dict(snapshot))


def test_config_hash_changes_when_strategy_threshold_changes() -> None:
    config = SignalConfig()
    base = _build_runtime_config_snapshot(config)
    changed = dict(base)
    changed["threshold_pct"] = float(base.get("threshold_pct", 0.0)) + 0.01
    assert _build_config_hash(base) != _build_config_hash(changed)


def test_validate_live_mode_error_does_not_echo_credential_values() -> None:
    with pytest.raises(ValueError, match="requires API credentials") as exc_info:
        validate_trading_mode(TradingMode.LIVE, api_key="visible-key", api_secret=None)
    assert "visible-key" not in str(exc_info.value)
