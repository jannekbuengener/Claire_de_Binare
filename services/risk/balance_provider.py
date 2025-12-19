"""
Balance Provider for Risk Service
Fetches real account balances from MEXC Exchange

Read-only - no order execution, just balance queries for risk management.
"""

import logging
import os
from typing import Optional, Dict
from datetime import datetime, timedelta

# Import MEXC client from execution service
import sys
from pathlib import Path

# Add execution service to path
exec_service_path = Path(__file__).parent.parent / "execution"
sys.path.insert(0, str(exec_service_path))

try:
    from mexc_client import MEXCClient
except ImportError:
    MEXCClient = None
    logging.warning("MEXCClient not available - using fallback balance")


class BalanceProvider:
    """
    Provides real-time account balance information for risk management

    This is READ-ONLY - only queries balances, never executes trades.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        use_live_balance: bool = False,
        fallback_balance: float = 10000.0
    ):
        """
        Initialize Balance Provider

        Args:
            api_key: MEXC API key (optional, for live balance)
            api_secret: MEXC API secret (optional, for live balance)
            use_live_balance: Whether to fetch live balances from exchange
            fallback_balance: Fallback balance if live unavailable
        """
        self.logger = logging.getLogger(__name__)
        self.use_live_balance = use_live_balance
        self.fallback_balance = fallback_balance
        self.client: Optional[MEXCClient] = None

        # Balance cache (to avoid hammering API)
        self._cached_balance: Optional[float] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(seconds=30)  # 30 second cache

        if use_live_balance:
            if not api_key or not api_secret:
                self.logger.warning(
                    "Live balance requested but no API credentials - using fallback"
                )
                self.use_live_balance = False
            elif MEXCClient is None:
                self.logger.error("MEXCClient not available - using fallback balance")
                self.use_live_balance = False
            else:
                try:
                    self.client = MEXCClient(api_key, api_secret, testnet=False)
                    if self.client.health_check():
                        self.logger.info("✅ Balance Provider connected to MEXC (read-only)")
                    else:
                        self.logger.error("MEXC API health check failed - using fallback")
                        self.use_live_balance = False
                except Exception as e:
                    self.logger.error(f"Failed to initialize MEXC client: {e}")
                    self.use_live_balance = False

        if not self.use_live_balance:
            self.logger.info(f"Using fallback balance: ${fallback_balance:,.2f}")

    def get_total_balance_usdt(self) -> float:
        """
        Get total account balance in USDT

        Returns:
            Total balance in USDT
        """
        if not self.use_live_balance:
            return self.fallback_balance

        # Check cache
        if self._is_cache_valid():
            self.logger.debug(f"Using cached balance: ${self._cached_balance:,.2f}")
            return self._cached_balance

        # Fetch fresh balance
        try:
            balance = self._fetch_live_balance()
            if balance is not None:
                # Update cache
                self._cached_balance = balance
                self._cache_timestamp = datetime.utcnow()
                self.logger.info(f"📊 Live balance: ${balance:,.2f} USDT")
                return balance
            else:
                self.logger.warning("Failed to fetch live balance - using fallback")
                return self.fallback_balance

        except Exception as e:
            self.logger.error(f"Error fetching balance: {e} - using fallback")
            return self.fallback_balance

    def _fetch_live_balance(self) -> Optional[float]:
        """
        Fetch live balance from MEXC

        Returns:
            Total USDT balance or None if error
        """
        if not self.client:
            return None

        try:
            account = self.client.get_account_balance()
            if not account:
                return None

            # Calculate total balance in USDT
            total_usdt = 0.0
            balances = account.get("balances", [])

            for balance_entry in balances:
                asset = balance_entry.get("asset", "")
                free = float(balance_entry.get("free", 0))
                locked = float(balance_entry.get("locked", 0))

                total_asset = free + locked

                if total_asset > 0:
                    if asset == "USDT":
                        # USDT is already in USDT
                        total_usdt += total_asset
                    else:
                        # For other assets, would need to convert to USDT
                        # For now, skip (or implement price conversion)
                        # TODO: Add multi-asset balance conversion
                        pass

            return total_usdt

        except Exception as e:
            self.logger.error(f"Failed to fetch live balance: {e}")
            return None

    def _is_cache_valid(self) -> bool:
        """Check if cached balance is still valid"""
        if self._cached_balance is None or self._cache_timestamp is None:
            return False

        age = datetime.utcnow() - self._cache_timestamp
        return age < self._cache_duration

    def get_asset_balance(self, asset: str) -> float:
        """
        Get balance for specific asset

        Args:
            asset: Asset symbol (e.g., 'USDT', 'BTC')

        Returns:
            Available balance for asset
        """
        if not self.use_live_balance or not self.client:
            # Fallback for testing
            if asset == "USDT":
                return self.fallback_balance
            return 0.0

        try:
            balance = self.client.get_asset_balance(asset)
            return balance if balance is not None else 0.0
        except Exception as e:
            self.logger.error(f"Failed to get {asset} balance: {e}")
            return 0.0

    def invalidate_cache(self):
        """Force refresh on next balance query"""
        self._cached_balance = None
        self._cache_timestamp = None
        self.logger.debug("Balance cache invalidated")

    @staticmethod
    def from_env() -> "BalanceProvider":
        """
        Create BalanceProvider from environment variables

        Returns:
            Configured BalanceProvider instance
        """
        use_live = os.getenv("USE_LIVE_BALANCE", "false").lower() == "true"
        api_key = os.getenv("MEXC_API_KEY", "")
        api_secret = os.getenv("MEXC_API_SECRET", "")
        fallback = float(os.getenv("TEST_BALANCE", "10000"))

        return BalanceProvider(
            api_key=api_key,
            api_secret=api_secret,
            use_live_balance=use_live,
            fallback_balance=fallback
        )
