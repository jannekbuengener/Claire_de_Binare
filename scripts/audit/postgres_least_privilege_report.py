"""Offline least-privilege and RLS baseline report for Issue #741."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPORT_SCHEMA = "governance.postgres_least_privilege_report.v1"
DEFAULT_BASELINE_PATH = Path(__file__).with_name("desired_privileges.json")
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
RESULT_VIOLATION = "VIOLATION"
RESULT_UNKNOWN = "UNKNOWN"

DATASET_CANDIDATES = {
    "roles": ("roles.csv", "roles.json"),
    "role_memberships": ("role_memberships.csv", "role_memberships.json"),
    "table_privileges": ("table_privileges.csv", "table_privileges.json"),
    "rls_tables": ("rls_tables.csv", "rls_tables.json"),
    "policies": ("policies.csv", "policies.json"),
    "default_privileges": ("default_privileges.csv", "default_privileges.json"),
}
REQUIRED_DATASETS = (
    "roles",
    "role_memberships",
    "table_privileges",
    "rls_tables",
    "policies",
)


@dataclass(frozen=True)
class LoadedDataset:
    name: str
    path: str | None
    rows: tuple[dict[str, Any], ...]


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    return normalized in {"1", "t", "true", "yes", "y", "on"}


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        with path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, list):
            raise ValueError(f"{path} must contain a JSON array")
        return [dict(row) for row in loaded]

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def load_datasets(input_dir: str) -> dict[str, LoadedDataset]:
    """Load all known datasets from ``input_dir`` with stable defaults."""
    base_dir = Path(input_dir)
    loaded: dict[str, LoadedDataset] = {}

    for dataset_name, candidates in DATASET_CANDIDATES.items():
        dataset_path = None
        dataset_rows: tuple[dict[str, Any], ...] = ()

        for candidate in candidates:
            candidate_path = base_dir / candidate
            if candidate_path.exists():
                dataset_path = str(candidate_path)
                dataset_rows = tuple(_load_rows(candidate_path))
                break

        loaded[dataset_name] = LoadedDataset(
            name=dataset_name,
            path=dataset_path,
            rows=dataset_rows,
        )

    return loaded


def load_baseline(path: str | None = None) -> dict[str, Any]:
    baseline_path = Path(path) if path else DEFAULT_BASELINE_PATH
    with baseline_path.open("r", encoding="utf-8") as handle:
        baseline = json.load(handle)
    baseline["_baseline_path"] = str(baseline_path)
    return baseline


def _normalize_roles(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    normalized = [
        {
            "rolname": str(row.get("rolname", "")).strip(),
            "rolcanlogin": _parse_bool(row.get("rolcanlogin")),
            "rolinherit": _parse_bool(row.get("rolinherit")),
            "rolsuper": _parse_bool(row.get("rolsuper")),
        }
        for row in rows
    ]
    return sorted(normalized, key=lambda item: item["rolname"])


def _normalize_role_memberships(
    rows: tuple[dict[str, Any], ...],
) -> list[dict[str, str]]:
    normalized = [
        {
            "role_name": str(row.get("role_name", row.get("role", ""))).strip(),
            "member_name": str(row.get("member_name", row.get("member", ""))).strip(),
        }
        for row in rows
    ]
    return sorted(normalized, key=lambda item: (item["role_name"], item["member_name"]))


def _normalize_table_privileges(
    rows: tuple[dict[str, Any], ...],
) -> list[dict[str, str]]:
    normalized = [
        {
            "grantee": str(row.get("grantee", "")).strip(),
            "table_schema": str(row.get("table_schema", "")).strip(),
            "table_name": str(row.get("table_name", "")).strip(),
            "privilege_type": str(row.get("privilege_type", "")).strip().upper(),
        }
        for row in rows
    ]
    return sorted(
        normalized,
        key=lambda item: (
            item["grantee"],
            item["table_schema"],
            item["table_name"],
            item["privilege_type"],
        ),
    )


def _normalize_rls_tables(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    normalized = [
        {
            "table_schema": str(row.get("table_schema", "")).strip(),
            "table_name": str(row.get("table_name", "")).strip(),
            "row_security_enabled": _parse_bool(
                row.get("row_security_enabled", row.get("relrowsecurity"))
            ),
            "force_row_security_enabled": _parse_bool(
                row.get(
                    "force_row_security_enabled",
                    row.get("relforcerowsecurity"),
                )
            ),
        }
        for row in rows
    ]
    return sorted(
        normalized, key=lambda item: (item["table_schema"], item["table_name"])
    )


def _normalize_policies(rows: tuple[dict[str, Any], ...]) -> list[dict[str, str]]:
    normalized = [
        {
            "table_schema": str(
                row.get("table_schema", row.get("schemaname", ""))
            ).strip(),
            "table_name": str(row.get("table_name", row.get("tablename", ""))).strip(),
            "policyname": str(
                row.get("policyname", row.get("policy_name", ""))
            ).strip(),
            "cmd": str(row.get("cmd", row.get("command", ""))).strip().upper(),
            "roles": str(row.get("roles", "")).strip(),
            "qual": str(row.get("qual", "")).strip(),
            "with_check": str(row.get("with_check", "")).strip(),
            "permissive": str(row.get("permissive", "")).strip().upper(),
        }
        for row in rows
    ]
    return sorted(
        normalized,
        key=lambda item: (
            item["table_schema"],
            item["table_name"],
            item["policyname"],
            item["cmd"],
            item["roles"],
        ),
    )


def _normalize_default_privileges(
    rows: tuple[dict[str, Any], ...],
) -> list[dict[str, str]]:
    normalized = [
        {
            "role_name": str(row.get("role_name", "")).strip(),
            "object_schema": str(row.get("object_schema", "")).strip(),
            "object_type": str(row.get("object_type", "")).strip(),
            "privilege_spec": str(row.get("privilege_spec", "")).strip(),
        }
        for row in rows
    ]
    return sorted(
        normalized,
        key=lambda item: (
            item["role_name"],
            item["object_schema"],
            item["object_type"],
            item["privilege_spec"],
        ),
    )


def _normalize_observed(datasets: dict[str, LoadedDataset]) -> dict[str, Any]:
    return {
        "roles": _normalize_roles(datasets["roles"].rows),
        "role_memberships": _normalize_role_memberships(
            datasets["role_memberships"].rows
        ),
        "table_privileges": _normalize_table_privileges(
            datasets["table_privileges"].rows
        ),
        "rls_tables": _normalize_rls_tables(datasets["rls_tables"].rows),
        "policies": _normalize_policies(datasets["policies"].rows),
        "default_privileges": _normalize_default_privileges(
            datasets["default_privileges"].rows
        ),
    }


def _expected_privileges(baseline: dict[str, Any]) -> set[tuple[str, str, str, str]]:
    expected: set[tuple[str, str, str, str]] = set()
    expected_by_grantee = baseline.get("expected_table_privileges", {})

    for grantee, privileges in expected_by_grantee.items():
        for privilege_type, tables in privileges.items():
            for table_name in tables:
                expected.add(
                    (grantee, "public", table_name, str(privilege_type).upper())
                )

    return expected


def _expected_roles(baseline: dict[str, Any]) -> dict[str, dict[str, bool | str]]:
    return {
        role["rolname"]: {
            "rolname": role["rolname"],
            "rolcanlogin": bool(role["rolcanlogin"]),
            "rolinherit": bool(role["rolinherit"]),
            "rolsuper": bool(role["rolsuper"]),
        }
        for role in baseline.get("required_roles", [])
    }


def _expected_memberships(baseline: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (membership["role_name"], membership["member_name"])
        for membership in baseline.get("required_role_memberships", [])
    }


def _expected_rls_tables(
    baseline: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (entry["table_schema"], entry["table_name"]): {
            "table_schema": entry["table_schema"],
            "table_name": entry["table_name"],
            "row_security_enabled": bool(entry["row_security_enabled"]),
            "force_row_security_enabled": bool(entry["force_row_security_enabled"]),
        }
        for entry in baseline.get("expected_rls_tables", [])
    }


def _expected_policies(baseline: dict[str, Any]) -> set[tuple[str, str, str, str, str]]:
    return {
        (
            entry["table_schema"],
            entry["table_name"],
            entry["policyname"],
            str(entry.get("cmd", "")).upper(),
            str(entry.get("roles", "")).strip(),
        )
        for entry in baseline.get("expected_policies", [])
    }


def _sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda item: (
            item["category"],
            item["resource"],
            item["detail"],
        ),
    )


def build_report(
    datasets: dict[str, LoadedDataset],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Build a deterministic least-privilege report from offline dump files."""
    gaps: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    for dataset_name in REQUIRED_DATASETS:
        if datasets[dataset_name].path is None:
            gaps.append(
                {
                    "status": RESULT_UNKNOWN,
                    "category": "INPUT",
                    "resource": dataset_name,
                    "detail": f"required dataset {dataset_name}.csv|json is missing",
                }
            )

    observed = _normalize_observed(datasets)
    expected_roles = _expected_roles(baseline)
    observed_roles = {row["rolname"]: row for row in observed["roles"]}
    for role_name, expected in expected_roles.items():
        current = observed_roles.get(role_name)
        if current is None:
            violations.append(
                {
                    "status": RESULT_VIOLATION,
                    "category": "ROLE",
                    "resource": role_name,
                    "detail": "required role is missing from pg_roles dump",
                }
            )
            continue

        for field in ("rolcanlogin", "rolinherit", "rolsuper"):
            if current[field] != expected[field]:
                violations.append(
                    {
                        "status": RESULT_VIOLATION,
                        "category": "ROLE",
                        "resource": role_name,
                        "detail": (
                            f"{field} expected {expected[field]!r} but observed "
                            f"{current[field]!r}"
                        ),
                    }
                )

    expected_memberships = _expected_memberships(baseline)
    observed_memberships = {
        (row["role_name"], row["member_name"]) for row in observed["role_memberships"]
    }
    for membership in sorted(expected_memberships):
        if membership not in observed_memberships:
            violations.append(
                {
                    "status": RESULT_VIOLATION,
                    "category": "ROLE_MEMBERSHIP",
                    "resource": f"{membership[1]}->{membership[0]}",
                    "detail": "required role membership is missing",
                }
            )

    expected_privileges = _expected_privileges(baseline)
    monitored_grantees = {
        str(grantee).strip() for grantee in baseline.get("monitored_grantees", [])
    }
    observed_privileges = {
        (
            row["grantee"],
            row["table_schema"],
            row["table_name"],
            row["privilege_type"],
        )
        for row in observed["table_privileges"]
        if row["grantee"] in monitored_grantees
    }

    for privilege in sorted(expected_privileges):
        if privilege not in observed_privileges:
            violations.append(
                {
                    "status": RESULT_VIOLATION,
                    "category": "TABLE_PRIVILEGE",
                    "resource": (
                        f"{privilege[0]}:{privilege[1]}.{privilege[2]}:{privilege[3]}"
                    ),
                    "detail": "expected table privilege is missing",
                }
            )

    for privilege in sorted(observed_privileges - expected_privileges):
        violations.append(
            {
                "status": RESULT_VIOLATION,
                "category": "TABLE_PRIVILEGE",
                "resource": (
                    f"{privilege[0]}:{privilege[1]}.{privilege[2]}:{privilege[3]}"
                ),
                "detail": "unexpected table privilege is present",
            }
        )

    expected_rls = _expected_rls_tables(baseline)
    observed_rls = {
        (row["table_schema"], row["table_name"]): row for row in observed["rls_tables"]
    }
    for table_key, expected in sorted(expected_rls.items()):
        current = observed_rls.get(table_key)
        if current is None:
            gaps.append(
                {
                    "status": RESULT_UNKNOWN,
                    "category": "RLS",
                    "resource": f"{table_key[0]}.{table_key[1]}",
                    "detail": "RLS table flags are missing from the live dump",
                }
            )
            continue

        for field in ("row_security_enabled", "force_row_security_enabled"):
            if current[field] != expected[field]:
                violations.append(
                    {
                        "status": RESULT_VIOLATION,
                        "category": "RLS",
                        "resource": f"{table_key[0]}.{table_key[1]}",
                        "detail": (
                            f"{field} expected {expected[field]!r} but observed "
                            f"{current[field]!r}"
                        ),
                    }
                )

    expected_policies = _expected_policies(baseline)
    observed_policies = {
        (
            row["table_schema"],
            row["table_name"],
            row["policyname"],
            row["cmd"],
            row["roles"],
        )
        for row in observed["policies"]
    }
    for policy in sorted(expected_policies - observed_policies):
        violations.append(
            {
                "status": RESULT_VIOLATION,
                "category": "POLICY",
                "resource": f"{policy[0]}.{policy[1]}:{policy[2]}",
                "detail": "expected RLS policy is missing",
            }
        )
    for policy in sorted(observed_policies - expected_policies):
        violations.append(
            {
                "status": RESULT_VIOLATION,
                "category": "POLICY",
                "resource": f"{policy[0]}.{policy[1]}:{policy[2]}",
                "detail": "unexpected RLS policy is present",
            }
        )

    gap_count = len(gaps)
    violation_count = len(violations)
    status = STATUS_PASS if gap_count == 0 and violation_count == 0 else STATUS_FAIL

    return {
        "schema": REPORT_SCHEMA,
        "status": status,
        "reason_code": (
            "POSTGRES_LEAST_PRIVILEGE_OK"
            if status == STATUS_PASS
            else "POSTGRES_LEAST_PRIVILEGE_GAPS_OR_VIOLATIONS"
        ),
        "baseline_schema": baseline.get("schema"),
        "baseline_name": baseline.get("baseline_name"),
        "baseline_path": baseline.get("_baseline_path"),
        "inputs": {
            name: {
                "path": dataset.path,
                "row_count": len(dataset.rows),
            }
            for name, dataset in sorted(datasets.items())
        },
        "summary": {
            "ok": status == STATUS_PASS,
            "gap_count": gap_count,
            "violation_count": violation_count,
            "observed_role_count": len(observed["roles"]),
            "observed_table_privilege_count": len(observed["table_privileges"]),
            "observed_policy_count": len(observed["policies"]),
        },
        "gaps": _sort_findings(gaps),
        "violations": _sort_findings(violations),
        "observed": observed,
    }


def build_summary_markdown(report: dict[str, Any]) -> str:
    """Render a short human-readable summary alongside the JSON report."""
    lines = [
        "# Postgres Least-Privilege Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Baseline: `{report['baseline_name']}`",
        f"- Gaps: `{report['summary']['gap_count']}`",
        f"- Violations: `{report['summary']['violation_count']}`",
        "",
        "## Inputs",
        "",
        "| Dataset | Rows | Source |",
        "|---|---:|---|",
    ]

    for dataset_name, metadata in sorted(report["inputs"].items()):
        source = metadata["path"] or "MISSING"
        lines.append(f"| `{dataset_name}` | {metadata['row_count']} | `{source}` |")

    lines.extend(["", "## Findings", ""])

    if not report["gaps"] and not report["violations"]:
        lines.append("- No gaps or violations detected against the desired baseline.")
        return "\n".join(lines) + "\n"

    for finding in report["gaps"]:
        lines.append(
            f"- `{finding['status']}` `{finding['category']}` "
            f"`{finding['resource']}`: {finding['detail']}"
        )
    for finding in report["violations"]:
        lines.append(
            f"- `{finding['status']}` `{finding['category']}` "
            f"`{finding['resource']}`: {finding['detail']}"
        )

    return "\n".join(lines) + "\n"


def generate_report(
    out_dir: str,
    *,
    input_dir: str,
    baseline_path: str | None = None,
) -> dict[str, Any]:
    """Load fixtures, compare them to the baseline, and persist report files."""
    datasets = load_datasets(input_dir)
    baseline = load_baseline(baseline_path)
    report = build_report(datasets, baseline)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    report_json = out_path / "report.json"
    report_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_md = build_summary_markdown(report)
    (out_path / "summary.md").write_text(summary_md, encoding="utf-8")

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline least-privilege + RLS baseline report for Issue #741."
    )
    parser.add_argument(
        "--input-dir", required=True, help="Directory with CSV/JSON dumps"
    )
    parser.add_argument(
        "--out-dir",
        required=True,
        help="Directory where report.json and summary.md should be written",
    )
    parser.add_argument(
        "--baseline",
        default=str(DEFAULT_BASELINE_PATH),
        help="Path to desired_privileges.json",
    )
    args = parser.parse_args(argv)

    report = generate_report(
        args.out_dir,
        input_dir=args.input_dir,
        baseline_path=args.baseline,
    )
    sys.stdout.write(build_summary_markdown(report))
    return 0 if report["status"] == STATUS_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
