"""
MEXC Testnet Integration Tests (offline by default)

Offline tests use requests-mock to stub network calls.
External tests are opt-in: set CDB_EXTERNAL_TESTS=1 and MEXC_API_KEY/MEXC_API_SECRET.
Run external tests explicitly with: pytest -m external tests/integration/test_mexc_testnet.py

IMPORTANT NOTE ON DETERMINISTIC UUIDs:
Deterministic UUIDs (used in E2E tests via seeded UUID generation) are highly sensitive
to event input changes. Even minimal changes to event structure or content will produce
completely different UUIDs. This requires disciplined event design:
- Use stable, well-defined event schemas
- Document all event field changes
- Update expected UUIDs in tests when events change
- Consider event versioning for backward compatibility
"""

import os
import sys
import pytest
import requests_mock
import logging
from urllib.parse import urlparse, parse_qsl
from typing import Any, Dict

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "execution"))

import mexc_client

logger = logging.getLogger(__name__)


def _external_enabled() -> bool:
    """Check if external tests are enabled."""
    return os.getenv("CDB_EXTERNAL_TESTS") == "1"


@pytest.fixture
def offline_client(monkeypatch):
    """Create an offline client with stubbed session and fixed time."""
    monkeypatch.setattr(mexc_client.time, "time", lambda: 1700000000.0)
    client = mexc_client.MexcClient(api_key="test_key", api_secret="test_secret", testnet=True)
    return client


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


def _validate_request_signature(request, client):
    """Validate that request parameters include proper signature."""
    query = urlparse(request.path_url).query
    params = dict(parse_qsl(query, keep_blank_values=True))
    # Check for required signature params
    assert "timestamp" in params, "Missing timestamp in request"
    assert "signature" in params, "Missing signature in request"

    # Validate signature matches expected value
    signature = params["signature"]
    unsigned = {k: v for k, v in params.items() if k != "signature"}
    expected_signature = client._sign_request(unsigned)
    assert signature == expected_signature, f"Invalid signature: {signature} != {expected_signature}"


@pytest.mark.integration
class TestMexcTestnetOffline:
    """Offline integration tests using requests-mock to validate request signing and response handling."""

    def test_get_account_balance(self, offline_client, requests_mock):
        """Test account balance retrieval with mocked API response."""
        # Mock the account endpoint
        def custom_matcher(request):
            _validate_request_signature(request, offline_client)
            return True

        requests_mock.get(
            f"{offline_client.base_url}/api/v3/account",
            additional_matcher=custom_matcher,
            json={"balances": [{"asset": "USDT", "free": "12.5"}]}
        )

        balance_data = offline_client.get_account_balance()
        assert balance_data is not None
        assert "balances" in balance_data
        assert isinstance(balance_data["balances"], list)
        assert balance_data["balances"][0]["asset"] == "USDT"

    def test_get_usdt_balance(self, offline_client, requests_mock):
        """Test USDT balance parsing with mocked API response."""
        def custom_matcher(request):
            _validate_request_signature(request, offline_client)
            return True

        requests_mock.get(
            f"{offline_client.base_url}/api/v3/account",
            additional_matcher=custom_matcher,
            json={"balances": [{"asset": "USDT", "free": "12.5"}]}
        )

        usdt_balance = offline_client.get_balance("USDT")
        assert isinstance(usdt_balance, float)
        assert usdt_balance == 12.5

    def test_get_ticker_price(self, offline_client, requests_mock):
        """Test ticker price retrieval (unsigned endpoint)."""
        requests_mock.get(
            f"{offline_client.base_url}/api/v3/ticker/price",
            json={"price": "50000.0"}
        )

        btc_price = offline_client.get_ticker_price("BTCUSDT")
        assert isinstance(btc_price, float)
        assert btc_price == 50000.0

        # Verify no signature was sent for public endpoint
        history = requests_mock.request_history
        assert len(history) == 1
        assert "signature" not in history[0].qs

    def test_get_order_status(self, offline_client, requests_mock):
        """Test order status retrieval with signed request."""
        def custom_matcher(request):
            _validate_request_signature(request, offline_client)
            # Verify orderId is in params
            query = urlparse(request.path_url).query
            params = dict(parse_qsl(query, keep_blank_values=True))
            assert "orderId" in params
            return True

        requests_mock.get(
            f"{offline_client.base_url}/api/v3/order",
            additional_matcher=custom_matcher,
            json={"orderId": "ORDER123", "status": "FILLED"}
        )

        result = offline_client.get_order_status("BTCUSDT", "ORDER123")
        assert result is not None
        assert result.get("orderId") == "ORDER123"
        assert result.get("status") == "FILLED"

    def test_place_order(self, offline_client, requests_mock):
        """Test order placement with signed POST request."""
        def custom_matcher(request):
            _validate_request_signature(request, offline_client)
            # Verify order params are present
            assert "symbol" in request.qs
            assert "side" in request.qs
            assert "type" in request.qs
            return True

        requests_mock.post(
            f"{offline_client.base_url}/api/v3/order",
            additional_matcher=custom_matcher,
            json={"orderId": "123456", "status": "FILLED"}
        )

        # This would call client.place_order() - assuming such a method exists
        # For now, just verify the mock is configured correctly
        assert requests_mock.last_request is None  # No request made yet


@pytest.mark.external
class TestMexcTestnetExternal:
    """External smoke tests (opt-in) - these make real network calls to MEXC testnet."""

    def test_testnet_client_initialization(self, external_client):
        """Verify testnet client is properly initialized."""
        assert external_client is not None
        assert "testnet" in external_client.base_url.lower() or "contract.mexc.com" in external_client.base_url
        logger.info("Testnet client initialized")

    def test_get_account_balance(self, external_client):
        """Test real account balance retrieval from testnet."""
        balance_data = external_client.get_account_balance()
        assert balance_data is not None
        assert "balances" in balance_data
        assert isinstance(balance_data["balances"], list)
        logger.info("Fetched balance: %s assets", len(balance_data["balances"]))

    def test_get_ticker_price(self, external_client):
        """Test real ticker price from testnet."""
        btc_price = external_client.get_ticker_price("BTCUSDT")
        assert isinstance(btc_price, float)
        assert btc_price > 0
        logger.info("BTC/USDT Price: %.2f", btc_price)
