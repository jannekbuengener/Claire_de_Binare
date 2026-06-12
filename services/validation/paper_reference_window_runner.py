"""CLI runner to export a comparison-grade paper_reference_window (#1907).

Source of truth:
  - Postgres public.correlation_ledger (append-only audit trail)

Produces:
  - paper_reference_window.json (contract_version arvp_paper_reference_window.v1)

Exit codes:
  0  export succeeded
  1  CLI / argument error
  2  runtime / DB / contract validation error (fail-closed)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2

from core.replay.canonical_json import canonical_json_dumps
from core.replay.paper_reference_window_export import (
    PaperReferenceExportError,
    build_export_request,
    export_paper_reference_window,
)
from core.utils.clock import utcnow
from core.utils.evidence_class import (
    EvidenceClassError,
    evidence_class_warning_banner,
    validate_evidence_class,
)

_READONLY_DSN_ENV = "POSTGRES_READONLY_PASSWORD_DSN"
_EXPECTED_READONLY_LOGIN = "cdb_readonly"
_IDENTITY_PROBE_SQL = "SELECT current_database(), current_user, session_user;"
_READONLY_PRIVILEGE_PROBE_SQL = """
SELECT
  has_table_privilege(current_user, 'public.correlation_ledger', 'SELECT'),
  has_table_privilege(current_user, 'public.correlation_ledger', 'INSERT'),
  has_table_privilege(current_user, 'public.correlation_ledger', 'UPDATE'),
  has_table_privilege(current_user, 'public.correlation_ledger', 'DELETE')
"""


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="paper_reference_window_runner")
    p.add_argument("--strategy-id", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--start-ts-ms", required=True, type=int)
    p.add_argument("--end-ts-ms", required=True, type=int)
    p.add_argument(
        "--bot-id",
        help="Optional bot_id filter applied via SIGNAL anchor metadata.",
    )
    p.add_argument(
        "--config-hash",
        help="Optional config_hash filter applied via SIGNAL anchor metadata.",
    )
    p.add_argument(
        "--output",
        default="artifacts/paper_reference_windows/paper_reference_window.json",
        help="Output path for paper_reference_window JSON.",
    )
    p.add_argument(
        "--extracted-by",
        default="paper_reference_window_runner",
        help="Extractor identifier (non-empty).",
    )
    p.add_argument(
        "--causal-lookup-start-ms",
        type=int,
        help="Optional earlier bound for causal pre-window SIGNAL lookup (#3058).",
    )
    p.add_argument(
        "--causal-lookup-end-ms",
        type=int,
        help="Optional later bound for causal post-window SIGNAL lookup (#3058).",
    )
    p.add_argument(
        "--chain-source",
        default="live",
        choices=["live", "stimulus"],
        help="Source of the chain: 'live' (natural market, default) or 'stimulus' (synthetic fixture). "
        "Stimulus chains are classified as pipeline_test_evidence.",
    )
    return p.parse_args(argv)


def _build_source_query_intent(args: argparse.Namespace) -> str:
    qualifiers = [
        "select correlation_ledger events by symbol+timestamp_ms window",
        "validate payload.strategy_id",
        "resolve bot_id/config_hash via SIGNAL anchors",
        "enforce homogeneity+chain-integrity fail-closed",
        "qualify paper via order_id prefix",
    ]
    if args.bot_id:
        qualifiers.append(f"filter bot_id={args.bot_id}")
    if args.config_hash:
        qualifiers.append(f"filter config_hash={args.config_hash}")
    qualifiers.append(f"chain_source={getattr(args, 'chain_source', 'live')}")
    return "; ".join(qualifiers)


def _get_required_readonly_dsn() -> str:
    readonly_dsn = os.getenv(_READONLY_DSN_ENV)
    if readonly_dsn is None or not readonly_dsn.strip():
        raise RuntimeError(
            f"{_READONLY_DSN_ENV} is required for readonly paper_reference_window export"
        )
    return readonly_dsn.strip()


def _create_readonly_connection():
    readonly_dsn = _get_required_readonly_dsn()
    return psycopg2.connect(readonly_dsn, connect_timeout=10)


def _verify_readonly_identity(conn) -> tuple[str, str, str]:
    with conn.cursor() as cursor:
        cursor.execute(_IDENTITY_PROBE_SQL)
        identity_row = cursor.fetchone()

    if identity_row is None or len(identity_row) != 3:
        raise RuntimeError(
            "Readonly identity probe did not return current_database/current_user/session_user"
        )

    current_database, current_user, session_user = identity_row
    if (
        current_user != _EXPECTED_READONLY_LOGIN
        or session_user != _EXPECTED_READONLY_LOGIN
    ):
        raise RuntimeError(
            "Readonly identity probe failed: "
            f"current_user={current_user}, session_user={session_user}, "
            f"expected={_EXPECTED_READONLY_LOGIN}"
        )

    return str(current_database), str(current_user), str(session_user)


def _verify_readonly_privileges(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute(_READONLY_PRIVILEGE_PROBE_SQL)
        privilege_row = cursor.fetchone()

    if privilege_row is None or len(privilege_row) != 4:
        raise RuntimeError(
            "Readonly privilege probe did not return SELECT/INSERT/UPDATE/DELETE flags"
        )

    can_select, can_insert, can_update, can_delete = privilege_row
    if not can_select:
        raise RuntimeError(
            "Readonly privilege probe failed: missing SELECT on public.correlation_ledger"
        )
    if can_insert or can_update or can_delete:
        raise RuntimeError(
            "Readonly privilege probe failed: write privileges detected on "
            "public.correlation_ledger"
        )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    request = None
    readonly_identity: tuple[str, str, str] | None = None
    try:
        request = build_export_request(
            strategy_id=str(args.strategy_id),
            symbol=str(args.symbol),
            start_ts_ms_utc=int(args.start_ts_ms),
            end_ts_ms_utc=int(args.end_ts_ms),
            extracted_by=str(args.extracted_by),
            source_query_intent=_build_source_query_intent(args),
            bot_id=str(args.bot_id) if args.bot_id is not None else None,
            config_hash=str(args.config_hash) if args.config_hash is not None else None,
        )

        conn = _create_readonly_connection()
        causal_context_rows: list[dict[str, Any]] = []
        try:
            readonly_identity = _verify_readonly_identity(conn)
            _verify_readonly_privileges(conn)
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      event_pk,
                      correlation_id,
                      signal_id,
                      decision_id,
                      order_id,
                      fill_id,
                      event_type,
                      symbol,
                      timestamp_ms,
                      payload
                    FROM correlation_ledger
                    WHERE symbol = %s
                      AND timestamp_ms >= %s
                      AND timestamp_ms <= %s
                    ORDER BY timestamp_ms ASC, event_pk ASC
                    """,
                    (request.symbol, request.start_ts_ms_utc, request.end_ts_ms_utc),
                )
                colnames = [d.name for d in cursor.description]
                rows = [dict(zip(colnames, r, strict=True)) for r in cursor.fetchall()]

                # Causal context lookup (#3058):
                # Find signal_ids on in-window ORDER/FILL events, then look up
                # SIGNAL events with those signal_ids outside the window bounds.
                causal_signal_ids: set[str] = set()
                for r in rows:
                    et = (r.get("event_type") or "").upper()
                    if et in ("ORDER", "FILL"):
                        sid = r.get("signal_id")
                        if isinstance(sid, str) and sid.strip():
                            causal_signal_ids.add(sid.strip())
                if causal_signal_ids and (
                    args.causal_lookup_start_ms is not None
                    or args.causal_lookup_end_ms is not None
                ):
                    lookup_start = (
                        args.causal_lookup_start_ms or request.start_ts_ms_utc
                    )
                    lookup_end = args.causal_lookup_end_ms or request.end_ts_ms_utc
                    cursor.execute(
                        """
                        SELECT
                          event_pk,
                          correlation_id,
                          signal_id,
                          decision_id,
                          order_id,
                          fill_id,
                          event_type,
                          symbol,
                          timestamp_ms,
                          payload
                        FROM correlation_ledger
                        WHERE event_type = 'SIGNAL'
                          AND signal_id = ANY(%s)
                          AND symbol = %s
                          AND (
                            timestamp_ms < %s
                            OR timestamp_ms > %s
                          )
                          AND timestamp_ms >= %s
                          AND timestamp_ms <= %s
                        ORDER BY timestamp_ms ASC
                        """,
                        (
                            list(causal_signal_ids),
                            request.symbol,
                            request.start_ts_ms_utc,
                            request.end_ts_ms_utc,
                            lookup_start,
                            lookup_end,
                        ),
                    )
                    causal_colnames = [d.name for d in cursor.description]
                    causal_context_rows = [
                        dict(zip(causal_colnames, r, strict=True))
                        for r in cursor.fetchall()
                    ]
        finally:
            conn.close()

        payload = export_paper_reference_window(
            request=request, rows=rows, causal_context_rows=causal_context_rows
        )
    except PaperReferenceExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: paper_reference_window export failed: {exc}", file=sys.stderr)
        return 2

    now_utc = utcnow().isoformat()
    extracted_by = getattr(request, "extracted_by", "paper_reference_window_runner")

    # Evidence class is determined by --chain-source CLI arg. Stimulus-runner
    # chains cannot be detected from persisted ledger fields (stimulus_run_id
    # is used for UUIDv5 signal-id seeding but never stored), so the operator
    # must explicitly declare the chain source (#3129 review).
    chain_source = getattr(args, "chain_source", "live")
    if chain_source == "stimulus":
        evidence_class = "pipeline_test_evidence"
        payload["pipeline_tool"] = "paper_runtime_stimulus_runner"
        payload["fixture_source"] = f"extracted_by={extracted_by}"
    else:
        evidence_class = "natural_paper_evidence"
        payload["campaign_id"] = request.strategy_id
        payload["start_criterion"] = "ledger_export"
        payload["safety_flags"] = {
            "mock_trading": True,
            "dry_run": True,
            "mexc_testnet": True,
        }
        payload["provenance"] = f"extracted_by={extracted_by}@{now_utc}"

    warning_banner = evidence_class_warning_banner(evidence_class)
    payload["evidence_class"] = evidence_class
    payload["evidence_class_version"] = "1.0"
    payload["produced_by"] = "paper_reference_window_runner"
    payload["produced_at_utc"] = now_utc
    if warning_banner:
        payload["warning_banner"] = warning_banner

    try:
        validate_evidence_class(payload)
    except EvidenceClassError as exc:
        print(f"EVIDENCE CLASS VALIDATION FAILED: {exc}", file=sys.stderr)
        return 2

    out_path.write_text(canonical_json_dumps(payload), encoding="utf-8")

    readonly_database, readonly_current_user, readonly_session_user = readonly_identity
    print(
        "OK: paper_reference_window exported "
        f"(strategy_id={request.strategy_id}, symbol={request.symbol}, "
        f"window=[{request.start_ts_ms_utc},{request.end_ts_ms_utc}], "
        f"bot_id={request.bot_id or '*'}, config_hash={request.config_hash or '*'}, "
        f"evidence_class={evidence_class}, "
        f"chain_source={chain_source}, "
        f"database={readonly_database}, current_user={readonly_current_user}, "
        f"session_user={readonly_session_user})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
