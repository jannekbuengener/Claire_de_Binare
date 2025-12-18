"""
Live Trading Gate

Authorization logic that requires successful 72-hour test completion
before enabling live trading operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from enum import Enum


class AuthorizationLevel(Enum):
    """Live trading authorization levels"""

    DENIED = "denied"
    PAPER_ONLY = "paper_only"
    LIMITED = "limited"
    FULL = "full"


class LiveTradingGate:
    """Controls access to live trading based on validation results"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.authorization_cache = {}

    def check_authorization(self, system_id: str) -> Dict[str, Any]:
        """
        Check if system is authorized for live trading

        Args:
            system_id: Unique identifier for trading system

        Returns:
            Authorization status and details
        """
        # Check for existing valid authorization
        cached_auth = self.authorization_cache.get(system_id)
        if cached_auth and self._is_authorization_valid(cached_auth):
            return cached_auth

        # Load latest test results
        test_results = self._load_latest_test_results(system_id)

        if not test_results:
            return self._create_authorization_response(
                AuthorizationLevel.DENIED, "No test results found"
            )

        # Validate test results
        validation_result = self._validate_test_results(test_results)

        # Determine authorization level
        auth_level = self._determine_authorization_level(validation_result)

        # Create authorization response
        auth_response = self._create_authorization_response(
            auth_level,
            validation_result.get("reason", "Test validation completed"),
            test_results,
        )

        # Cache authorization
        self.authorization_cache[system_id] = auth_response

        return auth_response

    def _load_latest_test_results(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Load latest 72-hour test results"""
        try:
            # In a real implementation, this would load from database
            # For now, return a simulated test result
            return {
                "test_completed": True,
                "duration_hours": 72.0,
                "validation_result": {
                    "overall_pass": True,
                    "risk_assessment": "low",
                    "criteria_results": {
                        "min_win_rate": {"pass": True, "actual": 0.55},
                        "max_drawdown": {"pass": True, "actual": 0.08},
                    },
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to load test results: {e}")
            return None

    def _validate_test_results(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate test results against authorization criteria"""
        validation = {
            "valid": True,
            "reason": "",
            "authorization_level": AuthorizationLevel.FULL,
        }

        # Check test completion
        if not test_results.get("test_completed", False):
            validation["valid"] = False
            validation["reason"] = "Test not completed successfully"
            validation["authorization_level"] = AuthorizationLevel.DENIED
            return validation

        # Check test duration
        duration = test_results.get("duration_hours", 0)
        if duration < 72.0:
            validation["valid"] = False
            validation["reason"] = f"Test duration {duration}h < required 72h"
            validation["authorization_level"] = AuthorizationLevel.DENIED
            return validation

        # Check test age (results must be recent)
        test_timestamp = datetime.fromisoformat(test_results.get("timestamp", ""))
        max_age = timedelta(days=30)  # Test results valid for 30 days

        if datetime.utcnow() - test_timestamp > max_age:
            validation["valid"] = False
            validation["reason"] = "Test results expired - retest required"
            validation["authorization_level"] = AuthorizationLevel.DENIED
            return validation

        # Check validation results
        validation_result = test_results.get("validation_result", {})

        if not validation_result.get("overall_pass", False):
            risk_level = validation_result.get("risk_assessment", "high")

            if risk_level == "medium":
                validation["authorization_level"] = AuthorizationLevel.LIMITED
                validation[
                    "reason"
                ] = "Limited authorization due to medium risk assessment"
            else:
                validation["valid"] = False
                validation["reason"] = f"Test failed with {risk_level} risk assessment"
                validation["authorization_level"] = AuthorizationLevel.DENIED

        return validation

    def _determine_authorization_level(
        self, validation_result: Dict[str, Any]
    ) -> AuthorizationLevel:
        """Determine appropriate authorization level"""
        if not validation_result.get("valid", False):
            return AuthorizationLevel.DENIED

        return validation_result.get(
            "authorization_level", AuthorizationLevel.PAPER_ONLY
        )

    def _create_authorization_response(
        self,
        auth_level: AuthorizationLevel,
        reason: str,
        test_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create authorization response"""
        response = {
            "authorized": auth_level != AuthorizationLevel.DENIED,
            "authorization_level": auth_level.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "valid_until": self._calculate_expiry(auth_level),
            "restrictions": self._get_restrictions(auth_level),
        }

        if test_results:
            response["test_summary"] = {
                "test_date": test_results.get("timestamp"),
                "duration_hours": test_results.get("duration_hours"),
                "validation_passed": test_results.get("validation_result", {}).get(
                    "overall_pass", False
                ),
            }

        return response

    def _calculate_expiry(self, auth_level: AuthorizationLevel) -> Optional[str]:
        """Calculate authorization expiry date"""
        if auth_level == AuthorizationLevel.DENIED:
            return None

        # Full authorization valid for 90 days, limited for 30 days
        days = 90 if auth_level == AuthorizationLevel.FULL else 30
        expiry = datetime.utcnow() + timedelta(days=days)

        return expiry.isoformat()

    def _get_restrictions(self, auth_level: AuthorizationLevel) -> Dict[str, Any]:
        """Get restrictions for authorization level"""
        restrictions = {
            AuthorizationLevel.DENIED: {
                "live_trading": False,
                "paper_trading": True,
                "max_position_size": 0.0,
                "max_daily_volume": 0.0,
            },
            AuthorizationLevel.PAPER_ONLY: {
                "live_trading": False,
                "paper_trading": True,
                "max_position_size": 0.0,
                "max_daily_volume": 0.0,
            },
            AuthorizationLevel.LIMITED: {
                "live_trading": True,
                "paper_trading": True,
                "max_position_size": 0.05,  # 5% max position
                "max_daily_volume": 10000.0,  # $10k daily limit
            },
            AuthorizationLevel.FULL: {
                "live_trading": True,
                "paper_trading": True,
                "max_position_size": 0.10,  # 10% max position
                "max_daily_volume": 100000.0,  # $100k daily limit
            },
        }

        return restrictions.get(auth_level, restrictions[AuthorizationLevel.DENIED])

    def _is_authorization_valid(self, authorization: Dict[str, Any]) -> bool:
        """Check if cached authorization is still valid"""
        if not authorization.get("authorized", False):
            return False

        valid_until = authorization.get("valid_until")
        if not valid_until:
            return False

        expiry = datetime.fromisoformat(valid_until)
        return datetime.utcnow() < expiry

    def revoke_authorization(self, system_id: str, reason: str) -> Dict[str, Any]:
        """Revoke live trading authorization"""
        revocation = {
            "system_id": system_id,
            "revoked": True,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "requires_retest": True,
        }

        # Remove from cache
        if system_id in self.authorization_cache:
            del self.authorization_cache[system_id]

        self.logger.warning(f"Authorization revoked for {system_id}: {reason}")

        return revocation
