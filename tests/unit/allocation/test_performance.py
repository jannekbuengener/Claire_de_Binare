import importlib
import os


def _load_service():
    os.environ["ALLOCATION_RULES_JSON"] = (
        '{"trend_bot": {"TREND": 1.0, "RANGE": 0.0, "HIGH_VOL_CHAOTIC": 0.0, "UNKNOWN": 0.0}}'
    )
    os.environ["ALLOCATION_REGIME_MIN_STABLE_SECONDS"] = "60"
    from services.allocation import config as alloc_config
    import services.allocation.service as alloc_service

    importlib.reload(alloc_config)
    importlib.reload(alloc_service)
    return alloc_service


def test_performance_window_ready():
    alloc_service = _load_service()
    svc = alloc_service.AllocationService()
    now_ts = 1_700_000_000
    start_ts = now_ts - 7 * 86400
    step = (7 * 86400) // 29
    for i in range(30):
        svc.trades["trend_bot"].append(
            alloc_service.TradeRecord(ts=start_ts + i * step, return_pct=0.01)
        )
    score, ready = svc._compute_performance("trend_bot", now_ts)
    assert ready is True
    assert score is not None


def test_performance_window_not_ready():
    alloc_service = _load_service()
    svc = alloc_service.AllocationService()
    now_ts = 1_700_000_000
    for i in range(10):
        svc.trades["trend_bot"].append(
            alloc_service.TradeRecord(ts=now_ts - i * 60, return_pct=0.01)
        )
    score, ready = svc._compute_performance("trend_bot", now_ts)
    assert ready is False
    assert score is None
