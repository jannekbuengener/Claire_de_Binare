"""
MEXC Testnet Integration Tests
Tests real API connectivity in testnet environment
"""

import os
import sys
import pytest
import logging

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "execution"))

from mexc_client import MexcClient

logger = logging.getLogger(__name__)


@pytest.fixture
def testnet_client():
    """Create MEXC testnet client (requires credentials in .env)"""
    api_key = os.getenv("MEXC_API_KEY")
    api_secret = os.getenv("MEXC_API_SECRET")

    if not api_key or not api_secret:
        pytest.skip("MEXC API credentials not configured (set MEXC_API_KEY and MEXC_API_SECRET)")

    return MexcClient(api_key=api_key, api_secret=api_secret, testnet=True)


class TestMexcTestnetConnection:
    """Test MEXC Testnet API connectivity"""

    def test_testnet_client_initialization(self, testnet_client):
        """Test testnet client initializes correctly"""
        assert testnet_client is not None
        assert "testnet" in testnet_client.base_url.lower() or "contract.mexc.com" in testnet_client.base_url
        logger.info("✅ Testnet client initialized")

    def test_get_account_balance(self, testnet_client):
        """Test fetching account balance from testnet"""
        balance_data = testnet_client.get_account_balance()

        assert balance_data is not None
        assert "balances" in balance_data
        assert isinstance(balance_data["balances"], list)

        logger.info(f"✅ Fetched balance: {len(balance_data['balances'])} assets")

    def test_get_usdt_balance(self, testnet_client):
        """Test fetching USDT balance"""
        usdt_balance = testnet_client.get_balance("USDT")

        assert isinstance(usdt_balance, float)
        assert usdt_balance >= 0

        logger.info(f"✅ USDT Balance: {usdt_balance:.2f}")

    def test_get_ticker_price(self, testnet_client):
        """Test fetching ticker price (public endpoint)"""
        btc_price = testnet_client.get_ticker_price("BTCUSDT")

        assert isinstance(btc_price, float)
        assert btc_price > 0

        logger.info(f"✅ BTC/USDT Price: {btc_price:.2f}")


class TestMexcTestnetDryRun:
    """Test dry-run mode (no real orders)"""

    @pytest.mark.parametrize("symbol,side,quantity", [
        ("BTCUSDT", "BUY", 0.001),
        ("ETHUSDT", "SELL", 0.01),
    ])
    def test_market_order_validation(self, testnet_client, symbol, side, quantity):
        """Test market order parameters (dry-run - don't execute)"""
        # This test validates parameters WITHOUT placing real orders
        # In production, check DRY_RUN=true before executing

        # Validate symbol format
        assert len(symbol) >= 6
        assert symbol.isupper()

        # Validate side
        assert side in ["BUY", "SELL"]

        # Validate quantity
        assert quantity > 0

        logger.info(f"✅ Order params validated: {symbol} {side} {quantity}")


@pytest.mark.slow
class TestMexcTestnetOrders:
    """Test real order placement (requires DRY_RUN=false and testnet balance)"""

    @pytest.mark.skip(reason="Requires manual execution - set DRY_RUN=false")
    def test_place_market_order_testnet(self, testnet_client):
        """Test placing market order on testnet (MANUAL TEST ONLY)"""
        # WARNING: This will place a REAL order on testnet
        # Only run manually when ready to test execution

        # Small test order
        result = testnet_client.place_market_order(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.0001  # Very small test order
        )

        assert result is not None
        assert "orderId" in result
        assert result.get("status") in ["FILLED", "PARTIALLY_FILLED", "NEW"]

        logger.info(f"✅ Test order placed: {result['orderId']}")

    @pytest.mark.skip(reason="Requires manual execution")
    def test_get_order_status_testnet(self, testnet_client):
        """Test fetching order status (MANUAL TEST ONLY)"""
        # Replace with actual order ID from previous test
        order_id = "TEST_ORDER_ID"
        symbol = "BTCUSDT"

        result = testnet_client.get_order_status(symbol, order_id)

        assert result is not None
        assert result.get("orderId") == order_id
        assert "status" in result

        logger.info(f"✅ Order status: {result['status']}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
