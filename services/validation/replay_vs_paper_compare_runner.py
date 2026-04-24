"""CLI runner for ARVP replay-vs-paper comparison (#1902).

Consumes:
  - replay report artifact: replay_report.v1 (report.json)
  - paper reference artifact: arvp_paper_reference_window.v1 (JSON)

Produces:
  - shadow_comparison.json
  - shadow_comparison_summary.md

Exit codes:
  0  comparison aligned (status=aligned)
  1  CLI usage / argument error
  2  input parse error or comparison unusable (status=unusable)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.replay.replay_vs_paper_compare import (
    ComparePaths,
    ReplayVsPaperCompareError,
    compare_from_paths,
    load_json,
    load_replay_output_window,
    write_comparison_bundle,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="replay_vs_paper_compare_runner")
    p.add_argument(
        "--replay-report",
        required=True,
        help="Path to replay report.json (schema replay_report.v1).",
    )
    p.add_argument(
        "--paper-reference",
        required=True,
        help="Path to paper_reference_window JSON (contract_version arvp_paper_reference_window.v1).",
    )
    p.add_argument(
        "--output-dir",
        default="artifacts/replay_vs_paper_compare",
        help="Root directory for comparison artifacts (default: artifacts/replay_vs_paper_compare).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    replay_path = Path(args.replay_report)
    paper_path = Path(args.paper_reference)
    output_root = Path(args.output_dir)

    try:
        # Determine replay_run_id early so outputs land under a stable folder.
        replay_dict = load_json(replay_path)
        replay_window = load_replay_output_window(replay_dict)

        paths = ComparePaths(
            replay_report_json=replay_path,
            paper_reference_json=paper_path,
        )
        result = compare_from_paths(paths)

        out_dir = output_root / replay_window.run_id
        write_comparison_bundle(result=result, output_dir=out_dir)
    except ReplayVsPaperCompareError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if result.status != "aligned":
        # Unusable comparisons are explicit artifacts, but still fail-closed at the CLI layer.
        print(f"ERROR: comparison unusable: {result.alignment_issue}", file=sys.stderr)
        return 2

    print(f"OK: shadow comparison aligned (fingerprint={result.comparison_fingerprint})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

