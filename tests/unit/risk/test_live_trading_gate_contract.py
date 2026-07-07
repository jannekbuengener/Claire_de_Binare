"""Live trading gate contract tests (#3834).

Mocked — no real validation fetcher or live trading authorization.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.risk.live_trading_gate import AuthorizationLevel, LiveTradingGate

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_check_authorization_denied_without_test_results(monkeypatch) -> None:
    gate = LiveTradingGate()
    monkeypatch.setattr(gate, "_load_latest_test_results", lambda _sid: None)
    result = gate.check_authorization("test-system")
    assert result["authorization_level"] == AuthorizationLevel.DENIED.value
    assert "No test results" in result["reason"]


def test_paper_only_when_validation_incomplete(monkeypatch) -> None:
    gate = LiveTradingGate()
    monkeypatch.setattr(
        gate,
        "_load_latest_test_results",
        lambda _sid: {
            "test_completed": False,
            "duration_hours": 0,
            "validation_result": {"overall_pass": False, "reason": "incomplete"},
        },
    )
    result = gate.check_authorization("test-system")
    assert result["authorization_level"] in {
        AuthorizationLevel.DENIED.value,
        AuthorizationLevel.PAPER_ONLY.value,
    }


def test_authorization_cache_reused_when_valid() -> None:
    gate = LiveTradingGate()
    gate.authorization_cache["cached-system"] = gate._create_authorization_response(
        AuthorizationLevel.PAPER_ONLY,
        "cached",
    )
    loader = MagicMock(return_value=None)
    gate._load_latest_test_results = loader
    gate.check_authorization("cached-system")
    loader.assert_not_called()
