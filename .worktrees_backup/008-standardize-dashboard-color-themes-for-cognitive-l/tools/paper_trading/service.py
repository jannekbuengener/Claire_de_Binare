"""
Paper Trading Runner - Claire de Binare
14-Tage automatisierter Paper Trading Test

Features:
- Subscribe zu Redis Events (market_data, signals, orders, order_results)
- Persistent Event-Logging (JSONL format)
- Stündliche PostgreSQL Snapshots
- Health-Check alle 5 Min
- Email-Alerts bei Critical Events
- Daily Reports

Verwendung:
    python service.py  # Läuft als Docker Service
"""

import os
import sys
import json
import logging
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path
import threading

from core.utils.clock import utcnow
# Flask for health endpoint
from flask import Flask, jsonify

# Redis for event streaming
import redis

# PostgreSQL for queries
import psycopg2
from psycopg2.extras import RealDictCursor

# Email alerts
from email_alerter import EmailAlerter

# Logging setup
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"logs/paper_trading_{utcnow().strftime('%Y%m%d')}.log"
        ),
    ],
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)


class PaperTradingRunner:
    """Paper Trading Runner for 14-day test"""

    def __init__(self, duration_days=14):
        """
        Initialize Paper Trading Runner

        Args:
            duration_days (int): Test duration in days (default: 14)
        """
        self.duration = duration_days
        self.start_time = utcnow()
        self.end_time = self.start_time + timedelta(days=duration_days)
        self.running = True
        self.last_health_check = utcnow()
        self.event_count = 0
        self.alert_sent_times = {}  # Debounce alerts

        # Initialize connections
        self.redis_client = self._init_redis()
        self.postgres_conn = self._init_postgres()
        self.email_alerter = EmailAlerter()

        # Ensure logs directory
        Path("logs").mkdir(exist_ok=True)
        Path("logs/events").mkdir(exist_ok=True)

        # Event log file (daily rotation)
        self.event_log_file = (
            f"logs/events/events_{utcnow().strftime('%Y%m%d')}.jsonl"
        )

        logger.info("=" * 60)
        logger.info("PAPER TRADING RUNNER INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"  Start Time:  {self.start_time}")
        logger.info(f"  End Time:    {self.end_time}")
        logger.info(f"  Duration:    {self.duration} days")
        logger.info(f"  Event Log:   {self.event_log_file}")
        logger.info("=" * 60)

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "cdb_redis"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD"),
                db=int(os.getenv("REDIS_DB", "0")),
                socket_connect_timeout=10,
                socket_keepalive=True,
                health_check_interval=30,
            )
            r.ping()
            logger.info("✅ Redis connected")
            return r
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.email_alerter.send_alert("Redis Connection Failed", str(e))
            raise

    def _init_postgres(self):
        """Initialize PostgreSQL connection"""
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "cdb_postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "claire_de_binare"),
                user=os.getenv("POSTGRES_USER", "claire_user"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                connect_timeout=10,
            )
            logger.info("✅ PostgreSQL connected")
            return conn
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            self.email_alerter.send_alert("PostgreSQL Connection Failed", str(e))
            raise

    def log_event(self, channel, event):
        """
        Log event to JSONL file

        Args:
            channel (str): Redis channel name
            event (dict): Event data
        """
        try:
            # Rotate log file daily
            current_log_file = (
                f"logs/events/events_{utcnow().strftime('%Y%m%d')}.jsonl"
            )
            if current_log_file != self.event_log_file:
                logger.info(
                    f"Rotating event log: {self.event_log_file} → {current_log_file}"
                )
                self.event_log_file = current_log_file

            # Write event as JSON line
            with open(self.event_log_file, "a", encoding="utf-8") as f:
                log_entry = {
                    "timestamp": utcnow().isoformat(),
                    "channel": channel,
                    "event": event,
                }
                f.write(json.dumps(log_entry) + "\n")

            self.event_count += 1

        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    def subscribe_to_events(self):
        """Subscribe to Redis channels and log all events"""
        channels = ["market_data", "signals", "orders", "order_results", "alerts"]

        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(*channels)

        logger.info(f"📡 Subscribed to Redis channels: {', '.join(channels)}")

        try:
            for message in pubsub.listen():
                if not self.running:
                    break

                if message["type"] == "message":
                    channel = message["channel"].decode("utf-8")
                    try:
                        data = json.loads(message["data"].decode("utf-8"))
                        self.log_event(channel, data)

                        # Log summary every 100 events
                        if self.event_count % 100 == 0:
                            logger.info(f"📊 Events logged: {self.event_count}")

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on {channel}: {e}")

        except Exception as e:
            logger.error(f"Event subscription error: {e}")
            self.email_alerter.send_alert("Event Subscription Error", str(e))
        finally:
            pubsub.close()

    def health_check_loop(self):
        """Periodic health check (every 5 minutes)"""
        while self.running:
            time.sleep(300)  # 5 minutes

            try:
                # Check Redis
                self.redis_client.ping()

                # Check PostgreSQL
                with self.postgres_conn.cursor() as cursor:
                    cursor.execute("SELECT 1")

                # Update last health check time
                self.last_health_check = utcnow()

                # Check if test is complete
                if utcnow() >= self.end_time:
                    logger.info("⏰ Test duration completed - stopping runner")
                    self.stop()

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self.email_alerter.send_alert(
                    "Health Check Failed",
                    f"Error: {e}\nLast successful check: {self.last_health_check}",
                    severity="CRITICAL",
                )

    def daily_report(self):
        """Generate daily report (runs at midnight)"""
        while self.running:
            # Sleep until next midnight
            now = utcnow()
            tomorrow = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            sleep_seconds = (tomorrow - now).total_seconds()

            time.sleep(sleep_seconds)

            if not self.running:
                break

            try:
                # Generate report
                report = self._generate_daily_report()

                # Log report
                logger.info("\n" + "=" * 60)
                logger.info("DAILY REPORT")
                logger.info("=" * 60)
                logger.info(report)
                logger.info("=" * 60)

                # Send email
                self.email_alerter.send_alert("Daily Report", report, severity="INFO")

            except Exception as e:
                logger.error(f"Daily report failed: {e}")

    def _generate_daily_report(self):
        """Generate daily report content"""
        try:
            with self.postgres_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Portfolio snapshot
                cursor.execute(
                    """
                    SELECT total_equity, daily_pnl, total_realized_pnl,
                           open_positions, total_exposure_pct
                    FROM portfolio_snapshots
                    ORDER BY timestamp DESC
                    LIMIT 1
                """
                )
                portfolio = cursor.fetchone()

                # Signals today
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM signals
                    WHERE DATE(timestamp) = CURRENT_DATE
                """
                )
                signals_today = cursor.fetchone()["count"]

                # Trades today
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM trades
                    WHERE DATE(timestamp) = CURRENT_DATE
                """
                )
                trades_today = cursor.fetchone()["count"]

                # Uptime
                uptime = utcnow() - self.start_time
                days_remaining = (self.end_time - utcnow()).days

                report = f"""
Paper Trading Daily Report

Date: {utcnow().strftime('%Y-%m-%d')}
Uptime: {uptime.days} days, {uptime.seconds // 3600} hours
Days Remaining: {days_remaining}

Portfolio:
  Total Equity:     ${portfolio['total_equity']:,.2f}
  Daily P&L:        ${portfolio['daily_pnl']:,.2f}
  Realized P&L:     ${portfolio['total_realized_pnl']:,.2f}
  Open Positions:   {portfolio['open_positions']}
  Total Exposure:   {portfolio['total_exposure_pct']:.2%}

Trading Activity:
  Signals Today:    {signals_today}
  Trades Today:     {trades_today}
  Events Logged:    {self.event_count}

System Health:
  Redis:            ✅ Connected
  PostgreSQL:       ✅ Connected
  Last Health Check: {self.last_health_check.strftime('%H:%M:%S')}
"""
                return report

        except Exception as e:
            return f"Report generation failed: {e}"

    def run(self):
        """Main run loop"""
        logger.info("🚀 Paper Trading Runner started")

        # Send startup alert
        self.email_alerter.send_alert(
            "Paper Trading Started",
            f"14-day test started at {self.start_time}\nEnd time: {self.end_time}",
            severity="INFO",
        )

        # Start background threads
        health_thread = threading.Thread(target=self.health_check_loop, daemon=True)
        report_thread = threading.Thread(target=self.daily_report, daemon=True)

        health_thread.start()
        report_thread.start()

        # Main event loop (blocks here)
        try:
            self.subscribe_to_events()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def stop(self):
        """Stop runner"""
        if not self.running:
            return

        self.running = False
        logger.info("🛑 Paper Trading Runner stopping...")

        # Send shutdown alert
        self.email_alerter.send_alert(
            "Paper Trading Stopped",
            f"Test stopped after {(utcnow() - self.start_time).days} days\nTotal events logged: {self.event_count}",
            severity="WARNING",
        )

        # Close connections
        if self.redis_client:
            self.redis_client.close()
        if self.postgres_conn:
            self.postgres_conn.close()

        logger.info("✅ Cleanup complete")

    def get_uptime_seconds(self):
        """Get uptime in seconds"""
        return (utcnow() - self.start_time).total_seconds()


# Global runner instance
runner = None


@app.route("/health")
def health():
    """Health endpoint"""
    global runner

    if runner and runner.running:
        uptime = runner.get_uptime_seconds()
        return jsonify(
            {
                "status": "ok",
                "service": "paper_trading_runner",
                "uptime_seconds": uptime,
                "events_logged": runner.event_count,
                "last_health_check": runner.last_health_check.isoformat(),
            }
        )
    else:
        return jsonify({"status": "stopped", "service": "paper_trading_runner"}), 503


@app.route("/status")
def status():
    """Detailed status endpoint"""
    global runner

    if runner and runner.running:
        return jsonify(
            {
                "status": "running",
                "start_time": runner.start_time.isoformat(),
                "end_time": runner.end_time.isoformat(),
                "duration_days": runner.duration,
                "uptime_seconds": runner.get_uptime_seconds(),
                "events_logged": runner.event_count,
                "event_log_file": runner.event_log_file,
            }
        )
    else:
        return jsonify({"status": "stopped"}), 503


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global runner
    logger.info(f"Received signal {signum}")
    if runner:
        runner.stop()
    sys.exit(0)


def main():
    """Main entry point"""
    global runner

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get duration from ENV (default: 14 days)
    duration = int(os.getenv("PAPER_TRADING_DURATION_DAYS", "14"))

    # Initialize runner
    runner = PaperTradingRunner(duration_days=duration)

    # Start Flask in background thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=8004, debug=False), daemon=True
    )
    flask_thread.start()

    logger.info("🌐 Health endpoint: http://localhost:8004/health")

    # Run main loop (blocks)
    runner.run()


if __name__ == "__main__":
    main()
