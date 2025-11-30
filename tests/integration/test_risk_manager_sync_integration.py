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


@pytest.mark.integration
def test_startup_and_heal_keep_db_truth(monkeypatch):
    reset_state()
    manager = RiskManager()
    manager.redis_client = FakeRedis()

    # DB truth snapshot (10% of 50k -> 5k)
    monkeypatch.setattr(
        manager,
        "_fetch_latest_snapshot",
        lambda: {
            "total_equity": 50_000.0,
            "total_exposure_pct": 0.10,
            "daily_pnl": 100.0,
            "open_positions": 4,
        },
    )

    manager.perform_startup_sync()

    persisted = json.loads(manager.redis_client.store["risk_state:persistence"])
    assert persisted["total_exposure"] == pytest.approx(5_000.0)
    assert risk_state.total_exposure == pytest.approx(5_000.0)
    assert stats["risk_state_resync_total"] in (0, 1)

    # Drift by 3% (within tolerance) -> no resync
    manager.redis_client.store["risk_state:persistence"] = json.dumps(
        {"total_exposure": 5_150.0}
    )
    manager._auto_heal_tick()
    assert stats["risk_state_recovery_total"] == 0

    # Drift by 20% -> resync
    manager.redis_client.store["risk_state:persistence"] = json.dumps(
        {"total_exposure": 7_000.0}
    )
    manager._auto_heal_tick()
    healed = json.loads(manager.redis_client.store["risk_state:persistence"])
    assert healed["total_exposure"] == pytest.approx(5_000.0)
    assert stats["risk_state_recovery_total"] == 1
