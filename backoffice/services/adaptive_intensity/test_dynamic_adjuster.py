"""
Unit Tests für Dynamic Adjuster
Tests für Performance Score Berechnung und dynamische Parameter
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

# Import actual classes (relative imports for package)
from .models import PerformanceMetrics
from .dynamic_adjuster import (
    DynamicAdjuster,
    PerformanceScore,
    DynamicParameters,
)


@pytest.fixture
def mock_analyzer():
    """Erstelle Mock PerformanceAnalyzer"""
    return MagicMock()


@pytest.fixture
def adjuster(mock_analyzer):
    """Erstelle DynamicAdjuster mit Mock Analyzer"""
    return DynamicAdjuster(
        performance_analyzer=mock_analyzer,
        winrate_weight=0.4,
        profit_factor_weight=0.4,
        drawdown_weight=0.2,
        threshold_range=(3.0, 1.5),
        rsi_range=(60.0, 40.0),
        volume_range=(2.0, 0.5),
        position_range=(0.08, 0.12),
        exposure_range=(0.40, 0.80),
        max_change_per_update=0.05,
    )


class TestPerformanceScoreCalculation:
    """Tests für Performance Score Berechnung"""

    def test_perfect_performance(self, adjuster, mock_analyzer):
        """Test: Perfekte Performance → Score 1.0"""
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=1.0,  # 100%
            profit_factor=2.0,  # Optimal
            max_drawdown_pct=0.0,  # Kein Drawdown
            total_pnl=1000.0,
            avg_win=50.0,
            avg_loss=0.0,
        )

        # Mock analyzer to return these metrics
        mock_analyzer.analyze_recent_performance.return_value = metrics

        score = adjuster.calculate_performance_score()

        assert score is not None
        assert score.score == pytest.approx(1.0, abs=0.01)
        assert score.winrate_score == 1.0
        assert score.profit_factor_score == 1.0
        assert score.drawdown_score == 1.0

    def test_worst_performance(self, adjuster, mock_analyzer):
        """Test: Schlechteste Performance → Score 0.0"""
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.0,  # 0%
            profit_factor=0.3,  # PF < 0.5
            max_drawdown_pct=0.15,  # > 10% DD
            total_pnl=-500.0,
            avg_win=0.0,
            avg_loss=25.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics

        score = adjuster.calculate_performance_score()

        assert score is not None
        assert score.score == pytest.approx(0.0, abs=0.01)
        assert score.winrate_score == 0.0
        assert score.profit_factor_score == 0.0
        assert score.drawdown_score == 0.0

    def test_average_performance(self, adjuster, mock_analyzer):
        """Test: Durchschnittliche Performance → Score ~0.5"""
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.50,  # 50%
            profit_factor=1.0,  # Break-even
            max_drawdown_pct=0.05,  # 5% DD
            total_pnl=0.0,
            avg_win=50.0,
            avg_loss=50.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics

        score = adjuster.calculate_performance_score()

        assert score is not None
        # WR: 0.5, PF: 0.5, DD: 0.5 → Weighted: 0.5
        assert score.score == pytest.approx(0.5, abs=0.02)

    def test_good_performance_example(self, adjuster, mock_analyzer):
        """Test: Gute Performance wie im Beispiel → Score ~0.66"""
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.58,  # 58%
            profit_factor=1.4,  # Solider PF
            max_drawdown_pct=0.025,  # 2.5% DD
            total_pnl=400.0,
            avg_win=60.0,
            avg_loss=40.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics

        score = adjuster.calculate_performance_score()

        assert score is not None
        # WR: 0.58 → 0.58
        # PF: 1.4 → 0.5 + (1.4-1.0)/2 = 0.7
        # DD: 2.5% → 1.0 - (0.025/0.10) = 0.75
        # Overall: 0.58*0.4 + 0.7*0.4 + 0.75*0.2 = 0.662
        assert score.score == pytest.approx(0.662, abs=0.01)
        assert score.winrate_score == pytest.approx(0.58, abs=0.01)
        assert score.profit_factor_score == pytest.approx(0.70, abs=0.01)
        assert score.drawdown_score == pytest.approx(0.75, abs=0.01)

    def test_insufficient_trades(self, adjuster, mock_analyzer):
        """Test: Zu wenig Trades → None zurückgeben"""
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=30,  # < 50 Mindest-Trades
            lookback_trades=300,
            winrate=0.60,
            profit_factor=1.5,
            max_drawdown_pct=0.03,
            total_pnl=100.0,
            avg_win=50.0,
            avg_loss=30.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics

        score = adjuster.calculate_performance_score()

        assert score is None


class TestDynamicParameterCalculation:
    """Tests für dynamische Parameter-Berechnung"""

    def test_score_zero_parameters(self, adjuster):
        """Test: Score 0.0 → MIN-Werte (konservativ)"""
        score = PerformanceScore(
            timestamp=datetime.utcnow(),
            score=0.0,
            winrate_score=0.0,
            profit_factor_score=0.0,
            drawdown_score=0.0,
            raw_winrate=0.0,
            raw_profit_factor=0.3,
            raw_max_drawdown=0.15,
            trade_count=300,
        )

        params = adjuster.calculate_dynamic_parameters(score)

        assert params.signal_threshold_pct == 3.0  # Max threshold (konservativ)
        assert params.rsi_threshold == 60.0  # Hoher RSI (nur bullish)
        assert params.volume_multiplier == 2.0  # Strenger Volume-Filter
        assert params.max_position_pct == 0.08  # Kleinere Positionen
        assert params.max_exposure_pct == 0.40  # Niedrige Exposure

    def test_score_one_parameters(self, adjuster):
        """Test: Score 1.0 → MAX-Werte (aggressiv)"""
        score = PerformanceScore(
            timestamp=datetime.utcnow(),
            score=1.0,
            winrate_score=1.0,
            profit_factor_score=1.0,
            drawdown_score=1.0,
            raw_winrate=1.0,
            raw_profit_factor=2.0,
            raw_max_drawdown=0.0,
            trade_count=300,
        )

        params = adjuster.calculate_dynamic_parameters(score)

        assert params.signal_threshold_pct == 1.5  # Min threshold (aggressiv)
        assert params.rsi_threshold == 40.0  # Niedriger RSI (loose filter)
        assert params.volume_multiplier == 0.5  # Lockerer Volume-Filter
        assert params.max_position_pct == 0.12  # Größere Positionen
        assert params.max_exposure_pct == 0.80  # Hohe Exposure

    def test_linear_interpolation_mid_score(self, adjuster):
        """Test: Score 0.5 → Mittelwerte"""
        score = PerformanceScore(
            timestamp=datetime.utcnow(),
            score=0.5,
            winrate_score=0.5,
            profit_factor_score=0.5,
            drawdown_score=0.5,
            raw_winrate=0.5,
            raw_profit_factor=1.0,
            raw_max_drawdown=0.05,
            trade_count=300,
        )

        params = adjuster.calculate_dynamic_parameters(score)

        # Threshold: 3.0 + (1.5 - 3.0) * 0.5 = 2.25
        assert params.signal_threshold_pct == pytest.approx(2.25, abs=0.01)

        # RSI: 60 + (40 - 60) * 0.5 = 50
        assert params.rsi_threshold == pytest.approx(50.0, abs=0.01)

        # Volume: 2.0 + (0.5 - 2.0) * 0.5 = 1.25
        assert params.volume_multiplier == pytest.approx(1.25, abs=0.01)

        # Position: 0.08 + (0.12 - 0.08) * 0.5 = 0.10
        assert params.max_position_pct == pytest.approx(0.10, abs=0.001)

        # Exposure: 0.40 + (0.80 - 0.40) * 0.5 = 0.60
        assert params.max_exposure_pct == pytest.approx(0.60, abs=0.01)

    def test_linear_interpolation_example_662(self, adjuster):
        """Test: Score 0.662 → Werte wie im Beispiel"""
        score = PerformanceScore(
            timestamp=datetime.utcnow(),
            score=0.662,
            winrate_score=0.58,
            profit_factor_score=0.70,
            drawdown_score=0.75,
            raw_winrate=0.58,
            raw_profit_factor=1.4,
            raw_max_drawdown=0.025,
            trade_count=300,
        )

        params = adjuster.calculate_dynamic_parameters(score)

        # Threshold: 3.0 + (1.5 - 3.0) * 0.662 = 2.007
        assert params.signal_threshold_pct == pytest.approx(2.007, abs=0.01)

        # Exposure: 0.40 + (0.80 - 0.40) * 0.662 = 0.665
        assert params.max_exposure_pct == pytest.approx(0.665, abs=0.01)


class TestEdgeCases:
    """Tests für Edge-Cases"""

    def test_zero_trades(self, adjuster, mock_analyzer):
        """Test: 0 Trades → None"""
        metrics = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=0,
            lookback_trades=300,
            winrate=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            total_pnl=0.0,
            avg_win=0.0,
            avg_loss=0.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics

        score = adjuster.calculate_performance_score()
        assert score is None

    def test_timestamp_in_parameters(self, adjuster):
        """Test: Timestamp wird korrekt gesetzt"""
        score = PerformanceScore(
            timestamp=datetime.utcnow(),
            score=0.5,
            winrate_score=0.5,
            profit_factor_score=0.5,
            drawdown_score=0.5,
            raw_winrate=0.5,
            raw_profit_factor=1.0,
            raw_max_drawdown=0.05,
            trade_count=300,
        )

        params = adjuster.calculate_dynamic_parameters(score)

        assert params.timestamp is not None
        assert isinstance(params.timestamp, datetime)
        # Timestamp sollte ca. jetzt sein (innerhalb 1 Sekunde)
        now = datetime.utcnow()
        assert abs((now - params.timestamp).total_seconds()) < 1.0


class TestIntegrationScenarios:
    """Integration Tests für realistische Szenarien"""

    def test_scenario_improving_performance(self, adjuster, mock_analyzer):
        """Test: Performance verbessert sich graduell"""
        # t=0: Mittelmäßige Performance
        metrics1 = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.52,
            profit_factor=1.15,
            max_drawdown_pct=0.032,
            total_pnl=100.0,
            avg_win=55.0,
            avg_loss=45.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics1
        score1 = adjuster.calculate_performance_score()
        params1 = adjuster.calculate_dynamic_parameters(score1)

        # t=30: Bessere Performance
        metrics2 = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.55,
            profit_factor=1.28,
            max_drawdown_pct=0.028,
            total_pnl=200.0,
            avg_win=60.0,
            avg_loss=40.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics2
        score2 = adjuster.calculate_performance_score()
        params2 = adjuster.calculate_dynamic_parameters(score2)

        # Score sollte gestiegen sein
        assert score2.score > score1.score

        # Threshold sollte niedriger sein (aggressiver)
        assert params2.signal_threshold_pct < params1.signal_threshold_pct

        # Exposure sollte höher sein
        assert params2.max_exposure_pct > params1.max_exposure_pct

    def test_scenario_deteriorating_performance(self, adjuster, mock_analyzer):
        """Test: Performance verschlechtert sich"""
        # t=0: Gute Performance
        metrics1 = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.58,
            profit_factor=1.40,
            max_drawdown_pct=0.025,
            total_pnl=400.0,
            avg_win=60.0,
            avg_loss=40.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics1
        score1 = adjuster.calculate_performance_score()
        params1 = adjuster.calculate_dynamic_parameters(score1)

        # t=30: Schlechtere Performance
        metrics2 = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            trade_count=300,
            lookback_trades=300,
            winrate=0.54,
            profit_factor=1.10,
            max_drawdown_pct=0.045,
            total_pnl=150.0,
            avg_win=55.0,
            avg_loss=48.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics2
        score2 = adjuster.calculate_performance_score()
        params2 = adjuster.calculate_dynamic_parameters(score2)

        # Score sollte gefallen sein
        assert score2.score < score1.score

        # Threshold sollte höher sein (konservativer)
        assert params2.signal_threshold_pct > params1.signal_threshold_pct

        # Exposure sollte niedriger sein
        assert params2.max_exposure_pct < params1.max_exposure_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
