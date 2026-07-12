"""CLI for ARVP candidate evidence packet assembly (#4016)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from services.validation.arvp_candidate_evidence_assembler import (
    ArvpCandidateEvidenceAssemblerError,
    assemble_arvp_candidate_evidence,
    assemble_from_metrics_bundle_path,
    write_assembly_outputs,
)
from tools.arvp_vacation.strategy_metric_extraction import extract_from_queue_state_path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Assemble profitability_evidence_packet.v1 candidate bundles from "
            "arvp_strategy_metrics.v1 inputs."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--metrics-bundle",
        type=Path,
        help="Path to arvp_strategy_metrics.v1 JSON bundle",
    )
    source.add_argument(
        "--queue-state",
        type=Path,
        help="Path to vacation queue_state.json (extract metrics then assemble)",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root when using --queue-state",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Optional output directory for packets and bundle manifest",
    )
    parser.add_argument(
        "--hash-only",
        action="store_true",
        help="Print only bundle_hash",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.metrics_bundle is not None:
            result = assemble_from_metrics_bundle_path(args.metrics_bundle.resolve())
        else:
            repo_root = Path(args.repo_root).resolve()
            bundle = extract_from_queue_state_path(
                args.queue_state.resolve(),
                repo_root=repo_root,
            )
            result = assemble_arvp_candidate_evidence(bundle)

        if args.hash_only:
            print(result.bundle_hash)
        else:
            print(
                json.dumps(
                    {
                        "bundle_hash": result.bundle_hash,
                        "packet_count": result.packet_count,
                        "source_record_count": result.source_record_count,
                        "candidates": list(result.candidates),
                    },
                    indent=2,
                )
            )

        if args.output_dir is not None:
            write_assembly_outputs(result, output_dir=args.output_dir.resolve())
    except (ArvpCandidateEvidenceAssemblerError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
