"""Unit tests for services.market.email_alerter"""

import time
from unittest.mock import MagicMock, patch

import pytest

from services.market.email_alerter import EmailAlerter, get_alerter


@pytest.fixture()
def alerter():
    """Create an EmailAlerter with fake credentials (enabled)."""
    with patch("services.market.email_alerter._read_secret", return_value=None):
        with patch.dict(
            "os.environ",
            {
                "ALERT_EMAIL_FROM": "test@example.com",
                "ALERT_EMAIL_TO": "ops@example.com",
                "ALERT_EMAIL_PASSWORD": "fake-password",
                "SMTP_SERVER": "localhost",
                "SMTP_PORT": "2525",
            },
        ):
            yield EmailAlerter(dedup_window=1)


@pytest.fixture()
def disabled_alerter():
    """Create an EmailAlerter with missing credentials (disabled)."""
    with patch("services.market.email_alerter._read_secret", return_value=None):
        with patch.dict("os.environ", {}, clear=True):
            yield EmailAlerter()


class TestEmailAlerterInit:
    def test_enabled_with_credentials(self, alerter):
        assert alerter.enabled is True
        assert alerter.sender == "test@example.com"
        assert alerter.recipient == "ops@example.com"

    def test_disabled_without_credentials(self, disabled_alerter):
        assert disabled_alerter.enabled is False

    def test_secrets_take_precedence(self):
        def fake_secret(name):
            return {
                "smtp_from": "secret@ex.com",
                "alert_email_to": "secops@ex.com",
                "smtp_password": "s3cr3t",
            }.get(name)

        with patch(
            "services.market.email_alerter._read_secret", side_effect=fake_secret
        ):
            with patch.dict(
                "os.environ", {"ALERT_EMAIL_FROM": "env@ex.com"}, clear=True
            ):
                a = EmailAlerter()
                assert a.sender == "secret@ex.com"
                assert a.enabled is True


class TestSendAlert:
    def test_disabled_returns_false(self, disabled_alerter):
        assert disabled_alerter.send_alert("sub", "msg") is False

    @patch("services.market.email_alerter.smtplib.SMTP")
    def test_sends_email(self, mock_smtp_cls, alerter):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = alerter.send_alert("Test Subject", "body", severity="CRITICAL")

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()

    @patch("services.market.email_alerter.smtplib.SMTP")
    def test_smtp_error_returns_false(self, mock_smtp_cls, alerter):
        import smtplib

        mock_smtp_cls.return_value.__enter__ = MagicMock(
            side_effect=smtplib.SMTPException("fail")
        )
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = alerter.send_alert("Fail", "msg")
        assert result is False


class TestDeduplication:
    @patch("services.market.email_alerter.smtplib.SMTP")
    def test_duplicate_suppressed(self, mock_smtp_cls, alerter):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        assert alerter.send_alert("dup", "msg") is True
        assert alerter.send_alert("dup", "msg") is True  # deduplicated
        # SMTP send called only once
        assert mock_server.send_message.call_count == 1

    @patch("services.market.email_alerter.smtplib.SMTP")
    def test_different_severity_not_deduplicated(self, mock_smtp_cls, alerter):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        alerter.send_alert("same", "msg", severity="INFO")
        alerter.send_alert("same", "msg", severity="CRITICAL")
        assert mock_server.send_message.call_count == 2

    @patch("services.market.email_alerter.smtplib.SMTP")
    def test_dedup_expires(self, mock_smtp_cls, alerter):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        alerter.send_alert("expire", "msg")
        # Manipulate sent timestamp to simulate expiry
        for key in alerter._sent:
            alerter._sent[key] -= alerter._dedup_window + 1
        alerter.send_alert("expire", "msg")
        assert mock_server.send_message.call_count == 2


class TestSendMarketAlert:
    @patch("services.market.email_alerter.smtplib.SMTP")
    def test_market_alert_formats_correctly(self, mock_smtp_cls, alerter):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = alerter.send_market_alert("BTC/USDT", "Price spike", {"delta": "5%"})
        assert result is True
        mock_server.send_message.assert_called_once()


class TestGlobalInstance:
    def test_get_alerter_returns_instance(self):
        from services.market import email_alerter as mod

        mod._alerter = None
        with patch("services.market.email_alerter._read_secret", return_value=None):
            with patch.dict("os.environ", {}, clear=True):
                a = get_alerter()
                assert isinstance(a, EmailAlerter)
                assert get_alerter() is a  # same instance
        mod._alerter = None
