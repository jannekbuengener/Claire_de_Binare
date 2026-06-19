"""Readonly correlation_ledger inventory for #3343 window-bank expansion.

Safe usage:
  SET POSTGRES_READONLY_PASSWORD_DSN=postgresql://...
  python scripts/_3343_inventory_windows.py

Output: aggregated window candidates; no DSN/secret values printed.
"""

from __future__ import annotations

import os
import sys

import psycopg2

_READONLY_DSN_ENV = "POSTGRES_READONLY_PASSWORD_DSN"
_EXPECTED_READONLY_LOGIN = "cdb_readonly"

_MIN_WINDOW_MS = 7_200_000  # 2 hours
_STRATEGY_ID = "primary_breakout_v1"
_SYMBOL = "BTCUSDT"


def _get_readonly_dsn() -> str:
    dsn = os.getenv(_READONLY_DSN_ENV)
    if not dsn or not dsn.strip():
        raise RuntimeError(f"{_READONLY_DSN_ENV} is required")
    return dsn.strip()


def _verify_identity(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT current_user, session_user")
        row = cur.fetchone()
    if (
        not row
        or row[0] != _EXPECTED_READONLY_LOGIN
        or row[1] != _EXPECTED_READONLY_LOGIN
    ):
        raise RuntimeError(
            f"Identity mismatch: {row}, expected {_EXPECTED_READONLY_LOGIN}"
        )


def _verify_readonly(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT has_table_privilege(current_user, 'public.correlation_ledger', 'SELECT'),"
            " has_table_privilege(current_user, 'public.correlation_ledger', 'INSERT'),"
            " has_table_privilege(current_user, 'public.correlation_ledger', 'UPDATE'),"
            " has_table_privilege(current_user, 'public.correlation_ledger', 'DELETE')"
        )
        row = cur.fetchone()
    if not row or not row[0]:
        raise RuntimeError("Missing SELECT on correlation_ledger")
    if row[1] or row[2] or row[3]:
        raise RuntimeError("Write privileges detected on correlation_ledger")


def _inventory_hourly(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              date_trunc('hour', to_timestamp(timestamp_ms::double precision / 1000)) AS hour_bucket,
              event_type,
              COUNT(*) AS cnt,
              COUNT(DISTINCT correlation_id) AS distinct_chains,
              MIN(timestamp_ms) AS first_ts_ms,
              MAX(timestamp_ms) AS last_ts_ms
            FROM public.correlation_ledger
            WHERE payload->>'strategy_id' = %s
              AND symbol = %s
            GROUP BY hour_bucket, event_type
            ORDER BY hour_bucket, event_type
            """,
            (_STRATEGY_ID, _SYMBOL),
        )
        colnames = [d.name for d in cur.description]
        cols_lower = [c.lower() for c in colnames]
        rows = [dict(zip(cols_lower, r, strict=True)) for r in cur.fetchall()]
    return rows


def _inventory_candidate_windows(conn) -> list[dict]:
    """Find contiguous event clusters (>2h) via gap detection (>1h gap = new cluster).

    This avoids aggregating the entire dataset into one pseudo-window.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH numbered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                LAG(timestamp_ms) OVER (ORDER BY timestamp_ms) AS prev_ts_ms
              FROM public.correlation_ledger
              WHERE payload->>'strategy_id' = %s
                AND symbol = %s
            ),
            gaps AS (
              SELECT
                timestamp_ms,
                CASE WHEN prev_ts_ms IS NULL
                      OR timestamp_ms - prev_ts_ms > 3600000  -- 1h gap = new cluster
                     THEN 1 ELSE 0 END AS new_cluster
              FROM numbered
            ),
            clustered AS (
              SELECT
                timestamp_ms,
                SUM(new_cluster) OVER (ORDER BY timestamp_ms) AS cluster_id
              FROM gaps
            ),
            cluster_stats AS (
              SELECT
                cluster_id,
                MIN(timestamp_ms) AS min_ts_ms,
                MAX(timestamp_ms) AS max_ts_ms,
                MAX(timestamp_ms) - MIN(timestamp_ms) AS span_ms,
                COUNT(*) AS total_events,
                COUNT(DISTINCT n.correlation_id) AS total_chains,
                COUNT(*) FILTER (WHERE n.event_type = 'SIGNAL') AS signal_count,
                COUNT(*) FILTER (WHERE n.event_type = 'DECISION') AS decision_count,
                COUNT(*) FILTER (WHERE n.event_type = 'ORDER') AS order_count,
                COUNT(*) FILTER (WHERE n.event_type = 'FILL') AS fill_count
              FROM clustered c
              JOIN numbered n ON n.timestamp_ms = c.timestamp_ms
              GROUP BY cluster_id
            )
            SELECT
              min_ts_ms,
              max_ts_ms,
              span_ms,
              total_events,
              total_chains,
              signal_count,
              decision_count,
              order_count,
              fill_count
            FROM cluster_stats
            WHERE span_ms >= %s
            ORDER BY min_ts_ms ASC
            """,
            (_STRATEGY_ID, _SYMBOL, _MIN_WINDOW_MS),
        )
        colnames = [d.name for d in cur.description]
        cols_lower = [c.lower() for c in colnames]
        rows = [dict(zip(cols_lower, r, strict=True)) for r in cur.fetchall()]
    return rows


def _inventory_all_clusters(conn) -> tuple[list[dict], list[dict]]:
    """Find ALL contiguous event clusters regardless of duration.

    Returns (over_2h, under_2h) lists.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH numbered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                LAG(timestamp_ms) OVER (ORDER BY timestamp_ms) AS prev_ts_ms
              FROM public.correlation_ledger
              WHERE payload->>'strategy_id' = %s
                AND symbol = %s
            ),
            gaps AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                CASE WHEN prev_ts_ms IS NULL
                      OR timestamp_ms - prev_ts_ms > 3600000
                     THEN 1 ELSE 0 END AS new_cluster
              FROM numbered
            ),
            clustered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                SUM(new_cluster) OVER (ORDER BY timestamp_ms) AS cluster_id
              FROM gaps
            ),
            cluster_stats AS (
              SELECT
                cluster_id,
                MIN(timestamp_ms) AS min_ts_ms,
                MAX(timestamp_ms) AS max_ts_ms,
                MAX(timestamp_ms) - MIN(timestamp_ms) AS span_ms,
                COUNT(*) AS total_events,
                COUNT(DISTINCT correlation_id) AS total_chains,
                COUNT(*) FILTER (WHERE event_type = 'SIGNAL') AS signal_count,
                COUNT(*) FILTER (WHERE event_type = 'DECISION') AS decision_count,
                COUNT(*) FILTER (WHERE event_type = 'ORDER') AS order_count,
                COUNT(*) FILTER (WHERE event_type = 'FILL') AS fill_count
              FROM clustered
              GROUP BY cluster_id
            )
            SELECT
              cluster_id,
              min_ts_ms,
              max_ts_ms,
              span_ms,
              total_events,
              total_chains,
              signal_count,
              decision_count,
              order_count,
              fill_count
            FROM cluster_stats
            WHERE span_ms >= %s
            ORDER BY min_ts_ms ASC
            """,
            (_STRATEGY_ID, _SYMBOL, _MIN_WINDOW_MS),
        )
        colnames = [d.name for d in cur.description]
        cols_lower = [c.lower() for c in colnames]
        over_2h = [dict(zip(cols_lower, r, strict=True)) for r in cur.fetchall()]

        cur.execute(
            """
            WITH numbered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                LAG(timestamp_ms) OVER (ORDER BY timestamp_ms) AS prev_ts_ms
              FROM public.correlation_ledger
              WHERE payload->>'strategy_id' = %s
                AND symbol = %s
            ),
            gaps AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                CASE WHEN prev_ts_ms IS NULL
                      OR timestamp_ms - prev_ts_ms > 3600000
                     THEN 1 ELSE 0 END AS new_cluster
              FROM numbered
            ),
            clustered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                SUM(new_cluster) OVER (ORDER BY timestamp_ms) AS cluster_id
              FROM gaps
            ),
            cluster_stats AS (
              SELECT
                cluster_id,
                MIN(timestamp_ms) AS min_ts_ms,
                MAX(timestamp_ms) AS max_ts_ms,
                MAX(timestamp_ms) - MIN(timestamp_ms) AS span_ms,
                COUNT(*) AS total_events,
                COUNT(DISTINCT correlation_id) AS total_chains,
                COUNT(*) FILTER (WHERE event_type = 'SIGNAL') AS signal_count,
                COUNT(*) FILTER (WHERE event_type = 'DECISION') AS decision_count,
                COUNT(*) FILTER (WHERE event_type = 'ORDER') AS order_count,
                COUNT(*) FILTER (WHERE event_type = 'FILL') AS fill_count
              FROM clustered
              GROUP BY cluster_id
            )
            SELECT
              cluster_id,
              min_ts_ms,
              max_ts_ms,
              span_ms,
              total_events,
              total_chains,
              signal_count,
              decision_count,
              order_count,
              fill_count
            FROM cluster_stats
            WHERE span_ms < %s
            ORDER BY min_ts_ms ASC
            """,
            (_STRATEGY_ID, _SYMBOL, _MIN_WINDOW_MS),
        )
        cols_lower = [c.lower() for c in colnames]
        under_2h = [dict(zip(cols_lower, r, strict=True)) for r in cur.fetchall()]

    return over_2h, under_2h


def _inventory_by_day(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
              date_trunc('day', to_timestamp(timestamp_ms::double precision / 1000)) AS day_bucket,
              COUNT(*) AS total_events,
              COUNT(DISTINCT correlation_id) AS total_chains,
              COUNT(*) FILTER (WHERE event_type = 'SIGNAL') AS signal_count,
              COUNT(*) FILTER (WHERE event_type = 'FILL') AS fill_count,
              MIN(timestamp_ms) AS first_ts_ms,
              MAX(timestamp_ms) AS last_ts_ms,
              MAX(timestamp_ms) - MIN(timestamp_ms) AS span_ms
            FROM public.correlation_ledger
            WHERE payload->>'strategy_id' = %s
              AND symbol = %s
            GROUP BY day_bucket
            ORDER BY day_bucket
            """,
            (_STRATEGY_ID, _SYMBOL),
        )
        colnames = [d.name for d in cur.description]
        cols_lower = [c.lower() for c in colnames]
        rows = [dict(zip(cols_lower, r, strict=True)) for r in cur.fetchall()]
    return rows


def _existing_windows_ms() -> list[tuple[int, int, str]]:
    """Define existing windows to avoid overlap."""
    return [
        # Pilot 1m: 2026-04-24T00:42:00Z to 2026-04-24T00:43:00Z
        (1713919320000, 1713919380000, "pilot_1m"),
        # #3028 2m: 2026-06-06T00:28:12.551Z to 2026-06-06T00:30:12.814Z
        (1780705692551, 1780705812814, "3028_2m"),
        # June6 1h: 2026-06-05T23:30:00Z to 2026-06-06T00:30:00Z
        (1780702200000, 1780705800000, "june6_1h"),
    ]


def _format_ts(ts_ms: int) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def main() -> int:
    dsn = _get_readonly_dsn()
    conn = psycopg2.connect(dsn, connect_timeout=10)
    try:
        db_name = None
        with conn.cursor() as cur:
            cur.execute("SELECT current_database()")
            db_name = cur.fetchone()[0]

        _verify_identity(conn)
        _verify_readonly(conn)

        print(f"=== #3343 Window-Bank Inventory ===")
        print(f"Database: {db_name}")
        print(f"Strategy: {_STRATEGY_ID}, Symbol: {_SYMBOL}")
        print(f"Min window: {_MIN_WINDOW_MS}ms ({_MIN_WINDOW_MS/3600000:.1f}h)")
        print()

        # 1. Hourly distribution
        hourly = _inventory_hourly(conn)
        print("--- Hourly Event Distribution ---")
        print(
            f"{'Hour (UTC)':<22} {'Event Type':<12} {'Count':<8} {'Chains':<8} {'Span':<10}"
        )
        print("-" * 60)
        current_hour = None
        for row in hourly:
            hb = str(row["hour_bucket"])
            if hb != current_hour:
                if current_hour is not None:
                    print()
                current_hour = hb
            span_ms = (
                int(row["last_ts_ms"]) - int(row["first_ts_ms"])
                if row["last_ts_ms"] and row["first_ts_ms"]
                else 0
            )
            print(
                f"{hb:<22} {str(row['event_type']):<12} {int(row['cnt']):<8} {int(row['distinct_chains']):<8} {span_ms/1000:.1f}s"
            )
        print()

        # 2. By-day overview
        daily = _inventory_by_day(conn)
        print("--- Daily Overview ---")
        print(
            f"{'Day (UTC)':<22} {'Events':<8} {'Chains':<8} {'SIGNAL':<8} {'FILL':<8} {'Span':<12}"
        )
        print("-" * 66)
        for row in daily:
            span_h = int(row["span_ms"]) / 3600000 if row["span_ms"] else 0
            print(
                f"{str(row['day_bucket']):<22} {int(row['total_events']):<8} {int(row['total_chains']):<8} {int(row['signal_count']):<8} {int(row['fill_count']):<8} {span_h:.1f}h"
            )
        print()

        # 3. All clusters
        over_2h, under_2h = _inventory_all_clusters(conn)
        existing = _existing_windows_ms()

        print(f"--- All Event Clusters (>{_MIN_WINDOW_MS/3600000:.0f}h) ---")
        print(
            f"{'#':<4} {'Start (UTC)':<26} {'End (UTC)':<26} {'Span(h)':<9} {'Events':<8} {'Chains':<8} {'SIG':<6} {'DEC':<6} {'ORD':<6} {'FILL':<6}"
        )
        print("-" * 115)
        if not over_2h:
            print("  NO CLUSTERS >2h found.")
        for c in over_2h:
            start_ts = _format_ts(c["min_ts_ms"])
            end_ts = _format_ts(c["max_ts_ms"])
            span_h = c["span_ms"] / 3600000
            print(
                f"{int(c['cluster_id']):<4} {start_ts:<26} {end_ts:<26} {span_h:<9.1f} {int(c['total_events']):<8} {int(c['total_chains']):<8} {int(c['signal_count']):<6} {int(c['decision_count']):<6} {int(c['order_count']):<6} {int(c['fill_count']):<6}"
            )
        print()

        print("--- Sub-2h Clusters ---")
        print(
            f"{'#':<4} {'Start (UTC)':<26} {'End (UTC)':<26} {'Span(min)':<11} {'Events':<8} {'Chains':<8} {'SIG':<6} {'DEC':<6} {'ORD':<6} {'FILL':<6} {'Overlap':<12}"
        )
        print("-" * 128)
        if not under_2h:
            print("  NO sub-2h clusters found.")
        for c in under_2h:
            start_ts = _format_ts(c["min_ts_ms"])
            end_ts = _format_ts(c["max_ts_ms"])
            span_min = c["span_ms"] / 60000
            overlap_str = "none"
            for es, ee, en in existing:
                if c["min_ts_ms"] < ee and c["max_ts_ms"] > es:
                    overlap_str = f"overlaps {en}"
                    break
            print(
                f"{int(c['cluster_id']):<4} {start_ts:<26} {end_ts:<26} {span_min:<11.1f} {int(c['total_events']):<8} {int(c['total_chains']):<8} {int(c['signal_count']):<6} {int(c['decision_count']):<6} {int(c['order_count']):<6} {int(c['fill_count']):<6} {overlap_str:<12}"
            )
        print()

        # 4. Existing windows for reference
        print("--- Existing Window Bank ---")
        print(f"{'Name':<12} {'Start (UTC)':<28} {'End (UTC)':<28} {'Span'}")
        print("-" * 80)
        for es, ee, en in existing:
            print(
                f"{en:<12} {_format_ts(es):<28} {_format_ts(ee):<28} {(ee-es)/3600000:.2f}h"
            )

        print()
        print("--- Inventory Complete ---")
        print("No secrets printed. No DB mutations. Readonly session closed.")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
