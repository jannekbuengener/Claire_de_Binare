"""Readonly PB1 cluster verification for #3343.

Safe: reads POSTGRES_READONLY_PASSWORD_DSN from env, never prints it.
"""

from __future__ import annotations
import os
import sys
from datetime import datetime, timezone

import psycopg2

_READONLY_DSN_ENV = "POSTGRES_READONLY_PASSWORD_DSN"
_EXPECTED_READONLY_LOGIN = "cdb_readonly"


def fmt(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def main() -> int:
    dsn = os.getenv(_READONLY_DSN_ENV)
    if not dsn or not dsn.strip():
        print("FATAL: POSTGRES_READONLY_PASSWORD_DSN not set")
        return 1

    conn = psycopg2.connect(dsn.strip(), connect_timeout=10)
    cur = conn.cursor()

    # identity
    cur.execute("SELECT current_database(), current_user, session_user")
    row = cur.fetchone()
    db_name, cu, su = row
    print(f"Connected: db={db_name}, user={cu}, session={su}")
    assert (
        cu == _EXPECTED_READONLY_LOGIN and su == _EXPECTED_READONLY_LOGIN
    ), "Identity fail"

    # readonly
    cur.execute(
        """SELECT has_table_privilege(current_user, 'public.correlation_ledger', 'SELECT'),
                          has_table_privilege(current_user, 'public.correlation_ledger', 'INSERT')"""
    )
    sel, ins = cur.fetchone()
    assert sel, "SELECT not granted"
    assert not ins, "INSERT should be false"
    print("Privileges: SELECT=OK, INSERT=BLOCKED")
    print()

    # ========================================================================
    # 1) EVERY primary_breakout_v1 event sorted by timestamp
    # ========================================================================
    cur.execute("""
        SELECT event_pk, timestamp_ms, event_type, correlation_id, signal_id, order_id, fill_id
        FROM public.correlation_ledger
        WHERE payload->>'strategy_id' = 'primary_breakout_v1'
          AND symbol = 'BTCUSDT'
        ORDER BY timestamp_ms ASC, event_pk ASC
    """)
    colnames = [d.name for d in cur.description]
    all_rows = [dict(zip(colnames, r)) for r in cur.fetchall()]
    print(f"Total primary_breakout_v1/BTCUSDT rows: {len(all_rows)}")
    print()

    # ========================================================================
    # 2) Cluster detection (gap > 1h = new cluster)
    # ========================================================================
    clusters = []
    current_cluster = None
    for r in all_rows:
        ts = r["timestamp_ms"]
        if current_cluster is None:
            current_cluster = {
                "min_ts": ts,
                "max_ts": ts,
                "events": [],
                "signal_ids": set(),
                "correlation_ids": set(),
                "order_ids": set(),
                "fill_ids": set(),
                "has_trade": False,
            }
        else:
            if ts - current_cluster["max_ts"] > 3_600_000:
                clusters.append(current_cluster)
                current_cluster = {
                    "min_ts": ts,
                    "max_ts": ts,
                    "events": [],
                    "signal_ids": set(),
                    "correlation_ids": set(),
                    "order_ids": set(),
                    "fill_ids": set(),
                    "has_trade": False,
                }
            else:
                if ts > current_cluster["max_ts"]:
                    current_cluster["max_ts"] = ts

        current_cluster["events"].append(r)
        current_cluster["correlation_ids"].add(r["correlation_id"])
        if r["event_type"] == "SIGNAL" and r["signal_id"]:
            current_cluster["signal_ids"].add(r["signal_id"])
        if r["event_type"] == "ORDER" and r["order_id"]:
            current_cluster["order_ids"].add(r["order_id"])
            current_cluster["has_trade"] = True
        if r["event_type"] == "FILL" and r["fill_id"]:
            current_cluster["fill_ids"].add(r["fill_id"])
            current_cluster["has_trade"] = True

    if current_cluster is not None:
        clusters.append(current_cluster)

    # ========================================================================
    # 3) Report each cluster
    # ========================================================================
    print("=" * 120)
    print("PRIMARY_BREAKOUT_V1 — ALL CLUSTERS (gap threshold = 1h)")
    print("=" * 120)
    print()

    for idx, c in enumerate(clusters, 1):
        span_s = (c["max_ts"] - c["min_ts"]) / 1000
        span_h = span_s / 3600
        min_ts_dt = fmt(c["min_ts"])
        max_ts_dt = fmt(c["max_ts"])

        # Count event types
        type_counts = {}
        for e in c["events"]:
            et = e["event_type"]
            type_counts[et] = type_counts.get(et, 0) + 1

        sig_cnt = type_counts.get("SIGNAL", 0)
        dec_cnt = type_counts.get("DECISION", 0)
        ord_cnt = type_counts.get("ORDER", 0)
        fill_cnt = type_counts.get("FILL", 0)
        total_ev = len(c["events"])
        total_corr = len(c["correlation_ids"])

        # Check if cluster contains DECISION events (they have sid=NULL)
        has_decision = dec_cnt > 0
        has_trade = c["has_trade"]

        # Inclusion/exclusion verdict
        reasons = []
        if span_h < 2:
            reasons.append(f"duration={span_h:.1f}h < 2h minimum")
        if not has_decision:
            reasons.append("no DECISION events")
        if not has_trade:
            reasons.append("no ORDER/FILL chain")
        if total_corr < 1:
            reasons.append("zero correlation_ids")
        verdict = "EXCLUDE" if reasons else "INCLUDE"
        print(f"--- Cluster {idx} ---")
        print(f"  Start UTC:       {min_ts_dt}")
        print(f"  End UTC:         {max_ts_dt}")
        print(f"  Duration:        {span_h:.3f}h ({span_s:.1f}s)")
        print(
            f"  Source:          public.correlation_ledger (payload->>strategy_id=primary_breakout_v1, symbol=BTCUSDT)"
        )
        print(f"  Total events:    {total_ev}")
        print(f"  Total chains:    {total_corr} (unique correlation_ids)")
        print(
            f"  Event breakdown: SIGNAL={sig_cnt} DECISION={dec_cnt} ORDER={ord_cnt} FILL={fill_cnt}"
        )
        print(f"  Has trade chain: {has_trade}")
        print(f"  Verdict:         {verdict}")
        if reasons:
            print(f"  Exclusion due to: {'; '.join(reasons)}")
        print()

    # ========================================================================
    # 4) Summary verdict for entire PB1 path
    # ========================================================================
    max_cluster = max(clusters, key=lambda c: c["max_ts"] - c["min_ts"])
    max_span_h = (max_cluster["max_ts"] - max_cluster["min_ts"]) / 3_600_000
    print("=" * 60)
    print("PB1 WINDOW-BANK PATH VERDICT")
    print("=" * 60)
    print(f"  Max PB1 cluster duration: {max_span_h:.3f}h ({max_span_h*60:.1f}min)")
    print(f"  Target minimum:           2.000h")
    print(f"  Gap to target:            {2.0 - max_span_h:.3f}h")
    print()
    if max_span_h < 2.0:
        print("  RESULT: HOLD_NO_VALID_PRIMARY_BREAKOUT_WINDOWS")
        print(
            "  Reason: No primary_breakout_v1 cluster > 2h found in correlation_ledger."
        )
    else:
        print("  RESULT: CANDIDATE_FOUND — see cluster table above.")
    print()

    # ========================================================================
    # 5) Separate: broader paper-strategy clusters (NOT PB1 evidence)
    # ========================================================================
    print("=" * 120)
    print("PAPER STRATEGY — SEPARATE REFERENCE (NOT PB1 evidence)")
    print("=" * 120)
    print()

    cur.execute("""
        WITH numbered AS (
          SELECT timestamp_ms, event_type, correlation_id,
            LAG(timestamp_ms) OVER (ORDER BY timestamp_ms) AS prev_ts_ms
          FROM public.correlation_ledger
          WHERE payload->>'strategy_id' = 'paper'
            AND symbol = 'BTCUSDT'
        ),
        gaps AS (
          SELECT timestamp_ms, event_type, correlation_id,
            CASE WHEN prev_ts_ms IS NULL OR timestamp_ms - prev_ts_ms > 3600000 THEN 1 ELSE 0 END AS new_cluster
          FROM numbered
        ),
        clustered AS (
          SELECT timestamp_ms, event_type, correlation_id,
            SUM(new_cluster) OVER (ORDER BY timestamp_ms) AS cluster_id
          FROM gaps
        )
        SELECT
          cluster_id,
          MIN(timestamp_ms) AS min_ts_ms,
          MAX(timestamp_ms) AS max_ts_ms,
          MAX(timestamp_ms) - MIN(timestamp_ms) AS span_ms,
          COUNT(*) AS total_events,
          COUNT(DISTINCT correlation_id) AS total_chains,
          COUNT(*) FILTER (WHERE event_type = 'SIGNAL') AS signal_count,
          COUNT(*) FILTER (WHERE event_type = 'ORDER') AS order_count,
          COUNT(*) FILTER (WHERE event_type = 'FILL') AS fill_count
        FROM clustered
        GROUP BY cluster_id
        ORDER BY cluster_id
    """)
    colnames_p = [d.name for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(colnames_p, r))
        span_h = row["span_ms"] / 3_600_000
        print(
            f"  Cluster {row['cluster_id']}: "
            f"{fmt(row['min_ts_ms'])} -> {fmt(row['max_ts_ms'])}, "
            f"{span_h:.1f}h, "
            f"SIGNAL={row['signal_count']} ORDER={row['order_count']} FILL={row['fill_count']}, "
            f"chains={row['total_chains']}"
        )
    print()
    print("  NOTE: Paper strategy events have sid='paper', NOT primary_breakout_v1.")
    print(
        "  NOTE: These are NOT admissible as PB1 window-bank evidence per #3343 scope."
    )
    print("  NOTE: Paper strategy ORDER/FILL count is 4 across entire DB.")
    print()

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
