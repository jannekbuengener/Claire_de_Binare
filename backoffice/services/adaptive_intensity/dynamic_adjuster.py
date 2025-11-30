"""
Dynamic Adjuster - Kontinuierliche, proportionale Anpassung der Trading-Parameter

Statt festen Stufen (DRY/NEUTRAL/WET) berechnet dieses Modul dynamisch:
- Performance Score (0.0 - 1.0) aus letzten 300 Trades
- Trading-Parameter proportional zum Score (threshold, RSI, exposure)
- Kontinuierliche Updates in Echtzeit
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

try:
    from .performance_analyzer import PerformanceAnalyzer
except ImportError:
    from performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class PerformanceScore:
    """
    Performance Score 0.0 - 1.0

    0.0 = Sehr schlecht (viele Verluste, hoher Drawdown)
    1.0 = Perfekt (hohe Winrate, hoher Profit Factor, niedriger Drawdown)
    """

    timestamp: datetime
    score: float  # 0.0 - 1.0

    # Komponenten
    winrate_score: float  # 0.0 - 1.0
    profit_factor_score: float  # 0.0 - 1.0
    drawdown_score: float  # 0.0 - 1.0

    # Raw Metrics
    raw_winrate: float
    raw_profit_factor: float
    raw_max_drawdown: float
    trade_count: int

    def __str__(self):
        return (
            f"Score: {self.score*100:.1f}% "
            f"(WR={self.winrate_score*100:.0f}%, "
            f"PF={self.profit_factor_score*100:.0f}%, "
            f"DD={self.drawdown_score*100:.0f}%)"
        )


@dataclass
class DynamicParameters:
    """Dynamisch berechnete Trading-Parameter basierend auf Performance Score"""

    timestamp: datetime
    performance_score: float  # 0.0 - 1.0

    # Signal Engine Parameter
    signal_threshold_pct: float  # 1.5% - 3.0%
    rsi_threshold: float  # 40 - 60
    volume_multiplier: float  # 0.5 - 2.0

    # Risk Manager Parameter
    max_position_pct: float  # 0.08 - 0.12
    max_exposure_pct: float  # 0.40 - 0.80

    def __str__(self):
        return (
            f"Params(score={self.performance_score*100:.1f}%): "
            f"threshold={self.signal_threshold_pct:.2f}%, "
            f"exposure={self.max_exposure_pct*100:.0f}%"
        )


class DynamicAdjuster:
    """
    Berechnet kontinuierlich Performance Score und passt Parameter proportional an

    Workflow:
    1. Performance Analyzer holt letzte 300 Trades
    2. Berechne Performance Score (0.0 - 1.0)
    3. Mappe Score auf Trading-Parameter
    4. Smooth Transitions (Rate Limiting)
    """

    def __init__(
        self,
        performance_analyzer: PerformanceAnalyzer,
        # Score Gewichtung
        winrate_weight: float = 0.4,
        profit_factor_weight: float = 0.4,
        drawdown_weight: float = 0.2,
        # Parameter Ranges (min bei score=0.0, max bei score=1.0)
        threshold_range: tuple = (3.0, 1.5),  # (schlecht, gut)
        rsi_range: tuple = (60.0, 40.0),  # (konservativ, aggressiv)
        volume_range: tuple = (2.0, 0.5),  # (strikt, locker)
        position_range: tuple = (0.08, 0.12),  # (klein, groß)
        exposure_range: tuple = (0.40, 0.80),  # (niedrig, hoch)
        # Smooth Transitions
        max_change_per_update: float = 0.05,  # Max 5% Score-Änderung pro Update
    ):
        """
        Args:
            performance_analyzer: Analyzer für letzte 300 Trades
            winrate_weight: Gewicht von Winrate im Score (0.0-1.0)
            profit_factor_weight: Gewicht von Profit Factor
            drawdown_weight: Gewicht von Drawdown
            threshold_range: (min_threshold, max_threshold) für signal_threshold_pct
            max_change_per_update: Max Änderung des Scores pro Update (Smooth)
        """
        self.analyzer = performance_analyzer

        # Gewichtung
        self.winrate_weight = winrate_weight
        self.profit_factor_weight = profit_factor_weight
        self.drawdown_weight = drawdown_weight

        # Parameter Ranges
        self.threshold_range = threshold_range
        self.rsi_range = rsi_range
        self.volume_range = volume_range
        self.position_range = position_range
        self.exposure_range = exposure_range

        # Smooth Transitions
        self.max_change_per_update = max_change_per_update
        self.last_score: Optional[float] = None

        logger.info(
            f"DynamicAdjuster initialized - "
            f"Weights: WR={winrate_weight}, PF={profit_factor_weight}, DD={drawdown_weight}"
        )

    def calculate_performance_score(self) -> Optional[PerformanceScore]:
        """
        Berechnet Performance Score aus letzten 300 Trades

        Returns:
            PerformanceScore oder None wenn nicht genug Daten
        """
        metrics = self.analyzer.analyze_recent_performance()

        if not metrics or metrics.trade_count < 50:
            logger.warning(f"Not enough trades for score: {metrics.trade_count if metrics else 0}")
            return None

        # === Winrate Score (0.0 - 1.0) ===
        # 0% = 0.0, 50% = 0.5, 100% = 1.0
        winrate_score = min(max(metrics.winrate / 1.0, 0.0), 1.0)

        # === Profit Factor Score (0.0 - 1.0) ===
        # PF < 0.5 = 0.0, PF = 1.0 = 0.5, PF >= 2.0 = 1.0
        if metrics.profit_factor < 0.5:
            pf_score = 0.0
        elif metrics.profit_factor < 1.0:
            pf_score = metrics.profit_factor - 0.5  # 0.0 - 0.5
        else:
            # PF 1.0 - 2.0 → Score 0.5 - 1.0
            pf_score = min(0.5 + (metrics.profit_factor - 1.0) / 2.0, 1.0)

        # === Drawdown Score (0.0 - 1.0) ===
        # Drawdown > 10% = 0.0, Drawdown 0% = 1.0
        # Invertiert: niedriger Drawdown = höherer Score
        drawdown_score = max(1.0 - (metrics.max_drawdown_pct / 0.10), 0.0)

        # === Kombinierter Score (gewichtet) ===
        raw_score = (
            winrate_score * self.winrate_weight
            + pf_score * self.profit_factor_weight
            + drawdown_score * self.drawdown_weight
        )

        # Normalisiere auf 0.0 - 1.0
        total_weight = self.winrate_weight + self.profit_factor_weight + self.drawdown_weight
        normalized_score = raw_score / total_weight

        # Smooth Transition (Rate Limiting)
        if self.last_score is not None:
            max_delta = self.max_change_per_update
            score_delta = normalized_score - self.last_score

            if abs(score_delta) > max_delta:
                # Limitiere Änderung
                normalized_score = self.last_score + (max_delta if score_delta > 0 else -max_delta)
                logger.debug(
                    f"Score change limited: {score_delta*100:.1f}% → "
                    f"{(normalized_score - self.last_score)*100:.1f}%"
                )

        self.last_score = normalized_score

        return PerformanceScore(
            timestamp=datetime.utcnow(),
            score=normalized_score,
            winrate_score=winrate_score,
            profit_factor_score=pf_score,
            drawdown_score=drawdown_score,
            raw_winrate=metrics.winrate,
            raw_profit_factor=metrics.profit_factor,
            raw_max_drawdown=metrics.max_drawdown_pct,
            trade_count=metrics.trade_count,
        )

    def calculate_dynamic_parameters(
        self, performance_score: PerformanceScore
    ) -> DynamicParameters:
        """
        Berechnet Trading-Parameter proportional zum Performance Score

        Args:
            performance_score: Performance Score (0.0 - 1.0)

        Returns:
            DynamicParameters mit berechneten Werten
        """
        score = performance_score.score

        # Lineare Interpolation zwischen min und max
        def interpolate(range_tuple: tuple, score: float) -> float:
            min_val, max_val = range_tuple
            return min_val + (max_val - min_val) * score

        params = DynamicParameters(
            timestamp=datetime.utcnow(),
            performance_score=score,
            # Signal Engine
            signal_threshold_pct=interpolate(self.threshold_range, score),
            rsi_threshold=interpolate(self.rsi_range, score),
            volume_multiplier=interpolate(self.volume_range, score),
            # Risk Manager
            max_position_pct=interpolate(self.position_range, score),
            max_exposure_pct=interpolate(self.exposure_range, score),
        )

        logger.info(
            f"📊 Dynamic Parameters: {params} "
            f"(from {performance_score})"
        )

        return params

    def get_current_parameters(self) -> Optional[DynamicParameters]:
        """
        Berechnet aktuelle Parameter basierend auf letzten 300 Trades

        Returns:
            DynamicParameters oder None wenn nicht genug Daten
        """
        score = self.calculate_performance_score()

        if not score:
            return None

        return self.calculate_dynamic_parameters(score)

    def get_adjustment_summary(self) -> dict:
        """
        Erstellt Summary für Logging/Monitoring

        Returns:
            Dict mit aktuellem Status
        """
        params = self.get_current_parameters()

        if not params:
            return {
                "status": "insufficient_data",
                "message": "Not enough trades for dynamic adjustment"
            }

        return {
            "status": "active",
            "performance_score": f"{params.performance_score * 100:.1f}%",
            "parameters": {
                "signal_threshold_pct": f"{params.signal_threshold_pct:.2f}%",
                "rsi_threshold": f"{params.rsi_threshold:.1f}",
                "max_exposure_pct": f"{params.max_exposure_pct * 100:.0f}%",
            },
            "interpretation": self._interpret_score(params.performance_score),
        }

    def _interpret_score(self, score: float) -> str:
        """Interpretiert Score in natürlicher Sprache"""
        if score >= 0.8:
            return "🔥 Excellent - Running HOT (WET mode)"
        elif score >= 0.6:
            return "💧 Good - Flowing nicely"
        elif score >= 0.4:
            return "⚖️ Moderate - Balanced"
        elif score >= 0.2:
            return "☀️ Cautious - Drying up"
        else:
            return "🏜️ Poor - Full DRY mode"
