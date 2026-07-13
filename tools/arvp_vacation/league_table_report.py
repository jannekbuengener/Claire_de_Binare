"""CLI for governance-safe Strategy League table reports (#4017)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from services.validation.profitability_league_table_report_assembler import (
    ProfitabilityLeagueTableReportAssemblerError,
    assemble_from_candidate_bundle_dir,
    assemble_from_pep_paths,
    build_governance_league_table_report,
    write_report_output,
)
from services.validation.arvp_candidate_evidence_assembler import (
    assemble_arvp_candidate_evidence,
    assemble_from_metrics_bundle_path,
)
from tools.arvp_vacation.strategy_metric_extraction import extract_from_queue_state_path


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build governance-safe profitability_league_table_report.v1 from "
            "profitability_evidence_packet.v1 candidate bundles."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--bundle-dir",
        type=Path,
        help="Directory with bundle_manifest.json and *.pep.json files",
    )
    source.add_argument(
        "--pep",
        action="append",
        type=Path,
        dest="peps",
        help="Path to a PEP JSON file (repeatable; requires provenance flags)",
    )
    source.add_argument(
        "--assemble-from-metrics",
        type=Path,
        help="Assemble PEPs from arvp_strategy_metrics.v1 bundle then score",
    )
    source.add_argument(
        "--assemble-from-queue-state",
        type=Path,
        help="Extract metrics from queue_state.json, assemble PEPs, then score",
    )
    parser.add_argument("--repo-root", default=".", help="Repo root for queue-state path")
    parser.add_argument("--campaign-id", help="Required with --pep")
    parser.add_argument("--evidence-class", default="historical_cross_venue_research")
    parser.add_argument("--source-content-hash", help="Required with --pep")
    parser.add_argument("--candidate-bundle-hash", help="Required with --pep")
    parser.add_argument("--report-id", default=None)
    parser.add_argument(
        "--out-json",
        type=Path,
        help="Output path for league table report JSON",
    )
    parser.add_argument(
        "--hash-only",
        action="store_true",
        help="Print report_content_hash only",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip schema validation",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    validate = not args.no_validate

    try:
        if args.bundle_dir is not None:
            result = assemble_from_candidate_bundle_dir(
                args.bundle_dir.resolve(),
                validate=validate,
            )
        elif args.assemble_from_metrics is not None:
            assembly = assemble_from_metrics_bundle_path(
                args.assemble_from_metrics.resolve()
            )
            first = assembly.packets[0]
            result = build_governance_league_table_report(
                assembly.packets,
                campaign_id=str(first.get("campaign_id") or ""),
                evidence_class=str(first.get("evidence_class") or ""),
                source_content_hash=str(first.get("source_content_hash") or ""),
                candidate_bundle_hash=assembly.bundle_hash,
                validate=validate,
            )
        elif args.assemble_from_queue_state is not None:
            repo_root = Path(args.repo_root).resolve()
            bundle = extract_from_queue_state_path(
                args.assemble_from_queue_state.resolve(),
                repo_root=repo_root,
            )
            assembly = assemble_arvp_candidate_evidence(bundle)
            first = assembly.packets[0]
            result = build_governance_league_table_report(
                assembly.packets,
                campaign_id=str(first.get("campaign_id") or ""),
                evidence_class=str(first.get("evidence_class") or ""),
                source_content_hash=str(first.get("source_content_hash") or ""),
                candidate_bundle_hash=assembly.bundle_hash,
                validate=validate,
            )
        else:
            if not args.peps:
                raise ProfitabilityLeagueTableReportAssemblerError("--pep is required")
            for field_name, value in (
                ("campaign_id", args.campaign_id),
                ("source_content_hash", args.source_content_hash),
                ("candidate_bundle_hash", args.candidate_bundle_hash),
            ):
                if not value:
                    raise ProfitabilityLeagueTableReportAssemblerError(
                        f"{field_name} is required with --pep"
                    )
            result = assemble_from_pep_paths(
                [path.resolve() for path in args.peps],
                campaign_id=str(args.campaign_id),
                evidence_class=str(args.evidence_class),
                source_content_hash=str(args.source_content_hash),
                candidate_bundle_hash=str(args.candidate_bundle_hash),
                validate=validate,
            )

        if args.report_id:
            result.report["report_id"] = args.report_id
            from services.validation.profitability_league_table_report_assembler import (
                _report_content_hash,
            )

            result.report["report_content_hash"] = _report_content_hash(result.report)

        if args.hash_only:
            print(result.report_content_hash)
        elif args.out_json is not None:
            write_report_output(result, output_path=args.out_json.resolve())
            print(
                json.dumps(
                    {
                        "report_id": result.report["report_id"],
                        "table_status": result.report["table_status"],
                        "officially_ranked_count": result.report.get(
                            "officially_ranked_count"
                        ),
                        "report_content_hash": result.report_content_hash,
                    },
                    indent=2,
                )
            )
        else:
            print(json.dumps(result.report, indent=2, sort_keys=True))
    except (
        ProfitabilityLeagueTableReportAssemblerError,
        ValueError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
