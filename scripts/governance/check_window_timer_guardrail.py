#!/usr/bin/env python3
"""Check that an observed canary window does not exceed the P5 policy limit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def load_max_window_minutes(policy_path: Path) -> int:
    text = policy_path.read_text(encoding="utf-8")
    match = re.search(r"^\s*max_window_minutes:\s*(\d+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError("max_window_minutes not found in policy")
    return int(match.group(1))


def load_observed_minutes(*, minutes: int | None, run_summary_path: Path | None) -> int:
    if minutes is not None:
        return minutes
    if run_summary_path is None:
        raise ValueError("either --minutes or --run-summary is required")
    payload = json.loads(run_summary_path.read_text(encoding="utf-8"))
    observed = payload.get("soak_minutes")
    if observed is None:
        raise ValueError("run summary missing soak_minutes")
    return int(observed)


def evaluate_window(max_window_minutes: int, observed_minutes: int) -> dict:
    within_limit = observed_minutes <= max_window_minutes
    return {
        "schema_version": "1.0",
        "max_window_minutes": max_window_minutes,
        "observed_minutes": observed_minutes,
        "within_limit": within_limit,
        "verdict": "PASS" if within_limit else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="governance/p5_canary_readiness.yaml",
        help="Path to p5_canary_readiness policy file",
    )
    parser.add_argument(
        "--minutes",
        type=int,
        help="Observed window in minutes",
    )
    parser.add_argument(
        "--run-summary",
        help="Optional run_summary.json path containing soak_minutes",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path",
    )
    args = parser.parse_args()

    try:
        max_window_minutes = load_max_window_minutes(Path(args.policy))
        observed_minutes = load_observed_minutes(
            minutes=args.minutes,
            run_summary_path=Path(args.run_summary) if args.run_summary else None,
        )
        result = evaluate_window(max_window_minutes, observed_minutes)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    sys.exit(0 if result["within_limit"] else 1)


if __name__ == "__main__":
    main()
