"""CLI for #2720 cross-session memory rediscovery proof."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.surrealdb.memory_rediscovery_proof_runtime import (
    check_memory_rediscovery_proof_preconditions,
    run_memory_rediscovery_proof_cycle,
    run_prove_phase_only,
)

EXIT_OK = 0
EXIT_RUNTIME = 1
EXIT_USAGE = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Cross-session memory rediscovery proof (manifest + DB). "
            "LR: NO-GO. No productive write."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="Check local SurrealDB preconditions")
    preflight.add_argument("--confirm", action="store_true")

    run = sub.add_parser(
        "run-proof",
        help="Seed fixtures, write manifest, prove in subprocess, cleanup",
    )
    run.add_argument("--confirm", action="store_true")

    prove = sub.add_parser(
        "prove-phase",
        help="Prove phase only (subprocess); requires existing manifest + DB rows",
    )
    prove.add_argument(
        "--manifest",
        required=True,
        help="Path to rediscovery manifest.json",
    )
    prove.add_argument("--confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "preflight":
            result = check_memory_rediscovery_proof_preconditions(confirm=args.confirm)
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK if result["ok"] else EXIT_RUNTIME

        if args.command == "run-proof":
            result = run_memory_rediscovery_proof_cycle(confirm=args.confirm)
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK

        if args.command == "prove-phase":
            result = run_prove_phase_only(
                manifest_path=Path(args.manifest),
                confirm=args.confirm,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return EXIT_OK

    except RuntimeError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, indent=2))
        return EXIT_RUNTIME

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
