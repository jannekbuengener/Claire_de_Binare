"""CLI for #2603 memory DB read + stale proof against local SurrealDB."""

from __future__ import annotations

import argparse
import json
import sys

from tools.surrealdb.memory_db_proof_runtime import (
    check_memory_db_proof_preconditions,
    run_memory_db_proof_cycle,
)

EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run read-only memory DB proof (read + stale scan) against "
            "surrealdb-local. LR: NO-GO. No productive write."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser(
        "preflight",
        help="Check env, secrets, query config, and local SurrealDB health",
    )
    preflight.add_argument(
        "--confirm",
        action="store_true",
        help="Skip CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE requirement for preflight only",
    )

    run = sub.add_parser(
        "run-proof",
        help="Seed run-scoped fixtures, prove read + stale, cleanup",
    )
    run.add_argument(
        "--confirm",
        action="store_true",
        help="Operator GO without CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1",
    )
    run.add_argument(
        "--format",
        choices=("json",),
        default="json",
        help="Output format (json only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "preflight":
            result = check_memory_db_proof_preconditions(confirm=args.confirm)
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK if result["ok"] else EXIT_RUNTIME

        if args.command == "run-proof":
            result = run_memory_db_proof_cycle(confirm=args.confirm)
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK

    except RuntimeError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        return EXIT_RUNTIME

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
