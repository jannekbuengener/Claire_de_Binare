from services.regime.models import Candle, compute_adx, compute_atr


def _make_flat_candles(count: int) -> list[Candle]:
    candles = []
    base_ts = 1_700_000_000
    for i in range(count):
        candles.append(
            Candle(
                ts=base_ts + i * 60,
                symbol="TEST",
                timeframe="1m",
                open=10.0,
                high=11.0,
                low=9.0,
                close=10.0,
                volume=100.0,
            )
        )
    return candles


def test_atr_flat_market():
    candles = _make_flat_candles(20)
    atr = compute_atr(candles, period=14)
    assert atr == 2.0


def test_adx_flat_market_returns_zeroish():
    candles = _make_flat_candles(20)
    adx = compute_adx(candles, period=14)
    assert adx is not None
    assert 0.0 <= adx <= 100.0


def test_adx_insufficient_data():
    candles = _make_flat_candles(5)
    adx = compute_adx(candles, period=14)
    assert adx is None
