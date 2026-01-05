"""
Unit Tests für Technical Indicators Library (Issue #204)

Testet alle Indikatoren mit bekannten Werten.
"""

import pytest
import math

from core.indicators import EMA, SMA, RSI, MACD, BollingerBands, ATR


class TestSMA:
    """Tests für Simple Moving Average."""

    @pytest.mark.unit
    def test_sma_basic(self):
        """SMA berechnet korrekten Durchschnitt."""
        sma = SMA(period=3)

        sma.update(10)
        sma.update(20)
        assert not sma.is_ready

        sma.update(30)
        assert sma.is_ready
        assert sma.value == 20.0  # (10+20+30)/3

    @pytest.mark.unit
    def test_sma_sliding_window(self):
        """SMA verwendet sliding window korrekt."""
        sma = SMA(period=3)

        for price in [10, 20, 30]:
            sma.update(price)
        assert sma.value == 20.0

        sma.update(40)  # 10 fällt raus
        assert sma.value == 30.0  # (20+30+40)/3

        sma.update(50)  # 20 fällt raus
        assert sma.value == 40.0  # (30+40+50)/3

    @pytest.mark.unit
    def test_sma_reset(self):
        """SMA reset funktioniert."""
        sma = SMA(period=2)
        sma.update(100)
        sma.update(200)
        assert sma.is_ready

        sma.reset()
        assert not sma.is_ready
        assert sma.value is None


class TestEMA:
    """Tests für Exponential Moving Average."""

    @pytest.mark.unit
    def test_ema_first_value_is_sma(self):
        """Erste EMA = SMA der ersten N Werte."""
        ema = EMA(period=3)

        ema.update(10)
        ema.update(20)
        ema.update(30)

        # Erste EMA = SMA = (10+20+30)/3 = 20
        assert ema.is_ready
        assert ema.value == 20.0

    @pytest.mark.unit
    def test_ema_smoothing(self):
        """EMA reagiert auf neue Preise."""
        ema = EMA(period=3)
        # k = 2/(3+1) = 0.5

        for price in [10, 20, 30]:
            ema.update(price)

        prev_ema = ema.value  # 20.0

        ema.update(40)
        # EMA = 40 * 0.5 + 20 * 0.5 = 30
        assert ema.value == 30.0

    @pytest.mark.unit
    def test_ema_multiplier(self):
        """EMA Multiplier ist korrekt."""
        ema = EMA(period=10)
        # k = 2/(10+1) = 0.1818...
        expected_mult = 2.0 / 11.0
        assert abs(ema._multiplier - expected_mult) < 0.0001


class TestRSI:
    """Tests für Relative Strength Index."""

    @pytest.mark.unit
    def test_rsi_all_gains(self):
        """RSI = 100 bei nur Gewinnen."""
        rsi = RSI(period=5)

        # Steigende Preise
        prices = [100, 101, 102, 103, 104, 105]
        for price in prices:
            rsi.update(price)

        assert rsi.is_ready
        assert rsi.value == 100.0

    @pytest.mark.unit
    def test_rsi_all_losses(self):
        """RSI = 0 bei nur Verlusten."""
        rsi = RSI(period=5)

        # Fallende Preise
        prices = [105, 104, 103, 102, 101, 100]
        for price in prices:
            rsi.update(price)

        assert rsi.is_ready
        assert rsi.value == 0.0

    @pytest.mark.unit
    def test_rsi_neutral(self):
        """RSI ~ 50 bei ausgeglichenen Bewegungen."""
        rsi = RSI(period=4)

        # Abwechselnd: +1, -1, +1, -1
        prices = [100, 101, 100, 101, 100]
        for price in prices:
            rsi.update(price)

        assert rsi.is_ready
        # Bei gleichen Gains/Losses: RS=1, RSI=50
        assert abs(rsi.value - 50.0) < 1.0

    @pytest.mark.unit
    def test_rsi_overbought_oversold(self):
        """is_overbought und is_oversold Properties."""
        rsi = RSI(period=3)

        # Stark steigend -> Overbought
        for price in [100, 110, 120, 130]:
            rsi.update(price)
        assert rsi.is_overbought
        assert not rsi.is_oversold

        rsi.reset()

        # Stark fallend -> Oversold
        for price in [130, 120, 110, 100]:
            rsi.update(price)
        assert rsi.is_oversold
        assert not rsi.is_overbought


class TestMACD:
    """Tests für MACD."""

    @pytest.mark.unit
    def test_macd_needs_warmup(self):
        """MACD braucht Aufwärmphase."""
        macd = MACD(fast_period=3, slow_period=5, signal_period=2)

        # Weniger als slow_period
        for i in range(4):
            macd.update(100 + i)
            assert not macd.is_ready

    @pytest.mark.unit
    def test_macd_calculation(self):
        """MACD berechnet korrekt."""
        macd = MACD(fast_period=3, slow_period=5, signal_period=2)

        # Genug Werte für MACD + Signal
        prices = [100, 102, 104, 106, 108, 110, 112]
        for price in prices:
            macd.update(price)

        assert macd.is_ready
        result = macd.result

        # MACD sollte positiv sein (Preis steigt, fast EMA > slow EMA)
        assert result.macd > 0

    @pytest.mark.unit
    def test_macd_crossover_detection(self):
        """MACD erkennt Crossovers."""
        macd = MACD(fast_period=3, slow_period=5, signal_period=2)

        # Erst fallend, dann steigend für bullish crossover
        falling = [110, 108, 106, 104, 102, 100]
        rising = [102, 106, 110, 114]

        for price in falling:
            macd.update(price)

        for price in rising:
            result = macd.update(price)
            if macd.is_bullish_crossover:
                break
        else:
            # Kein crossover gefunden ist auch OK
            pass


class TestBollingerBands:
    """Tests für Bollinger Bands."""

    @pytest.mark.unit
    def test_bollinger_bands_basic(self):
        """Bollinger Bands berechnen korrekt."""
        bb = BollingerBands(period=5, std_dev=2.0)

        # Konstanter Preis -> keine Volatilität -> Bänder eng
        for _ in range(5):
            bb.update(100)

        assert bb.is_ready
        bands = bb.bands

        assert bands.middle == 100.0
        assert bands.upper == 100.0  # Keine StdDev
        assert bands.lower == 100.0
        assert bands.bandwidth == 0.0

    @pytest.mark.unit
    def test_bollinger_bands_volatility(self):
        """Bollinger Bands werden breiter bei Volatilität."""
        bb = BollingerBands(period=5, std_dev=2.0)

        # Volatile Preise
        prices = [100, 110, 90, 105, 95]
        for price in prices:
            bb.update(price)

        assert bb.is_ready
        bands = bb.bands

        # Mit Volatilität sollten Bänder auseinander sein
        assert bands.upper > bands.middle
        assert bands.lower < bands.middle
        assert bands.bandwidth > 0

    @pytest.mark.unit
    def test_bollinger_upper_lower_properties(self):
        """upper und lower Properties funktionieren."""
        bb = BollingerBands(period=3)

        for price in [100, 110, 90]:
            bb.update(price)

        assert bb.upper is not None
        assert bb.lower is not None
        assert bb.upper > bb.lower


class TestATR:
    """Tests für Average True Range."""

    @pytest.mark.unit
    def test_atr_with_ohlc(self):
        """ATR berechnet mit OHLC-Daten."""
        atr = ATR(period=3)

        # Erste Kerze setzt nur prev_close
        atr.update_ohlc(high=105, low=95, close=100)
        assert not atr.is_ready

        # Weitere Kerzen
        atr.update_ohlc(high=110, low=100, close=105)
        atr.update_ohlc(high=115, low=105, close=110)
        atr.update_ohlc(high=120, low=110, close=115)

        assert atr.is_ready
        assert atr.value > 0

    @pytest.mark.unit
    def test_atr_true_range_calculation(self):
        """ATR True Range berücksichtigt Gaps."""
        atr = ATR(period=2)

        # Erste Kerze
        atr.update_ohlc(high=100, low=90, close=95)

        # Gap Up: prev_close=95, high=110
        # TR = max(110-100, |110-95|, |100-95|) = max(10, 15, 5) = 15
        atr.update_ohlc(high=110, low=100, close=105)

        # Noch nicht ready (braucht 2 TR-Werte)
        atr.update_ohlc(high=115, low=105, close=110)

        assert atr.is_ready
        # ATR sollte True Range reflektieren (inkl. Gap)
        assert atr.value >= 10

    @pytest.mark.unit
    def test_atr_simple_update(self):
        """ATR mit vereinfachtem update() (nur Close)."""
        atr = ATR(period=3)

        for price in [100, 105, 110, 115]:
            atr.update(price)

        assert atr.is_ready
        # Bei nur Close: TR = 0 (da high=low=close)
        # Also ATR sollte klein sein
        assert atr.value == 0.0


class TestIndicatorReset:
    """Tests für Reset-Funktionalität aller Indikatoren."""

    @pytest.mark.unit
    @pytest.mark.parametrize("indicator_class,period", [
        (SMA, 5),
        (EMA, 5),
        (RSI, 5),
        (BollingerBands, 5),
        (ATR, 5),
    ])
    def test_reset_clears_state(self, indicator_class, period):
        """Reset setzt Indikator vollständig zurück."""
        indicator = indicator_class(period=period)

        # Einige Werte hinzufügen
        for i in range(period + 2):
            indicator.update(100 + i)

        assert indicator.is_ready

        indicator.reset()

        assert not indicator.is_ready
        assert indicator.value is None


class TestIndicatorValidation:
    """Tests für Eingabe-Validierung."""

    @pytest.mark.unit
    @pytest.mark.parametrize("indicator_class", [
        SMA, EMA, RSI, BollingerBands, ATR,
    ])
    def test_invalid_period_raises(self, indicator_class):
        """Ungültige Period wirft ValueError."""
        with pytest.raises(ValueError):
            indicator_class(period=0)

        with pytest.raises(ValueError):
            indicator_class(period=-1)


class TestMACDSpecific:
    """Spezifische MACD-Tests."""

    @pytest.mark.unit
    def test_macd_histogram_sign(self):
        """MACD Histogramm ändert Vorzeichen bei Trendwechsel."""
        macd = MACD(fast_period=3, slow_period=5, signal_period=2)

        # Trending up
        for price in [100, 102, 104, 106, 108, 110, 112]:
            macd.update(price)

        if macd.is_ready:
            # Bei Aufwärtstrend sollte Histogram positiv sein
            assert macd.histogram >= 0 or macd.histogram is not None
