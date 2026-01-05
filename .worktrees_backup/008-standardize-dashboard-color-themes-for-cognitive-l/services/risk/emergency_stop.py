"""Emergency Stop Mechanism - Manual trading halt"""
import logging
from typing import Optional, Tuple
import redis

logger = logging.getLogger(__name__)


class EmergencyStop:
    """Manual emergency stop for trading operations"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.stop_key = "emergency_stop"

    def activate(self, reason: str = "Manual stop") -> None:
        """Activate emergency stop - halts all trading"""
        self.redis.set(self.stop_key, reason)
        logger.critical(f"🚨 EMERGENCY STOP ACTIVATED: {reason}")

    def deactivate(self) -> None:
        """Deactivate emergency stop - resume trading"""
        self.redis.delete(self.stop_key)
        logger.warning("⚠️ Emergency stop deactivated - trading resumed")

    def is_active(self) -> Tuple[bool, Optional[str]]:
        """Check if emergency stop active"""
        reason = self.redis.get(self.stop_key)
        if reason:
            return True, reason.decode() if isinstance(reason, bytes) else reason
        return False, None


# CLI usage:
# redis-cli SET emergency_stop "Market anomaly detected"
# redis-cli DEL emergency_stop
