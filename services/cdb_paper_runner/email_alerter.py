"""
Email Alerter - Claire de Binare
Sendet Email-Benachrichtigungen bei Critical Events

Verwendung:
    alerter = EmailAlerter()
    alerter.send_alert("Container Down", "cdb_risk crashed", severity="CRITICAL")
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailAlerter:
    """Email Alert System"""

    def __init__(self):
        """Initialize email configuration from ENV"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("ALERT_EMAIL_FROM")
        self.receiver_email = os.getenv("ALERT_EMAIL_TO")
        self.password = os.getenv("ALERT_EMAIL_PASSWORD")
        self.enabled = all([self.sender_email, self.receiver_email, self.password])

        if not self.enabled:
            logger.warning("⚠️  Email alerts DISABLED - missing ENV variables")
            logger.warning(
                "   Required: ALERT_EMAIL_FROM, ALERT_EMAIL_TO, ALERT_EMAIL_PASSWORD"
            )
        else:
            logger.info(f"✅ Email alerts ENABLED - sending to {self.receiver_email}")

    def send_alert(self, subject, message, severity="CRITICAL"):
        """
        Send email alert

        Args:
            subject (str): Alert subject
            message (str): Alert message body
            severity (str): Severity level (CRITICAL, WARNING, INFO)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"Email alert NOT sent (disabled): [{severity}] {subject}")
            return False

        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = self.receiver_email
            msg["Subject"] = f"[{severity}] Claire de Binare: {subject}"

            # Email body
            body = f"""
Claire de Binare Paper Trading Alert

Severity: {severity}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Subject: {subject}

{message}

---
Dashboard: http://localhost:3000/d/claire-paper-trading
Logs: docker compose logs cdb_paper_runner --tail=100

This is an automated alert from Claire de Binare Paper Trading System.
"""

            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.password)
                server.send_message(msg)

            logger.info(f"✅ Email alert sent: [{severity}] {subject}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ Email authentication failed: {e}")
            logger.error(
                "   Check ALERT_EMAIL_PASSWORD (use Gmail App Password, not account password)"
            )
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Email alert failed: {e}")
            return False

    def test_connection(self):
        """Test email configuration"""
        if not self.enabled:
            return False

        return self.send_alert(
            "Email Alert Test",
            "This is a test alert to verify email configuration.",
            severity="INFO",
        )
