"""Unit tests for core.utils.redis_client connection pooling."""

from unittest.mock import MagicMock, patch

import pytest
import redis

import core.utils.redis_client as redis_client_module
from core.utils.redis_client import create_redis_client, get_redis_connection_pool


@pytest.fixture(autouse=True)
def clear_pool_cache():
    redis_client_module._POOL_CACHE.clear()
    redis_client_module._PINGED_POOLS.clear()
    yield
    redis_client_module._POOL_CACHE.clear()
    redis_client_module._PINGED_POOLS.clear()


def test_get_redis_connection_pool_reuses_identical_config():
    with patch.object(redis_client_module.redis, "ConnectionPool") as pool_cls:
        pool_cls.side_effect = [MagicMock(name="pool_a"), MagicMock(name="pool_b")]

        first = get_redis_connection_pool(
            host="redis.internal",
            port=6379,
            password="secret",
            db=0,
            decode_responses=True,
        )
        second = get_redis_connection_pool(
            host="redis.internal",
            port=6379,
            password="secret",
            db=0,
            decode_responses=True,
        )

    assert first is second
    pool_cls.assert_called_once()


def test_get_redis_connection_pool_distinct_for_different_db():
    with patch.object(redis_client_module.redis, "ConnectionPool") as pool_cls:
        pool_cls.side_effect = [MagicMock(name="pool_0"), MagicMock(name="pool_1")]

        pool_0 = get_redis_connection_pool(host="h", port=6379, db=0)
        pool_1 = get_redis_connection_pool(host="h", port=6379, db=1)

    assert pool_0 is not pool_1
    assert pool_cls.call_count == 2


def test_create_redis_client_uses_pool_and_pings_once():
    mock_pool = MagicMock(name="pool")
    mock_client = MagicMock(name="client")
    mock_client.ping.return_value = True

    with patch.object(redis_client_module.redis, "ConnectionPool", return_value=mock_pool):
        with patch.object(redis_client_module.redis, "Redis", return_value=mock_client) as redis_cls:
            first = create_redis_client(host="h", port=6379, password="p")
            second = create_redis_client(host="h", port=6379, password="p")

    redis_cls.assert_called()
    for call in redis_cls.call_args_list:
        assert call.kwargs.get("connection_pool") is mock_pool

    assert first is mock_client
    assert second is mock_client
    mock_client.ping.assert_called_once()


def test_create_redis_client_evicts_pool_on_ping_failure_and_retries():
    mock_pool_fail = MagicMock(name="pool_fail")
    mock_pool_ok = MagicMock(name="pool_ok")
    mock_client_fail = MagicMock(name="client_fail")
    mock_client_ok = MagicMock(name="client_ok")
    mock_client_fail.ping.side_effect = redis.ConnectionError("redis unavailable")
    mock_client_ok.ping.return_value = True

    with patch.object(
        redis_client_module.redis, "ConnectionPool", side_effect=[mock_pool_fail, mock_pool_ok]
    ) as pool_cls:
        with patch.object(
            redis_client_module.redis,
            "Redis",
            side_effect=[mock_client_fail, mock_client_ok],
        ):
            with pytest.raises(redis.ConnectionError, match="redis unavailable"):
                create_redis_client(host="h", port=6379, password="p")

            assert redis_client_module._POOL_CACHE == {}
            assert redis_client_module._PINGED_POOLS == set()
            mock_pool_fail.disconnect.assert_called_once()

            client = create_redis_client(host="h", port=6379, password="p")

    assert pool_cls.call_count == 2
    assert client is mock_client_ok
    mock_client_ok.ping.assert_called_once()
    assert mock_pool_ok in redis_client_module._POOL_CACHE.values()
