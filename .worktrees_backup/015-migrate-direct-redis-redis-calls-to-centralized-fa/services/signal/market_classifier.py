"""
Market Classifier

Automated market phase detection for trend, sideways, and volatile market conditions.
Used in 72-hour paper trading validation to categorize system behavior.
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

from core.utils.clock import utcnow

class MarketPhase(Enum):
    """Market phase classifications"""

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


@dataclass
class MarketMetrics:
    """Market condition metrics"""

    phase: MarketPhase
    trend_strength: float  # 0-1, higher = stronger trend
    volatility_score: float  # 0-1, higher = more volatile
    momentum: float  # -1 to 1, negative = down momentum
    confidence: float  # 0-1, higher = more confident classification
    timestamp: datetime
    lookback_period: int


class MarketClassifier:
    """
    Classifies market conditions based on price action analysis

    Provides real-time market phase detection for trading system
    validation and performance analysis.
    """

    def __init__(
        self,
        trend_threshold: float = 0.02,
        volatility_threshold: float = 0.015,
        lookback_periods: Dict[str, int] = None,
        min_data_points: int = 20,
    ):
        """
        Initialize market classifier

        Args:
            trend_threshold: Minimum return for trend classification
            volatility_threshold: Threshold for high volatility classification
            lookback_periods: Different lookback periods for analysis
            min_data_points: Minimum data points required for classification
        """
        self.trend_threshold = trend_threshold
        self.volatility_threshold = volatility_threshold
        self.min_data_points = min_data_points

        # Default lookback periods
        self.lookback_periods = lookback_periods or {
            "short": 20,  # Short-term: 20 periods
            "medium": 50,  # Medium-term: 50 periods
            "long": 100,  # Long-term: 100 periods
        }

        # Price history storage
        self.price_history: List[Tuple[datetime, float]] = []
        self.classification_history: List[MarketMetrics] = []

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def add_price_data(self, timestamp: datetime, price: float):
        """Add new price data point"""
        self.price_history.append((timestamp, price))

        # Keep only necessary history (max lookback + buffer)
        max_lookback = max(self.lookback_periods.values())
        if len(self.price_history) > max_lookback * 2:
            self.price_history = self.price_history[-max_lookback * 2 :]

    def classify_current_market(self, lookback_period: str = "medium") -> MarketMetrics:
        """
        Classify current market conditions

        Args:
            lookback_period: Which lookback period to use ('short', 'medium', 'long')

        Returns:
            MarketMetrics with current classification
        """
        if len(self.price_history) < self.min_data_points:
            return MarketMetrics(
                phase=MarketPhase.UNKNOWN,
                trend_strength=0.0,
                volatility_score=0.0,
                momentum=0.0,
                confidence=0.0,
                timestamp=utcnow(),
                lookback_period=0,
            )

        # Get lookback period
        periods = self.lookback_periods.get(
            lookback_period, self.lookback_periods["medium"]
        )

        # Extract recent prices
        recent_data = self.price_history[-periods:]
        prices = np.array([price for _, price in recent_data])
        timestamps = [ts for ts, _ in recent_data]

        # Calculate metrics
        trend_strength, trend_direction = self._calculate_trend_strength(prices)
        volatility_score = self._calculate_volatility(prices)
        momentum = self._calculate_momentum(prices)

        # Classify market phase
        phase, confidence = self._classify_phase(
            trend_strength, trend_direction, volatility_score, momentum
        )

        # Create metrics object
        metrics = MarketMetrics(
            phase=phase,
            trend_strength=trend_strength,
            volatility_score=volatility_score,
            momentum=momentum,
            confidence=confidence,
            timestamp=timestamps[-1] if timestamps else utcnow(),
            lookback_period=periods,
        )

        # Store classification history
        self.classification_history.append(metrics)

        self.logger.debug(
            f"Market classified as {phase.value} (confidence: {confidence:.2f})"
        )

        return metrics

    def _calculate_trend_strength(self, prices: np.ndarray) -> Tuple[float, int]:
        """
        Calculate trend strength and direction

        Returns:
            Tuple of (strength, direction) where:
            - strength: 0-1, higher = stronger trend
            - direction: 1 (up), -1 (down), 0 (sideways)
        """
        if len(prices) < 2:
            return 0.0, 0

        # Linear regression to find trend
        x = np.arange(len(prices))
        coeffs = np.polyfit(x, prices, 1)
        slope = coeffs[0]

        # Calculate R-squared for trend strength
        y_pred = np.polyval(coeffs, x)
        ss_res = np.sum((prices - y_pred) ** 2)
        ss_tot = np.sum((prices - np.mean(prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Normalize slope by price range
        price_range = np.max(prices) - np.min(prices)
        normalized_slope = slope / (price_range / len(prices)) if price_range > 0 else 0

        # Determine direction
        if abs(normalized_slope) < 0.1:
            direction = 0  # Sideways
        else:
            direction = 1 if slope > 0 else -1

        # Trend strength combines R-squared with slope magnitude
        strength = min(1.0, r_squared * abs(normalized_slope) * 2)

        return strength, direction

    def _calculate_volatility(self, prices: np.ndarray) -> float:
        """
        Calculate volatility score (0-1)

        Uses rolling standard deviation of returns
        """
        if len(prices) < 2:
            return 0.0

        # Calculate returns
        returns = np.diff(prices) / prices[:-1]

        # Calculate rolling volatility (standard deviation of returns)
        volatility = np.std(returns)

        # Normalize to 0-1 scale (using typical market volatility as reference)
        # Daily volatility of 2% is considered high
        normalized_volatility = min(1.0, volatility / 0.02)

        return normalized_volatility

    def _calculate_momentum(self, prices: np.ndarray) -> float:
        """
        Calculate momentum (-1 to 1)

        Compares recent price action to longer-term average
        """
        if len(prices) < 4:
            return 0.0

        # Short-term average (last 25% of data)
        short_period = max(1, len(prices) // 4)
        short_avg = np.mean(prices[-short_period:])

        # Long-term average (full period)
        long_avg = np.mean(prices)

        # Calculate momentum as percentage difference
        momentum = (short_avg - long_avg) / long_avg if long_avg > 0 else 0.0

        # Normalize to -1 to 1 range
        return np.tanh(momentum * 10)  # tanh provides smooth -1 to 1 mapping

    def _classify_phase(
        self,
        trend_strength: float,
        trend_direction: int,
        volatility_score: float,
        momentum: float,
    ) -> Tuple[MarketPhase, float]:
        """
        Classify market phase based on metrics

        Returns:
            Tuple of (phase, confidence)
        """
        confidence_factors = []

        # High volatility overrides other factors
        if volatility_score > self.volatility_threshold:
            confidence_factors.append(volatility_score)
            return MarketPhase.VOLATILE, np.mean(confidence_factors)

        # Strong trend classification
        if trend_strength > 0.6:
            confidence_factors.append(trend_strength)

            if trend_direction > 0:
                phase = MarketPhase.TRENDING_UP
            elif trend_direction < 0:
                phase = MarketPhase.TRENDING_DOWN
            else:
                phase = MarketPhase.SIDEWAYS

            # Momentum should align with trend direction for higher confidence
            momentum_alignment = (
                (trend_direction > 0 and momentum > 0)
                or (trend_direction < 0 and momentum < 0)
                or (trend_direction == 0 and abs(momentum) < 0.2)
            )

            if momentum_alignment:
                confidence_factors.append(0.8)
            else:
                confidence_factors.append(0.4)

            return phase, np.mean(confidence_factors)

        # Moderate trend with momentum confirmation
        elif trend_strength > 0.3 and abs(momentum) > 0.2:
            confidence_factors.extend([trend_strength, abs(momentum)])

            if momentum > 0:
                return MarketPhase.TRENDING_UP, np.mean(confidence_factors)
            else:
                return MarketPhase.TRENDING_DOWN, np.mean(confidence_factors)

        # Default to sideways if no clear pattern
        confidence_factors.append(max(0.2, 1.0 - trend_strength))
        return MarketPhase.SIDEWAYS, np.mean(confidence_factors)

    def get_market_summary(self, periods: List[str] = None) -> Dict[str, Any]:
        """
        Get market classification summary across different timeframes

        Args:
            periods: List of lookback periods to analyze

        Returns:
            Dictionary with market analysis across timeframes
        """
        if periods is None:
            periods = list(self.lookback_periods.keys())

        summary = {
            "timestamp": utcnow().isoformat(),
            "data_points": len(self.price_history),
            "timeframes": {},
        }

        for period in periods:
            if period in self.lookback_periods:
                metrics = self.classify_current_market(period)
                summary["timeframes"][period] = {
                    "phase": metrics.phase.value,
                    "trend_strength": metrics.trend_strength,
                    "volatility_score": metrics.volatility_score,
                    "momentum": metrics.momentum,
                    "confidence": metrics.confidence,
                }

        # Overall market assessment
        phases = [
            summary["timeframes"][p]["phase"]
            for p in periods
            if p in summary["timeframes"]
        ]

        # Determine dominant phase
        phase_counts = {}
        for phase in phases:
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        dominant_phase = (
            max(phase_counts, key=phase_counts.get) if phase_counts else "unknown"
        )

        summary["overall_assessment"] = {
            "dominant_phase": dominant_phase,
            "phase_agreement": (
                max(phase_counts.values()) / len(phases) if phases else 0
            ),
            "avg_confidence": np.mean(
                [
                    summary["timeframes"][p]["confidence"]
                    for p in periods
                    if p in summary["timeframes"]
                ]
            ),
        }

        return summary

    def get_phase_distribution(self, hours_back: int = 24) -> Dict[str, float]:
        """
        Get distribution of market phases over specified period

        Args:
            hours_back: Number of hours to look back

        Returns:
            Dictionary with phase percentages
        """
        cutoff_time = utcnow() - timedelta(hours=hours_back)

        recent_classifications = [
            m for m in self.classification_history if m.timestamp >= cutoff_time
        ]

        if not recent_classifications:
            return {}

        # Count phases
        phase_counts = {}
        for metrics in recent_classifications:
            phase = metrics.phase.value
            phase_counts[phase] = phase_counts.get(phase, 0) + 1

        # Convert to percentages
        total = len(recent_classifications)
        phase_percentages = {
            phase: (count / total) * 100 for phase, count in phase_counts.items()
        }

        return phase_percentages

    def should_trade_in_current_conditions(
        self, min_confidence: float = 0.6, avoid_volatile_markets: bool = True
    ) -> Dict[str, Any]:
        """
        Determine if current market conditions are suitable for trading

        Args:
            min_confidence: Minimum confidence required for trading
            avoid_volatile_markets: Whether to avoid volatile market conditions

        Returns:
            Dictionary with trading recommendation
        """
        current_metrics = self.classify_current_market()

        recommendation = {
            "should_trade": False,
            "reason": "",
            "current_phase": current_metrics.phase.value,
            "confidence": current_metrics.confidence,
            "risk_level": "unknown",
        }

        # Check confidence threshold
        if current_metrics.confidence < min_confidence:
            recommendation[
                "reason"
            ] = f"Low confidence ({current_metrics.confidence:.2f} < {min_confidence})"
            recommendation["risk_level"] = "high"
            return recommendation

        # Check for volatile conditions
        if avoid_volatile_markets and current_metrics.phase == MarketPhase.VOLATILE:
            recommendation["reason"] = "Volatile market conditions detected"
            recommendation["risk_level"] = "high"
            return recommendation

        # Check for unknown conditions
        if current_metrics.phase == MarketPhase.UNKNOWN:
            recommendation["reason"] = "Insufficient data for classification"
            recommendation["risk_level"] = "high"
            return recommendation

        # Conditions are suitable for trading
        recommendation["should_trade"] = True
        recommendation["reason"] = f"Suitable conditions: {current_metrics.phase.value}"

        # Set risk level based on market phase
        if current_metrics.phase in [
            MarketPhase.TRENDING_UP,
            MarketPhase.TRENDING_DOWN,
        ]:
            recommendation["risk_level"] = (
                "low" if current_metrics.trend_strength > 0.7 else "medium"
            )
        elif current_metrics.phase == MarketPhase.SIDEWAYS:
            recommendation["risk_level"] = "medium"

        return recommendation
