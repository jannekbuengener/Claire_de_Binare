"""
Unit tests for core.utils.postgres_client module.
Tests SSL mode defaults and configuration options.

Security context:
    These tests verify that the default sslmode is 'require' to prevent
    TLS downgrade attacks as documented in OWASP_TOP10_AUDIT.md (Finding #2).
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from core.utils.postgres_client import get_postgres_dsn, create_postgres_connection


class TestGetPostgresDsn:
    """Tests for get_postgres_dsn() function"""

    def test_default_sslmode_is_require(self, monkeypatch):
        """Test that default sslmode is 'require' when no env var is set"""
        # Clear any existing POSTGRES_SSLMODE env var
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)

        dsn = get_postgres_dsn()

        assert "sslmode=require" in dsn

    def test_sslmode_override_via_parameter(self, monkeypatch):
        """Test that sslmode can be overridden via function parameter"""
        # Clear env var to ensure parameter takes effect
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)

        dsn = get_postgres_dsn(sslmode="verify-full")

        assert "sslmode=verify-full" in dsn
        assert "sslmode=require" not in dsn

    def test_sslmode_override_via_env_var(self, monkeypatch):
        """Test that sslmode can be overridden via environment variable"""
        monkeypatch.setenv("POSTGRES_SSLMODE", "verify-ca")

        dsn = get_postgres_dsn()

        assert "sslmode=verify-ca" in dsn
        assert "sslmode=require" not in dsn

    def test_parameter_takes_precedence_over_env_var(self, monkeypatch):
        """Test that function parameter takes precedence over env var"""
        monkeypatch.setenv("POSTGRES_SSLMODE", "verify-ca")

        dsn = get_postgres_dsn(sslmode="verify-full")

        # Parameter should win
        assert "sslmode=verify-full" in dsn
        assert "sslmode=verify-ca" not in dsn

    def test_dsn_contains_all_ssl_params(self, monkeypatch):
        """Test that DSN includes all SSL certificate parameters when provided"""
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.delenv("POSTGRES_SSLROOTCERT", raising=False)
        monkeypatch.delenv("POSTGRES_SSLCERT", raising=False)
        monkeypatch.delenv("POSTGRES_SSLKEY", raising=False)

        dsn = get_postgres_dsn(
            sslmode="verify-full",
            sslrootcert="/path/to/ca.crt",
            sslcert="/path/to/client.crt",
            sslkey="/path/to/client.key",
        )

        assert "sslmode=verify-full" in dsn
        assert "sslrootcert=/path/to/ca.crt" in dsn
        assert "sslcert=/path/to/client.crt" in dsn
        assert "sslkey=/path/to/client.key" in dsn

    def test_dsn_format_is_correct(self, monkeypatch):
        """Test that DSN follows postgresql:// format"""
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        dsn = get_postgres_dsn(
            host="testhost",
            port=5433,
            database="testdb",
            user="testuser",
        )

        assert dsn.startswith("postgresql://")
        assert "testuser:testpassword@testhost:5433/testdb" in dsn


class TestCreatePostgresConnection:
    """Tests for create_postgres_connection() function"""

    def test_default_sslmode_is_require(self, monkeypatch):
        """Test that default sslmode is 'require' when no env var is set"""
        # Clear any existing POSTGRES_SSLMODE env var
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            create_postgres_connection()

            # Verify psycopg2.connect was called with sslmode='require'
            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs["sslmode"] == "require"

    def test_sslmode_override_via_parameter(self, monkeypatch):
        """Test that sslmode can be overridden via function parameter"""
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            create_postgres_connection(sslmode="disable")

            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs["sslmode"] == "disable"

    def test_sslmode_override_via_env_var(self, monkeypatch):
        """Test that sslmode can be overridden via environment variable"""
        monkeypatch.setenv("POSTGRES_SSLMODE", "prefer")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            create_postgres_connection()

            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs["sslmode"] == "prefer"

    def test_parameter_takes_precedence_over_env_var(self, monkeypatch):
        """Test that function parameter takes precedence over env var"""
        monkeypatch.setenv("POSTGRES_SSLMODE", "prefer")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            create_postgres_connection(sslmode="verify-full")

            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs["sslmode"] == "verify-full"

    def test_ssl_cert_file_not_found_raises_error(self, monkeypatch, tmp_path):
        """Test that FileNotFoundError is raised for missing SSL cert files"""
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with pytest.raises(FileNotFoundError) as exc_info:
            create_postgres_connection(sslrootcert="/nonexistent/ca.crt")

        assert "SSL root cert not found" in str(exc_info.value)

    def test_ssl_client_cert_not_found_raises_error(self, monkeypatch, tmp_path):
        """Test that FileNotFoundError is raised for missing SSL client cert"""
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with pytest.raises(FileNotFoundError) as exc_info:
            create_postgres_connection(sslcert="/nonexistent/client.crt")

        assert "SSL client cert not found" in str(exc_info.value)

    def test_ssl_client_key_not_found_raises_error(self, monkeypatch, tmp_path):
        """Test that FileNotFoundError is raised for missing SSL client key"""
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with pytest.raises(FileNotFoundError) as exc_info:
            create_postgres_connection(sslkey="/nonexistent/client.key")

        assert "SSL client key not found" in str(exc_info.value)

    def test_connection_uses_all_ssl_params(self, monkeypatch, tmp_path):
        """Test that connection includes all SSL certificate parameters"""
        # Create temporary cert files
        ca_cert = tmp_path / "ca.crt"
        client_cert = tmp_path / "client.crt"
        client_key = tmp_path / "client.key"
        ca_cert.write_text("CA CERT")
        client_cert.write_text("CLIENT CERT")
        client_key.write_text("CLIENT KEY")

        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            create_postgres_connection(
                sslmode="verify-full",
                sslrootcert=str(ca_cert),
                sslcert=str(client_cert),
                sslkey=str(client_key),
            )

            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs["sslmode"] == "verify-full"
            assert call_kwargs["sslrootcert"] == str(ca_cert)
            assert call_kwargs["sslcert"] == str(client_cert)
            assert call_kwargs["sslkey"] == str(client_key)


class TestSecurityRequirements:
    """Tests specifically validating OWASP security requirements"""

    def test_sslmode_require_prevents_downgrade_attack(self, monkeypatch):
        """
        Verify that default sslmode='require' prevents TLS downgrade attacks.

        OWASP Finding #2: sslmode=prefer allows MITM attackers to force
        unencrypted connections. The default must be 'require' or stronger.
        """
        # Clear all SSL-related env vars
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)
        monkeypatch.delenv("POSTGRES_SSLROOTCERT", raising=False)
        monkeypatch.delenv("POSTGRES_SSLCERT", raising=False)
        monkeypatch.delenv("POSTGRES_SSLKEY", raising=False)

        # Test get_postgres_dsn
        dsn = get_postgres_dsn()
        assert "sslmode=require" in dsn, "get_postgres_dsn must default to sslmode=require"

        # Test create_postgres_connection
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpassword")

        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn

            create_postgres_connection()

            call_kwargs = mock_connect.call_args.kwargs
            assert call_kwargs["sslmode"] == "require", (
                "create_postgres_connection must default to sslmode=require"
            )

    def test_vulnerable_sslmodes_require_explicit_opt_in(self, monkeypatch):
        """
        Verify that vulnerable sslmodes (disable, allow, prefer) require explicit opt-in.

        Users must explicitly set POSTGRES_SSLMODE or pass sslmode parameter
        to use weaker modes that are vulnerable to downgrade attacks.
        """
        # Without any configuration, default should be secure
        monkeypatch.delenv("POSTGRES_SSLMODE", raising=False)

        dsn = get_postgres_dsn()
        assert "sslmode=require" in dsn

        # Vulnerable modes must be explicitly requested
        for vulnerable_mode in ["disable", "allow", "prefer"]:
            dsn = get_postgres_dsn(sslmode=vulnerable_mode)
            assert f"sslmode={vulnerable_mode}" in dsn
