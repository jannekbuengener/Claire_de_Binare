from services.signal import models as signal_models
from services.signal.models import normalize_ts_ms


def test_normalize_ts_ms_seconds_to_ms():
    assert normalize_ts_ms(1713916800) == 1713916800000


def test_normalize_ts_ms_keeps_milliseconds():
    assert normalize_ts_ms(1713916800000) == 1713916800000


def test_normalize_ts_ms_fallback_uses_wallclock_ms(monkeypatch):
    monkeypatch.setattr(signal_models.time, "time", lambda: 1713916800.123)

    assert normalize_ts_ms(None) == 1713916800123
    assert normalize_ts_ms(0) == 1713916800123
