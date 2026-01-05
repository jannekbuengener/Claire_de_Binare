"""
Unit tests for core.secrets module
Tests secret loading from Docker secrets, env vars, and file paths.
"""

import os
import tempfile
from pathlib import Path
import pytest
from core.secrets import read_secret, read_secret_file, validate_secrets


class TestReadSecret:
    """Tests for read_secret() function"""

    def test_read_from_docker_secret(self, tmp_path):
        """Test reading from Docker secret file"""
        # Create mock Docker secret
        secret_dir = tmp_path / "run" / "secrets"
        secret_dir.mkdir(parents=True)
        secret_file = secret_dir / "test_secret"
        secret_file.write_text("secret_value_from_docker")

        # Monkeypatch the secret path
        original_path = Path
        def mock_path(path_str):
            if "/run/secrets/test_secret" in path_str:
                return secret_file
            return original_path(path_str)

        # Test
        import core.secrets
        original_path_cls = core.secrets.Path
        core.secrets.Path = mock_path
        try:
            result = read_secret("test_secret", "TEST_ENV")
            assert result == "secret_value_from_docker"
        finally:
            core.secrets.Path = original_path_cls

    def test_fallback_to_env_var(self, monkeypatch):
        """Test fallback to environment variable when Docker secret not found"""
        monkeypatch.setenv("TEST_SECRET_ENV", "secret_from_env")
        result = read_secret("nonexistent_secret", "TEST_SECRET_ENV")
        assert result == "secret_from_env"

    def test_return_empty_when_not_found(self):
        """Test returns empty string when secret not found"""
        result = read_secret("nonexistent_secret", "NONEXISTENT_ENV")
        assert result == ""

    def test_strips_whitespace(self, tmp_path):
        """Test secret value is stripped of whitespace"""
        secret_dir = tmp_path / "run" / "secrets"
        secret_dir.mkdir(parents=True)
        secret_file = secret_dir / "test_secret"
        secret_file.write_text("  secret_with_whitespace  \n")

        import core.secrets
        original_path_cls = core.secrets.Path
        def mock_path(path_str):
            if "/run/secrets/test_secret" in path_str:
                return secret_file
            return Path(path_str)

        core.secrets.Path = mock_path
        try:
            result = read_secret("test_secret")
            assert result == "secret_with_whitespace"
        finally:
            core.secrets.Path = original_path_cls

    def test_prevents_directory_error(self, tmp_path):
        """Test prevents IsADirectoryError when secret path is a directory"""
        # Create directory instead of file
        secret_dir = tmp_path / "run" / "secrets" / "test_secret"
        secret_dir.mkdir(parents=True)

        import core.secrets
        original_path_cls = core.secrets.Path
        def mock_path(path_str):
            if "/run/secrets/test_secret" in path_str:
                return secret_dir
            return Path(path_str)

        core.secrets.Path = mock_path
        try:
            # Should not raise IsADirectoryError
            result = read_secret("test_secret", "FALLBACK_ENV")
            assert result == ""  # Returns empty (no fallback set)
        finally:
            core.secrets.Path = original_path_cls


class TestReadSecretFile:
    """Tests for read_secret_file() function"""

    def test_read_from_file_path(self, tmp_path):
        """Test reading secret from file path"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("file_secret_value")

        result = read_secret_file(str(secret_file), "FALLBACK_ENV")
        assert result == "file_secret_value"

    def test_fallback_to_env_when_file_missing(self, monkeypatch):
        """Test fallback to env var when file doesn't exist"""
        monkeypatch.setenv("FILE_FALLBACK_ENV", "env_value")
        result = read_secret_file("/nonexistent/path.txt", "FILE_FALLBACK_ENV")
        assert result == "env_value"

    def test_handles_directory_path(self, tmp_path):
        """Test handles directory path gracefully (Issue #223)"""
        # Create directory instead of file
        secret_dir = tmp_path / "secret_dir"
        secret_dir.mkdir()

        result = read_secret_file(str(secret_dir), "FALLBACK_ENV")
        assert result == ""  # Should not crash, returns empty

    def test_strips_whitespace_from_file(self, tmp_path):
        """Test file content is stripped"""
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("\n  whitespace_value  \n\n")

        result = read_secret_file(str(secret_file))
        assert result == "whitespace_value"


class TestValidateSecrets:
    """Tests for validate_secrets() function"""

    def test_validates_all_present(self):
        """Test validation passes when all secrets present"""
        result = validate_secrets("secret1", "secret2", "secret3")
        assert result is True

    def test_fails_on_empty_secret(self):
        """Test validation fails when any secret is empty"""
        result = validate_secrets("secret1", "", "secret3")
        assert result is False

    def test_fails_on_none_secret(self):
        """Test validation fails when any secret is None"""
        result = validate_secrets("secret1", None, "secret3")
        assert result is False

    def test_empty_validation_passes(self):
        """Test validation passes with no secrets to validate"""
        result = validate_secrets()
        assert result is True


class TestIntegration:
    """Integration tests for real-world scenarios"""

    def test_docker_secret_priority_over_env(self, tmp_path, monkeypatch):
        """Test Docker secret takes priority over env var"""
        # Setup both Docker secret and env var
        secret_dir = tmp_path / "run" / "secrets"
        secret_dir.mkdir(parents=True)
        secret_file = secret_dir / "priority_test"
        secret_file.write_text("docker_value")

        monkeypatch.setenv("PRIORITY_TEST_ENV", "env_value")

        import core.secrets
        original_path_cls = core.secrets.Path
        def mock_path(path_str):
            if "/run/secrets/priority_test" in path_str:
                return secret_file
            return Path(path_str)

        core.secrets.Path = mock_path
        try:
            result = read_secret("priority_test", "PRIORITY_TEST_ENV")
            assert result == "docker_value"  # Docker secret wins
        finally:
            core.secrets.Path = original_path_cls

    def test_empty_env_var_treated_as_missing(self, monkeypatch):
        """Test empty env var is treated as missing"""
        monkeypatch.setenv("EMPTY_ENV", "")
        result = read_secret("nonexistent", "EMPTY_ENV")
        assert result == ""  # Empty env var should return empty
