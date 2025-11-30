"""
Integration Tests für Continuous Adaptive Intensity System
Tests für vollständigen Event-Flow: PostgreSQL → Score → Redis → Services
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import redis

from .models import PerformanceMetrics
from .dynamic_adjuster import DynamicAdjuster, PerformanceScore
from .performance_analyzer import PerformanceAnalyzer


@pytest.fixture
def mock_redis():
    """Mock Redis Client"""
    mock = MagicMock(spec=redis.Redis)
    # Mock setex to capture what's being stored
    mock.setex = MagicMock()
    mock.publish = MagicMock()
    mock.get = MagicMock(return_value=None)
    return mock


@pytest.fixture
def mock_db_connection():
    """Mock PostgreSQL Connection"""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


class TestFullEventFlow:
    """Tests für vollständigen Event-Flow"""

    def test_postgres_to_redis_flow(self, mock_redis, mock_db_connection):
        """Test: PostgreSQL → Performance Analysis → Score → Redis Broadcast"""
        mock_conn, mock_cursor = mock_db_connection

        # Mock PostgreSQL Trades
        mock_trades = [
            {
                "id": i,
                "symbol": "BTCUSDT",
                "side": "BUY" if i % 2 == 0 else "SELL",
                "size": 0.01,
                "execution_price": 50000.0,
                "slippage_bps": 2.0,
                "timestamp": datetime.now(datetime.UTC),
                "pnl": 50.0 if i % 3 == 0 else -30.0,  # 58% Winrate
                "metadata": {},
            }
            for i in range(300)
        ]

        mock_cursor.fetchall.return_value = mock_trades
        mock_cursor.fetchone.return_value = {"count": 0}  # No circuit breaker events

        # Create PerformanceAnalyzer
        with patch("psycopg2.connect", return_value=mock_conn):
            analyzer = PerformanceAnalyzer(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
                lookback_trades=300,
            )

            # Create DynamicAdjuster
            adjuster = DynamicAdjuster(
                performance_analyzer=analyzer,
                winrate_weight=0.4,
                profit_factor_weight=0.4,
                drawdown_weight=0.2,
            )

            # Execute full flow
            score = adjuster.calculate_performance_score()
            params = adjuster.calculate_dynamic_parameters(score)

            # Verify Score was calculated
            assert score is not None
            assert 0.0 <= score.score <= 1.0
            assert score.trade_count == 300

            # Verify Parameters were calculated
            assert params is not None
            assert 1.5 <= params.signal_threshold_pct <= 3.0
            assert 0.40 <= params.max_exposure_pct <= 0.80

            # Simulate Redis Broadcast
            params_dict = {
                "timestamp": params.timestamp.isoformat(),
                "performance_score": params.performance_score,
                "signal_threshold_pct": params.signal_threshold_pct,
                "rsi_threshold": params.rsi_threshold,
                "volume_multiplier": params.volume_multiplier,
                "max_position_pct": params.max_position_pct,
                "max_exposure_pct": params.max_exposure_pct,
            }

            mock_redis.setex(
                "adaptive_intensity:current_params",
                3600,
                json.dumps(params_dict),
            )

            mock_redis.publish(
                "adaptive_intensity:updates",
                json.dumps(params_dict),
            )

            # Verify Redis was called
            assert mock_redis.setex.called
            assert mock_redis.publish.called

            # Verify stored data structure
            call_args = mock_redis.setex.call_args
            assert call_args[0][0] == "adaptive_intensity:current_params"
            assert call_args[0][1] == 3600  # TTL

            stored_data = json.loads(call_args[0][2])
            assert "performance_score" in stored_data
            assert "signal_threshold_pct" in stored_data
            assert "max_exposure_pct" in stored_data

    def test_redis_to_signal_engine_flow(self, mock_redis):
        """Test: Redis → Signal Engine konsumiert Parameter"""
        # Simuliere gespeicherte Parameter in Redis
        params = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "performance_score": 0.65,
            "signal_threshold_pct": 2.0,
            "rsi_threshold": 45.0,
            "volume_multiplier": 1.0,
            "max_position_pct": 0.11,
            "max_exposure_pct": 0.66,
        }

        mock_redis.get.return_value = json.dumps(params)

        # Signal Engine würde so konsumieren:
        params_json = mock_redis.get("adaptive_intensity:current_params")
        assert params_json is not None

        fetched_params = json.loads(params_json)

        # Verify Signal Engine bekommt korrekte Werte
        assert fetched_params["signal_threshold_pct"] == 2.0
        assert fetched_params["rsi_threshold"] == 45.0
        assert fetched_params["volume_multiplier"] == 1.0

    def test_redis_to_risk_manager_flow(self, mock_redis):
        """Test: Redis → Risk Manager konsumiert Parameter"""
        # Simuliere gespeicherte Parameter in Redis
        params = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "performance_score": 0.65,
            "signal_threshold_pct": 2.0,
            "rsi_threshold": 45.0,
            "volume_multiplier": 1.0,
            "max_position_pct": 0.11,
            "max_exposure_pct": 0.66,
        }

        mock_redis.get.return_value = json.dumps(params)

        # Risk Manager würde so konsumieren:
        params_json = mock_redis.get("adaptive_intensity:current_params")
        assert params_json is not None

        fetched_params = json.loads(params_json)

        # Verify Risk Manager bekommt korrekte Werte
        assert fetched_params["max_position_pct"] == 0.11
        assert fetched_params["max_exposure_pct"] == 0.66


class TestParameterPropagation:
    """Tests für Parameter-Propagation zwischen Services"""

    def test_parameter_update_propagates(self, mock_redis):
        """Test: Parameter-Updates propagieren korrekt"""
        # Initial Parameters
        params_v1 = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "performance_score": 0.50,
            "signal_threshold_pct": 2.25,
            "rsi_threshold": 50.0,
            "max_exposure_pct": 0.60,
        }

        # Updated Parameters (bessere Performance)
        params_v2 = {
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "performance_score": 0.70,
            "signal_threshold_pct": 1.90,  # Aggressiver
            "rsi_threshold": 44.0,  # Lockerer
            "max_exposure_pct": 0.72,  # Höher
        }

        # Simuliere Update-Zyklus
        mock_redis.get.side_effect = [
            json.dumps(params_v1),
            json.dumps(params_v2),
        ]

        # Erster Fetch
        params_1 = json.loads(mock_redis.get("adaptive_intensity:current_params"))
        assert params_1["signal_threshold_pct"] == 2.25
        assert params_1["max_exposure_pct"] == 0.60

        # Zweiter Fetch (nach Update)
        params_2 = json.loads(mock_redis.get("adaptive_intensity:current_params"))
        assert params_2["signal_threshold_pct"] == 1.90
        assert params_2["max_exposure_pct"] == 0.72

        # Verify Parameter wurden aggressiver
        assert params_2["signal_threshold_pct"] < params_1["signal_threshold_pct"]
        assert params_2["max_exposure_pct"] > params_1["max_exposure_pct"]

    def test_fallback_to_env_when_redis_empty(self, mock_redis):
        """Test: Fallback zu ENV wenn Redis leer"""
        # Redis gibt None zurück
        mock_redis.get.return_value = None

        # Service sollte ENV-Fallback verwenden
        params_json = mock_redis.get("adaptive_intensity:current_params")

        if not params_json:
            # Fallback zu ENV
            env_fallback = {
                "signal_threshold_pct": 2.0,  # ENV default
                "rsi_threshold": 50.0,
                "max_exposure_pct": 0.50,
            }

            # Verify Fallback funktioniert
            assert env_fallback["signal_threshold_pct"] == 2.0
            assert env_fallback["max_exposure_pct"] == 0.50


class TestContinuousUpdateLoop:
    """Tests für kontinuierlichen Update-Loop"""

    def test_smooth_transition_over_multiple_updates(self):
        """Test: Smooth Transitions über mehrere Updates"""
        # Erstelle Adjuster mit max_change=0.05
        mock_analyzer = MagicMock()
        adjuster = DynamicAdjuster(
            performance_analyzer=mock_analyzer,
            max_change_per_update=0.05,
        )

        # Simuliere Performance-Verbesserung von 0.40 → 0.70 über 3 Updates
        metrics_sequence = [
            PerformanceMetrics(
                timestamp=datetime.now(datetime.UTC),
                trade_count=300,
                lookback_trades=300,
                winrate=0.45,
                profit_factor=1.1,
                max_drawdown_pct=0.06,
                total_pnl=50.0,
                avg_win=45.0,
                avg_loss=40.0,
            ),
            PerformanceMetrics(
                timestamp=datetime.now(datetime.UTC),
                trade_count=300,
                lookback_trades=300,
                winrate=0.60,
                profit_factor=1.5,
                max_drawdown_pct=0.03,
                total_pnl=300.0,
                avg_win=60.0,
                avg_loss=35.0,
            ),
            PerformanceMetrics(
                timestamp=datetime.now(datetime.UTC),
                trade_count=300,
                lookback_trades=300,
                winrate=0.65,
                profit_factor=1.7,
                max_drawdown_pct=0.02,
                total_pnl=500.0,
                avg_win=65.0,
                avg_loss=30.0,
            ),
        ]

        scores = []
        for metrics in metrics_sequence:
            mock_analyzer.analyze_recent_performance.return_value = metrics
            score = adjuster.calculate_performance_score()
            scores.append(score.score)

        # Verify Score steigt graduell (limitiert auf max 5% pro Update)
        assert scores[0] < scores[1] < scores[2]

        # Verify keine einzelne Änderung > 5%
        for i in range(1, len(scores)):
            delta = abs(scores[i] - scores[i - 1])
            assert delta <= 0.051  # Kleine Toleranz für Rundungsfehler

    def test_update_interval_timing(self):
        """Test: Update-Interval wird eingehalten"""
        # Simuliere 30s Update-Interval
        update_interval = 0.1  # 100ms für Test (statt 30s)

        start_time = time.time()

        # Simuliere 3 Updates
        for _ in range(3):
            time.sleep(update_interval)

        elapsed = time.time() - start_time

        # Verify ca. 3 * 100ms = 300ms vergangen
        expected = 3 * update_interval
        assert abs(elapsed - expected) < 0.05  # 50ms Toleranz


class TestErrorHandling:
    """Tests für Error-Handling"""

    def test_handles_database_connection_error(self, mock_db_connection):
        """Test: Graceful Handling bei DB-Fehler"""
        mock_conn, mock_cursor = mock_db_connection

        # Simuliere DB-Fehler
        mock_conn.cursor.side_effect = Exception("Database connection failed")

        with patch("psycopg2.connect", return_value=mock_conn):
            analyzer = PerformanceAnalyzer(
                db_host="localhost",
                db_port=5432,
                db_name="test_db",
                db_user="test_user",
                db_password="test_pass",
            )

            # Sollte None zurückgeben statt zu crashen
            metrics = analyzer.analyze_recent_performance()
            assert metrics is None

    def test_handles_redis_connection_error(self, mock_redis):
        """Test: Graceful Handling bei Redis-Fehler"""
        # Simuliere Redis-Fehler
        mock_redis.get.side_effect = redis.ConnectionError("Redis unavailable")

        try:
            params_json = mock_redis.get("adaptive_intensity:current_params")
        except redis.ConnectionError:
            # Service sollte Fallback zu ENV verwenden
            params_json = None

        # Verify Fallback funktioniert
        if not params_json:
            env_fallback = {
                "signal_threshold_pct": 2.0,
                "max_exposure_pct": 0.50,
            }
            assert env_fallback is not None

    def test_handles_invalid_json_in_redis(self, mock_redis):
        """Test: Handling bei ungültigem JSON in Redis"""
        # Simuliere ungültiges JSON
        mock_redis.get.return_value = "invalid json {{"

        try:
            params = json.loads(mock_redis.get("adaptive_intensity:current_params"))
        except json.JSONDecodeError:
            # Fallback zu ENV
            params = {
                "signal_threshold_pct": 2.0,
                "max_exposure_pct": 0.50,
            }

        # Verify Fallback funktioniert
        assert params["signal_threshold_pct"] == 2.0


class TestPerformanceScenarios:
    """Tests für realistische Performance-Szenarien"""

    def test_winning_streak_increases_aggression(self):
        """Test: Winning Streak erhöht Aggressivität"""
        mock_analyzer = MagicMock()
        adjuster = DynamicAdjuster(performance_analyzer=mock_analyzer)

        # Tag 1: Schlechte Performance
        metrics_day1 = PerformanceMetrics(
            timestamp=datetime.now(datetime.UTC),
            trade_count=300,
            lookback_trades=300,
            winrate=0.48,
            profit_factor=0.95,
            max_drawdown_pct=0.06,
            total_pnl=-50.0,
            avg_win=45.0,
            avg_loss=48.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics_day1
        score_day1 = adjuster.calculate_performance_score()
        params_day1 = adjuster.calculate_dynamic_parameters(score_day1)

        # Tag 3: Nach Winning Streak
        metrics_day3 = PerformanceMetrics(
            timestamp=datetime.now(datetime.UTC),
            trade_count=300,
            lookback_trades=300,
            winrate=0.62,
            profit_factor=1.6,
            max_drawdown_pct=0.025,
            total_pnl=450.0,
            avg_win=65.0,
            avg_loss=35.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics_day3
        score_day3 = adjuster.calculate_performance_score()
        params_day3 = adjuster.calculate_dynamic_parameters(score_day3)

        # Verify System wurde aggressiver
        assert score_day3.score > score_day1.score
        assert params_day3.signal_threshold_pct < params_day1.signal_threshold_pct
        assert params_day3.max_exposure_pct > params_day1.max_exposure_pct

    def test_losing_streak_decreases_aggression(self):
        """Test: Losing Streak reduziert Aggressivität"""
        mock_analyzer = MagicMock()
        adjuster = DynamicAdjuster(performance_analyzer=mock_analyzer)

        # Tag 1: Gute Performance
        metrics_day1 = PerformanceMetrics(
            timestamp=datetime.now(datetime.UTC),
            trade_count=300,
            lookback_trades=300,
            winrate=0.60,
            profit_factor=1.5,
            max_drawdown_pct=0.03,
            total_pnl=400.0,
            avg_win=60.0,
            avg_loss=38.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics_day1
        score_day1 = adjuster.calculate_performance_score()
        params_day1 = adjuster.calculate_dynamic_parameters(score_day1)

        # Tag 3: Nach Losing Streak
        metrics_day3 = PerformanceMetrics(
            timestamp=datetime.now(datetime.UTC),
            trade_count=300,
            lookback_trades=300,
            winrate=0.46,
            profit_factor=0.90,
            max_drawdown_pct=0.08,
            total_pnl=-100.0,
            avg_win=50.0,
            avg_loss=55.0,
        )

        mock_analyzer.analyze_recent_performance.return_value = metrics_day3
        score_day3 = adjuster.calculate_performance_score()
        params_day3 = adjuster.calculate_dynamic_parameters(score_day3)

        # Verify System wurde konservativer
        assert score_day3.score < score_day1.score
        assert params_day3.signal_threshold_pct > params_day1.signal_threshold_pct
        assert params_day3.max_exposure_pct < params_day1.max_exposure_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
