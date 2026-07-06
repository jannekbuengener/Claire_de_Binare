"""Readonly natural-paper window bank inventory for #3742.

Safe usage:
  POSTGRES_READONLY_PASSWORD_DSN must be set in the environment.
  python scripts/arvp_3742_natural_paper_window_inventory.py

Output: cluster inventory + classification matrix; no DSN/credential values printed.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg2

_READONLY_DSN_ENV = "POSTGRES_READONLY_PASSWORD_DSN"
_EXPECTED_READONLY_LOGIN = "cdb_readonly"
_SYMBOL = "BTCUSDT"
_GAP_MS = 3_600_000  # 1h gap = new cluster
_MIN_COMPARISON_SPAN_MS = 7_200_000  # 2h aspirational minimum from #3343/#3742 context
_PAPER_PREFIX = "paper_"

_EXISTING_WINDOWS: list[tuple[int, int, str]] = [
    (1713919320000, 1713919380000, "pilot_1m"),
    (1780705692551, 1780705812814, "3028_2m"),
    (1780702200000, 1780705800000, "june6_1h"),
]

_ADMISSIBLE_STRATEGY_IDS = ("primary_breakout_v1", "paper")


@dataclass(frozen=True)
class ClusterRow:
    source: str
    strategy_id: str
    cluster_id: int
    min_ts_ms: int
    max_ts_ms: int
    span_ms: int
    total_events: int
    total_chains: int
    signal_count: int
    decision_count: int
    order_count: int
    fill_count: int
    paper_order_count: int
    paper_fill_count: int
    has_trade_chain: bool

    @property
    def span_hours(self) -> float:
        return self.span_ms / 3_600_000

    @property
    def span_minutes(self) -> float:
        return self.span_ms / 60_000


def _format_ts(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()


def _get_readonly_dsn() -> str:
    dsn = os.getenv(_READONLY_DSN_ENV)
    if not dsn or not dsn.strip():
        raise RuntimeError(f"{_READONLY_DSN_ENV} is required")
    return dsn.strip()


def _verify_identity_and_privileges(conn) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user, session_user")
        db_name, current_user, session_user = cur.fetchone()
        if (
            current_user != _EXPECTED_READONLY_LOGIN
            or session_user != _EXPECTED_READONLY_LOGIN
        ):
            raise RuntimeError(
                "Identity mismatch: "
                f"current_user={current_user}, session_user={session_user}"
            )

        cur.execute(
            """
            SELECT
              has_table_privilege(current_user, 'public.correlation_ledger', 'SELECT'),
              has_table_privilege(current_user, 'public.correlation_ledger', 'INSERT'),
              has_table_privilege(current_user, 'public.correlation_ledger', 'UPDATE'),
              has_table_privilege(current_user, 'public.correlation_ledger', 'DELETE')
            """
        )
        ledger_sel, ledger_ins, ledger_upd, ledger_del = cur.fetchone()
        if not ledger_sel or ledger_ins or ledger_upd or ledger_del:
            raise RuntimeError(
                "Invalid correlation_ledger privileges: "
                f"SELECT={ledger_sel}, INSERT={ledger_ins}, "
                f"UPDATE={ledger_upd}, DELETE={ledger_del}"
            )

        cur.execute(
            """
            SELECT
              has_table_privilege(current_user, 'public.candles_1m', 'SELECT'),
              has_table_privilege(current_user, 'public.candles_1m', 'INSERT'),
              has_table_privilege(current_user, 'public.candles_1m', 'UPDATE'),
              has_table_privilege(current_user, 'public.candles_1m', 'DELETE')
            """
        )
        candles_sel, candles_ins, candles_upd, candles_del = cur.fetchone()
        candles_ok = bool(candles_sel) and not (
            candles_ins or candles_upd or candles_del
        )

        cur.execute("SELECT COUNT(*) FROM public.correlation_ledger")
        total_rows = int(cur.fetchone()[0])
        cur.execute(
            """
            SELECT MIN(timestamp_ms), MAX(timestamp_ms)
            FROM public.correlation_ledger
            """
        )
        min_ts, max_ts = cur.fetchone()

        cur.execute(
            """
            SELECT payload->>'strategy_id' AS strategy_id, COUNT(*) AS cnt
            FROM public.correlation_ledger
            WHERE symbol = %s
            GROUP BY payload->>'strategy_id'
            ORDER BY cnt DESC
            """,
            (_SYMBOL,),
        )
        strategy_counts = {row[0] or "<null>": int(row[1]) for row in cur.fetchall()}

    return {
        "database": db_name,
        "current_user": current_user,
        "session_user": session_user,
        "ledger_privileges": {
            "select": bool(ledger_sel),
            "insert": bool(ledger_ins),
            "update": bool(ledger_upd),
            "delete": bool(ledger_del),
        },
        "candles_privileges_ok": candles_ok,
        "total_rows": total_rows,
        "min_ts_ms": int(min_ts) if min_ts is not None else None,
        "max_ts_ms": int(max_ts) if max_ts is not None else None,
        "strategy_counts": strategy_counts,
    }


def _fetch_clusters_for_strategy(conn, strategy_id: str) -> list[ClusterRow]:
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH numbered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                order_id,
                fill_id,
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
                order_id,
                fill_id,
                CASE
                  WHEN prev_ts_ms IS NULL OR timestamp_ms - prev_ts_ms > %s
                  THEN 1 ELSE 0
                END AS new_cluster
              FROM numbered
            ),
            clustered AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                order_id,
                fill_id,
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
                COUNT(*) FILTER (WHERE event_type = 'FILL') AS fill_count,
                COUNT(*) FILTER (
                  WHERE event_type = 'ORDER'
                    AND order_id LIKE %s
                ) AS paper_order_count,
                COUNT(*) FILTER (
                  WHERE event_type = 'FILL'
                    AND fill_id IS NOT NULL
                    AND EXISTS (
                      SELECT 1
                      FROM public.correlation_ledger o
                      WHERE o.correlation_id = clustered.correlation_id
                        AND o.event_type = 'ORDER'
                        AND o.order_id LIKE %s
                    )
                ) AS paper_fill_count
              FROM clustered
              GROUP BY cluster_id
            )
            SELECT *
            FROM cluster_stats
            ORDER BY min_ts_ms ASC
            """,
            (strategy_id, _SYMBOL, _GAP_MS, f"{_PAPER_PREFIX}%", f"{_PAPER_PREFIX}%"),
        )
        colnames = [d.name for d in cur.description]
        rows: list[ClusterRow] = []
        for raw in cur.fetchall():
            row = dict(zip(colnames, raw, strict=True))
            paper_orders = int(row["paper_order_count"])
            paper_fills = int(row["paper_fill_count"])
            rows.append(
                ClusterRow(
                    source=f"strategy_id={strategy_id}",
                    strategy_id=strategy_id,
                    cluster_id=int(row["cluster_id"]),
                    min_ts_ms=int(row["min_ts_ms"]),
                    max_ts_ms=int(row["max_ts_ms"]),
                    span_ms=int(row["span_ms"]),
                    total_events=int(row["total_events"]),
                    total_chains=int(row["total_chains"]),
                    signal_count=int(row["signal_count"]),
                    decision_count=int(row["decision_count"]),
                    order_count=int(row["order_count"]),
                    fill_count=int(row["fill_count"]),
                    paper_order_count=paper_orders,
                    paper_fill_count=paper_fills,
                    has_trade_chain=paper_orders > 0 and paper_fills > 0,
                )
            )
    return rows


def _fetch_paper_qualified_clusters(conn) -> list[ClusterRow]:
    """Clusters built from paper_-qualified ORDER/FILL events regardless of strategy_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH paper_events AS (
              SELECT
                timestamp_ms,
                event_type,
                correlation_id,
                order_id,
                fill_id,
                COALESCE(payload->>'strategy_id', '<null>') AS strategy_id
              FROM public.correlation_ledger
              WHERE symbol = %s
                AND (
                  (event_type = 'ORDER' AND order_id LIKE %s)
                  OR (
                    event_type = 'FILL'
                    AND EXISTS (
                      SELECT 1
                      FROM public.correlation_ledger o
                      WHERE o.correlation_id = correlation_ledger.correlation_id
                        AND o.event_type = 'ORDER'
                        AND o.order_id LIKE %s
                    )
                  )
                )
            ),
            numbered AS (
              SELECT
                *,
                LAG(timestamp_ms) OVER (ORDER BY timestamp_ms) AS prev_ts_ms
              FROM paper_events
            ),
            gaps AS (
              SELECT
                *,
                CASE
                  WHEN prev_ts_ms IS NULL OR timestamp_ms - prev_ts_ms > %s
                  THEN 1 ELSE 0
                END AS new_cluster
              FROM numbered
            ),
            clustered AS (
              SELECT
                *,
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
                COUNT(*) FILTER (WHERE event_type = 'FILL') AS fill_count,
                COUNT(*) FILTER (
                  WHERE event_type = 'ORDER' AND order_id LIKE %s
                ) AS paper_order_count,
                COUNT(*) FILTER (WHERE event_type = 'FILL') AS paper_fill_count,
                array_agg(DISTINCT strategy_id) AS strategy_ids
              FROM clustered
              GROUP BY cluster_id
            )
            SELECT *
            FROM cluster_stats
            ORDER BY min_ts_ms ASC
            """,
            (_SYMBOL, f"{_PAPER_PREFIX}%", f"{_PAPER_PREFIX}%", _GAP_MS, f"{_PAPER_PREFIX}%"),
        )
        colnames = [d.name for d in cur.description]
        rows: list[ClusterRow] = []
        for raw in cur.fetchall():
            row = dict(zip(colnames, raw, strict=True))
            strategy_ids = row.get("strategy_ids") or []
            sid_label = ",".join(sorted(str(s) for s in strategy_ids))
            rows.append(
                ClusterRow(
                    source="paper_qualified_chains",
                    strategy_id=sid_label or "<mixed>",
                    cluster_id=int(row["cluster_id"]),
                    min_ts_ms=int(row["min_ts_ms"]),
                    max_ts_ms=int(row["max_ts_ms"]),
                    span_ms=int(row["span_ms"]),
                    total_events=int(row["total_events"]),
                    total_chains=int(row["total_chains"]),
                    signal_count=int(row["signal_count"]),
                    decision_count=int(row["decision_count"]),
                    order_count=int(row["order_count"]),
                    fill_count=int(row["fill_count"]),
                    paper_order_count=int(row["paper_order_count"]),
                    paper_fill_count=int(row["paper_fill_count"]),
                    has_trade_chain=True,
                )
            )
    return rows


def _overlap_existing(min_ts_ms: int, max_ts_ms: int) -> str:
    for start_ms, end_ms, name in _EXISTING_WINDOWS:
        if min_ts_ms < end_ms and max_ts_ms > start_ms:
            return f"overlaps_{name}"
    return "none"


def _candles_coverage(conn, min_ts_ms: int, max_ts_ms: int) -> dict[str, Any] | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)::bigint
            FROM public.candles_1m
            WHERE symbol = %s
              AND ts_ms >= %s
              AND ts_ms <= %s
            """,
            (_SYMBOL, min_ts_ms, max_ts_ms),
        )
        count = int(cur.fetchone()[0])
    if count == 0:
        return {"candle_count": 0, "coverage": "none"}
    span_minutes = max(1, int((max_ts_ms - min_ts_ms) / 60_000))
    return {
        "candle_count": count,
        "coverage": "partial" if count < span_minutes else "full_or_better",
        "span_minutes": span_minutes,
    }


def _classify_cluster(cluster: ClusterRow) -> dict[str, str]:
    overlap = _overlap_existing(cluster.min_ts_ms, cluster.max_ts_ms)
    reasons: list[str] = []

    if cluster.strategy_id == "paper" and cluster.source.startswith("strategy_id="):
        reasons.append(
            "strategy_id=paper not PB1 replay-comparable without adapter scope change"
        )

    if not cluster.has_trade_chain:
        reasons.append("no paper_-qualified ORDER+FILL chain")

    if cluster.paper_order_count < 1 or cluster.paper_fill_count < 1:
        reasons.append("insufficient paper order/fill qualification")

    if cluster.span_ms < _MIN_COMPARISON_SPAN_MS:
        reasons.append(f"span={cluster.span_hours:.2f}h < 2h comparison target")

    if cluster.signal_count == 0 and cluster.decision_count == 0:
        reasons.append("no SIGNAL/DECISION anchor context in cluster slice")

    if overlap != "none":
        reasons.append(f"existing_bank_{overlap}")

    if not cluster.has_trade_chain:
        classification = "inadmissible"
    elif cluster.strategy_id == "paper" and cluster.source.startswith("strategy_id="):
        classification = "inadmissible"
    elif overlap != "none":
        classification = "non-comparable"
    elif cluster.span_ms < _MIN_COMPARISON_SPAN_MS:
        classification = "non-comparable"
    else:
        classification = "comparable"

    regime_status = "unavailable"
    if classification == "inadmissible":
        regime_status = "not_assessable"
    elif not cluster.has_trade_chain:
        regime_status = "not_assessable"

    return {
        "comparability": classification,
        "regime_segments": regime_status,
        "overlap": overlap,
        "reasons": "; ".join(reasons) if reasons else "meets readonly pre-check",
    }


def _print_cluster_table(clusters: list[ClusterRow], conn, candles_ok: bool) -> None:
    print(
        f"{'Src':<22} {'#':<4} {'Start UTC':<26} {'End UTC':<26} "
        f"{'Span':<8} {'Ev':<6} {'Ch':<5} {'PO':<4} {'PF':<4} "
        f"{'Class':<14} {'Regime':<12} {'Overlap':<14}"
    )
    print("-" * 150)
    for cluster in clusters:
        verdict = _classify_cluster(cluster)
        span_label = (
            f"{cluster.span_hours:.1f}h"
            if cluster.span_hours >= 1
            else f"{cluster.span_minutes:.1f}m"
        )
        print(
            f"{cluster.source:<22} {cluster.cluster_id:<4} "
            f"{_format_ts(cluster.min_ts_ms):<26} "
            f"{_format_ts(cluster.max_ts_ms):<26} "
            f"{span_label:<8} {cluster.total_events:<6} {cluster.total_chains:<5} "
            f"{cluster.paper_order_count:<4} {cluster.paper_fill_count:<4} "
            f"{verdict['comparability']:<14} {verdict['regime_segments']:<12} "
            f"{verdict['overlap']:<14}"
        )
        if candles_ok and cluster.has_trade_chain:
            coverage = _candles_coverage(conn, cluster.min_ts_ms, cluster.max_ts_ms)
            if coverage is not None:
                print(
                    f"    candles_1m: count={coverage['candle_count']}, "
                    f"coverage={coverage['coverage']}"
                )
        if verdict["reasons"]:
            print(f"    note: {verdict['reasons']}")


def _recommend_verdict(clusters: list[ClusterRow]) -> str:
    comparable_new = [
        c
        for c in clusters
        if _classify_cluster(c)["comparability"] == "comparable"
        and _overlap_existing(c.min_ts_ms, c.max_ts_ms) == "none"
    ]
    if comparable_new:
        return "WINDOW_EXTRACTED_REGIME_UNAVAILABLE"

    trade_clusters = [c for c in clusters if c.has_trade_chain]
    long_trade = [c for c in trade_clusters if c.span_ms >= _MIN_COMPARISON_SPAN_MS]
    if long_trade:
        return "WINDOW_EXTRACTED_REGIME_UNAVAILABLE"
    if trade_clusters:
        return "HOLD_NO_VALID_WINDOWS_READONLY"
    return "HOLD_NO_VALID_WINDOWS_READONLY"


def main() -> int:
    try:
        dsn = _get_readonly_dsn()
    except RuntimeError as exc:
        print(f"FATAL: {exc}")
        print("VERDICT_ENUM: HOLD_READONLY_ACCESS_UNAVAILABLE")
        return 1

    print("=== #3742 Natural-Paper Window Bank Inventory ===")
    print(f"DSN env: {_READONLY_DSN_ENV}=SET (value not printed)")
    print()

    try:
        conn = psycopg2.connect(dsn, connect_timeout=15)
    except psycopg2.OperationalError as exc:
        print("FATAL: readonly PostgreSQL connection failed")
        print(f"error_class: {exc.__class__.__name__}")
        print(
            "hint: verify POSTGRES_READONLY_PASSWORD_DSN operator config, cdb_readonly role, "
            "and that cdb_postgres is reachable on the DSN host/port"
        )
        print("VERDICT_ENUM: HOLD_READONLY_ACCESS_UNAVAILABLE")
        return 1

    try:
        ctx = _verify_identity_and_privileges(conn)
        print("--- Readonly Preflight ---")
        print(f"database: {ctx['database']}")
        print(
            f"identity: current_user={ctx['current_user']}, "
            f"session_user={ctx['session_user']}"
        )
        print(
            "correlation_ledger privileges: "
            f"SELECT={ctx['ledger_privileges']['select']}, "
            f"INSERT={ctx['ledger_privileges']['insert']}, "
            f"UPDATE={ctx['ledger_privileges']['update']}, "
            f"DELETE={ctx['ledger_privileges']['delete']}"
        )
        print(f"candles_1m readonly ok: {ctx['candles_privileges_ok']}")
        print(f"total correlation_ledger rows: {ctx['total_rows']}")
        if ctx["min_ts_ms"] is not None and ctx["max_ts_ms"] is not None:
            print(
                "date range: "
                f"{_format_ts(ctx['min_ts_ms'])} .. {_format_ts(ctx['max_ts_ms'])}"
            )
        print("strategy_id counts (BTCUSDT):")
        for sid, cnt in ctx["strategy_counts"].items():
            print(f"  {sid}: {cnt}")
        print()

        all_clusters: list[ClusterRow] = []
        for strategy_id in _ADMISSIBLE_STRATEGY_IDS:
            clusters = _fetch_clusters_for_strategy(conn, strategy_id)
            all_clusters.extend(clusters)
            print(
                f"--- Clusters: strategy_id={strategy_id} "
                f"({len(clusters)} total) ---"
            )
            _print_cluster_table(clusters, conn, ctx["candles_privileges_ok"])
            print()

        paper_clusters = _fetch_paper_qualified_clusters(conn)
        all_clusters.extend(paper_clusters)
        print(
            f"--- Clusters: paper_-qualified ORDER/FILL chains "
            f"({len(paper_clusters)} total) ---"
        )
        _print_cluster_table(paper_clusters, conn, ctx["candles_privileges_ok"])
        print()

        trade_dense = [c for c in all_clusters if c.has_trade_chain]
        over_2h_trade = [
            c for c in trade_dense if c.span_ms >= _MIN_COMPARISON_SPAN_MS
        ]
        comparable_new = [
            c
            for c in all_clusters
            if _classify_cluster(c)["comparability"] == "comparable"
            and _overlap_existing(c.min_ts_ms, c.max_ts_ms) == "none"
        ]

        print("--- Summary ---")
        print(f"trade-dense clusters (paper ORDER+FILL): {len(trade_dense)}")
        print(f"trade-dense clusters >=2h span: {len(over_2h_trade)}")
        print(
            f"new comparable candidates (not in existing bank): {len(comparable_new)}"
        )
        print(
            "regime_segments readonly path: unavailable "
            "(not in paper_reference export)"
        )
        print(
            "regime_segments artifact path: no populated segments in prior repo evidence"
        )
        print()

        verdict = _recommend_verdict(all_clusters)
        if not trade_dense and not over_2h_trade:
            verdict = "HOLD_NO_VALID_WINDOWS_READONLY"
        if verdict == "HOLD_NO_VALID_WINDOWS_READONLY":
            print(
                "follow-up gate: REQUIRES_RUNTIME_GO_FOR_FRESH_PAPER "
                "(separate #1784 Runtime Human-GO; not in #3742 scope)"
            )
        print(f"VERDICT_ENUM: {verdict}")
        print()
        print("No credentials printed. No DB mutations. Readonly session closed.")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
