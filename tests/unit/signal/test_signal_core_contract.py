"""Signal core contract tests (#3833)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_services_signal = Path(__file__).resolve().parents[3] / "services" / "signal"
if str(_services_signal) not in sys.path:
    sys.path.insert(0, str(_services_signal))

from config import SignalConfig  # noqa: E402
from service import (  # noqa: E402
    SignalEngine,
    _build_config_hash,
    _build_runtime_config_snapshot,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _primary_config(**overrides) -> SignalConfig:
    base = {
        "strategy_id": "primary_breakout_v1",
        "symbol": "BTCUSDT",
        "threshold_pct": 3.0,
        "lookback_minutes": 15,
        "min_volume": 100000.0,
    }
    base.update(overrides)
    return SignalConfig(**base)


def test_config_hash_deterministic_for_runtime_snapshot() -> None:
    config = _primary_config()
    first = _build_config_hash(_build_runtime_config_snapshot(config))
    second = _build_config_hash(_build_runtime_config_snapshot(config))
    assert first == second
    assert len(first) == 64


@pytest.mark.parametrize("threshold", [2.5, 3.0, 4.0])
def test_config_hash_changes_when_strategy_parameter_changes(threshold: float) -> None:
    hashes = {
        _build_config_hash(
            _build_runtime_config_snapshot(_primary_config(threshold_pct=threshold))
        )
        for threshold in [2.5, 3.0, 4.0]
    }
    assert len(hashes) == 3


def test_unknown_adapter_id_fails_closed_at_engine_init(monkeypatch) -> None:
    monkeypatch.setenv("SIGNAL_ADAPTER_ID", "not_a_real_adapter")
    test_config = _primary_config(strategy_id="test_strategy")
    with patch("service.config", test_config):
        with pytest.raises(KeyError, match="Unknown strategy adapter id"):
            SignalEngine()


@pytest.mark.parametrize(
    "strategy_id",
    ["primary_breakout_v1", "donchian_breakout_v1"],
)
def test_canonical_strategy_ids_accept_engine_init(strategy_id: str, monkeypatch) -> None:
    monkeypatch.delenv("SIGNAL_ADAPTER_ID", raising=False)
    test_config = _primary_config(strategy_id=strategy_id)
    with patch("service.config", test_config):
        engine = SignalEngine()
        assert engine is not None
