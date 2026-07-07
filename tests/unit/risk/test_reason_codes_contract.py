"""Reason code stability contract (#3834)."""

from __future__ import annotations

import inspect

import pytest

from services.risk import reason_codes
from services.risk import service as risk_service

from tests.contract.test_decision_contract import _base_inputs

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_EXPECTED_CODES = {
    "RC_001",
    "RC_002",
    "RC_003",
    "RC_004",
    "RC_010",
    "RC_020",
    "RC_021",
    "RC_022",
}


def test_reason_codes_are_stable_and_unique() -> None:
    exported = {
        name
        for name, value in inspect.getmembers(reason_codes)
        if name.startswith("RC_") and isinstance(value, str)
    }
    assert exported == _EXPECTED_CODES
    values = [getattr(reason_codes, name) for name in exported]
    assert len(values) == len(set(values))


def test_reason_code_docstrings_agent_readable() -> None:
    for name in sorted(_EXPECTED_CODES):
        value = getattr(reason_codes, name)
        assert value == name
        assert reason_codes.__doc__ is not None


def test_decide_trade_returns_known_reason_codes_only() -> None:
    now_ms, signal, market_state, account_state, market_health = _base_inputs()
    market_state["regime_id"] = 2
    _, reason_code, _ = risk_service.decide_trade(
        signal, market_state, account_state, market_health, now_ms
    )
    assert reason_code in _EXPECTED_CODES
