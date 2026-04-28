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
import json
import sys
from pathlib import Path

from core.replay.canonical_json import canonical_json_dumps
from core.replay.paper_reference_window_export import (
    PaperReferenceExportError,
    build_export_request,
    export_paper_reference_window,
)
from core.utils.postgres_client import create_postgres_connection


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
    return "; ".join(qualifiers)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    request = None
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

        conn = create_postgres_connection()
        try:
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
        finally:
            conn.close()

        payload = export_paper_reference_window(request=request, rows=rows)
        out_path.write_text(canonical_json_dumps(payload), encoding="utf-8")
    except PaperReferenceExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERROR: paper_reference_window export failed: {exc}", file=sys.stderr)
        return 2

    print(
        "OK: paper_reference_window exported "
        f"(strategy_id={request.strategy_id}, symbol={request.symbol}, "
        f"window=[{request.start_ts_ms_utc},{request.end_ts_ms_utc}], "
        f"bot_id={request.bot_id or '*'}, config_hash={request.config_hash or '*'})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
