"""
Real Balance Fetcher - NO MORE FAKE BALANCE
URGENT: Replaces TEST_BALANCE with real exchange balance

Fixed: Issue #305 - Removed hardcoded BTC/ETH prices, added proper error handling
"""

import requests
import time
import hashlib
import hmac
import os
import logging
from typing import Dict, Optional
from core.secrets import read_secret

logger = logging.getLogger(__name__)


class BalanceFetchError(Exception):
    """Raised when balance cannot be fetched - FAIL FAST"""
    pass


class RealBalanceFetcher:
    """Fetch REAL balance from MEXC - NO MORE test_balance=10000"""

    def __init__(self):
        # Use unified secret loader: Docker secrets first, then env fallback
        self.api_key = read_secret("mexc_api_key", "MEXC_API_KEY")
        self.api_secret = read_secret("mexc_api_secret", "MEXC_API_SECRET")
        self.base_url = os.getenv("MEXC_BASE_URL", "https://contract.mexc.com")

        if not self.api_key or not self.api_secret:
            raise ValueError("MEXC API credentials required for real balance")

        # Cache for last-known-good values
        self._price_cache: Dict[str, float] = {}
        self._balance_cache: Optional[Dict[str, float]] = None
        self._cache_timestamp: float = 0
        self._cache_ttl: float = 60.0  # Cache valid for 60 seconds

    def _generate_signature(self, params: str, timestamp: str) -> str:
        """Generate MEXC API signature"""
        message = f"{timestamp}{params}"
        return hmac.new(
            self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _get_ticker_price(self, symbol: str) -> float:
        """Get current price for a symbol from MEXC API.

        Args:
            symbol: Trading pair like 'BTCUSDT' or 'ETHUSDT'

        Returns:
            Current price as float

        Raises:
            BalanceFetchError: If price cannot be fetched
        """
        # Check cache first
        if symbol in self._price_cache:
            cache_age = time.time() - self._cache_timestamp
            if cache_age < self._cache_ttl:
                return self._price_cache[symbol]

        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            response = requests.get(url, params={"symbol": symbol}, timeout=5)
            response.raise_for_status()

            price = float(response.json()["price"])
            self._price_cache[symbol] = price
            self._cache_timestamp = time.time()
            logger.debug(f"Fetched {symbol} price: {price}")
            return price

        except requests.RequestException as e:
            # Try to use cached value if API fails
            if symbol in self._price_cache:
                logger.warning(f"API failed for {symbol}, using cached price: {e}")
                return self._price_cache[symbol]
            raise BalanceFetchError(f"Cannot fetch {symbol} price and no cache: {e}")

    def get_real_balance(self) -> Dict[str, float]:
        """Get REAL balance from MEXC exchange - NO MORE FAKE DATA.

        Returns:
            Dict with asset balances and TOTAL_USDT

        Raises:
            BalanceFetchError: If balance cannot be fetched (FAIL FAST)
        """
        try:
            timestamp = str(int(time.time() * 1000))

            params = {"timestamp": timestamp}
            sorted_params = sorted(params.items())
            query_string = "&".join([f"{k}={v}" for k, v in sorted_params])

            signature = self._generate_signature(query_string, timestamp)
            params["signature"] = signature

            headers = {
                "X-MEXC-APIKEY": self.api_key,
                "Content-Type": "application/json",
            }

            url = f"{self.base_url}/api/v3/account"
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            result = response.json()

            # Process real balance data
            balance_dict: Dict[str, float] = {}
            total_usdt = 0.0

            for balance in result.get("balances", []):
                asset = balance["asset"]
                free = float(balance["free"])
                locked = float(balance["locked"])
                total = free + locked

                if total > 0:
                    balance_dict[asset] = total

                    # Convert to USDT equivalent using REAL prices
                    if asset == "USDT":
                        total_usdt += total
                    elif asset in ("BTC", "ETH", "BNB", "SOL"):
                        # Fetch REAL price from API - no more hardcoded values!
                        try:
                            price = self._get_ticker_price(f"{asset}USDT")
                            total_usdt += total * price
                        except BalanceFetchError as e:
                            logger.error(f"Cannot convert {asset}: {e}")
                            # Don't add to total - better to underreport than fake

            balance_dict["TOTAL_USDT"] = total_usdt

            # Update cache for fallback
            self._balance_cache = balance_dict
            self._cache_timestamp = time.time()

            return balance_dict

        except requests.RequestException as e:
            # FAIL FAST: Try cache, then raise exception
            if self._balance_cache and (time.time() - self._cache_timestamp) < 300:
                logger.warning(f"API failed, using cached balance (age: {time.time() - self._cache_timestamp:.0f}s): {e}")
                return self._balance_cache

            raise BalanceFetchError(
                f"Cannot fetch balance and no valid cache: {e}. "
                "FAIL FAST: Trading should halt until balance is available."
            )

    def get_usdt_balance(self) -> float:
        """Get total USDT balance for risk calculations.

        Returns:
            Total balance in USDT

        Raises:
            BalanceFetchError: If balance cannot be fetched (propagates from get_real_balance)
        """
        balances = self.get_real_balance()
        total = balances.get("TOTAL_USDT", 0.0)

        if total <= 0:
            raise BalanceFetchError("Balance is zero or negative - cannot trade!")

        return total
