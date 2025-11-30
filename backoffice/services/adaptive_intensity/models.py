"""
Adaptive Intensity - Data Models
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class RiskProfile(str, Enum):
    """
    Risk Profile Levels - "Dry/Wet" System

    DRY = Mehr Bodenhaftung (controlled, grip, safer)
    WET = Fließen lassen (flowing, liquid, higher frequency)
    """

    DRY = "DRY"  # Mehr Bodenhaftung: High thresholds, strict filters, controlled
    NEUTRAL = "NEUTRAL"  # Moderate: Balanced approach
    WET = "WET"  # Fließen lassen: Low thresholds, loose filters, flowing


@dataclass
class ProfileConfig:
    """Configuration for a specific Risk Profile"""

    # Signal Engine Parameters
    signal_threshold_pct: float
    rsi_threshold: float  # Minimum RSI for LONG signals
    volume_multiplier: float  # Multiplier for min_volume

    # Risk Manager Parameters
    max_position_pct: float
    max_exposure_pct: float
    max_daily_drawdown_pct: float

    # Profile Metadata
    profile: RiskProfile
    description: str


# Pre-defined Risk Profiles - "Wet/Dry" System
PROFILE_CONFIGS = {
    RiskProfile.DRY: ProfileConfig(
        profile=RiskProfile.DRY,
        description="DRY mode - Conservative, fewer trades, safer (trocken)",
        # Signal Engine
        signal_threshold_pct=3.0,
        rsi_threshold=60.0,
        volume_multiplier=2.0,
        # Risk Manager
        max_position_pct=0.08,  # 8% per position (vs 10% NEUTRAL)
        max_exposure_pct=0.40,  # 40% total exposure (vs 50% NEUTRAL)
        max_daily_drawdown_pct=0.03,  # 3% daily drawdown (vs 5% NEUTRAL)
    ),
    RiskProfile.NEUTRAL: ProfileConfig(
        profile=RiskProfile.NEUTRAL,
        description="NEUTRAL mode - Balanced approach",
        # Signal Engine
        signal_threshold_pct=2.0,
        rsi_threshold=50.0,
        volume_multiplier=1.0,
        # Risk Manager
        max_position_pct=0.10,  # 10% per position
        max_exposure_pct=0.50,  # 50% total exposure
        max_daily_drawdown_pct=0.05,  # 5% daily drawdown
    ),
    RiskProfile.WET: ProfileConfig(
        profile=RiskProfile.WET,
        description="WET mode - Aggressive, more trades, higher frequency (nass/fließend)",
        # Signal Engine
        signal_threshold_pct=1.5,
        rsi_threshold=40.0,
        volume_multiplier=0.5,
        # Risk Manager
        max_position_pct=0.12,  # 12% per position
        max_exposure_pct=0.60,  # 60% total exposure
        max_daily_drawdown_pct=0.05,  # Same as NEUTRAL (hard limit)
    ),
}


@dataclass
class PerformanceMetrics:
    """Performance Metrics über letzte N Trades"""

    # Timeframe
    timestamp: datetime
    trade_count: int  # Anzahl Trades in Analyse-Fenster
    lookback_trades: int  # Fenster-Größe (z.B. 300)

    # Core Metrics
    winrate: float  # Winning Trades / Total Trades (0.0 - 1.0)
    profit_factor: float  # Total Profit / Total Loss
    max_drawdown_pct: float  # Maximaler Drawdown (0.0 - 1.0)

    # Additional Context
    total_pnl: float  # Gesamt P&L im Fenster
    avg_win: float  # Durchschnittlicher Gewinn pro Winning Trade
    avg_loss: float  # Durchschnittlicher Verlust pro Losing Trade
    sharpe_ratio: Optional[float] = None  # Optional: Sharpe Ratio

    # Circuit Breaker Events
    circuit_breaker_events: int = 0  # Anzahl Circuit Breaker in Zeitraum

    def meets_upgrade_criteria(self) -> bool:
        """
        Prüft ob Performance gut genug für Upgrade zu aggressiverem Profil

        Kriterien (aus Deep Research):
        - Winrate > 60%
        - Max Drawdown < 3%
        - Profit Factor > 1.5
        - Keine Circuit Breaker in letzten 7 Tagen
        - Min 300 Trades im Fenster
        """
        return (
            self.trade_count >= self.lookback_trades
            and self.winrate > 0.60
            and self.max_drawdown_pct < 0.03
            and self.profit_factor > 1.5
            and self.circuit_breaker_events == 0
        )

    def meets_downgrade_criteria(self) -> bool:
        """
        Prüft ob Performance zu schlecht → Downgrade zu konservativerem Profil

        Kriterien:
        - Winrate < 50%
        - Max Drawdown > 5%
        - Profit Factor < 1.0
        - Circuit Breaker aktiv
        """
        return (
            self.winrate < 0.50
            or self.max_drawdown_pct > 0.05
            or self.profit_factor < 1.0
            or self.circuit_breaker_events > 0
        )

    def should_stay_current(self) -> bool:
        """Prüft ob aktuelles Profil beibehalten werden sollte"""
        return not self.meets_upgrade_criteria() and not self.meets_downgrade_criteria()


@dataclass
class ProfileTransition:
    """Event wenn Risk Profile gewechselt wird"""

    timestamp: datetime
    from_profile: RiskProfile
    to_profile: RiskProfile
    reason: str  # "UPGRADE", "DOWNGRADE", "MANUAL", "CIRCUIT_BREAKER"
    metrics: PerformanceMetrics
