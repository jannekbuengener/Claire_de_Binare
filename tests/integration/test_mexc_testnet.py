"""
MEXC Testnet Integration Tests (offline by default)

Offline tests stub network calls via FakeSession.
External tests are opt-in: set CDB_EXTERNAL_TESTS=1 and MEXC_API_KEY/MEXC_API_SECRET.
Run external tests explicitly with: pytest -m external tests/integration/test_mexc_testnet.py
"""

import os
import sys
import pytest
import logging
from typing import Any, Dict, List, Optional

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "execution"))

import mexc_client

logger = logging.getLogger(__name__)


class FakeResponse:
    """Minimal response stub for requests.Session."""

    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Fake requests session to prevent network calls and validate request shape."""

    def __init__(self, client: mexc_client.MexcClient) -> None:
        self.client = client
        self.headers = {
            "X-MEXC-APIKEY": client.api_key,
            "Content-Type": "application/json",
        }
        self.calls: List[Dict[str, Any]] = []

    def get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> FakeResponse:
        return self._handle("GET", url, params or {}, timeout)

    def post(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 10) -> FakeResponse:
        return self._handle("POST", url, params or {}, timeout)

    def _handle(self, method: str, url: str, params: Dict[str, Any], timeout: int) -> FakeResponse:
        endpoint = url.replace(self.client.base_url, "")
        self.calls.append({"method": method, "endpoint": endpoint, "params": params})

        signed_endpoints = {"/api/v3/account", "/api/v3/order"}
        if endpoint in signed_endpoints:
            assert "timestamp" in params
            assert "signature" in params
            signature = params["signature"]
            unsigned = {k: v for k, v in params.items() if k != "signature"}
            assert signature == self.client._sign_request(unsigned)
        else:
            assert "signature" not in params

        if endpoint == "/api/v3/account":
            return FakeResponse({"balances": [{"asset": "USDT", "free": "12.5"}]})
        if endpoint == "/api/v3/ticker/price":
            return FakeResponse({"price": "50000.0"})
        if endpoint == "/api/v3/order" and method == "GET":
            return FakeResponse({"orderId": params.get("orderId"), "status": "FILLED"})
        if endpoint == "/api/v3/order" and method == "POST":
            return FakeResponse({"orderId": "123456", "status": "FILLED"})
        return FakeResponse({})


@pytest.fixture
def offline_client(monkeypatch):
    """Create an offline client with stubbed session and fixed time."""
    monkeypatch.setattr(mexc_client.time, "time", lambda: 1700000000.0)
    client = mexc_client.MexcClient(api_key="test_key", api_secret="test_secret", testnet=True)
    client.session = FakeSession(client)
    return client


def _external_enabled() -> bool:
    return os.getenv("CDB_EXTERNAL_TESTS") == "1"


@pytest.fixture
def external_client():
    """Create a real testnet client (opt-in via CDB_EXTERNAL_TESTS=1)."""
    if not _external_enabled():
        pytest.skip("External tests disabled (set CDB_EXTERNAL_TESTS=1 to enable)")
    api_key = os.getenv("MEXC_API_KEY")
    api_secret = os.getenv("MEXC_API_SECRET")
    if not api_key or not api_secret:
        pytest.skip("MEXC API credentials not configured (set MEXC_API_KEY and MEXC_API_SECRET)")
    return mexc_client.MexcClient(api_key=api_key, api_secret=api_secret, testnet=True)


@pytest.mark.integration
class TestMexcTestnetOffline:
    """Offline integration tests that validate request signing and response handling."""

    def test_get_account_balance(self, offline_client):
        balance_data = offline_client.get_account_balance()
        assert balance_data is not None
        assert "balances" in balance_data
        assert isinstance(balance_data["balances"], list)
        assert balance_data["balances"][0]["asset"] == "USDT"

    def test_get_usdt_balance(self, offline_client):
        usdt_balance = offline_client.get_balance("USDT")
        assert isinstance(usdt_balance, float)
        assert usdt_balance == 12.5

    def test_get_ticker_price(self, offline_client):
        btc_price = offline_client.get_ticker_price("BTCUSDT")
        assert isinstance(btc_price, float)
        assert btc_price == 50000.0

    def test_get_order_status(self, offline_client):
        result = offline_client.get_order_status("BTCUSDT", "ORDER123")
        assert result is not None
        assert result.get("orderId") == "ORDER123"
        assert result.get("status") == "FILLED"


@pytest.mark.external
class TestMexcTestnetExternal:
    """External smoke tests (opt-in)."""

    def test_testnet_client_initialization(self, external_client):
        assert external_client is not None
        assert "testnet" in external_client.base_url.lower() or "contract.mexc.com" in external_client.base_url
        logger.info("Testnet client initialized")

    def test_get_account_balance(self, external_client):
        balance_data = external_client.get_account_balance()
        assert balance_data is not None
        assert "balances" in balance_data
        assert isinstance(balance_data["balances"], list)
        logger.info("Fetched balance: %s assets", len(balance_data["balances"]))

    def test_get_ticker_price(self, external_client):
        btc_price = external_client.get_ticker_price("BTCUSDT")
        assert isinstance(btc_price, float)
        assert btc_price > 0
        logger.info("BTC/USDT Price: %.2f", btc_price)

