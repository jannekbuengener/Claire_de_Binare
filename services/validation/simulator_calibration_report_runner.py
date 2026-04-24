"""CLI runner for simulator calibration report (#1903).

Consumes:
  - shadow_comparison.json (from replay-vs-paper compare, #1902)

Produces (under output_dir/<replay_run_id>/):
  - simulator_calibration_report.json
  - simulator_calibration_summary.md

Exit codes:
  0  report built from aligned comparison
  1  CLI usage / argument error
  2  input parse error or unusable comparison input (fail-closed)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.replay.simulator_calibration_report import (
    SimulatorCalibrationError,
    build_simulator_calibration_report,
    load_json,
    load_shadow_comparison_artifact,
    write_calibration_bundle,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="simulator_calibration_report_runner")
    p.add_argument(
        "--comparison",
        required=True,
        help="Path to shadow_comparison.json (from replay-vs-paper compare).",
    )
    p.add_argument(
        "--output-dir",
        default="artifacts/simulator_calibration",
        help="Root directory for calibration artifacts (default: artifacts/simulator_calibration).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    comparison_path = Path(args.comparison)
    output_root = Path(args.output_dir)

    try:
        payload = load_json(comparison_path)
        comparison = load_shadow_comparison_artifact(payload)
        report = build_simulator_calibration_report(comparison)

        out_dir = output_root / report.replay_run_id
        write_calibration_bundle(report=report, output_dir=out_dir)
    except SimulatorCalibrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if report.status != "aligned":
        print("ERROR: unusable comparison input; calibration report is unusable", file=sys.stderr)
        return 2

    print(f"OK: calibration report built (fingerprint={report.calibration_fingerprint})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

