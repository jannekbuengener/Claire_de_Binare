"""
Unit Tests - Adaptive Intensity "Wet/Dry" System

Tests für:
- Performance Gates (Upgrade/Downgrade-Kriterien)
- Profile Transitions (DRY ↔ NEUTRAL ↔ WET)
- Profile Manager Logik
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from backoffice.services.adaptive_intensity.models import (
    RiskProfile,
    PerformanceMetrics,
    ProfileConfig,
    PROFILE_CONFIGS,
)
from backoffice.services.adaptive_intensity.profile_manager import ProfileManager


# === Fixtures ===


@pytest.fixture
def mock_analyzer():
    """Mock Performance Analyzer"""
    analyzer = Mock()
    analyzer.lookback_trades = 300
    return analyzer


@pytest.fixture
def profile_manager(mock_analyzer):
    """ProfileManager mit Mock Analyzer"""
    return ProfileManager(
        performance_analyzer=mock_analyzer,
        initial_profile=RiskProfile.NEUTRAL,
        auto_adjust=True,
    )


# === Performance Metrics Tests ===


def test_upgrade_criteria_met():
    """Test: Upgrade-Kriterien erfüllt → should upgrade"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.62,  # > 60% ✓
        profit_factor=1.6,  # > 1.5 ✓
        max_drawdown_pct=0.025,  # < 3% ✓
        total_pnl=1250.0,
        avg_win=45.0,
        avg_loss=28.0,
        circuit_breaker_events=0,  # = 0 ✓
    )

    assert metrics.meets_upgrade_criteria() is True
    assert metrics.meets_downgrade_criteria() is False
    assert metrics.should_stay_current() is False


def test_upgrade_criteria_not_enough_trades():
    """Test: Nicht genug Trades → kein Upgrade"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=250,  # < 300 ✗
        lookback_trades=300,
        winrate=0.65,
        profit_factor=1.7,
        max_drawdown_pct=0.02,
        total_pnl=1500.0,
        avg_win=50.0,
        avg_loss=25.0,
        circuit_breaker_events=0,
    )

    assert metrics.meets_upgrade_criteria() is False


def test_upgrade_criteria_winrate_too_low():
    """Test: Winrate zu niedrig → kein Upgrade"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.58,  # < 60% ✗
        profit_factor=1.6,
        max_drawdown_pct=0.02,
        total_pnl=1200.0,
        avg_win=42.0,
        avg_loss=30.0,
        circuit_breaker_events=0,
    )

    assert metrics.meets_upgrade_criteria() is False


def test_downgrade_criteria_low_winrate():
    """Test: Winrate < 50% → Downgrade erforderlich"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.48,  # < 50% ✗
        profit_factor=0.95,
        max_drawdown_pct=0.04,
        total_pnl=-250.0,
        avg_win=35.0,
        avg_loss=38.0,
        circuit_breaker_events=0,
    )

    assert metrics.meets_downgrade_criteria() is True
    assert metrics.meets_upgrade_criteria() is False


def test_downgrade_criteria_high_drawdown():
    """Test: Drawdown > 5% → Downgrade erforderlich"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.52,
        profit_factor=1.05,
        max_drawdown_pct=0.06,  # > 5% ✗
        total_pnl=120.0,
        avg_win=40.0,
        avg_loss=37.0,
        circuit_breaker_events=0,
    )

    assert metrics.meets_downgrade_criteria() is True


def test_downgrade_criteria_circuit_breaker():
    """Test: Circuit Breaker aktiv → sofortiger Downgrade"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.55,
        profit_factor=1.2,
        max_drawdown_pct=0.04,
        total_pnl=500.0,
        avg_win=42.0,
        avg_loss=35.0,
        circuit_breaker_events=1,  # > 0 ✗
    )

    assert metrics.meets_downgrade_criteria() is True


def test_stable_performance_should_stay():
    """Test: Performance stabil → kein Wechsel"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.55,  # 50-60% → ok
        profit_factor=1.2,  # 1.0-1.5 → ok
        max_drawdown_pct=0.04,  # 3-5% → ok
        total_pnl=620.0,
        avg_win=41.0,
        avg_loss=33.0,
        circuit_breaker_events=0,
    )

    assert metrics.should_stay_current() is True
    assert metrics.meets_upgrade_criteria() is False
    assert metrics.meets_downgrade_criteria() is False


# === Profile Config Tests ===


def test_profile_configs_exist():
    """Test: Alle 3 Profile-Configs existieren"""
    assert RiskProfile.DRY in PROFILE_CONFIGS
    assert RiskProfile.NEUTRAL in PROFILE_CONFIGS
    assert RiskProfile.WET in PROFILE_CONFIGS


def test_dry_config_most_conservative():
    """Test: DRY hat konservativste Parameter"""
    dry = PROFILE_CONFIGS[RiskProfile.DRY]
    neutral = PROFILE_CONFIGS[RiskProfile.NEUTRAL]
    wet = PROFILE_CONFIGS[RiskProfile.WET]

    # DRY: Höchste Schwelle
    assert dry.signal_threshold_pct > neutral.signal_threshold_pct
    assert dry.signal_threshold_pct > wet.signal_threshold_pct

    # DRY: Höchster RSI Threshold
    assert dry.rsi_threshold > neutral.rsi_threshold
    assert dry.rsi_threshold > wet.rsi_threshold

    # DRY: Niedrigstes Exposure
    assert dry.max_exposure_pct < neutral.max_exposure_pct


def test_wet_config_most_aggressive():
    """Test: WET hat aggressivste Parameter"""
    wet = PROFILE_CONFIGS[RiskProfile.WET]
    neutral = PROFILE_CONFIGS[RiskProfile.NEUTRAL]

    # WET: Niedrigste Schwelle
    assert wet.signal_threshold_pct < neutral.signal_threshold_pct

    # WET: Niedrigster RSI Threshold
    assert wet.rsi_threshold < neutral.rsi_threshold

    # WET: Höchstes Exposure
    assert wet.max_exposure_pct > neutral.max_exposure_pct


# === Profile Manager Tests ===


def test_profile_manager_initialization():
    """Test: ProfileManager initialisiert korrekt"""
    analyzer = Mock()
    analyzer.lookback_trades = 300

    manager = ProfileManager(
        performance_analyzer=analyzer,
        initial_profile=RiskProfile.NEUTRAL,
        auto_adjust=True,
    )

    assert manager.current_profile == RiskProfile.NEUTRAL
    assert manager.auto_adjust is True
    assert len(manager.transition_history) == 0


def test_get_current_config():
    """Test: get_current_config gibt richtiges Config zurück"""
    analyzer = Mock()
    manager = ProfileManager(analyzer, initial_profile=RiskProfile.DRY)

    config = manager.get_current_config()

    assert config.profile == RiskProfile.DRY
    assert config.signal_threshold_pct == 3.0
    assert config.rsi_threshold == 60.0


def test_upgrade_dry_to_neutral(profile_manager, mock_analyzer):
    """Test: Upgrade von DRY → NEUTRAL bei guter Performance"""
    # Setup: Start mit DRY
    profile_manager.current_profile = RiskProfile.DRY

    # Mock Performance: Upgrade-Kriterien erfüllt
    good_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.62,
        profit_factor=1.6,
        max_drawdown_pct=0.025,
        total_pnl=1250.0,
        avg_win=45.0,
        avg_loss=28.0,
        circuit_breaker_events=0,
    )
    mock_analyzer.analyze_recent_performance.return_value = good_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert
    assert transition is not None
    assert transition.from_profile == RiskProfile.DRY
    assert transition.to_profile == RiskProfile.NEUTRAL
    assert transition.reason == "UPGRADE"
    assert profile_manager.current_profile == RiskProfile.NEUTRAL


def test_upgrade_neutral_to_wet(profile_manager, mock_analyzer):
    """Test: Upgrade von NEUTRAL → WET bei exzellenter Performance"""
    # Setup: Start mit NEUTRAL (default)
    assert profile_manager.current_profile == RiskProfile.NEUTRAL

    # Mock Performance: Upgrade-Kriterien erfüllt
    excellent_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=310,
        lookback_trades=300,
        winrate=0.65,
        profit_factor=1.8,
        max_drawdown_pct=0.02,
        total_pnl=1850.0,
        avg_win=50.0,
        avg_loss=25.0,
        circuit_breaker_events=0,
    )
    mock_analyzer.analyze_recent_performance.return_value = excellent_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert
    assert transition.from_profile == RiskProfile.NEUTRAL
    assert transition.to_profile == RiskProfile.WET
    assert transition.reason == "UPGRADE"


def test_downgrade_wet_to_neutral(profile_manager, mock_analyzer):
    """Test: Downgrade von WET → NEUTRAL bei schlechter Performance"""
    # Setup: Start mit WET
    profile_manager.current_profile = RiskProfile.WET

    # Mock Performance: Downgrade-Kriterien erfüllt
    bad_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.48,  # < 50%
        profit_factor=0.9,
        max_drawdown_pct=0.055,  # > 5%
        total_pnl=-320.0,
        avg_win=35.0,
        avg_loss=40.0,
        circuit_breaker_events=0,
    )
    mock_analyzer.analyze_recent_performance.return_value = bad_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert
    assert transition.from_profile == RiskProfile.WET
    assert transition.to_profile == RiskProfile.NEUTRAL
    assert transition.reason == "DOWNGRADE"


def test_downgrade_neutral_to_dry(profile_manager, mock_analyzer):
    """Test: Downgrade von NEUTRAL → DRY bei sehr schlechter Performance"""
    # Setup: Start mit NEUTRAL (default)

    # Mock Performance: Sehr schlechte Performance
    terrible_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.42,  # < 50%
        profit_factor=0.75,  # < 1.0
        max_drawdown_pct=0.08,  # >> 5%
        total_pnl=-850.0,
        avg_win=28.0,
        avg_loss=38.0,
        circuit_breaker_events=0,
    )
    mock_analyzer.analyze_recent_performance.return_value = terrible_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert
    assert transition.from_profile == RiskProfile.NEUTRAL
    assert transition.to_profile == RiskProfile.DRY
    assert transition.reason == "DOWNGRADE"


def test_circuit_breaker_forces_dry(profile_manager, mock_analyzer):
    """Test: Circuit Breaker → sofort zu DRY (von jedem Profil)"""
    # Setup: Start mit WET (most aggressive)
    profile_manager.current_profile = RiskProfile.WET

    # Mock Performance: Circuit Breaker aktiv
    circuit_breaker_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.52,  # sonst ok
        profit_factor=1.1,  # sonst ok
        max_drawdown_pct=0.04,  # sonst ok
        total_pnl=200.0,
        avg_win=40.0,
        avg_loss=35.0,
        circuit_breaker_events=1,  # ✗
    )
    mock_analyzer.analyze_recent_performance.return_value = circuit_breaker_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert: Direkt zu DRY
    assert transition.from_profile == RiskProfile.WET
    assert transition.to_profile == RiskProfile.DRY
    assert transition.reason == "CIRCUIT_BREAKER"


def test_no_transition_when_stable(profile_manager, mock_analyzer):
    """Test: Keine Transition bei stabiler Performance"""
    # Mock Performance: Stabil (keine Upgrade/Downgrade-Kriterien)
    stable_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.55,  # 50-60%
        profit_factor=1.2,  # 1.0-1.5
        max_drawdown_pct=0.04,  # < 5%
        total_pnl=620.0,
        avg_win=41.0,
        avg_loss=33.0,
        circuit_breaker_events=0,
    )
    mock_analyzer.analyze_recent_performance.return_value = stable_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert: Kein Wechsel
    assert transition is None
    assert profile_manager.current_profile == RiskProfile.NEUTRAL


def test_auto_adjust_disabled_no_transition(profile_manager, mock_analyzer):
    """Test: Bei auto_adjust=False keine automatische Transition"""
    # Setup: Auto-adjust deaktivieren
    profile_manager.auto_adjust = False

    # Mock Performance: Upgrade-Kriterien erfüllt
    good_metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.65,
        profit_factor=1.7,
        max_drawdown_pct=0.02,
        total_pnl=1500.0,
        avg_win=48.0,
        avg_loss=26.0,
        circuit_breaker_events=0,
    )
    mock_analyzer.analyze_recent_performance.return_value = good_metrics

    # Execute
    transition = profile_manager.check_and_adjust()

    # Assert: Kein Wechsel trotz guter Performance
    assert transition is None
    assert profile_manager.current_profile == RiskProfile.NEUTRAL


def test_force_profile_manual():
    """Test: Manuelles force_profile erzwingt Wechsel"""
    analyzer = Mock()
    manager = ProfileManager(analyzer, initial_profile=RiskProfile.NEUTRAL)

    # Force zu WET
    transition = manager.force_profile(RiskProfile.WET, reason="MANUAL_TEST")

    assert transition.from_profile == RiskProfile.NEUTRAL
    assert transition.to_profile == RiskProfile.WET
    assert transition.reason == "MANUAL_TEST"
    assert manager.current_profile == RiskProfile.WET


def test_transition_history_tracking():
    """Test: Transitions werden in History gespeichert"""
    analyzer = Mock()
    manager = ProfileManager(analyzer, initial_profile=RiskProfile.DRY)

    # Mache mehrere Transitions
    manager.force_profile(RiskProfile.NEUTRAL, reason="TEST1")
    manager.force_profile(RiskProfile.WET, reason="TEST2")
    manager.force_profile(RiskProfile.DRY, reason="TEST3")

    # Check History
    history = manager.get_transition_history(limit=10)

    assert len(history) == 3
    assert history[0].to_profile == RiskProfile.NEUTRAL
    assert history[1].to_profile == RiskProfile.WET
    assert history[2].to_profile == RiskProfile.DRY


def test_get_status_summary():
    """Test: Status Summary erstellt korrekt"""
    analyzer = Mock()
    analyzer.analyze_recent_performance.return_value = None  # Keine Daten

    manager = ProfileManager(analyzer, initial_profile=RiskProfile.NEUTRAL)

    summary = manager.get_status_summary()

    assert summary["current_profile"] == "NEUTRAL"
    assert summary["auto_adjust"] is True
    assert "config" in summary
    assert summary["config"]["signal_threshold_pct"] == 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
