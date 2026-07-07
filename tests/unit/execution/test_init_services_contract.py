"""Execution init_services and live confirmation contract (#3835)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from services.execution import config, service

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_require_live_confirmation_allows_mock_trading_default() -> None:
    with patch.object(config, "MOCK_TRADING", True), patch.object(
        config, "DRY_RUN", True
    ), patch.object(config, "MEXC_TESTNET", False):
        service._require_live_confirmation()


def test_require_live_confirmation_blocks_live_without_confirm(monkeypatch) -> None:
    monkeypatch.delenv("CONFIRM_LIVE_TRADING", raising=False)
    with patch.object(config, "MOCK_TRADING", False), patch.object(
        config, "DRY_RUN", False
    ), patch.object(config, "MEXC_TESTNET", False):
        with pytest.raises(SystemExit):
            service._require_live_confirmation()


def test_init_services_selects_mock_executor_when_mock_trading_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_pubsub = MagicMock()
    mock_redis.pubsub.return_value = mock_pubsub
    mock_executor = MagicMock()

    monkeypatch.setattr(config, "MOCK_TRADING", True)
    monkeypatch.setattr(service, "redis_client", None)
    monkeypatch.setattr(service, "pubsub", None)
    monkeypatch.setattr(service, "executor", None)
    monkeypatch.setattr(service, "db", None)

    with patch("services.execution.service.redis.Redis", return_value=mock_redis), patch(
        "services.execution.service.build_execution_adapter",
        return_value=mock_executor,
    ) as build_adapter, patch("services.execution.service.Database") as db_cls:
        db_cls.return_value = MagicMock()
        service.init_services()
        build_adapter.assert_called_once()
        assert service.executor is mock_executor
