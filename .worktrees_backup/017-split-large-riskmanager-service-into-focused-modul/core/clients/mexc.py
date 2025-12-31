"""
MEXC Spot Trading API Client
Claire de Binare Trading Bot

Consolidated from:
- services/execution/mexc_client.py
- services/risk/mexc_client.py

Fix for Issue #307: 291 lines duplicated code.

Features:
- Spot Market/Limit Orders
- Balance Queries
- Order Status Tracking
- Rate Limiting
"""

import os
import time
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


class MexcClient:
    """MEXC Spot Trading API Client (Unified)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
    ):
        """
        Initialize MEXC API Client

        Args:
            api_key: MEXC API Key (default: from env MEXC_API_KEY)
            api_secret: MEXC API Secret (default: from env MEXC_API_SECRET)
            testnet: Use testnet API (default: False)
        """
        self.api_key = api_key or os.getenv("MEXC_API_KEY")
        self.api_secret = api_secret or os.getenv("MEXC_API_SECRET")

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "MEXC API credentials required. Set MEXC_API_KEY and MEXC_API_SECRET"
            )

        # API Endpoints
        if testnet:
            self.base_url = "https://contract.mexc.com"  # Testnet URL
            logger.info("🧪 MEXC Client initialized in TESTNET mode")
        else:
            self.base_url = "https://api.mexc.com"
            logger.warning("🔴 MEXC Client initialized in LIVE mode - real money!")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-MEXC-APIKEY": self.api_key,
                "Content-Type": "application/json",
            }
        )

    def _sign_request(self, params: Dict[str, Any]) -> str:
        """
        Generate HMAC SHA256 signature for authenticated requests

        Args:
            params: Request parameters

        Returns:
            Hex signature string
        """
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get spot account balance

        Returns:
            Dict with balance information

        Raises:
            Exception: API error
        """
        endpoint = "/api/v3/account"
        timestamp = int(time.time() * 1000)

        params = {"timestamp": timestamp}
        params["signature"] = self._sign_request(params)

        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}", params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"✅ Fetched account balance: {len(data.get('balances', []))} assets")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch account balance: {e}")
            raise

    def get_balance(self, asset: str = "USDT") -> float:
        """
        Get balance for specific asset

        Args:
            asset: Asset symbol (e.g., "USDT", "BTC")

        Returns:
            Available balance as float
        """
        account = self.get_account_balance()
        balances = account.get("balances", [])

        for balance in balances:
            if balance.get("asset") == asset:
                free = float(balance.get("free", 0))
                logger.info(f"💰 {asset} Balance: {free}")
                return free

        logger.warning(f"⚠️  Asset {asset} not found in balance")
        return 0.0

    def place_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> Dict[str, Any]:
        """
        Place market order

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "BUY" or "SELL"
            quantity: Order quantity

        Returns:
            Order response dict

        Raises:
            Exception: API error
        """
        endpoint = "/api/v3/order"
        timestamp = int(time.time() * 1000)

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
            "timestamp": timestamp,
        }
        params["signature"] = self._sign_request(params)

        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}", params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            logger.info(
                f"✅ Market order placed: {symbol} {side} {quantity} - Order ID: {data.get('orderId')}"
            )
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to place market order: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"   Response: {e.response.text}")
            raise

    def place_limit_order(
        self, symbol: str, side: str, quantity: float, price: float
    ) -> Dict[str, Any]:
        """
        Place limit order

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            side: "BUY" or "SELL"
            quantity: Order quantity
            price: Limit price

        Returns:
            Order response dict

        Raises:
            Exception: API error
        """
        endpoint = "/api/v3/order"
        timestamp = int(time.time() * 1000)

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "GTC",  # Good Till Cancel
            "quantity": quantity,
            "price": price,
            "timestamp": timestamp,
        }
        params["signature"] = self._sign_request(params)

        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}", params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            logger.info(
                f"✅ Limit order placed: {symbol} {side} {quantity} @ {price} - Order ID: {data.get('orderId')}"
            )
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to place limit order: {e}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"   Response: {e.response.text}")
            raise

    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order status

        Args:
            symbol: Trading pair
            order_id: Order ID from MEXC

        Returns:
            Order status dict

        Raises:
            Exception: API error
        """
        endpoint = "/api/v3/order"
        timestamp = int(time.time() * 1000)

        params = {"symbol": symbol, "orderId": order_id, "timestamp": timestamp}
        params["signature"] = self._sign_request(params)

        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}", params=params, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"📊 Order {order_id} status: {data.get('status')}")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get order status: {e}")
            raise

    def get_ticker_price(self, symbol: str) -> float:
        """
        Get current market price for symbol

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")

        Returns:
            Current price as float
        """
        endpoint = "/api/v3/ticker/price"

        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}", params={"symbol": symbol}, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            price = float(data.get("price", 0))
            logger.debug(f"💹 {symbol} price: {price}")
            return price

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get ticker price: {e}")
            raise
