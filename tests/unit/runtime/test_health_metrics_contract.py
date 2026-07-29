"""Health, metrics and observability contract tests (#3839).

No external monitoring stack; Flask test clients only.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest

import services.market.service as market_svc
import services.risk.service as risk_svc
from services.execution import service as execution_svc

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_LIVE_GO_MARKERS = (
    "live_go",
    "live-go",
    "echtgeld_go",
    "production_ready",
    "lr_go",
)


@pytest.fixture(autouse=True)
def _reset_market_state():
    with market_svc._cache_lock:
        market_svc._cache.clear()
    market_svc._stats["messages_received"] = 0
    market_svc._stats["messages_invalid"] = 0
    market_svc._redis_connected = False
    market_svc._subscription_active = False
    market_svc._redis_client = None
    yield


def test_market_health_degraded_when_dependencies_missing() -> None:
    client = market_svc.app.test_client()
    response = client.get("/health")
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["status"] == "degraded"
    assert "redis unavailable" in payload["detail"]


def test_market_health_healthy_when_connected_and_subscribed() -> None:
    market_svc._redis_connected = True
    market_svc._subscription_active = True
    response = market_svc.app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_market_status_does_not_expose_secrets() -> None:
    market_svc._redis_connected = True
    market_svc._subscription_active = True
    body = market_svc.app.test_client().get("/status").get_data(as_text=True).lower()
    assert "password" not in body
    assert "secret" not in body


def test_market_metrics_are_prometheus_text_not_live_go_claim() -> None:
    body = market_svc.app.test_client().get("/metrics").get_data(as_text=True).lower()
    assert "market_" in body or "# help" in body
    for marker in _LIVE_GO_MARKERS:
        assert marker not in body


@pytest.mark.skipif(
    not hasattr(risk_svc, "app"),
    reason="Flask unavailable in risk service import surface",
)
def test_risk_health_reports_running_state(monkeypatch: pytest.MonkeyPatch) -> None:
    risk_svc.stats["status"] = "running"
    response = risk_svc.app.test_client().get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "risk_manager"


@pytest.mark.skipif(
    not hasattr(risk_svc, "app"),
    reason="Flask unavailable in risk service import surface",
)
def test_risk_metrics_include_kill_switch_and_do_not_claim_live_go(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    risk_mod = importlib.import_module("services.risk.service")
    if risk_mod.app is None:
        pytest.skip("Flask app unavailable after risk service reload")

    risk_mod.stats["status"] = "running"
    risk_mod.stats["signals_received"] = 3
    risk_mod.stats["orders_blocked"] = 1
    risk_mod.risk_state.circuit_breaker_active = False
    monkeypatch.setattr(
        risk_mod,
        "get_kill_switch_details",
        lambda create_if_missing=False: (
            True,
            "MANUAL",
            "test",
            "2026-01-01T00:00:00Z",
        ),
    )
    body = risk_mod.app.test_client().get("/metrics").get_data(as_text=True)
    assert "risk_kill_switch_active 1" in body
    lowered = body.lower()
    for marker in _LIVE_GO_MARKERS:
        assert marker not in lowered


@pytest.mark.skipif(
    not hasattr(risk_svc, "app"),
    reason="Flask unavailable in risk service import surface",
)
def test_risk_metrics_kill_switch_read_failure_defaults_to_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    risk_mod = importlib.import_module("services.risk.service")
    if risk_mod.app is None:
        pytest.skip("Flask app unavailable after risk service reload")

    risk_mod.stats["status"] = "running"
    monkeypatch.setattr(
        risk_mod,
        "get_kill_switch_details",
        lambda create_if_missing=False: (_ for _ in ()).throw(
            OSError("state unreadable")
        ),
    )
    body = risk_mod.app.test_client().get("/metrics").get_data(as_text=True)
    # Fail-closed: unreadable kill-switch must report active (1), never permissive 0.
    assert "risk_kill_switch_active 1" in body


@pytest.mark.skipif(
    not hasattr(execution_svc, "app"),
    reason="Flask unavailable in execution service import surface",
)
def test_execution_health_ok_without_implying_live_trading() -> None:
    response = execution_svc.app.test_client().get("/health")
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert "live_go" not in response.get_data(as_text=True).lower()


@pytest.mark.skipif(
    not hasattr(execution_svc, "app"),
    reason="Flask unavailable in execution service import surface",
)
def test_execution_status_reports_mock_mode_and_missing_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(execution_svc, "redis_client", None)
    monkeypatch.setattr(
        execution_svc,
        "db",
        MagicMock(get_stats=lambda: {"connected": False}),
    )
    payload = execution_svc.app.test_client().get("/status").get_json()
    assert payload["mode"] == "mock"
    assert payload["redis"]["connected"] is False


@pytest.mark.skipif(
    not hasattr(execution_svc, "app"),
    reason="Flask unavailable in execution service import surface",
)
def test_execution_metrics_survive_invalid_stats_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = execution_svc.stats.copy()
    try:
        execution_svc.stats.clear()
        execution_svc.stats.update(
            {
                "orders_received": 0,
                "orders_filled": 0,
                "orders_rejected": 0,
                "shadow_blocked": 0,
                "invalid_payloads": 0,
                "start_time": original["start_time"],
                "last_result": None,
            }
        )
        body = execution_svc.app.test_client().get("/metrics").get_data(as_text=True)
        assert "execution_orders_received_total 0" in body
        assert "execution_uptime_seconds" in body
    finally:
        execution_svc.stats.clear()
        execution_svc.stats.update(original)
