"""CLI for #2719 claim evidence at rest proof against local SurrealDB."""

from __future__ import annotations

import argparse
import json
import sys

from tools.surrealdb.claim_evidence_proof_runtime import (
    check_claim_evidence_proof_preconditions,
    run_claim_evidence_proof_cycle,
)

EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run read-only claim evidence at rest proof against "
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
        help="Seed run-scoped fixtures, prove claim evidence at rest, cleanup",
    )
    run.add_argument(
        "--confirm",
        action="store_true",
        help="Operator GO without CDB_RUN_REAL_SURREALDB_MEMORY_SMOKE=1",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "preflight":
            result = check_claim_evidence_proof_preconditions(confirm=args.confirm)
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK if result["ok"] else EXIT_RUNTIME

        if args.command == "run-proof":
            result = run_claim_evidence_proof_cycle(confirm=args.confirm)
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK

    except RuntimeError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        return EXIT_RUNTIME

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
