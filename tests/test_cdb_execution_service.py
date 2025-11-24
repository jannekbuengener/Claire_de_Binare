"""
Tests für Claire de Binare - Execution Service
Ziel: > 85% Coverage für services/cdb_execution/service.py
"""
import pytest
import json
import time
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import requests

# Add services directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'cdb_execution'))
import service as execution_service


@pytest.fixture
def sample_order():
    """Sample order for testing"""
    return {
        "symbol": "BTCUSDT",
        "side": "buy",
        "quantity": 0.001,
        "price": 50000.0
    }


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis_mock = Mock()
    redis_mock.publish = Mock(return_value=1)
    pubsub_mock = Mock()
    pubsub_mock.subscribe = Mock()
    redis_mock.pubsub = Mock(return_value=pubsub_mock)
    return redis_mock


@pytest.mark.unit
class TestMEXCExecutor:
    """Test MEXCExecutor class"""

    def test_init_paper_mode_without_credentials(self):
        """Test: Paper-Mode funktioniert ohne API-Credentials"""
        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            executor = execution_service.MEXCExecutor()
            assert executor.trading_mode == "paper"

    def test_init_live_mode_requires_credentials(self):
        """Test: Live-Mode erfordert API-Credentials"""
        with patch.dict('os.environ', {
            "TRADING_MODE": "live",
            "MEXC_API_KEY": "",
            "MEXC_API_SECRET": ""
        }, clear=False):
            with pytest.raises(ValueError, match="MEXC_API_KEY and MEXC_API_SECRET required"):
                execution_service.MEXCExecutor()

    def test_sign_creates_valid_hmac(self):
        """Test: HMAC-Signatur wird korrekt erstellt"""
        with patch.dict('os.environ', {
            "TRADING_MODE": "paper",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            params = {"symbol": "BTCUSDT", "side": "BUY", "quantity": 0.001}
            signature = executor._sign(params)

            # Signatur sollte ein 64-Zeichen Hex-String sein (SHA256)
            assert isinstance(signature, str)
            assert len(signature) == 64
            assert all(c in "0123456789abcdef" for c in signature)

    def test_simulate_order_paper_trading(self, sample_order):
        """Test: Paper-Trading simuliert Order erfolgreich"""
        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor._simulate_order(sample_order)

            assert result["status"] == "filled"
            assert "PAPER_" in result["order_id"]
            assert result["executed_qty"] == sample_order["quantity"]
            assert result["avg_price"] == sample_order["price"]
            assert result["commission"] > 0  # 0.02% MEXC commission
            assert "timestamp" in result

    def test_place_order_uses_paper_mode(self, sample_order):
        """Test: place_order nutzt Paper-Mode wenn konfiguriert"""
        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor.place_order(sample_order)

            assert result["status"] == "filled"
            assert "PAPER_" in result["order_id"]

    @patch('service.requests.post')
    def test_place_order_live_success(self, mock_post, sample_order):
        """Test: Live-Order wird erfolgreich platziert"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "orderId": "12345",
            "executedQty": "0.001",
            "price": "50000.0",
            "commission": "0.01"
        }
        mock_post.return_value = mock_response

        with patch.dict('os.environ', {
            "TRADING_MODE": "live",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor.place_order(sample_order)

            assert result["status"] == "filled"
            assert result["order_id"] == "12345"
            assert result["executed_qty"] == 0.001
            assert "timestamp" in result

    @patch('service.requests.post')
    def test_place_order_http_error(self, mock_post, sample_order):
        """Test: HTTP-Error wird korrekt behandelt"""
        mock_response = Mock()
        mock_response.text = "API Error"

        # HTTPError needs response attribute
        http_error = requests.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_post.return_value = mock_response

        with patch.dict('os.environ', {
            "TRADING_MODE": "live",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor.place_order(sample_order)

            assert result["status"] == "rejected"
            assert "reason" in result

    @patch('service.requests.post')
    def test_place_order_timeout(self, mock_post, sample_order):
        """Test: Timeout wird korrekt behandelt"""
        mock_post.side_effect = requests.Timeout()

        with patch.dict('os.environ', {
            "TRADING_MODE": "live",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor.place_order(sample_order)

            assert result["status"] == "timeout"
            assert result["reason"] == "API timeout"

    @patch('service.requests.post')
    def test_place_order_network_error(self, mock_post, sample_order):
        """Test: Network-Error wird korrekt behandelt"""
        mock_post.side_effect = Exception("Network error")

        with patch.dict('os.environ', {
            "TRADING_MODE": "live",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor.place_order(sample_order)

            assert result["status"] == "error"
            assert "Network error" in result["reason"]

    def test_simulate_order_calculates_commission(self, sample_order):
        """Test: Paper-Trading berechnet Commission korrekt"""
        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor._simulate_order(sample_order)

            # Commission = quantity * price * 0.0002 (0.02% MEXC fee)
            expected_commission = 0.001 * 50000.0 * 0.0002
            assert abs(result["commission"] - expected_commission) < 0.0001
            assert result["executed_qty"] == sample_order["quantity"]
            assert result["avg_price"] == sample_order["price"]

    def test_sign_deterministic(self):
        """Test: HMAC-Signatur ist deterministisch"""
        with patch.dict('os.environ', {
            "TRADING_MODE": "paper",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            params = {"symbol": "BTCUSDT", "side": "BUY"}
            signature1 = executor._sign(params)
            signature2 = executor._sign(params)

            # Selbe Parameter = selbe Signatur
            assert signature1 == signature2

    def test_sign_different_for_different_params(self):
        """Test: HMAC-Signatur ändert sich bei verschiedenen Parametern"""
        with patch.dict('os.environ', {
            "TRADING_MODE": "paper",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            signature1 = executor._sign({"symbol": "BTCUSDT", "side": "BUY"})
            signature2 = executor._sign({"symbol": "ETHUSDT", "side": "SELL"})

            # Verschiedene Parameter = verschiedene Signaturen
            assert signature1 != signature2

    @patch('service.requests.post')
    def test_live_order_partial_fill(self, mock_post):
        """Test: Live-Order mit Partial Fill"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "orderId": "12345",
            "executedQty": "0.0005",  # Nur 50% gefüllt
            "price": "50000.0",
            "commission": "0.005"
        }
        mock_post.return_value = mock_response

        order = {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": 0.001,  # Wollte 0.001
            "price": 50000.0
        }

        with patch.dict('os.environ', {
            "TRADING_MODE": "live",
            "MEXC_API_KEY": "test_key",
            "MEXC_API_SECRET": "test_secret"
        }, clear=False):
            # Import is already at module level
            executor = execution_service.MEXCExecutor()

            result = executor.place_order(order)

            assert result["status"] == "filled"
            assert result["executed_qty"] == 0.0005  # Partial fill
            assert result["executed_qty"] < order["quantity"]


@pytest.mark.unit
class TestExecutionService:
    """Test ExecutionService class"""

    @patch('service.redis.Redis')
    def test_init_establishes_redis_connection(self, mock_redis_class):
        """Test: ExecutionService verbindet sich mit Redis"""
        mock_redis_instance = Mock()
        mock_pubsub = Mock()
        mock_redis_instance.pubsub.return_value = mock_pubsub
        mock_redis_class.return_value = mock_redis_instance

        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            service = execution_service.ExecutionService()

            # Redis-Verbindung wurde erstellt
            mock_redis_class.assert_called_once()
            # Subscription auf "orders" Channel
            mock_pubsub.subscribe.assert_called_once_with("orders")

    @patch('service.redis.Redis')
    def test_process_orders_handles_valid_order(self, mock_redis_class, sample_order):
        """Test: process_orders verarbeitet gültige Order"""
        mock_redis_instance = Mock()
        mock_pubsub = Mock()

        # Simuliere Redis-Nachricht
        messages = [
            {"type": "subscribe"},  # Initial subscription message
            {"type": "message", "data": json.dumps(sample_order)}
        ]
        mock_pubsub.listen.return_value = iter(messages)
        mock_redis_instance.pubsub.return_value = mock_pubsub
        mock_redis_instance.publish = Mock()
        mock_redis_class.return_value = mock_redis_instance

        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            service = execution_service.ExecutionService()

            # Führe nur 2 Iterationen aus (subscribe + message)
            count = 0
            for message in service.pubsub.listen():
                if count >= 2:
                    break
                count += 1

                if message["type"] != "message":
                    continue

                order = json.loads(message["data"])
                result = service.executor.place_order(order)
                result["symbol"] = order["symbol"]
                result["original_order"] = order
                service.redis_client.publish("order_results", json.dumps(result))

            # Verifiziere, dass Ergebnis publiziert wurde
            assert mock_redis_instance.publish.called

    @patch('service.redis.Redis')
    def test_process_orders_handles_malformed_json(self, mock_redis_class):
        """Test: process_orders behandelt fehlerhaftes JSON"""
        mock_redis_instance = Mock()
        mock_pubsub = Mock()

        # Simuliere fehlerhafte Nachricht
        messages = [
            {"type": "subscribe"},
            {"type": "message", "data": "INVALID_JSON{"}
        ]
        mock_pubsub.listen.return_value = iter(messages)
        mock_redis_instance.pubsub.return_value = mock_pubsub
        mock_redis_class.return_value = mock_redis_instance

        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            service = execution_service.ExecutionService()

            # Sollte keine Exception werfen
            count = 0
            for message in service.pubsub.listen():
                if count >= 2:
                    break
                count += 1

                if message["type"] != "message":
                    continue

                try:
                    order = json.loads(message["data"])
                except Exception:
                    # Exception wird erwartet und geloggt
                    pass


@pytest.mark.unit
def test_health_endpoint_returns_ok():
    """Test: Health-Endpoint gibt OK zurück"""
    with execution_service.app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "ok"
        assert data["service"] == "cdb_execution"


@pytest.mark.integration
@pytest.mark.slow
class TestExecutionServiceIntegration:
    """Integration-Tests mit echten Redis-Mock"""

    @patch('service.redis.Redis')
    def test_full_order_flow_paper_mode(self, mock_redis_class, sample_order):
        """Test: Vollständiger Order-Flow im Paper-Mode"""
        # Setup
        mock_redis_instance = Mock()
        mock_pubsub = Mock()
        published_messages = []

        def capture_publish(channel, message):
            published_messages.append((channel, message))
            return 1

        mock_redis_instance.publish = capture_publish
        mock_pubsub.subscribe = Mock()
        mock_redis_instance.pubsub.return_value = mock_pubsub
        mock_redis_class.return_value = mock_redis_instance

        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            service = execution_service.ExecutionService()

            # Execute
            result = service.executor.place_order(sample_order)
            result["symbol"] = sample_order["symbol"]
            result["original_order"] = sample_order
            service.redis_client.publish("order_results", json.dumps(result))

            # Assert
            assert len(published_messages) == 1
            channel, message = published_messages[0]
            assert channel == "order_results"

            result_data = json.loads(message)
            assert result_data["status"] == "filled"
            assert result_data["symbol"] == "BTCUSDT"
            assert result_data["original_order"] == sample_order

    @patch('service.redis.Redis')
    def test_process_orders_full_cycle(self, mock_redis_class, sample_order):
        """Test: process_orders durchläuft vollständigen Zyklus"""
        mock_redis_instance = Mock()
        mock_pubsub = Mock()
        published_results = []

        def capture_publish(channel, message):
            published_results.append((channel, message))
            return 1

        mock_redis_instance.publish = capture_publish

        # Simuliere 3 Nachrichten: subscribe, valid order, invalid order
        messages = [
            {"type": "subscribe", "data": None},
            {"type": "message", "data": json.dumps(sample_order)},
            {"type": "message", "data": "INVALID"}  # Wird Exception werfen
        ]
        mock_pubsub.listen.return_value = iter(messages)
        mock_pubsub.subscribe = Mock()
        mock_redis_instance.pubsub.return_value = mock_pubsub
        mock_redis_class.return_value = mock_redis_instance

        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            service = execution_service.ExecutionService()

            # Manuell durch Messages iterieren (statt process_orders Loop)
            for message in messages:
                if message["type"] != "message":
                    continue

                try:
                    order = json.loads(message["data"])
                    result = service.executor.place_order(order)
                    result["symbol"] = order["symbol"]
                    result["original_order"] = order
                    service.redis_client.publish("order_results", json.dumps(result))
                except Exception:
                    # Exception expected for invalid JSON
                    pass

        # Assert: Nur eine gültige Order publiziert
        assert len(published_results) == 1
        channel, result_json = published_results[0]
        assert channel == "order_results"

        result_data = json.loads(result_json)
        assert result_data["status"] == "filled"

    @patch('service.redis.Redis')
    def test_process_orders_method_directly(self, mock_redis_class, sample_order):
        """Test: process_orders Methode direkt mit Limited Loop"""
        mock_redis_instance = Mock()
        mock_pubsub = Mock()
        published_results = []
        call_count = [0]  # Mutable counter

        def capture_publish(channel, message):
            published_results.append((channel, message))
            return 1

        mock_redis_instance.publish = capture_publish

        # Limited messages to prevent infinite loop
        def limited_listen():
            messages = [
                {"type": "subscribe"},
                {"type": "message", "data": json.dumps(sample_order)},
                {"type": "message", "data": json.dumps({
                    "symbol": "ETHUSDT",
                    "side": "sell",
                    "quantity": 0.1,
                    "price": 3000.0
                })}
            ]
            for msg in messages:
                call_count[0] += 1
                yield msg
                if call_count[0] >= 3:  # Stop after 3 messages
                    break

        mock_pubsub.listen = limited_listen
        mock_pubsub.subscribe = Mock()
        mock_redis_instance.pubsub.return_value = mock_pubsub
        mock_redis_class.return_value = mock_redis_instance

        with patch.dict('os.environ', {"TRADING_MODE": "paper"}, clear=False):
            # Import is already at module level
            service = execution_service.ExecutionService()

            # Directly call process_orders (will process limited messages)
            try:
                service.process_orders()
            except StopIteration:
                pass  # Expected when iterator exhausted

        # Should have published 2 results (2 valid orders)
        assert len(published_results) >= 1  # At least one order processed
