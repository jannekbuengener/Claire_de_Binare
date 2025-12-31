"""
Unit tests for core.config.trading_mode module
Tests trading mode configuration, safety checks, and defaults.
"""

import os
import pytest
from unittest.mock import patch
from core.config.trading_mode import (
    TradingMode,
    get_trading_mode,
    validate_trading_mode,
    get_legacy_config,
)


class TestTradingModeEnum:
    """Tests for TradingMode enum properties"""

    def test_paper_is_safe(self):
        """Test PAPER mode is safe"""
        assert TradingMode.PAPER.is_safe is True

    def test_staged_is_safe(self):
        """Test STAGED mode is safe"""
        assert TradingMode.STAGED.is_safe is True

    def test_live_is_not_safe(self):
        """Test LIVE mode is not safe"""
        assert TradingMode.LIVE.is_safe is False

    def test_paper_no_exchange(self):
        """Test PAPER mode does not use exchange"""
        assert TradingMode.PAPER.uses_exchange is False

    def test_staged_uses_exchange(self):
        """Test STAGED mode uses exchange (testnet)"""
        assert TradingMode.STAGED.uses_exchange is True

    def test_live_uses_exchange(self):
        """Test LIVE mode uses exchange"""
        assert TradingMode.LIVE.uses_exchange is True

    def test_paper_no_confirmation(self):
        """Test PAPER mode does not require confirmation"""
        assert TradingMode.PAPER.requires_confirmation is False

    def test_staged_no_confirmation(self):
        """Test STAGED mode does not require confirmation"""
        assert TradingMode.STAGED.requires_confirmation is False

    def test_live_requires_confirmation(self):
        """Test LIVE mode requires confirmation"""
        assert TradingMode.LIVE.requires_confirmation is True


class TestGetTradingMode:
    """Tests for get_trading_mode() function"""

    def test_default_is_paper(self, monkeypatch):
        """Test default mode is PAPER when no env var set"""
        monkeypatch.delenv("TRADING_MODE", raising=False)
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.PAPER

    def test_paper_mode_from_env(self, monkeypatch):
        """Test PAPER mode from environment variable"""
        monkeypatch.setenv("TRADING_MODE", "paper")
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.PAPER

    def test_staged_mode_from_env(self, monkeypatch):
        """Test STAGED mode from environment variable"""
        monkeypatch.setenv("TRADING_MODE", "staged")
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.STAGED

    def test_live_mode_with_confirmation(self, monkeypatch):
        """Test LIVE mode succeeds with confirmation"""
        monkeypatch.setenv("TRADING_MODE", "live")
        monkeypatch.setenv("LIVE_TRADING_CONFIRMED", "yes")
        mode = get_trading_mode(require_confirmation=True)
        assert mode == TradingMode.LIVE

    def test_live_mode_without_confirmation_exits(self, monkeypatch):
        """Test LIVE mode exits without confirmation"""
        monkeypatch.setenv("TRADING_MODE", "live")
        monkeypatch.delenv("LIVE_TRADING_CONFIRMED", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            get_trading_mode(require_confirmation=True)

        assert exc_info.value.code == 1

    def test_live_mode_wrong_confirmation_exits(self, monkeypatch):
        """Test LIVE mode exits with wrong confirmation value"""
        monkeypatch.setenv("TRADING_MODE", "live")
        monkeypatch.setenv("LIVE_TRADING_CONFIRMED", "no")

        with pytest.raises(SystemExit) as exc_info:
            get_trading_mode(require_confirmation=True)

        assert exc_info.value.code == 1

    def test_live_mode_skip_confirmation_check(self, monkeypatch):
        """Test LIVE mode can skip confirmation check (for testing)"""
        monkeypatch.setenv("TRADING_MODE", "live")
        monkeypatch.delenv("LIVE_TRADING_CONFIRMED", raising=False)

        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.LIVE

    def test_invalid_mode_defaults_to_paper(self, monkeypatch):
        """Test invalid mode value defaults to PAPER for safety"""
        monkeypatch.setenv("TRADING_MODE", "invalid_mode")
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.PAPER

    def test_case_insensitive_mode(self, monkeypatch):
        """Test mode string is case insensitive"""
        monkeypatch.setenv("TRADING_MODE", "PAPER")
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.PAPER

        monkeypatch.setenv("TRADING_MODE", "StAgEd")
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.STAGED

    def test_whitespace_stripped(self, monkeypatch):
        """Test mode string whitespace is stripped"""
        monkeypatch.setenv("TRADING_MODE", "  paper  ")
        mode = get_trading_mode(require_confirmation=False)
        assert mode == TradingMode.PAPER

    def test_custom_env_var(self, monkeypatch):
        """Test custom environment variable name"""
        monkeypatch.setenv("CUSTOM_MODE", "staged")
        mode = get_trading_mode(env_var="CUSTOM_MODE", require_confirmation=False)
        assert mode == TradingMode.STAGED


class TestValidateTradingMode:
    """Tests for validate_trading_mode() function"""

    def test_validate_paper_mode(self):
        """Test PAPER mode validation (no credentials required)"""
        assert validate_trading_mode(TradingMode.PAPER) is True

    def test_validate_staged_mode_with_credentials(self):
        """Test STAGED mode validation with credentials"""
        assert (
            validate_trading_mode(
                TradingMode.STAGED, api_key="test_key", api_secret="test_secret"
            )
            is True
        )

    def test_validate_staged_mode_without_credentials_fails(self):
        """Test STAGED mode validation fails without credentials"""
        with pytest.raises(ValueError, match="requires API credentials"):
            validate_trading_mode(TradingMode.STAGED)

    def test_validate_live_mode_with_credentials_and_confirmation(self, monkeypatch):
        """Test LIVE mode validation with credentials and confirmation"""
        monkeypatch.setenv("LIVE_TRADING_CONFIRMED", "yes")
        assert (
            validate_trading_mode(
                TradingMode.LIVE, api_key="live_key", api_secret="live_secret"
            )
            is True
        )

    def test_validate_live_mode_without_credentials_fails(self, monkeypatch):
        """Test LIVE mode validation fails without credentials"""
        monkeypatch.setenv("LIVE_TRADING_CONFIRMED", "yes")
        with pytest.raises(ValueError, match="requires API credentials"):
            validate_trading_mode(TradingMode.LIVE)

    def test_validate_live_mode_without_confirmation_exits(self, monkeypatch):
        """Test LIVE mode validation exits without confirmation"""
        monkeypatch.delenv("LIVE_TRADING_CONFIRMED", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            validate_trading_mode(
                TradingMode.LIVE, api_key="live_key", api_secret="live_secret"
            )

        assert exc_info.value.code == 1

    def test_validate_invalid_type_raises(self):
        """Test validation raises on invalid type"""
        with pytest.raises(ValueError, match="Invalid mode type"):
            validate_trading_mode("paper")  # String instead of enum


class TestGetLegacyConfig:
    """Tests for get_legacy_config() function"""

    def test_paper_mode_legacy_config(self):
        """Test PAPER mode legacy config mapping"""
        config = get_legacy_config(TradingMode.PAPER)
        assert config == {
            "MOCK_TRADING": True,
            "DRY_RUN": True,
            "MEXC_TESTNET": True,
        }

    def test_staged_mode_legacy_config(self):
        """Test STAGED mode legacy config mapping"""
        config = get_legacy_config(TradingMode.STAGED)
        assert config == {
            "MOCK_TRADING": False,
            "DRY_RUN": False,
            "MEXC_TESTNET": True,
        }

    def test_live_mode_legacy_config(self):
        """Test LIVE mode legacy config mapping"""
        config = get_legacy_config(TradingMode.LIVE)
        assert config == {
            "MOCK_TRADING": False,
            "DRY_RUN": False,
            "MEXC_TESTNET": False,
        }


class TestIntegration:
    """Integration tests for real-world scenarios"""

    def test_safe_startup_no_env(self, monkeypatch):
        """Test safe startup with no environment variables (defaults to PAPER)"""
        monkeypatch.delenv("TRADING_MODE", raising=False)
        monkeypatch.delenv("LIVE_TRADING_CONFIRMED", raising=False)

        mode = get_trading_mode()
        assert mode == TradingMode.PAPER
        assert mode.is_safe is True

        # Validate mode (no credentials needed for paper)
        assert validate_trading_mode(mode) is True

        # Get legacy config
        legacy = get_legacy_config(mode)
        assert legacy["MOCK_TRADING"] is True

    def test_testnet_workflow(self, monkeypatch):
        """Test complete testnet workflow"""
        monkeypatch.setenv("TRADING_MODE", "staged")

        mode = get_trading_mode()
        assert mode == TradingMode.STAGED
        assert mode.is_safe is True
        assert mode.uses_exchange is True

        # Validate with credentials
        assert (
            validate_trading_mode(mode, api_key="test", api_secret="test") is True
        )

        # Get legacy config
        legacy = get_legacy_config(mode)
        assert legacy["MEXC_TESTNET"] is True
        assert legacy["MOCK_TRADING"] is False

    def test_live_workflow_with_all_safety_checks(self, monkeypatch):
        """Test complete live workflow with all safety checks"""
        monkeypatch.setenv("TRADING_MODE", "live")
        monkeypatch.setenv("LIVE_TRADING_CONFIRMED", "yes")

        mode = get_trading_mode()
        assert mode == TradingMode.LIVE
        assert mode.is_safe is False
        assert mode.uses_exchange is True
        assert mode.requires_confirmation is True

        # Validate with credentials
        assert (
            validate_trading_mode(mode, api_key="real", api_secret="real") is True
        )

        # Get legacy config
        legacy = get_legacy_config(mode)
        assert legacy["MEXC_TESTNET"] is False
        assert legacy["MOCK_TRADING"] is False
