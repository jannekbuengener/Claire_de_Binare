"""
Unit tests for core.auth module
Tests Redis and Postgres auth validation to prevent restart loops.
"""

import pytest
from unittest.mock import Mock, patch
import redis
import psycopg2
from core.auth import validate_redis_auth, validate_postgres_auth, validate_all_auth


class TestValidateRedisAuth:
    """Tests for validate_redis_auth() function"""

    @patch("core.auth.redis.Redis")
    def test_redis_auth_success(self, mock_redis_class):
        """Test successful Redis authentication"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        success, msg = validate_redis_auth("localhost", 6379, "password")

        assert success is True
        assert "successful" in msg
        mock_redis_class.assert_called_once_with(
            host="localhost", port=6379, password="password", db=0, socket_timeout=5
        )
        mock_client.ping.assert_called_once()

    @patch("core.auth.redis.Redis")
    def test_redis_auth_failure_bad_password(self, mock_redis_class):
        """Test Redis authentication failure with wrong password"""
        mock_client = Mock()
        mock_client.ping.side_effect = redis.AuthenticationError("ERR invalid password")
        mock_redis_class.return_value = mock_client

        success, msg = validate_redis_auth("localhost", 6379, "wrong_password")

        assert success is False
        assert "authentication FAILED" in msg
        assert "Invalid password" in msg

    @patch("core.auth.redis.Redis")
    def test_redis_connection_error(self, mock_redis_class):
        """Test Redis connection failure (cannot reach server)"""
        mock_redis_class.side_effect = redis.ConnectionError("Connection refused")

        success, msg = validate_redis_auth("localhost", 6379, "password")

        assert success is False
        assert "connection FAILED" in msg
        assert "Cannot reach" in msg

    @patch("core.auth.redis.Redis")
    def test_redis_auth_no_password(self, mock_redis_class):
        """Test Redis auth with no password (None)"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        success, msg = validate_redis_auth("localhost", 6379, None)

        assert success is True
        mock_redis_class.assert_called_once_with(
            host="localhost", port=6379, password=None, db=0, socket_timeout=5
        )

    @patch("core.auth.redis.Redis")
    def test_redis_auth_custom_db(self, mock_redis_class):
        """Test Redis auth with custom database number"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client

        success, msg = validate_redis_auth("localhost", 6379, "password", db=5)

        assert success is True
        mock_redis_class.assert_called_once_with(
            host="localhost", port=6379, password="password", db=5, socket_timeout=5
        )


class TestValidatePostgresAuth:
    """Tests for validate_postgres_auth() function"""

    @patch("core.auth.psycopg2.connect")
    def test_postgres_auth_success(self, mock_connect):
        """Test successful Postgres authentication"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        success, msg = validate_postgres_auth(
            "localhost", 5432, "user", "password", "database"
        )

        assert success is True
        assert "successful" in msg
        mock_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            user="user",
            password="password",
            database="database",
            connect_timeout=5,
        )
        mock_conn.close.assert_called_once()

    @patch("core.auth.psycopg2.connect")
    def test_postgres_auth_failure_bad_password(self, mock_connect):
        """Test Postgres authentication failure with wrong password"""
        mock_connect.side_effect = psycopg2.OperationalError(
            "FATAL: password authentication failed for user \"user\""
        )

        success, msg = validate_postgres_auth(
            "localhost", 5432, "user", "wrong_password", "database"
        )

        assert success is False
        assert "authentication FAILED" in msg
        assert "Invalid password" in msg

    @patch("core.auth.psycopg2.connect")
    def test_postgres_connection_error_unreachable(self, mock_connect):
        """Test Postgres connection failure (cannot reach server)"""
        mock_connect.side_effect = psycopg2.OperationalError(
            "could not connect to server: Connection refused"
        )

        success, msg = validate_postgres_auth(
            "localhost", 5432, "user", "password", "database"
        )

        assert success is False
        assert "connection FAILED" in msg
        assert "Cannot reach" in msg

    @patch("core.auth.psycopg2.connect")
    def test_postgres_database_not_exist(self, mock_connect):
        """Test Postgres database does not exist error"""
        mock_connect.side_effect = psycopg2.OperationalError(
            "FATAL: database \"nonexistent\" does not exist"
        )

        success, msg = validate_postgres_auth(
            "localhost", 5432, "user", "password", "nonexistent"
        )

        assert success is False
        assert "does not exist" in msg

    @patch("core.auth.psycopg2.connect")
    def test_postgres_generic_error(self, mock_connect):
        """Test Postgres generic operational error"""
        mock_connect.side_effect = psycopg2.OperationalError(
            "Some other error"
        )

        success, msg = validate_postgres_auth(
            "localhost", 5432, "user", "password", "database"
        )

        assert success is False
        assert "FAILED" in msg


class TestValidateAllAuth:
    """Tests for validate_all_auth() function"""

    @patch("core.auth.validate_postgres_auth")
    @patch("core.auth.validate_redis_auth")
    def test_all_auth_success(self, mock_redis_auth, mock_pg_auth):
        """Test successful validation of both Redis and Postgres"""
        mock_redis_auth.return_value = (True, "Redis OK")
        mock_pg_auth.return_value = (True, "Postgres OK")

        result = validate_all_auth(
            "redis_host", 6379, "redis_pass",
            "pg_host", 5432, "pg_user", "pg_pass", "pg_db"
        )

        assert result is True
        mock_redis_auth.assert_called_once_with("redis_host", 6379, "redis_pass")
        mock_pg_auth.assert_called_once_with(
            "pg_host", 5432, "pg_user", "pg_pass", "pg_db"
        )

    @patch("core.auth.validate_postgres_auth")
    @patch("core.auth.validate_redis_auth")
    @patch("core.auth.sys.exit")
    def test_all_auth_redis_fails(self, mock_exit, mock_redis_auth, mock_pg_auth):
        """Test validation fails when Redis auth fails (exits process)"""
        mock_redis_auth.return_value = (False, "Redis connection failed")

        validate_all_auth(
            "redis_host", 6379, "redis_pass",
            "pg_host", 5432, "pg_user", "pg_pass", "pg_db"
        )

        mock_exit.assert_called_once_with(1)
        mock_redis_auth.assert_called_once()
        # Postgres should not be called if Redis fails
        mock_pg_auth.assert_not_called()

    @patch("core.auth.validate_postgres_auth")
    @patch("core.auth.validate_redis_auth")
    @patch("core.auth.sys.exit")
    def test_all_auth_postgres_fails(self, mock_exit, mock_redis_auth, mock_pg_auth):
        """Test validation fails when Postgres auth fails (exits process)"""
        mock_redis_auth.return_value = (True, "Redis OK")
        mock_pg_auth.return_value = (False, "Postgres auth failed")

        validate_all_auth(
            "redis_host", 6379, "redis_pass",
            "pg_host", 5432, "pg_user", "pg_pass", "pg_db"
        )

        mock_exit.assert_called_once_with(1)
        mock_redis_auth.assert_called_once()
        mock_pg_auth.assert_called_once()

    @patch("core.auth.validate_postgres_auth")
    @patch("core.auth.validate_redis_auth")
    @patch("core.auth.sys.exit")
    def test_all_auth_both_fail(self, mock_exit, mock_redis_auth, mock_pg_auth):
        """Test validation fails when both Redis and Postgres fail"""
        mock_redis_auth.return_value = (False, "Redis failed")

        validate_all_auth(
            "redis_host", 6379, "redis_pass",
            "pg_host", 5432, "pg_user", "pg_pass", "pg_db"
        )

        # Should exit on first failure (Redis)
        mock_exit.assert_called_once_with(1)
        mock_redis_auth.assert_called_once()
        mock_pg_auth.assert_not_called()
