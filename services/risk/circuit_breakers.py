"""
Circuit Breakers

Emergency stop mechanisms for critical error scenarios during paper trading testing.
"""

from enum import Enum
from typing import Dict, Any, List
import logging


class CircuitBreakerType(Enum):
    """Types of circuit breakers"""

    ERROR_RATE = "error_rate"
    DRAWDOWN = "drawdown"
    LOSS_LIMIT = "loss_limit"
    FREQUENCY = "frequency"


class CircuitBreaker:
    """Emergency circuit breaker system"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.breakers = {
            CircuitBreakerType.ERROR_RATE: {"threshold": 0.1, "active": True},
            CircuitBreakerType.DRAWDOWN: {"threshold": 0.15, "active": True},
            CircuitBreakerType.LOSS_LIMIT: {"threshold": 0.05, "active": True},  # 5% max loss
            CircuitBreakerType.FREQUENCY: {"threshold": 60, "active": True},  # Max 60 orders/min
        }
        self.triggered_breakers: List[str] = []

    def check_breakers(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Check if any circuit breakers should be triggered"""
        result = {"triggered": False, "reasons": []}

        for breaker_type, config in self.breakers.items():
            if config["active"] and self._should_trigger(breaker_type, metrics, config):
                result["triggered"] = True
                result["reasons"].append(breaker_type.value)
                self.triggered_breakers.append(breaker_type.value)

        return result

    def _should_trigger(
        self,
        breaker_type: CircuitBreakerType,
        metrics: Dict[str, Any],
        config: Dict[str, Any],
    ) -> bool:
        """Check if specific breaker should trigger.

        Metrics expected:
            - drawdown: float (0.0 - 1.0) - Current drawdown from peak
            - error_rate: float (0.0 - 1.0) - Rate of failed operations
            - loss_pct: float (0.0 - 1.0) - Current loss as percentage of initial capital
            - orders_per_minute: int - Order frequency for rate limiting
        """
        if breaker_type == CircuitBreakerType.DRAWDOWN:
            return metrics.get("drawdown", 0) > config["threshold"]
        elif breaker_type == CircuitBreakerType.ERROR_RATE:
            return metrics.get("error_rate", 0) > config["threshold"]
        elif breaker_type == CircuitBreakerType.LOSS_LIMIT:
            # CRITICAL: Loss limit must be enforced to prevent unlimited losses
            loss_pct = metrics.get("loss_pct", 0)
            return loss_pct > config["threshold"]
        elif breaker_type == CircuitBreakerType.FREQUENCY:
            # Rate limiting: Too many orders indicates algo gone wild
            orders_per_minute = metrics.get("orders_per_minute", 0)
            return orders_per_minute > config.get("threshold", 60)

        self.logger.warning(f"Unknown breaker type: {breaker_type}")
        return False
