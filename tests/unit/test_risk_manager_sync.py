import json

import pytest

from backoffice.services.risk_manager.service import RiskManager, risk_state, stats


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value

    def publish(self, *args, **kwargs):
        return None

    def ping(self):
        return True


def reset_state():
    risk_state.total_exposure = 0.0
    risk_state.daily_pnl = 0.0
    risk_state.open_positions = 0
    risk_state.signals_blocked = 0
    risk_state.signals_approved = 0
    risk_state.circuit_breaker_active = False
    risk_state.positions = {}
    risk_state.pending_orders = 0
    risk_state.last_prices = {}

    stats["risk_state_inconsistency_total"] = 0
    stats["risk_state_resync_total"] = 0
    stats["risk_state_recovery_total"] = 0


def test_startup_sync_overwrites_corrupt_redis(monkeypatch):
    reset_state()
    manager = RiskManager()
    manager.redis_client = FakeRedis()

    # DB truth: 10% of 10k -> 1000
    monkeypatch.setattr(
        manager,
        "_fetch_latest_snapshot",
        lambda: {
            "total_equity": 10_000.0,
            "total_exposure_pct": 0.10,
            "daily_pnl": 0.0,
            "open_positions": 2,
        },
    )

    # Corrupted Redis value: massive exposure
    manager.redis_client.store["risk_state:persistence"] = json.dumps(
        {"total_exposure": 241_000.0, "open_positions": 9}
    )

    manager.perform_startup_sync()

    persisted = json.loads(manager.redis_client.store["risk_state:persistence"])
    assert risk_state.total_exposure == pytest.approx(1_000.0)
    assert persisted["total_exposure"] == pytest.approx(1_000.0)
    assert stats["risk_state_resync_total"] == 1


def test_startup_sync_without_db_snapshot_is_non_blocking(monkeypatch):
    reset_state()
    manager = RiskManager()
    manager.redis_client = FakeRedis()

    monkeypatch.setattr(manager, "_fetch_latest_snapshot", lambda: None)

    manager.perform_startup_sync()  # should not raise

    assert risk_state.total_exposure == 0.0
    assert stats["risk_state_resync_total"] == 0


def test_auto_heal_recovers_drift(monkeypatch):
    reset_state()
    manager = RiskManager()
    manager.redis_client = FakeRedis()

    monkeypatch.setattr(
        manager,
        "_fetch_latest_snapshot",
        lambda: {
            "total_equity": 20_000.0,
            "total_exposure_pct": 0.10,  # 2000 notional
            "daily_pnl": 0.0,
            "open_positions": 1,
        },
    )

    manager.perform_startup_sync()

    # Drift Redis to an inflated exposure
    manager.redis_client.store["risk_state:persistence"] = json.dumps(
        {"total_exposure": 50_000.0, "open_positions": 3}
    )

    manager._auto_heal_tick()

    repaired = json.loads(manager.redis_client.store["risk_state:persistence"])
    assert risk_state.total_exposure == pytest.approx(2_000.0)
    assert repaired["total_exposure"] == pytest.approx(2_000.0)
    assert stats["risk_state_recovery_total"] == 1
