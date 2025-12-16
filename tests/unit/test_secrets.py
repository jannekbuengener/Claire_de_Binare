"""Unit tests for core.domain.secrets module."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.domain.secrets import get_secret


def test_get_secret_from_docker_secrets(tmp_path):
    """Test reading secret from Docker secrets file."""
    secret_file = tmp_path / "test_secret"
    secret_file.write_text("my_secret_value\n")
    
    with patch('core.domain.secrets.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = "my_secret_value\n"
        
        result = get_secret("test_secret", "TEST_ENV", "default")
        assert result == "my_secret_value"


def test_get_secret_from_environment():
    """Test reading secret from environment variable when Docker secret doesn't exist."""
    with patch('core.domain.secrets.Path') as mock_path:
        mock_path.return_value.exists.return_value = False
        with patch.dict('os.environ', {'TEST_ENV': 'env_value'}):
            result = get_secret("test_secret", "TEST_ENV", "default")
            assert result == "env_value"


def test_get_secret_default_value():
    """Test returning default value when neither Docker secret nor env var exists."""
    with patch('core.domain.secrets.Path') as mock_path:
        mock_path.return_value.exists.return_value = False
        with patch.dict('os.environ', {}, clear=True):
            result = get_secret("test_secret", "NONEXISTENT_ENV", "default_value")
            assert result == "default_value"


def test_get_secret_strips_whitespace(tmp_path):
    """Test that secret values are stripped of leading/trailing whitespace."""
    with patch('core.domain.secrets.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.read_text.return_value = "  secret_with_spaces  \n"
        
        result = get_secret("test_secret", "TEST_ENV")
        assert result == "secret_with_spaces"
