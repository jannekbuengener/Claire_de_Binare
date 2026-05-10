#!/usr/bin/env python3
"""Compare shadow-soak evidence metrics against a versioned baseline threshold file.

Produces shadow_metrics_comparison.json and shadow_metrics_comparison.md in the
evidence directory, then exits:
  0 — PASS (all calibrated thresholds satisfied)
  1 — FAIL, UNCALIBRATED, or error (always writes artefacts before exit)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "1.0"

# Supported threshold specs per metric key
_SPEC_KEYS = ("min", "max", "exact")


def _load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"required file missing: {label} ({path})")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {label}: {exc}") from exc


def _evaluate_check(metric: str, spec: dict, actual: object) -> dict:
    """Evaluate one threshold spec against an actual value.

    Returns a check record with result PASS, FAIL, or SKIP (when spec is all-null).
    actual=None with a calibrated threshold is always FAIL (fail-closed).
    Unknown spec keys with non-null values are always FAIL (typo guard).
    """
    unknown_nonnull = {
        k: v for k, v in spec.items() if k not in _SPEC_KEYS and v is not None
    }
    if unknown_nonnull:
        return {
            "metric": metric,
            "threshold_spec": spec,
            "actual": actual,
            "result": "FAIL",
            "reason": f"invalid threshold spec keys (not in {_SPEC_KEYS}): {sorted(unknown_nonnull)}",
        }

    calibrated = {k: v for k, v in spec.items() if k in _SPEC_KEYS and v is not None}
    if not calibrated:
        return {
            "metric": metric,
            "threshold_spec": spec,
            "actual": actual,
            "result": "SKIP",
        }

    if actual is None:
        return {
            "metric": metric,
            "threshold_spec": spec,
            "actual": None,
            "result": "FAIL",
            "reason": "actual value unavailable; fail-closed on calibrated threshold",
        }

    failures = []
    if "min" in calibrated and actual < calibrated["min"]:
        failures.append(f"actual {actual!r} < min {calibrated['min']!r}")
    if "max" in calibrated and actual > calibrated["max"]:
        failures.append(f"actual {actual!r} > max {calibrated['max']!r}")
    if "exact" in calibrated and actual != calibrated["exact"]:
        failures.append(f"actual {actual!r} != exact {calibrated['exact']!r}")

    result = "FAIL" if failures else "PASS"
    record: dict = {
        "metric": metric,
        "threshold_spec": spec,
        "actual": actual,
        "result": result,
    }
    if failures:
        record["reason"] = "; ".join(failures)
    return record


def _build_md(
    verdict: str,
    checks: list[dict],
    failures: list[str],
    skipped: list[str],
    baseline_provenance: str,
    compared_at: str,
) -> str:
    lines = [
        "# LR-031 Shadow Metrics Comparison",
        "",
        f"**Verdict:** `{verdict}`  ",
        f"**Compared at:** {compared_at}  ",
        f"**Baseline:** {baseline_provenance}",
        "",
    ]
    if verdict == "UNCALIBRATED":
        lines += [
            "> All thresholds are uncalibrated (null). No PASS verdict can be derived.",
            "> Populate `docs/evidence/lr031_baseline_thresholds.json` after the first dry run.",
            "",
        ]
    elif failures:
        lines += [
            f"> **FAIL** — {len(failures)} threshold(s) violated: "
            + ", ".join(f"`{m}`" for m in failures),
            "",
        ]
    else:
        lines += ["> All calibrated thresholds satisfied.", ""]

    if checks:
        lines += [
            "## Check Results",
            "",
            "| Metric | Threshold | Actual | Result |",
            "|--------|-----------|--------|--------|",
        ]
        for c in checks:
            result = c["result"]
            actual = c.get("actual")
            spec = json.dumps(c.get("threshold_spec", {}))
            lines.append(f"| `{c['metric']}` | `{spec}` | `{actual}` | {result} |")
        lines.append("")

    if skipped:
        lines += [
            f"**Skipped (uncalibrated):** {', '.join(f'`{m}`' for m in skipped)}",
            "",
        ]

    return "\n".join(lines)


def compare_shadow_metrics(
    evidence_dir: Path, thresholds_path: Path
) -> tuple[dict, str]:
    """Run comparison and return (report_dict, md_text).

    Always returns a complete report. Raises only for unrecoverable I/O errors
    (caller writes artefacts from the partial report in that case too).
    """
    compared_at = datetime.now(tz=timezone.utc).isoformat()

    thresholds_data = _load_json(thresholds_path, "thresholds")
    baseline_provenance = (
        f"{thresholds_path} / calibration_status="
        f"{thresholds_data.get('calibration_status', 'UNKNOWN')}"
    )
    thresholds: dict = thresholds_data.get("thresholds", {})

    evidence_index = _load_json(
        evidence_dir / "evidence_index.json", "evidence_index.json"
    )

    checks: list[dict] = []
    failures: list[str] = []
    skipped_uncalibrated: list[str] = []

    for metric, spec in thresholds.items():
        actual = evidence_index.get(metric)
        check = _evaluate_check(metric, spec, actual)
        checks.append(check)
        if check["result"] == "FAIL":
            failures.append(metric)
        elif check["result"] == "SKIP":
            skipped_uncalibrated.append(metric)

    # Determine verdict
    calibrated_checks = [c for c in checks if c["result"] != "SKIP"]
    if not calibrated_checks:
        verdict = "UNCALIBRATED"
    elif failures:
        verdict = "FAIL"
    else:
        verdict = "PASS"

    report = {
        "schema_version": SCHEMA_VERSION,
        "baseline_provenance": baseline_provenance,
        "compared_at": compared_at,
        "verdict": verdict,
        "checks": checks,
        "failures": failures,
        "skipped_uncalibrated": skipped_uncalibrated,
    }
    md = _build_md(
        verdict,
        checks,
        failures,
        skipped_uncalibrated,
        baseline_provenance,
        compared_at,
    )
    return report, md


def _write_artefacts(evidence_dir: Path, report: dict, md: str) -> None:
    json_path = evidence_dir / "shadow_metrics_comparison.json"
    md_path = evidence_dir / "shadow_metrics_comparison.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    md_path.write_text(md, encoding="utf-8")


def _error_report(evidence_dir: Path, message: str) -> None:
    """Write minimal error artefacts so the workflow step always has output files."""
    compared_at = datetime.now(tz=timezone.utc).isoformat()
    report = {
        "schema_version": SCHEMA_VERSION,
        "baseline_provenance": "UNKNOWN",
        "compared_at": compared_at,
        "verdict": "FAIL",
        "checks": [],
        "failures": [],
        "skipped_uncalibrated": [],
        "error": message,
    }
    md = f"# LR-031 Shadow Metrics Comparison\n\n**Verdict:** `FAIL`\n\n**Error:** {message}\n"
    try:
        _write_artefacts(evidence_dir, report, md)
    except OSError:
        logging.getLogger(__name__).debug("Failed to write error artefacts (best-effort, ignored)", exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare shadow evidence metrics against baseline thresholds."
    )
    parser.add_argument("evidence_dir", help="Path to evidence directory")
    parser.add_argument(
        "--thresholds", required=True, help="Path to threshold JSON file"
    )
    args = parser.parse_args()

    evidence_dir = Path(args.evidence_dir)
    thresholds_path = Path(args.thresholds)

    if not evidence_dir.is_dir():
        _error_report(
            evidence_dir if evidence_dir.is_dir() else Path("."),
            f"evidence_dir not found: {evidence_dir}",
        )
        print(f"ERROR: evidence_dir not a directory: {evidence_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        report, md = compare_shadow_metrics(evidence_dir, thresholds_path)
    except (FileNotFoundError, ValueError) as exc:
        _error_report(evidence_dir, str(exc))
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Always write artefacts before deciding exit code
    _write_artefacts(evidence_dir, report, md)

    verdict = report["verdict"]
    print(f"--- shadow_metrics_comparison.json ---")
    print(json.dumps(report, indent=2, ensure_ascii=False))

    if verdict == "PASS":
        sys.exit(0)
    else:
        print(f"LR-031 Comparison verdict: {verdict}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
