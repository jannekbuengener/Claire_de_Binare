---
relations:
  role: system_check
  domain: automation
  upstream:
    - docker-compose.yml
  downstream:
    - Makefile
---
"""
Daily Check Script - Claire de Binare
Täglicher Gesundheitscheck während Paper Trading

Prüft:
1. Docker Container Status
2. Portfolio Snapshot
3. Trading Statistics (Signals, Trades, P&L)
4. Risk-Limit Status
5. Disk Space
6. Backup Status (letzte 24h)

Verwendung:
    python backoffice/scripts/daily_check.py

Output:
    - Console-Report
    - Markdown-Report in logs/daily_reports/report_YYYYMMDD.md
"""

import sys
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Optional imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️  psycopg2 not installed - PostgreSQL checks disabled")


class DailyCheck:
    """Daily Health Check"""

    def __init__(self):
        self.timestamp = datetime.now()
        self.report_lines = []
        self.report_file = f"logs/daily_reports/report_{self.timestamp.strftime('%Y%m%d')}.md"
        self.ensure_report_dir()

    def ensure_report_dir(self):
        """Ensure report directory exists"""
        Path("logs/daily_reports").mkdir(parents=True, exist_ok=True)

    def log(self, message):
        """Add line to report"""
        print(message)
        self.report_lines.append(message)

    def check_docker_status(self):
        """Check Docker container status"""
        self.log("\n## 1. Docker Container Status\n")

        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "table"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.log("```")
                self.log(result.stdout)
                self.log("```")
                self.log("\n✅ **All containers checked**")
            else:
                self.log(f"❌ **Docker Compose Error**: {result.stderr}")

        except Exception as e:
            self.log(f"❌ **Docker check failed**: {e}")

    def check_portfolio(self):
        """Check portfolio snapshot"""
        self.log("\n## 2. Portfolio Summary\n")

        if not PSYCOPG2_AVAILABLE:
            self.log("⚠️  PostgreSQL checks skipped (psycopg2 not installed)")
            return

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "claire_de_binare"),
                user=os.getenv("POSTGRES_USER", "claire_user"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                connect_timeout=5
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT
                        timestamp,
                        total_equity,
                        available_balance,
                        daily_pnl,
                        total_realized_pnl,
                        total_unrealized_pnl,
                        open_positions,
                        total_exposure_pct
                    FROM portfolio_snapshots
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                row = cursor.fetchone()

                if row:
                    self.log("| Metric | Value |")
                    self.log("|--------|-------|")
                    self.log(f"| Timestamp | {row['timestamp']} |")
                    self.log(f"| **Total Equity** | **${row['total_equity']:,.2f}** |")
                    self.log(f"| Available Balance | ${row['available_balance']:,.2f} |")
                    self.log(f"| Daily P&L | ${row['daily_pnl']:,.2f} |")
                    self.log(f"| Realized P&L | ${row['total_realized_pnl']:,.2f} |")
                    self.log(f"| Unrealized P&L | ${row['total_unrealized_pnl']:,.2f} |")
                    self.log(f"| Open Positions | {row['open_positions']} |")
                    self.log(f"| Total Exposure | {row['total_exposure_pct']:.2%} |")

                    # Status emoji
                    if row['daily_pnl'] >= 0:
                        self.log("\n✅ **Daily P&L: Positive**")
                    else:
                        self.log("\n⚠️  **Daily P&L: Negative**")
                else:
                    self.log("⚠️  No portfolio snapshots found")

            conn.close()

        except Exception as e:
            self.log(f"❌ **Portfolio check failed**: {e}")

    def check_trading_stats(self):
        """Check trading statistics"""
        self.log("\n## 3. Trading Statistics\n")

        if not PSYCOPG2_AVAILABLE:
            return

        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "claire_de_binare"),
                user=os.getenv("POSTGRES_USER", "claire_user"),
                password=os.getenv("POSTGRES_PASSWORD", ""),
                connect_timeout=5
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Signals today
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM signals
                    WHERE DATE(timestamp) = CURRENT_DATE
                """)
                signals_today = cursor.fetchone()["count"]

                # Trades today
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM trades
                    WHERE DATE(timestamp) = CURRENT_DATE
                """)
                trades_today = cursor.fetchone()["count"]

                # Total signals/trades
                cursor.execute("SELECT COUNT(*) as count FROM signals")
                total_signals = cursor.fetchone()["count"]

                cursor.execute("SELECT COUNT(*) as count FROM trades")
                total_trades = cursor.fetchone()["count"]

                self.log("| Metric | Today | Total |")
                self.log("|--------|-------|-------|")
                self.log(f"| Signals | {signals_today} | {total_signals} |")
                self.log(f"| Trades | {trades_today} | {total_trades} |")

            conn.close()

        except Exception as e:
            self.log(f"❌ **Trading stats failed**: {e}")

    def check_risk_limits(self):
        """Check risk limit status"""
        self.log("\n## 4. Risk Limits\n")

        risk_params = {
            "MAX_POSITION_PCT": 0.10,
            "MAX_DAILY_DRAWDOWN_PCT": 0.05,
            "MAX_TOTAL_EXPOSURE_PCT": 0.30,
            "CIRCUIT_BREAKER_THRESHOLD_PCT": 0.10,
        }

        self.log("| Parameter | Configured | Status |")
        self.log("|-----------|------------|--------|")
        for param, expected in risk_params.items():
            value = os.getenv(param)
            if value:
                try:
                    parsed = float(value)
                    status = "✅" if abs(parsed - expected) < 0.001 else "⚠️"
                    self.log(f"| {param} | {parsed:.2%} | {status} |")
                except ValueError:
                    self.log(f"| {param} | Invalid | ❌ |")
            else:
                self.log(f"| {param} | Not set | ❌ |")

    def check_disk_space(self):
        """Check disk space"""
        self.log("\n## 5. Disk Space\n")

        try:
            import shutil
            total, used, free = shutil.disk_usage(os.getcwd())

            free_gb = free // (1024**3)
            total_gb = total // (1024**3)
            used_pct = (used / total) * 100

            self.log(f"- **Total**: {total_gb} GB")
            self.log(f"- **Used**: {used_pct:.1f}%")
            self.log(f"- **Free**: {free_gb} GB")

            if free_gb >= 30:
                self.log("\n✅ **Sufficient space** (>= 30 GB)")
            else:
                self.log(f"\n⚠️  **Low disk space** ({free_gb} GB < 30 GB)")

        except Exception as e:
            self.log(f"❌ **Disk space check failed**: {e}")

    def check_backup_status(self):
        """Check recent backup status"""
        self.log("\n## 6. Backup Status (Last 24h)\n")

        backup_dir = Path("F:/Claire_Backups")

        if not backup_dir.exists():
            self.log("⚠️  Backup directory not found")
            return

        try:
            # Find backups from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            recent_backups = [
                f for f in backup_dir.glob("*.zip")
                if f.stat().st_mtime > yesterday.timestamp()
            ]

            if recent_backups:
                self.log(f"✅ **{len(recent_backups)} backup(s) in last 24h**\n")
                self.log("Recent backups:")
                for backup in sorted(recent_backups, reverse=True)[:5]:
                    size_mb = backup.stat().st_size / (1024**2)
                    mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                    self.log(f"  - {backup.name} ({size_mb:.2f} MB) - {mtime.strftime('%Y-%m-%d %H:%M')}")
            else:
                self.log("⚠️  **No backups in last 24h**")
                self.log("   Run: `powershell .\\backoffice\\scripts\\backup_postgres.ps1`")

        except Exception as e:
            self.log(f"❌ **Backup check failed**: {e}")

    def save_report(self):
        """Save report to file"""
        try:
            with open(self.report_file, "w", encoding="utf-8") as f:
                # Add header
                f.write(f"# Daily Report - {self.timestamp.strftime('%Y-%m-%d')}\n\n")
                f.write(f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                # Write report content
                for line in self.report_lines:
                    f.write(line + "\n")

            print(f"\n📝 Report saved: {self.report_file}")

        except Exception as e:
            print(f"❌ Failed to save report: {e}")

    def run_all(self):
        """Run all checks"""
        self.log("# 📊 Claire de Binare - Daily Check")
        self.log(f"\n**Date**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log("---")

        self.check_docker_status()
        self.check_portfolio()
        self.check_trading_stats()
        self.check_risk_limits()
        self.check_disk_space()
        self.check_backup_status()

        self.log("\n---\n")
        self.log(f"**Report generated**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        self.save_report()


def main():
    """Main entry point"""
    checker = DailyCheck()
    checker.run_all()


if __name__ == "__main__":
    main()
