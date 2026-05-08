"""Quality Scoring CLI — read-only, no writes, no DB, no network.

Issues:
    #2172 — [SURREALDB][CONTEXT][QUALITY-CLI] Add quality scoring CLI
    Parent: #2170 (Wave-18 anchor)
    Depends on: #2171 (quality_scoring service)
    Epic: #1976

Commands:
    score-knowledge     Score a bundle, output all quality dimensions
    show-score          Show score details for a specific dimension
    report-quality      Generate a structured quality summary report

Exit codes:
    0 = success (or weak/blocking findings without --fail-on-weak)
    1 = blocking, watch, or weak-grade overall and --fail-on-weak set
    2 = CLI / input / validation error
    3 = show-score: dimension not found

Guardrails:
    - Read-only. No writes. No file output. Stdout only.
    - No DB access. No SurrealDB SDK. No network. No GitHub calls.
    - Score is signal, not authorization.
    - LR status remains NO-GO for live trading.
    - No auto-fix. No live-go. No Echtgeld-Go.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.surrealdb.quality_scoring import (
    GUARDRAILS,
    SCORE_DIMENSIONS,
    QualityScoringError,
    QualityScoreResult,
    score_knowledge_quality_v1,
)

SCHEMA_VERSION = "quality-scoring-cli/v1"

EXIT_OK = 0
EXIT_WEAK = 1
EXIT_ERROR = 2
EXIT_NOT_FOUND = 3

SUPPORTED_FORMATS = frozenset({"json", "markdown"})


class QualityScoringCLIError(Exception):
    """Raised for CLI / input / validation errors (exit 2) or not-found (exit 3)."""

    def __init__(self, message: str, exit_code: int = EXIT_ERROR) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def _load_bundle(path: Path) -> dict[str, Any]:
    """Load a JSON input bundle from *path*."""
    if not path.exists():
        raise QualityScoringCLIError(
            f"bundle not found: {path}", exit_code=EXIT_NOT_FOUND
        )
    if not path.is_file():
        raise QualityScoringCLIError(
            f"bundle path is not a file: {path}", exit_code=EXIT_ERROR
        )
    try:
        raw = path.read_text(encoding="utf-8")
        bundle = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QualityScoringCLIError(
            f"invalid JSON in bundle: {path}: {exc}", exit_code=EXIT_ERROR
        ) from exc
    except OSError as exc:
        raise QualityScoringCLIError(
            f"cannot read bundle: {path}: {exc}", exit_code=EXIT_ERROR
        ) from exc
    if not isinstance(bundle, dict):
        raise QualityScoringCLIError(
            "bundle root must be a JSON object", exit_code=EXIT_ERROR
        )
    return bundle


def _render_score_result_json(result: QualityScoreResult) -> str:
    return json.dumps(result.to_dict(), indent=2, sort_keys=True, ensure_ascii=True)


def _render_score_result_markdown(result: QualityScoreResult) -> str:
    lines = [
        "# Knowledge Quality Score Report",
        f"- **scope_id**: `{result.scope_id}`",
        f"- **level**: `{result.level}`",
        f"- **scored_at**: `{result.scored_at}`",
        f"- **overall_score**: `{result.overall_score:.4f}`",
        f"- **overall_grade**: `{result.overall_grade}`",
    ]
    if result.blocking_dimensions:
        lines.append(
            "- **blocking_dimensions**: "
            + ", ".join(f"`{d}`" for d in result.blocking_dimensions)
        )
    if result.watch_dimensions:
        lines.append(
            "- **watch_dimensions**: "
            + ", ".join(f"`{d}`" for d in result.watch_dimensions)
        )
    lines.append("")
    lines.append("## Dimensions")
    lines.append("")
    lines.append("| Dimension | Score | Grade | Inputs |")
    lines.append("|-----------|-------|-------|--------|")
    for dim in result.dimensions:
        lines.append(
            f"| `{dim.dimension}` | `{dim.score:.4f}` | `{dim.grade}` | {dim.inputs_used} |"
        )
    lines.append("")
    lines.append("## Guardrails")
    for g in result.guardrails:
        lines.append(f"- {g}")
    return "\n".join(lines)


def _render_dimension_json(result: QualityScoreResult, dimension: str) -> str:
    for dim in result.dimensions:
        if dim.dimension == dimension:
            payload = {
                "schema_version": SCHEMA_VERSION,
                "scope_id": result.scope_id,
                "scored_at": result.scored_at,
                "dimension": dim.to_dict(),
                "guardrails": list(GUARDRAILS),
            }
            return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
    raise QualityScoringCLIError(
        f"dimension not found: {dimension}", exit_code=EXIT_NOT_FOUND
    )


def _render_dimension_markdown(result: QualityScoreResult, dimension: str) -> str:
    for dim in result.dimensions:
        if dim.dimension == dimension:
            lines = [
                f"# Quality Score: {dimension}",
                f"- **scope_id**: `{result.scope_id}`",
                f"- **score**: `{dim.score:.4f}`",
                f"- **grade**: `{dim.grade}`",
                f"- **inputs_used**: `{dim.inputs_used}`",
                f"- **explanation**: {dim.explanation}",
            ]
            if dim.warnings:
                lines.append("**warnings**:")
                for w in dim.warnings:
                    lines.append(f"  - {w}")
            return "\n".join(lines)
    raise QualityScoringCLIError(
        f"dimension not found: {dimension}", exit_code=EXIT_NOT_FOUND
    )


def _render_report_json(result: QualityScoreResult, fail_on_weak: bool) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "scope_id": result.scope_id,
        "level": result.level,
        "scored_at": result.scored_at,
        "overall_score": result.overall_score,
        "overall_grade": result.overall_grade,
        "blocking_dimensions": list(result.blocking_dimensions),
        "watch_dimensions": list(result.watch_dimensions),
        "recommended_next_reads": list(result.recommended_next_reads),
        "guardrails": list(result.guardrails),
        "summary": {
            "total_dimensions": len(result.dimensions),
            "blocking_count": len(result.blocking_dimensions),
            "watch_count": len(result.watch_dimensions),
            "fail_on_weak_active": fail_on_weak,
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)


def _render_report_markdown(result: QualityScoreResult) -> str:
    lines = [
        "# Quality Score Report",
        f"- **scope**: `{result.scope_id}`",
        f"- **level**: `{result.level}`",
        f"- **overall_score**: `{result.overall_score:.4f}` — **{result.overall_grade.upper()}**",
        "",
        "## Summary",
        f"- Blocking dimensions: {len(result.blocking_dimensions)}",
        f"- Watch dimensions: {len(result.watch_dimensions)}",
    ]
    if result.blocking_dimensions:
        lines.append("- **Blocking**: " + ", ".join(result.blocking_dimensions))
    lines.append("")
    lines.append("## Guardrails")
    for g in result.guardrails:
        lines.append(f"- {g}")
    return "\n".join(lines)


# ── Command handlers ──────────────────────────────────────────────────────────


def handle_score_knowledge(
    args: argparse.Namespace,
) -> tuple[str, int]:
    bundle = _load_bundle(args.input)
    try:
        result = score_knowledge_quality_v1(bundle)
    except QualityScoringError as exc:
        raise QualityScoringCLIError(str(exc), exit_code=EXIT_ERROR) from exc

    fmt = getattr(args, "format", "json")
    if fmt == "json":
        output = _render_score_result_json(result)
    elif fmt == "markdown":
        output = _render_score_result_markdown(result)
    else:
        raise QualityScoringCLIError(f"unsupported format: {fmt}", exit_code=EXIT_ERROR)

    fail_on_weak = getattr(args, "fail_on_weak", False)
    exit_code = EXIT_OK
    if fail_on_weak and result.overall_grade in ("blocking", "watch", "weak"):
        exit_code = EXIT_WEAK
    return output, exit_code


def handle_show_score(
    args: argparse.Namespace,
) -> tuple[str, int]:
    bundle = _load_bundle(args.input)
    try:
        result = score_knowledge_quality_v1(bundle)
    except QualityScoringError as exc:
        raise QualityScoringCLIError(str(exc), exit_code=EXIT_ERROR) from exc

    dimension = args.dimension
    if dimension not in SCORE_DIMENSIONS:
        raise QualityScoringCLIError(
            f"unknown dimension: {dimension!r}. "
            f"Valid: {', '.join(sorted(SCORE_DIMENSIONS))}",
            exit_code=EXIT_NOT_FOUND,
        )

    fmt = getattr(args, "format", "json")
    if fmt == "json":
        output = _render_dimension_json(result, dimension)
    elif fmt == "markdown":
        output = _render_dimension_markdown(result, dimension)
    else:
        raise QualityScoringCLIError(f"unsupported format: {fmt}", exit_code=EXIT_ERROR)
    return output, EXIT_OK


def handle_report_quality(
    args: argparse.Namespace,
) -> tuple[str, int]:
    bundle = _load_bundle(args.input)
    try:
        result = score_knowledge_quality_v1(bundle)
    except QualityScoringError as exc:
        raise QualityScoringCLIError(str(exc), exit_code=EXIT_ERROR) from exc

    fmt = getattr(args, "format", "json")
    fail_on_weak = getattr(args, "fail_on_weak", False)
    if fmt == "json":
        output = _render_report_json(result, fail_on_weak)
    elif fmt == "markdown":
        output = _render_report_markdown(result)
    else:
        raise QualityScoringCLIError(f"unsupported format: {fmt}", exit_code=EXIT_ERROR)

    exit_code = EXIT_OK
    if fail_on_weak and result.overall_grade in ("blocking", "watch", "weak"):
        exit_code = EXIT_WEAK
    return output, exit_code


# ── Argparse ──────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quality_scoring_cli",
        description=(
            "Knowledge Quality Scoring CLI (#2172). "
            "Read-only — no DB, no network, no writes."
        ),
    )
    parser.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default="json",
        help="Output format (default: json).",
    )

    subs = parser.add_subparsers(dest="command", required=True)

    score = subs.add_parser(
        "score-knowledge",
        help="Score a quality bundle and output all dimension scores.",
    )
    score.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to JSON input bundle.",
    )
    score.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default=argparse.SUPPRESS,
        help="Output format (default: json). Overrides global --format when specified.",
    )
    score.add_argument(
        "--fail-on-weak",

        action="store_true",
        default=False,
        help="Exit 1 if overall grade is blocking, watch, or weak.",
    )

    show = subs.add_parser(
        "show-score",
        help="Show score details for a specific dimension.",
    )
    show.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to JSON input bundle.",
    )
    show.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default=argparse.SUPPRESS,
        help="Output format (default: json). Overrides global --format when specified.",
    )
    show.add_argument(
        "--dimension",
        required=True,
        choices=sorted(SCORE_DIMENSIONS),
        help="Dimension to show.",
    )

    report = subs.add_parser(
        "report-quality",
        help="Generate a structured quality summary report.",
    )
    report.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to JSON input bundle.",
    )
    report.add_argument(
        "--format",
        choices=sorted(SUPPORTED_FORMATS),
        default=argparse.SUPPRESS,
        help="Output format (default: json). Overrides global --format when specified.",
    )
    report.add_argument(
        "--fail-on-weak",

        action="store_true",
        default=False,
        help="Exit 1 if overall grade is blocking, watch, or weak.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "score-knowledge":
            output, exit_code = handle_score_knowledge(args)
        elif args.command == "show-score":
            output, exit_code = handle_show_score(args)
        elif args.command == "report-quality":
            output, exit_code = handle_report_quality(args)
        else:
            print(
                json.dumps(
                    {"error": "unknown_command", "command": args.command},
                    ensure_ascii=True,
                )
            )
            return EXIT_ERROR
    except QualityScoringCLIError as exc:
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "error": exc.message,
                    "guardrails": list(GUARDRAILS),
                },
                ensure_ascii=True,
                indent=2,
            )
        )
        return exc.exit_code

    print(output)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
