"""Fixture-based main runtime flow contract tests (#3838).

Synthetic market → regime context → signal → risk → paper execution.
No Docker, network, DB, or live services.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.utils.redis_payload import sanitize_market_data
from services.execution.models import OrderStatus
from services.risk import service as risk_service

from tests.unit.runtime._main_runtime_flow_helpers import (
    base_flow_inputs,
    evaluate_risk_gate,
    simulate_paper_execution,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "runtime_flow"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_happy_path_market_to_paper_execution_chain() -> None:
    now_ms, signal, market_state, account_state, market_health = base_flow_inputs()
    market_payload = _load_fixture("market_tick_happy.json")
    sanitized = sanitize_market_data(market_payload)
    assert sanitized["symbol"] == "BTCUSDT"

    decision, reason_code = evaluate_risk_gate(
        now_ms=now_ms,
        signal=signal,
        market_state=market_state,
        account_state=account_state,
        market_health=market_health,
    )
    assert decision == risk_service.DECISION_ALLOW
    assert reason_code is None

    result = simulate_paper_execution(signal)
    assert result.status == OrderStatus.FILLED.value
    assert result.metadata["mode"] == "paper"
    assert result.metadata["signal_id"] == signal["signal_id"]


def test_stale_data_blocks_before_execution() -> None:
    now_ms, signal, market_state, account_state, market_health = base_flow_inputs()
    stale = _load_fixture("stale_context.json")
    signal["ts_ms"] = stale["signal_ts_ms"]
    market_state["ts_ms"] = stale["market_state_ts_ms"]
    account_state["ts_ms"] = stale["account_state_ts_ms"]
    market_health["ts_ms"] = stale["market_health_ts_ms"]

    decision, reason_code = evaluate_risk_gate(
        now_ms=now_ms,
        signal=signal,
        market_state=market_state,
        account_state=account_state,
        market_health=market_health,
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_003"


def test_risk_blocked_regime_prevents_execution() -> None:
    now_ms, signal, market_state, account_state, market_health = base_flow_inputs()
    market_state["regime_id"] = _load_fixture("blocked_regime.json")["regime_id"]

    decision, reason_code = evaluate_risk_gate(
        now_ms=now_ms,
        signal=signal,
        market_state=market_state,
        account_state=account_state,
        market_health=market_health,
    )
    assert decision == risk_service.DECISION_BLOCK
    assert reason_code == "RC_001"


def test_invalid_execution_payload_rejected_by_execution_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.execution import service

    monkeypatch.setattr(
        "core.safety.kill_switch.get_kill_switch_details",
        lambda create_if_missing=False: (False, "inactive", None, None),
    )
    monkeypatch.setattr(service, "executor", None)
    monkeypatch.setattr(service, "db", None)
    monkeypatch.setattr(service, "_publish_result", lambda _r: None)

    invalid = _load_fixture("invalid_execution_order.json")
    result = service.process_order(invalid)
    assert result is None
    assert service.stats["invalid_payloads"] >= 1


def test_flow_docs_reference_core_runtime_eventflow() -> None:
    doc = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "onboarding"
        / "core-eventflows"
        / "core_runtime_eventflow.md"
    )
    body = doc.read_text(encoding="utf-8")
    for anchor in ("cdb_market", "cdb_risk", "cdb_execution", "cdb_signal"):
        assert anchor in body
