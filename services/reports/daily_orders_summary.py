#!/usr/bin/env python3
"""
Daily Orders Summary - CDB Reports Service
Sends daily email with orders statistics from last 24h
"""

import os
import time
import smtplib
import psycopg2
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def read_secret(path):
    """Read secret from Docker mounted file"""
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"[ERROR] Failed to read secret {path}: {e}")
        return None


def get_db_connection():
    """Connect to Postgres using connection string from secret"""
    try:
        # Read DSN from secret file
        dsn_path = os.getenv('POSTGRES_DSN_FILE', '/run/secrets/postgres_password_dsn')
        dsn = read_secret(dsn_path)

        if not dsn:
            # Fallback: construct DSN from individual secrets
            user = os.getenv('POSTGRES_USER', 'claire_user')
            password = read_secret('/run/secrets/postgres_password')
            host = os.getenv('POSTGRES_HOST', 'cdb_postgres')
            database = os.getenv('POSTGRES_DB', 'claire_de_binare')
            dsn = f"postgresql://{user}:{password}@{host}:5432/{database}"

        return psycopg2.connect(dsn)
    except Exception as e:
        print(f"[ERROR] Database connection failed: {e}")
        return None


def fetch_summary(conn, hours=24):
    """Fetch orders summary for last N hours"""
    query = """
    WITH order_summary AS (
      SELECT
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (WHERE status = 'filled') AS filled_count,
        COUNT(*) FILTER (WHERE status = 'rejected') AS rejected_count,
        COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_count,
        COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
        COALESCE(SUM(size * COALESCE(avg_fill_price, price, 0)), 0) AS total_notional
      FROM orders
      WHERE created_at >= NOW() - INTERVAL '%s hours'
    ),
    top_rejections AS (
      SELECT
        rejection_reason,
        COUNT(*) AS count
      FROM orders
      WHERE rejection_reason IS NOT NULL
        AND created_at >= NOW() - INTERVAL '%s hours'
      GROUP BY rejection_reason
      ORDER BY count DESC
      LIMIT 5
    ),
    trade_summary AS (
      SELECT
        COUNT(*) AS total_trades,
        COALESCE(SUM(size * execution_price), 0) AS total_notional,
        COALESCE(SUM(fees), 0) AS total_fees
      FROM trades
      WHERE timestamp >= NOW() - INTERVAL '%s hours'
    )
    SELECT
      o.total_orders, o.filled_count, o.rejected_count,
      o.cancelled_count, o.pending_count, o.total_notional,
      t.total_trades, t.total_fees
    FROM order_summary o, trade_summary t;
    """

    rejection_query = """
    SELECT rejection_reason, COUNT(*) as count
    FROM orders
    WHERE rejection_reason IS NOT NULL
      AND created_at >= NOW() - INTERVAL '%s hours'
    GROUP BY rejection_reason
    ORDER BY count DESC
    LIMIT 5;
    """

    try:
        with conn.cursor() as cur:
            # Get summary stats
            cur.execute(query % (hours, hours, hours))
            summary = cur.fetchone()

            # Get top rejections
            cur.execute(rejection_query % hours)
            rejections = cur.fetchall()

            return {
                'total_orders': summary[0] or 0,
                'filled': summary[1] or 0,
                'rejected': summary[2] or 0,
                'cancelled': summary[3] or 0,
                'pending': summary[4] or 0,
                'notional': float(summary[5] or 0),
                'total_trades': summary[6] or 0,
                'total_fees': float(summary[7] or 0),
                'rejections': rejections
            }
    except Exception as e:
        print(f"[ERROR] Query failed: {e}")
        return None


def format_email_body(data, start_time, end_time):
    """Format data as HTML email"""

    # Calculate fill rate
    fill_rate = 0
    if data['total_orders'] > 0:
        fill_rate = (data['filled'] / data['total_orders']) * 100

    # Format rejections table
    rejection_rows = ""
    if data['rejections']:
        for reason, count in data['rejections']:
            rejection_rows += f"""
            <tr>
                <td>{reason or 'Unknown'}</td>
                <td style="text-align: right;">{count}</td>
            </tr>
            """
    else:
        rejection_rows = '<tr><td colspan="2" style="text-align: center; color: #999;">No rejections</td></tr>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ background: #1f77b4; color: white; padding: 20px; }}
            .summary {{ background: #f5f5f5; padding: 20px; margin: 20px 0; }}
            .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
            .metric-value {{ font-size: 32px; font-weight: bold; color: #1f77b4; }}
            .metric-label {{ font-size: 14px; color: #666; margin-top: 5px; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #1f77b4; color: white; }}
            .footer {{ font-size: 12px; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>CDB Daily Orders Summary</h1>
            <p><strong>Period:</strong> {start_time.strftime('%Y-%m-%d %H:%M UTC')} - {end_time.strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>

        <div class="summary">
            <div class="metric">
                <div class="metric-value">{data['total_orders']}</div>
                <div class="metric-label">Total Orders</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['filled']}</div>
                <div class="metric-label">Filled</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['rejected']}</div>
                <div class="metric-label">Rejected</div>
            </div>
            <div class="metric">
                <div class="metric-value">{data['cancelled']}</div>
                <div class="metric-label">Cancelled</div>
            </div>
            <div class="metric">
                <div class="metric-value">{fill_rate:.1f}%</div>
                <div class="metric-label">Fill Rate</div>
            </div>
        </div>

        <h3>Top Rejection Reasons</h3>
        <table>
            <tr>
                <th>Reason</th>
                <th style="text-align: right;">Count</th>
            </tr>
            {rejection_rows}
        </table>

        <h3>Trade Execution</h3>
        <ul>
            <li><strong>Total Trades:</strong> {data['total_trades']}</li>
            <li><strong>Total Notional:</strong> ${data['notional']:,.2f}</li>
            <li><strong>Total Fees:</strong> ${data['total_fees']:.4f}</li>
        </ul>

        <div class="footer">
            <p>Generated by CDB Reports Service | {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><a href="http://localhost:3000">Grafana Dashboard</a></p>
        </div>
    </body>
    </html>
    """

    return html


def send_email(subject, body_html):
    """Send email via SMTP using Docker secrets"""
    try:
        # Read SMTP config from secrets
        smtp_host = "smtp.gmail.com:587"
        smtp_user = read_secret('/run/secrets/smtp_user')
        smtp_password = read_secret('/run/secrets/smtp_password')
        from_address = read_secret('/run/secrets/smtp_from')
        to_address = read_secret('/run/secrets/alert_email_to')

        if not all([smtp_user, smtp_password, from_address, to_address]):
            print("[ERROR] Missing SMTP credentials")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"CDB Reports <{from_address}>"
        msg['To'] = to_address

        # Attach HTML body
        html_part = MIMEText(body_html, 'html')
        msg.attach(html_part)

        # Send via SMTP
        with smtplib.SMTP(smtp_host.split(':')[0], int(smtp_host.split(':')[1])) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)

        print(f"[INFO] Email sent successfully to {to_address}")
        return True

    except Exception as e:
        print(f"[ERROR] Email send failed: {e}")
        return False


def wait_until_next_run(target_hour=8):
    """Calculate seconds until next run at target_hour UTC"""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)

    # If we've passed target hour today, schedule for tomorrow
    if now >= target:
        target += timedelta(days=1)

    wait_seconds = (target - now).total_seconds()
    print(f"[INFO] Next run scheduled for {target.strftime('%Y-%m-%d %H:%M UTC')} (in {wait_seconds/3600:.1f}h)")

    return wait_seconds


def main():
    """Main loop - run daily summary at 08:00 UTC"""
    print("[INFO] CDB Daily Orders Summary Service started")
    print(f"[INFO] Schedule: Daily at 08:00 UTC")

    while True:
        try:
            # Wait until next scheduled run
            wait_seconds = wait_until_next_run(target_hour=8)
            time.sleep(wait_seconds)

            # Run summary
            print(f"[INFO] Generating daily summary for {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")

            # Connect to database
            conn = get_db_connection()
            if not conn:
                print("[ERROR] Database connection failed, skipping this run")
                continue

            try:
                # Fetch summary data (last 24 hours)
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=24)

                data = fetch_summary(conn, hours=24)
                if not data:
                    print("[ERROR] Failed to fetch summary data")
                    continue

                # Format email
                subject = f"CDB Daily Orders Summary - {end_time.strftime('%Y-%m-%d')}"
                body = format_email_body(data, start_time, end_time)

                # Send email
                send_email(subject, body)

                print(f"[INFO] Summary complete: {data['total_orders']} orders, {data['filled']} filled, {data['rejected']} rejected")

            finally:
                conn.close()

        except KeyboardInterrupt:
            print("[INFO] Service stopped by user")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}")
            # Wait 5 minutes before retry on error
            time.sleep(300)


if __name__ == "__main__":
    main()
