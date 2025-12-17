"""
Circuit Breakers

Emergency stop mechanisms for critical error scenarios during paper trading testing.
"""

from enum import Enum
from typing import Dict, Any, List, Callable
from datetime import datetime
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
            CircuitBreakerType.ERROR_RATE: {'threshold': 0.1, 'active': True},
            CircuitBreakerType.DRAWDOWN: {'threshold': 0.15, 'active': True},
            CircuitBreakerType.LOSS_LIMIT: {'threshold': 0.05, 'active': True}
        }
        self.triggered_breakers: List[str] = []
    
    def check_breakers(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Check if any circuit breakers should be triggered"""
        result = {'triggered': False, 'reasons': []}
        
        for breaker_type, config in self.breakers.items():
            if config['active'] and self._should_trigger(breaker_type, metrics, config):
                result['triggered'] = True
                result['reasons'].append(breaker_type.value)
                self.triggered_breakers.append(breaker_type.value)
        
        return result
    
    def _should_trigger(self, breaker_type: CircuitBreakerType, metrics: Dict[str, Any], config: Dict[str, Any]) -> bool:
        """Check if specific breaker should trigger"""
        if breaker_type == CircuitBreakerType.DRAWDOWN:
            return metrics.get('drawdown', 0) > config['threshold']
        elif breaker_type == CircuitBreakerType.ERROR_RATE:
            return metrics.get('error_rate', 0) > config['threshold']
        return False