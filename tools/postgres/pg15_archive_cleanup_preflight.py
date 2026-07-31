"""Read-only preflight for PG15 archive cleanup (#3612).

Evaluates operator-supplied evidence before a future, separate cleanup GO.
This module performs no deletes, no volume mutations, and no restore actions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

ARCHIVE_PATH = "/data/.pg15_archived/"
ACTIVE_CLUSTER_PATH = "/data/18/"
EXPECTED_PG_IMAGE_PREFIX = "postgres:18.4-alpine"
DEFAULT_RETENTION_EARLIEST = date(2026, 7, 15)
MIGRATION_BASELINE_ROW_COUNTS: dict[str, int] = {
    "orders": 10511,
    "trades": 9963,
    "signals": 221161,
}

READY_FOR_OPERATOR_CLEANUP_GO = "READY_FOR_OPERATOR_CLEANUP_GO"
NOT_READY_RETENTION = "NOT_READY_RETENTION"
NOT_READY_BACKUP = "NOT_READY_BACKUP"
NOT_READY_PG18_HEALTH = "NOT_READY_PG18_HEALTH"
NOT_READY_CLUSTER_PATH = "NOT_READY_CLUSTER_PATH"
NOT_READY_ROW_COUNTS = "NOT_READY_ROW_COUNTS"
NOT_READY_ARCHIVE_REFERENCE = "NOT_READY_ARCHIVE_REFERENCE"

ALL_REASON_CODES = (
    READY_FOR_OPERATOR_CLEANUP_GO,
    NOT_READY_RETENTION,
    NOT_READY_BACKUP,
    NOT_READY_PG18_HEALTH,
    NOT_READY_CLUSTER_PATH,
    NOT_READY_ROW_COUNTS,
    NOT_READY_ARCHIVE_REFERENCE,
)

FORBIDDEN_COMMAND_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bdocker\s+volume\s+rm\b", re.IGNORECASE),
    re.compile(r"\bcompose\s+down\b[^\n]*-v\b", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
    re.compile(r"\brestore_all\.ps1\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+compose\b[^\n]*\bdown\b[^\n]*\b-v\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class PreflightInputs:
    """Operator-supplied evidence for read-only evaluation."""

    check_as_of: date
    retention_earliest: date = DEFAULT_RETENTION_EARLIEST
    backup_health_pass: bool | None = None
    fresh_backup_reference: str | None = None
    backup_reference_verified: bool | None = None
    pg_image: str | None = None
    pg_healthy: bool | None = None
    pg_isready: bool | None = None
    active_cluster_path: str | None = None
    archive_referenced_by_runtime: bool = False
    archive_path_exists: bool | None = None
    row_counts: dict[str, int] | None = None
    expected_row_counts: dict[str, int] = field(
        default_factory=lambda: dict(MIGRATION_BASELINE_ROW_COUNTS)
    )
    runtime_config_snippet: str | None = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    reason_code: str | None
    detail: str


@dataclass(frozen=True)
class PreflightReport:
    status: str
    reason_codes: tuple[str, ...]
    checks: tuple[CheckResult, ...]
    cleanup_target_candidate: str
    operator_go_required: bool
    informational_commands: tuple[str, ...]
    destructive_operations: tuple[str, ...]


def _normalize_path(path: str | None) -> str | None:
    if path is None:
        return None
    normalized = path.strip().replace("\\", "/")
    if not normalized.endswith("/"):
        normalized = f"{normalized}/"
    return normalized


def runtime_config_references_archive(snippet: str | None) -> bool:
    if not snippet:
        return False
    return ".pg15_archived" in snippet


def check_retention(inputs: PreflightInputs) -> CheckResult:
    passed = inputs.check_as_of >= inputs.retention_earliest
    return CheckResult(
        name="retention_window",
        passed=passed,
        reason_code=None if passed else NOT_READY_RETENTION,
        detail=(
            f"check_as_of={inputs.check_as_of.isoformat()} "
            f"retention_earliest={inputs.retention_earliest.isoformat()}"
        ),
    )


def check_backup(inputs: PreflightInputs) -> CheckResult:
    reasons: list[str] = []
    if inputs.backup_health_pass is not True:
        reasons.append("backup_health_pass is not true")
    if not inputs.fresh_backup_reference:
        reasons.append("fresh_backup_reference missing")
    if inputs.backup_reference_verified is not True:
        reasons.append("backup_reference_verified is not true")
    passed = not reasons
    return CheckResult(
        name="backup_evidence",
        passed=passed,
        reason_code=None if passed else NOT_READY_BACKUP,
        detail="; ".join(reasons) if reasons else "backup evidence complete",
    )


def check_pg18_health(inputs: PreflightInputs) -> CheckResult:
    reasons: list[str] = []
    image = (inputs.pg_image or "").strip()
    if not image.startswith(EXPECTED_PG_IMAGE_PREFIX):
        reasons.append(f"pg_image must start with {EXPECTED_PG_IMAGE_PREFIX!r}")
    if inputs.pg_healthy is not True:
        reasons.append("pg_healthy is not true")
    if inputs.pg_isready is not True:
        reasons.append("pg_isready is not true")
    passed = not reasons
    return CheckResult(
        name="pg18_health",
        passed=passed,
        reason_code=None if passed else NOT_READY_PG18_HEALTH,
        detail="; ".join(reasons) if reasons else "pg18 health evidence complete",
    )


def check_cluster_path(inputs: PreflightInputs) -> CheckResult:
    normalized = _normalize_path(inputs.active_cluster_path)
    expected = _normalize_path(ACTIVE_CLUSTER_PATH)
    passed = normalized == expected
    return CheckResult(
        name="active_cluster_path",
        passed=passed,
        reason_code=None if passed else NOT_READY_CLUSTER_PATH,
        detail=(
            f"active_cluster_path={inputs.active_cluster_path!r} "
            f"expected={ACTIVE_CLUSTER_PATH!r}"
        ),
    )


def check_row_counts(inputs: PreflightInputs) -> CheckResult:
    if inputs.row_counts is None:
        return CheckResult(
            name="row_count_sanity",
            passed=False,
            reason_code=NOT_READY_ROW_COUNTS,
            detail="row_counts missing",
        )
    mismatches: list[str] = []
    for table, expected in inputs.expected_row_counts.items():
        actual = inputs.row_counts.get(table)
        if actual is None:
            mismatches.append(f"{table}=missing")
        elif actual != expected:
            mismatches.append(f"{table}={actual} expected={expected}")
    passed = not mismatches
    return CheckResult(
        name="row_count_sanity",
        passed=passed,
        reason_code=None if passed else NOT_READY_ROW_COUNTS,
        detail="; ".join(mismatches) if mismatches else "row counts match baseline",
    )


def check_archive_reference(inputs: PreflightInputs) -> CheckResult:
    referenced = (
        inputs.archive_referenced_by_runtime
        or runtime_config_references_archive(inputs.runtime_config_snippet)
    )
    passed = not referenced
    detail = (
        "archive path is not referenced by runtime config"
        if passed
        else "archive path appears referenced by runtime config"
    )
    return CheckResult(
        name="archive_runtime_reference",
        passed=passed,
        reason_code=None if passed else NOT_READY_ARCHIVE_REFERENCE,
        detail=detail,
    )


def evaluate_preflight(inputs: PreflightInputs) -> PreflightReport:
    checks = (
        check_retention(inputs),
        check_backup(inputs),
        check_pg18_health(inputs),
        check_cluster_path(inputs),
        check_row_counts(inputs),
        check_archive_reference(inputs),
    )
    failing_codes = tuple(
        sorted({c.reason_code for c in checks if c.reason_code is not None})
    )
    if failing_codes:
        status = failing_codes[0]
        reason_codes = failing_codes
    else:
        status = READY_FOR_OPERATOR_CLEANUP_GO
        reason_codes = (READY_FOR_OPERATOR_CLEANUP_GO,)

    informational_commands = (
        "make backup-health",
        "make backup",
        "docker inspect --format '{{.Config.Image}}' <postgres-container>",
        "docker exec <postgres-container> pg_isready",
        (
            "docker exec <postgres-container> psql -U <user> -d <db> "
            "-c \"SELECT 'orders', count(*) FROM orders "
            "UNION ALL SELECT 'trades', count(*) FROM trades "
            "UNION ALL SELECT 'signals', count(*) FROM signals;\""
        ),
    )

    return PreflightReport(
        status=status,
        reason_codes=reason_codes,
        checks=checks,
        cleanup_target_candidate=ARCHIVE_PATH,
        operator_go_required=True,
        informational_commands=informational_commands,
        destructive_operations=(),
    )


def report_to_dict(report: PreflightReport) -> dict[str, Any]:
    payload = asdict(report)
    payload["checks"] = [asdict(check) for check in report.checks]
    return payload


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def inputs_from_mapping(data: dict[str, Any]) -> PreflightInputs:
    check_as_of_raw = data.get("check_as_of")
    if not isinstance(check_as_of_raw, str):
        raise ValueError("check_as_of must be an ISO date string")
    retention_raw = data.get(
        "retention_earliest", DEFAULT_RETENTION_EARLIEST.isoformat()
    )
    if not isinstance(retention_raw, str):
        raise ValueError("retention_earliest must be an ISO date string")
    row_counts = data.get("row_counts")
    if row_counts is not None and not isinstance(row_counts, dict):
        raise ValueError("row_counts must be an object")
    expected_row_counts = data.get("expected_row_counts", MIGRATION_BASELINE_ROW_COUNTS)
    if not isinstance(expected_row_counts, dict):
        raise ValueError("expected_row_counts must be an object")
    return PreflightInputs(
        check_as_of=parse_date(check_as_of_raw),
        retention_earliest=parse_date(retention_raw),
        backup_health_pass=data.get("backup_health_pass"),
        fresh_backup_reference=data.get("fresh_backup_reference"),
        backup_reference_verified=data.get("backup_reference_verified"),
        pg_image=data.get("pg_image"),
        pg_healthy=data.get("pg_healthy"),
        pg_isready=data.get("pg_isready"),
        active_cluster_path=data.get("active_cluster_path"),
        archive_referenced_by_runtime=bool(
            data.get("archive_referenced_by_runtime", False)
        ),
        archive_path_exists=data.get("archive_path_exists"),
        row_counts=row_counts,
        expected_row_counts={str(k): int(v) for k, v in expected_row_counts.items()},
        runtime_config_snippet=data.get("runtime_config_snippet"),
    )


def collect_forbidden_command_violations(text: str) -> list[str]:
    violations: list[str] = []
    for pattern in FORBIDDEN_COMMAND_PATTERNS:
        if pattern.search(text):
            violations.append(pattern.pattern)
    return violations


def assert_no_destructive_commands_in_source(source_text: str) -> None:
    violations = collect_forbidden_command_violations(source_text)
    if violations:
        joined = ", ".join(violations)
        raise ValueError(f"destructive command patterns found: {joined}")


def module_source_path() -> Path:
    return Path(__file__).resolve()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only PG15 archive cleanup preflight (#3612). "
            "Evaluates operator evidence; performs no mutations."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="JSON file with PreflightInputs fields",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report on stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.input is None:
        parser.error("--input is required for CLI evaluation")
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    inputs = inputs_from_mapping(payload)
    report = evaluate_preflight(inputs)
    if args.json:
        print(json.dumps(report_to_dict(report), indent=2, sort_keys=True))
    else:
        print(f"status: {report.status}")
        print(f"reason_codes: {', '.join(report.reason_codes)}")
        print(f"cleanup_target_candidate: {report.cleanup_target_candidate}")
        print(f"operator_go_required: {report.operator_go_required}")
        for check in report.checks:
            state = "PASS" if check.passed else "FAIL"
            print(f"  [{state}] {check.name}: {check.detail}")
    return 0 if report.status == READY_FOR_OPERATOR_CLEANUP_GO else 1


if __name__ == "__main__":
    sys.exit(main())
