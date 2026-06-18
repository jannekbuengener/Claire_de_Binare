"""Local append-only CDB Brain Apply.

Applies a validated Context Package to a local, audited ledger artifact.
Default mode: dry-run/report-only. Explicit --apply triggers actual append writes.

Usage:
    python tools/context/apply_context_brain_local.py \\
        --package <path> [--drift-radar <path>] [--output-dir <dir>]
    python tools/context/apply_context_brain_local.py \\
        --package <path> --apply [--output-dir <dir>]
    python tools/context/apply_context_brain_local.py --help

Exit codes:
    0 - OK (dry-run passed, or apply succeeded with no errors)
    1 - BLOCKED (precondition failure, risk detected, or apply blocked)
    2 - FAIL (unexpected error)

No network. No DB. No MCP mutation. No productive SurrealDB writes.
LR remains NO-GO. #3289
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from core.utils.clock import utcnow as cdb_utcnow

SCHEMA_VERSION = "brain_apply.v1"
LEDGER_FILENAME = "brain_apply_ledger.json"
APPLY_RUNS_FILENAME = "brain_apply_runs.json"
BRAIN_LEDGER_DIR = "_brain_ledger"

SUPPORTED_PACKAGE_VERSIONS: set[str] = {"1.0"}

SECRET_PATTERNS: list[str] = [
    "api_key",
    "api_secret",
    "REDIS_PASSWORD",
    "POSTGRES_PASSWORD",
    "MEXC_API_KEY",
    "MEXC_API_SECRET",
    "SECRETS_PATH",
    "SMTP_PASSWORD",
    "GRAFANA_PASSWORD",
]

FORBIDDEN_TAGS: list[str] = [
    "live-trade",
    "echtgeld",
    "real-money",
    "production-trade",
    "order",
    "fill",
    "position",
]


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_package_fingerprint(package: dict[str, Any]) -> str:
    pkg = package.get("package", {})
    record_ids = sorted(r.get("record_id", "") for r in pkg.get("records", []))
    material = f"{pkg.get('package_id', '')}|{pkg.get('source_commit', '')}|{','.join(record_ids)}"
    return "sha256:" + _sha256_hex(material)


def compute_content_hash(record: dict[str, Any]) -> str:
    relevant = {
        "record_id": record.get("record_id", ""),
        "record_type": record.get("record_type", ""),
        "source_path": record.get("source_path", ""),
        "source_commit": record.get("source_commit", ""),
        "source_hash": record.get("source_hash", ""),
        "confidence": record.get("confidence", ""),
    }
    return "sha256:" + _sha256_hex(json.dumps(relevant, sort_keys=True))


def read_json(path: str | Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _check_secret_content(package: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        summary = record.get("summary", "")
        source_path = record.get("source_path", "")
        content = summary + " " + source_path
        for pattern in SECRET_PATTERNS:
            if pattern.lower() in content.lower():
                findings.append(
                    f"$.package.records[{i}]: secret indicator '{pattern}' detected"
                )
                break
    return findings


def _check_forbidden_tags(package: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        tags = record.get("tags", [])
        for tag in tags:
            if tag.lower() in FORBIDDEN_TAGS:
                findings.append(f"$.package.records[{i}]: forbidden tag '{tag}'")
                break
    return findings


def validate_package_for_apply(package: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []

    if not isinstance(package, dict):
        return {
            "valid": False,
            "errors": [
                {
                    "path": "$",
                    "code": "not_an_object",
                    "message": "Package is not a JSON object",
                }
            ],
        }

    meta = package.get("meta", {})
    pkg = package.get("package", {})

    meta_version = meta.get("version", "")
    if meta_version not in SUPPORTED_PACKAGE_VERSIONS:
        errors.append(
            {
                "path": "$.meta.version",
                "code": "unsupported_schema_version",
                "message": f"Unsupported meta version '{meta_version}'. Supported: {sorted(SUPPORTED_PACKAGE_VERSIONS)}",
            }
        )

    package_id = pkg.get("package_id", "")
    if not package_id:
        errors.append(
            {
                "path": "$.package.package_id",
                "code": "missing_package_id",
                "message": "Package ID is required",
            }
        )

    source_commit = pkg.get("source_commit", "")
    if not source_commit:
        errors.append(
            {
                "path": "$.package.source_commit",
                "code": "missing_source_commit",
                "message": "Source commit is required",
            }
        )

    records = pkg.get("records", [])
    if not isinstance(records, list):
        errors.append(
            {
                "path": "$.package.records",
                "code": "records_not_array",
                "message": "Records must be an array",
            }
        )

    secret_findings = _check_secret_content(package)
    for f in secret_findings:
        errors.append(
            {
                "path": f,
                "code": "secret_content",
                "message": "Secret indicator detected. BLOCKED.",
            }
        )

    tag_findings = _check_forbidden_tags(package)
    for f in tag_findings:
        errors.append(
            {
                "path": f,
                "code": "forbidden_tag",
                "message": "Forbidden tag detected. BLOCKED.",
            }
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def load_drift_radar(radar_path: str | Path) -> dict[str, Any]:
    data = read_json(radar_path)
    radar_schema = data.get("schema_version", "")
    if "impact_radar" in radar_schema or "stale_claims" in radar_schema:
        return data
    if "safety_boundaries" in data or "brain_apply_blocked" in data:
        return data
    return data


def check_drift_radar_blocks(radar: dict[str, Any]) -> list[str]:
    blocks: list[str] = []

    brain_blocked = radar.get("brain_apply_blocked")
    if brain_blocked is True:
        blocks.append("Drift radar reports brain_apply_blocked=true")

    summary = radar.get("summary", {})
    if isinstance(summary, dict) and summary.get("blocks_brain_apply") is True:
        blocks.append(
            f"Drift radar summary blocks brain apply ({summary.get('blocking_claims', '?')} blocking claims)"
        )

    safety = radar.get("safety_boundaries", {})
    if safety.get("brain_apply_blocked") is True:
        blocks.append("Drift radar safety boundaries block brain apply")

    blockers = radar.get("brain_apply_blockers", [])
    for b in blockers:
        blocks.append(f"Blocker: {b.get('claim', 'unknown')}")

    by_category = radar.get("by_category", {})
    for cat, claims in by_category.items():
        for c in claims:
            if c.get("blocks_brain_apply"):
                blocks.append(f"[{cat}] {c.get('claim', 'unknown claim')}")

    return blocks


def load_ledger(output_dir: Path) -> list[dict[str, Any]]:
    ledger_path = output_dir / BRAIN_LEDGER_DIR / LEDGER_FILENAME
    if not ledger_path.exists():
        return []
    with open(ledger_path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def save_ledger(output_dir: Path, ledger: list[dict[str, Any]]) -> None:
    ledger_dir = output_dir / BRAIN_LEDGER_DIR
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / LEDGER_FILENAME
    ledger_path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def is_duplicate_fingerprint(
    ledger: list[dict[str, Any]], fingerprint: str
) -> dict[str, Any] | None:
    for run in ledger:
        if run.get("source_package_fingerprint") == fingerprint:
            return run
    return None


def build_apply_run(
    package: dict[str, Any],
    fingerprint: str,
    source_path: str,
    utc_now: str,
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    records = package.get("package", {}).get("records", [])
    duplicate_run = is_duplicate_fingerprint(ledger, fingerprint)
    is_duplicate = duplicate_run is not None

    seq = len(ledger) + 1
    pkg_id = package.get("package", {}).get("package_id", "unknown")
    run_id = f"brain-apply-{fingerprint[:16]}-{seq:04d}"

    entry_records: list[dict[str, Any]] = []
    applied = 0
    skipped = 0
    blocked = 0

    if is_duplicate:
        skipped = len(records)
        entry_records = []
    else:
        for record in records:
            content_hash = compute_content_hash(record)
            entry_records.append(
                {
                    "entry_id": f"entry-{content_hash[:24]}",
                    "package_record_id": record.get("record_id", ""),
                    "content_hash": content_hash,
                    "record_type": record.get("record_type", ""),
                    "source_path": record.get("source_path", ""),
                    "summary": record.get("summary", ""),
                }
            )
            applied += 1

    return {
        "apply_run_id": run_id,
        "source_package_fingerprint": fingerprint,
        "schema_version": SCHEMA_VERSION,
        "package_id": pkg_id,
        "source_path": os.path.abspath(source_path),
        "generated_at_utc": utc_now,
        "duplicate_fingerprint": is_duplicate,
        "duplicate_of_run_id": duplicate_run["apply_run_id"] if duplicate_run else None,
        "status": "skipped_duplicate" if is_duplicate else "applied",
        "summary": {
            "total_records_in_package": len(records),
            "records_applied": 0 if is_duplicate else applied,
            "records_skipped": skipped,
            "records_blocked": blocked,
        },
        "records": entry_records,
    }


def format_dry_run_report(
    package: dict[str, Any],
    fingerprint: str,
    validation_result: dict[str, Any],
    drift_blockers: list[str],
    secret_findings: list[str],
    tag_findings: list[str],
    ledger: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    pkg = package.get("package", {})
    pkg_id = pkg.get("package_id", "unknown")
    records = pkg.get("records", [])
    duplicate_run = is_duplicate_fingerprint(ledger, fingerprint)

    lines.append("=== Local Brain Apply — Dry Run ===")
    lines.append("")
    lines.append(f"Package:       {pkg_id}")
    lines.append(f"Package ID:    {pkg_id}")
    lines.append(f"Source commit: {pkg.get('source_commit', 'unknown')[:12]}")
    lines.append(f"Records:       {len(records)}")
    lines.append(f"Fingerprint:   {fingerprint}")
    lines.append(f"Schema:        {SCHEMA_VERSION}")
    lines.append("")

    if not validation_result["valid"]:
        lines.append(
            f"[BLOCKED] Package preconditions FAILED ({len(validation_result['errors'])} errors):"
        )
        for err in validation_result["errors"]:
            lines.append(f"  [{err['code']}] {err['message']}")
        lines.append("")
        lines.append("Verdict: BLOCKED — preconditions not met. Apply prevented.")
        return "\n".join(lines)

    if drift_blockers:
        lines.append(
            f"[BLOCKED] Drift radar prevents brain apply ({len(drift_blockers)} blocker(s)):"
        )
        for b in drift_blockers:
            lines.append(f"  {b}")
        lines.append("")
        lines.append("Verdict: BLOCKED — drift radar risk. Apply prevented.")
        return "\n".join(lines)

    if secret_findings:
        lines.append(
            f"[BLOCKED] Secret indicators detected ({len(secret_findings)} finding(s)):"
        )
        for f in secret_findings:
            lines.append(f"  {f}")
        lines.append("")
        lines.append("Verdict: BLOCKED — secret risk. Apply prevented.")
        return "\n".join(lines)

    if tag_findings:
        lines.append(
            f"[BLOCKED] Forbidden tags detected ({len(tag_findings)} finding(s)):"
        )
        for f in tag_findings:
            lines.append(f"  {f}")
        lines.append("")
        lines.append("Verdict: BLOCKED — forbidden content. Apply prevented.")
        return "\n".join(lines)

    if duplicate_run:
        lines.append(
            f"[SKIPPED] Package fingerprint already applied (run: {duplicate_run['apply_run_id']})"
        )
        lines.append(f"  Duplicate of run ID: {duplicate_run['apply_run_id']}")
        lines.append(
            f"  Applied at:          {duplicate_run.get('generated_at_utc', 'unknown')}"
        )
        lines.append("")
        lines.append("Verdict: SKIPPED — idempotent duplicate. No new records.")
        return "\n".join(lines)

    lines.append("[PASS] All preconditions met. Apply ready.")
    lines.append("")
    lines.append("Apply summary:")
    lines.append(f"  Records in package:     {len(records)}")
    lines.append(f"  Records to apply:       {len(records)}")
    lines.append(f"  Records skipped:        0")
    lines.append(f"  Records blocked:        0")
    lines.append(f"  Ledger entries (total): {len(ledger)}")
    lines.append("")
    lines.append("Verdict: READY — run with --apply to append to local ledger.")
    lines.append("")
    lines.append("No DB writes. No network. No MCP mutation. LR remains NO-GO.")

    return "\n".join(lines)


def format_apply_report(
    apply_run: dict[str, Any],
    ledger: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    summary = apply_run["summary"]

    lines.append("=== Local Brain Apply — Apply Report ===")
    lines.append("")
    lines.append(f"Apply run ID:  {apply_run['apply_run_id']}")
    lines.append(f"Package ID:    {apply_run['package_id']}")
    lines.append(f"Fingerprint:   {apply_run['source_package_fingerprint']}")
    lines.append(f"Status:        {apply_run['status']}")
    lines.append(f"Ledger path:   {BRAIN_LEDGER_DIR}/{LEDGER_FILENAME}")
    lines.append("")

    if apply_run["duplicate_fingerprint"]:
        lines.append(f"[SKIPPED] Duplicate fingerprint — no records appended.")
        lines.append(f"  Duplicate of run: {apply_run['duplicate_of_run_id']}")
    else:
        lines.append("[APPLIED] Records appended to local ledger:")
        lines.append(f"  Records applied:   {summary['records_applied']}")
        lines.append(f"  Records skipped:   {summary['records_skipped']}")
        lines.append(f"  Records blocked:   {summary['records_blocked']}")
        lines.append(f"  Ledger total runs: {len(ledger)}")

    lines.append("")
    lines.append("No DB writes. No network. No MCP mutation. LR remains NO-GO.")

    return "\n".join(lines)


def format_blocked_report(
    validation: dict[str, Any],
    drift_blockers: list[str],
    secret_findings: list[str],
    tag_findings: list[str],
) -> str:
    lines: list[str] = []
    lines.append("=== Local Brain Apply — BLOCKED ===")
    lines.append("")

    if not validation["valid"]:
        for err in validation["errors"]:
            lines.append(f"  [{err['code']}] {err['message']}")
        lines.append("")

    for b in drift_blockers:
        lines.append(f"  [DRIFT] {b}")
    for f in secret_findings:
        lines.append(f"  [SECRET] {f}")
    for f in tag_findings:
        lines.append(f"  [TAG] {f}")

    lines.append("")
    lines.append("Verdict: BLOCKED — preconditions prevent brain apply.")
    lines.append("No DB writes. No network. No MCP mutation. LR remains NO-GO.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Local append-only CDB Brain Apply (#3289)",
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Path to a validated context package JSON file.",
    )
    parser.add_argument(
        "--drift-radar",
        default=None,
        help="Optional path to impact_radar.json or stale_claims.json from drift radar (#3291).",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Output directory for local brain ledger (default: current dir).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write append-only records to local ledger. Default is dry-run/report-only.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress agent-readable output.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="emit_json",
        help="Output machine-readable JSON report.",
    )
    args = parser.parse_args()

    utc_now = cdb_utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        package = read_json(args.package)
    except FileNotFoundError:
        print(f"[FAIL] Package file not found: {args.package}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"[FAIL] Invalid JSON in package file: {e}", file=sys.stderr)
        return 2

    validation = validate_package_for_apply(package)
    fingerprint = compute_package_fingerprint(package)

    drift_blockers: list[str] = []
    if args.drift_radar:
        try:
            radar = load_drift_radar(args.drift_radar)
            drift_blockers = check_drift_radar_blocks(radar)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[WARN] Could not read drift radar file: {e}", file=sys.stderr)

    secret_findings = _check_secret_content(package)
    tag_findings = _check_forbidden_tags(package)

    blocked = (
        not validation["valid"]
        or bool(drift_blockers)
        or bool(secret_findings)
        or bool(tag_findings)
    )

    ledger = load_ledger(output_dir)

    if not blocked and not args.apply:
        report = format_dry_run_report(
            package=package,
            fingerprint=fingerprint,
            validation_result=validation,
            drift_blockers=drift_blockers,
            secret_findings=secret_findings,
            tag_findings=tag_findings,
            ledger=ledger,
        )
        if args.emit_json:
            result = {
                "mode": "dry_run",
                "blocked": False,
                "fingerprint": fingerprint,
                "package_id": package.get("package", {}).get("package_id", ""),
                "record_count": len(package.get("package", {}).get("records", [])),
                "ledger_run_count": len(ledger),
                "is_duplicate": is_duplicate_fingerprint(ledger, fingerprint)
                is not None,
                "schema_version": SCHEMA_VERSION,
                "generated_at_utc": utc_now,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif not args.quiet:
            print(report)
        return 0

    if blocked:
        report = format_blocked_report(
            validation, drift_blockers, secret_findings, tag_findings
        )
        if args.emit_json:
            result = {
                "mode": "dry_run" if not args.apply else "apply",
                "blocked": True,
                "fingerprint": fingerprint,
                "blocking_reasons": {
                    "validation_errors": len(validation["errors"]),
                    "drift_blockers": len(drift_blockers),
                    "secret_findings": len(secret_findings),
                    "tag_findings": len(tag_findings),
                },
                "schema_version": SCHEMA_VERSION,
                "generated_at_utc": utc_now,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif not args.quiet:
            print(report)
        return 1

    duplicate_run = is_duplicate_fingerprint(ledger, fingerprint)
    is_duplicate = duplicate_run is not None

    if is_duplicate and args.apply:
        apply_run = build_apply_run(package, fingerprint, args.package, utc_now, ledger)
        apply_run["status"] = "skipped_duplicate"
        apply_run["summary"]["records_applied"] = 0
        apply_run["summary"]["records_skipped"] = apply_run["summary"][
            "total_records_in_package"
        ]
        ledger.append(apply_run)
        save_ledger(output_dir, ledger)
        report = format_apply_report(apply_run, ledger)
        if args.emit_json:
            result = {
                "mode": "apply",
                "blocked": False,
                "skipped_duplicate": True,
                "apply_run_id": apply_run["apply_run_id"],
                "fingerprint": fingerprint,
                "package_id": apply_run["package_id"],
                "status": "skipped_duplicate",
                "summary": apply_run["summary"],
                "schema_version": SCHEMA_VERSION,
                "generated_at_utc": utc_now,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif not args.quiet:
            print(report)
        return 0

    if args.apply:
        apply_run = build_apply_run(package, fingerprint, args.package, utc_now, ledger)
        ledger.append(apply_run)
        save_ledger(output_dir, ledger)
        report = format_apply_report(apply_run, ledger)
        if args.emit_json:
            result = {
                "mode": "apply",
                "blocked": False,
                "skipped_duplicate": False,
                "apply_run_id": apply_run["apply_run_id"],
                "fingerprint": fingerprint,
                "package_id": apply_run["package_id"],
                "status": "applied",
                "summary": apply_run["summary"],
                "schema_version": SCHEMA_VERSION,
                "generated_at_utc": utc_now,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif not args.quiet:
            print(report)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
