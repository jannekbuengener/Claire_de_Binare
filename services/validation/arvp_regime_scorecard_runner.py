"""CLI runner for ARVP regime scorecards (#1904).

Consumes (optional inputs; fail-closed on invalid JSON, explicit on missing regime data):
  - replay trace JSON (runner-supplied): --replay-trace
  - comparison JSON (optional):         --comparison

Evidence class: configurable via --evidence-class (default: controlled_lab_evidence).

Produces (under output_dir/<run_id>/):
  - arvp_regime_scorecard.json
  - arvp_regime_scorecard_summary.md

Exit codes:
  0  scorecard built (status may be ok/unavailable/insufficient-data; still a valid artifact)
  1  CLI usage / argument error
  2  input parse error / invalid shape
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.replay.arvp_regime_scorecards import (
    ARVPRegimeScorecardError,
    build_comparison_regime_scorecard_or_unavailable,
    build_replay_regime_scorecard_from_trace,
    load_json,
    write_regime_scorecard_bundle,
)
from core.utils.clock import utcnow
from core.utils.evidence_class import (
    EvidenceClassError,
    evidence_class_warning_banner,
    validate_evidence_class,
)

_DEFAULT_EVIDENCE_CLASS = "controlled_lab_evidence"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="arvp_regime_scorecard_runner")
    p.add_argument("--run-id", required=True, help="Logical run id for output folder naming.")
    p.add_argument("--replay-trace", help="Path to replay trace JSON (for replay-side scorecard).")
    p.add_argument("--comparison", help="Path to comparison JSON (optional; supports regime_segments).")
    p.add_argument(
        "--output-dir",
        default="artifacts/arvp_regime_scorecards",
        help="Root directory for scorecard artifacts (default: artifacts/arvp_regime_scorecards).",
    )
    p.add_argument(
        "--evidence-class",
        default=_DEFAULT_EVIDENCE_CLASS,
        choices=["controlled_lab_evidence"],
        help=f"Evidence classification for the output artifact (default: {_DEFAULT_EVIDENCE_CLASS}).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parse_args(argv)
    except SystemExit:
        return 1

    evidence_class = str(args.evidence_class)
    warning_banner = evidence_class_warning_banner(evidence_class)
    now_utc = utcnow().isoformat()

    run_id = str(args.run_id)
    output_root = Path(args.output_dir)
    try:
        scorecards = []
        if args.replay_trace:
            trace_payload = load_json(Path(args.replay_trace))
            scorecards.append(build_replay_regime_scorecard_from_trace(trace_payload))
        if args.comparison:
            comparison_payload = load_json(Path(args.comparison))
            scorecards.append(
                build_comparison_regime_scorecard_or_unavailable(comparison_payload, run_id=run_id)
            )

        if not scorecards:
            raise ARVPRegimeScorecardError("At least one of --replay-trace or --comparison is required")

        # If both are provided, prefer replay-side scorecard as primary output.
        scorecard = scorecards[0]

        metadata: dict[str, str] = {
            "evidence_class": evidence_class,
            "evidence_class_version": "1.0",
            "produced_by": "arvp_regime_scorecard_runner",
            "produced_at_utc": now_utc,
            "scenario_source": args.replay_trace or args.comparison or "unknown",
            "reproducibility_contract": scorecard.scorecard_fingerprint,
        }
        if warning_banner:
            metadata["warning_banner"] = warning_banner

        try:
            validate_evidence_class(metadata)
        except EvidenceClassError as exc:
            print(f"EVIDENCE CLASS VALIDATION FAILED: {exc}", file=sys.stderr)
            return 2

        out_dir = output_root / run_id
        write_regime_scorecard_bundle(
            scorecard=scorecard, output_dir=out_dir, bundle_metadata=metadata
        )
    except ARVPRegimeScorecardError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(
        f"OK: regime scorecard built "
        f"(status={scorecard.status}, fingerprint={scorecard.scorecard_fingerprint}, "
        f"evidence_class={evidence_class})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

