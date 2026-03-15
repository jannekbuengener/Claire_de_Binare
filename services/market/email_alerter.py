"""
Email Alerter Module - Market Service
Sends email alerts for critical market events via SMTP.

Credentials are read from Docker secrets (/run/secrets/) for container
deployments, with environment variable fallback for local development.
"""

import logging
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.utils.clock import utcnow

logger = logging.getLogger(__name__)


def _read_secret(name: str) -> Optional[str]:
    """Read a Docker-mounted secret, return None on failure."""
    path = f"/run/secrets/{name}"
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning("Failed to read secret %s: %s", path, e)
        return None


class EmailAlerter:
    """
    Email alerting for critical market events.

    Reads SMTP credentials from Docker secrets first, falls back to
    environment variables for local development.

    Includes time-window deduplication to prevent alert spam.
    """

    # Default dedup window: suppress identical alerts within 300s
    DEDUP_WINDOW_SECONDS = 300

    def __init__(self, dedup_window: Optional[int] = None):
        self.smtp_host = _read_secret("smtp_host") or os.getenv(
            "SMTP_SERVER", "smtp.gmail.com"
        )
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender = _read_secret("smtp_from") or os.getenv("ALERT_EMAIL_FROM")
        self.recipient = _read_secret("alert_email_to") or os.getenv("ALERT_EMAIL_TO")
        self.password = _read_secret("smtp_password") or os.getenv(
            "ALERT_EMAIL_PASSWORD"
        )

        self.enabled = all([self.sender, self.recipient, self.password])
        self._dedup_window = (
            dedup_window if dedup_window is not None else self.DEDUP_WINDOW_SECONDS
        )
        # key -> last-sent monotonic timestamp
        self._sent: dict[str, float] = {}

        if not self.enabled:
            logger.warning(
                "EmailAlerter: disabled — missing SMTP credentials "
                "(need smtp_from, alert_email_to, smtp_password)"
            )
        else:
            logger.info("EmailAlerter: enabled — sending to %s", self.recipient)

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _dedup_key(self, subject: str, severity: str) -> str:
        return f"{severity}::{subject}"

    def _is_duplicate(self, key: str) -> bool:
        last = self._sent.get(key)
        if last is None:
            return False
        return (time.monotonic() - last) < self._dedup_window

    def _record_sent(self, key: str) -> None:
        now = time.monotonic()
        self._sent[key] = now
        # Prune old entries (> 2x window)
        cutoff = now - self._dedup_window * 2
        self._sent = {k: v for k, v in self._sent.items() if v > cutoff}

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

    def send_alert(self, subject: str, message: str, severity: str = "INFO") -> bool:
        """
        Send email alert with deduplication.

        Args:
            subject: Email subject line
            message: Alert message body
            severity: Alert severity (INFO, WARNING, ERROR, CRITICAL)

        Returns:
            True if sent (or deduplicated), False on error or disabled.
        """
        if not self.enabled:
            logger.warning(
                "Email alert NOT sent (disabled): [%s] %s", severity, subject
            )
            return False

        key = self._dedup_key(subject, severity)
        if self._is_duplicate(key):
            logger.debug("Alert deduplicated: [%s] %s", severity, subject)
            return True

        try:
            msg = MIMEMultipart()
            msg["From"] = self.sender
            msg["To"] = self.recipient
            msg["Subject"] = f"[{severity}] Claire de Binare: {subject}"

            body = (
                f"Claire de Binare Market Alert\n\n"
                f"Severity: {severity}\n"
                f"Time:     {utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                f"Subject:  {subject}\n\n"
                f"{message}\n\n"
                f"---\n"
                f"This is an automated alert from Claire de Binare.\n"
            )

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)

            self._record_sent(key)
            logger.info("Email alert sent: [%s] %s", severity, subject)
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error("SMTP authentication failed: %s", e)
            return False
        except smtplib.SMTPException as e:
            logger.error("SMTP error sending alert: %s", e)
            return False
        except Exception as e:
            logger.error("Email alert failed: %s", e)
            return False

    def send_market_alert(
        self, symbol: str, event: str, details: Optional[dict] = None
    ) -> bool:
        """
        Send market-specific alert.

        Args:
            symbol: Trading symbol (e.g. "BTC/USDT")
            event: Event description
            details: Optional additional context
        """
        message = f"Market event for {symbol}: {event}"
        if details:
            message += f"\nDetails: {details}"

        return self.send_alert(
            subject=f"Market Alert: {symbol}",
            message=message,
            severity="WARNING",
        )

    def test_connection(self) -> bool:
        """Send a test alert to verify SMTP configuration."""
        if not self.enabled:
            return False
        return self.send_alert(
            "Email Alert Test",
            "This is a test alert to verify email configuration.",
            severity="INFO",
        )


# Global instance
_alerter: Optional[EmailAlerter] = None


def get_alerter() -> EmailAlerter:
    """Get or create the global EmailAlerter instance."""
    global _alerter
    if _alerter is None:
        _alerter = EmailAlerter()
    return _alerter
