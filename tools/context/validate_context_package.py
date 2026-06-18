"""Fail-closed validator for CDB Context Packages.

Validates a context package JSON file against:
- JSON Schema (structure, required fields, allowed record types)
- Stop rules (secrets, forbidden trading state, live/echtgeld claims, canon evidence)

Usage:
    python tools/context/validate_context_package.py <package.json>
    python tools/context/validate_context_package.py --stdin < package.json
    python tools/context/validate_context_package.py --help

Exit codes:
    0 - PASS (all checks pass)
    1 - BLOCKED (validation failures)
    2 - FAIL (unexpected error)

Issue: #3288
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "context_package.schema.json"

SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(api[_-]?key|api[_-]?secret|secret|password|token|credential|private[_-]?key)"),
    re.compile(r"(?i)(?:REDIS_PASSWORD|POSTGRES_PASSWORD|GRAFANA_PASSWORD|MEXC_API_KEY|MEXC_API_SECRET|SECRETS_PATH|SMTP_PASSWORD)"),
]

FORBIDDEN_RECORD_SUBSTRINGS: list[re.Pattern] = [
    re.compile(r"(?i)(order|fill|position)\s*(id|data|status|event|record|update)"),
    re.compile(r"(?i)live[_-]risk[_-]state"),
    re.compile(r"(?i)trading[_-]state"),
]

FORBIDDEN_ALLOWED_LR_KEYS: set[str] = {"lr_status", "live_gate", "echtgeld_gate", "canary_status"}

LR_SSOT_PATH = "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md"

VALID_REPOS: set[str] = {"Claire_de_Binare"}

CANON_PATHS: set[str] = {
    "AGENTS.md",
    "agents/AGENTS.md",
    "agents/OPEN_CODE_AGENTS.md",
    "docs/runbooks/CONTROL_REGISTER.md",
    "CURRENT_STATUS.md",
    "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
    "knowledge/governance/CDB_CONSTITUTION.md",
    "knowledge/governance/CDB_GOVERNANCE.md",
    "knowledge/governance/CDB_AGENT_POLICY.md",
    "knowledge/governance/SYSTEM_INVARIANTS.md",
    "knowledge/CDB_KNOWLEDGE_HUB.md",
    "docs/meta/WORKING_REPO_CANON.md",
}


def load_schema() -> dict[str, Any]:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve_ref(ref: str, schema: dict[str, Any]) -> dict[str, Any]:
    if ref.startswith("#/definitions/"):
        key = ref[len("#/definitions/"):]
        return schema["definitions"][key]
    msg = f"Cannot resolve $ref: {ref}"
    raise ValueError(msg)


def validate_against_schema(
    package: dict[str, Any], schema: dict[str, Any]
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    _validate_object(package, schema, "$", errors, schema)
    return errors


def _validate_object(
    obj: Any, schema_node: dict[str, Any], path: str, errors: list[dict[str, Any]],
    root_schema: dict[str, Any],
) -> None:
    if not isinstance(obj, dict):
        _report_error(errors, path, "expected_object", f"Expected object, got {type(obj).__name__}")
        return

    if "$ref" in schema_node:
        resolved = resolve_ref(schema_node["$ref"], root_schema)
        _validate_object(obj, resolved, path, errors, root_schema)
        return

    required = schema_node.get("required", [])
    for field in required:
        if field not in obj:
            _report_error(errors, f"{path}.{field}", "missing_required", f"Missing required field: {field}")

    properties = schema_node.get("properties", {})
    for key, value in obj.items():
        prop_path = f"{path}.{key}"
        if key not in properties:
            if schema_node.get("additionalProperties", True) is False:
                _report_error(errors, prop_path, "unknown_field", f"Unknown field: {key}")
            continue
        prop_schema = properties[key]
        _validate_value(value, prop_schema, prop_path, errors, root_schema)


def _validate_value(
    value: Any, schema_node: dict[str, Any], path: str, errors: list[dict[str, Any]],
    root_schema: dict[str, Any],
) -> None:
    if "$ref" in schema_node:
        resolved_schema = resolve_ref(schema_node["$ref"], root_schema)
        type_schema = resolved_schema
    else:
        type_schema = schema_node

    if "type" in type_schema and type_schema["type"] == "object" and isinstance(value, dict):
        _validate_object(value, type_schema, path, errors, root_schema)
        return

    if type_schema.get("type") == "array" and isinstance(value, list):
        items_schema = type_schema.get("items", {})
        min_items = type_schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            _report_error(errors, path, "min_items", f"Minimum {min_items} items required, got {len(value)}")
        for i, item in enumerate(value):
            _validate_value(item, items_schema, f"{path}[{i}]", errors, root_schema)
        return

    if "type" in type_schema:
        expected = type_schema["type"]
        if expected == "string" and not isinstance(value, str):
            _report_error(errors, path, "type_mismatch", f"Expected string, got {type(value).__name__}")
        elif expected == "boolean" and not isinstance(value, bool):
            _report_error(errors, path, "type_mismatch", f"Expected boolean, got {type(value).__name__}")

    if isinstance(value, str):
        if "enum" in type_schema and value not in type_schema["enum"]:
            _report_error(
                errors, path, "invalid_enum",
                f"Invalid value '{value}'. Allowed: {type_schema['enum']}",
            )
        if "minLength" in type_schema and len(value) < type_schema["minLength"]:
            _report_error(errors, path, "min_length", f"Minimum length {type_schema['minLength']} required")
        if "pattern" in type_schema and not re.match(type_schema["pattern"], value):
            _report_error(errors, path, "pattern_mismatch", f"Value '{value}' does not match pattern {type_schema['pattern']}")

    if "oneOf" in type_schema:
        matched = False
        for option in type_schema["oneOf"]:
            if option.get("type") == "null" and value is None:
                matched = True
                break
            if isinstance(value, dict) and option.get("type") == "object":
                matched = True
                break
            if isinstance(value, str) and option.get("type") == "string":
                matched = True
                break
        if not matched:
            _report_error(errors, path, "oneof_mismatch", f"Value does not match any oneOf schema: {type(value).__name__}")


def check_secret_indicators(
    package: dict[str, Any], errors: list[dict[str, Any]]
) -> None:
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        summary = record.get("summary", "")
        if isinstance(summary, str) and any(p.search(summary) for p in SECRET_PATTERNS):
            _report_error(
                errors, f"$.package.records[{i}].summary",
                "secret_indicator",
                "Secret indicator detected in summary field. No secret values will be displayed.",
            )
        source_path = record.get("source_path", "")
        if isinstance(source_path, str) and any(p.search(source_path) for p in SECRET_PATTERNS):
            _report_error(
                errors, f"$.package.records[{i}].source_path",
                "secret_indicator",
                "Secret indicator detected in source_path. BLOCKED.",
            )


def check_forbidden_trading_state(
    package: dict[str, Any], errors: list[dict[str, Any]]
) -> None:
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        summary = record.get("summary", "")
        if isinstance(summary, str):
            for pattern in FORBIDDEN_RECORD_SUBSTRINGS:
                if pattern.search(summary):
                    _report_error(
                        errors, f"$.package.records[{i}].summary",
                        "forbidden_trading_state",
                        f"Orders/Fills/Positions/Live-Risk-State content detected. BLOCKED: matched '{pattern.pattern}'",
                    )


def check_live_echtgeld_claims(
    package: dict[str, Any], errors: list[dict[str, Any]]
) -> None:
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        claim = record.get("live_or_echtgeld_claim")
        if claim is not None:
            lr_ref = claim.get("lr_ssot_ref", "")
            if not lr_ref or LR_SSOT_PATH not in lr_ref:
                _report_error(
                    errors, f"$.package.records[{i}].live_or_echtgeld_claim.lr_ssot_ref",
                    "live_claim_without_lr_ssot",
                    f"Live/Echtgeld claim without valid LR-SSOT reference. Expected ref containing '{LR_SSOT_PATH}'.",
                )


def check_canon_read_evidence(
    package: dict[str, Any], errors: list[dict[str, Any]]
) -> None:
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        record_type = record.get("record_type", "")
        if record_type == "claim_record":
            canon_evidence = record.get("canon_read_evidence", [])
            if not canon_evidence:
                _report_error(
                    errors, f"$.package.records[{i}].canon_read_evidence",
                    "missing_canon_evidence",
                    "Claim record missing canon_read_evidence. BLOCKED.",
                )


def check_evidence_refs(
    package: dict[str, Any], errors: list[dict[str, Any]]
) -> None:
    records = package.get("package", {}).get("records", [])
    for i, record in enumerate(records):
        evidence_refs = record.get("evidence_refs", [])
        if not evidence_refs:
            _report_error(
                errors, f"$.package.records[{i}].evidence_refs",
                "missing_evidence_refs",
                "Record has no evidence_refs. BLOCKED.",
            )


def _report_error(
    errors: list[dict[str, Any]], path: str, code: str, message: str
) -> None:
    errors.append({
        "path": path,
        "code": code,
        "message": message,
    })


def build_report(
    schema_errors: list[dict[str, Any]],
    stop_rule_errors: list[dict[str, Any]],
    passed: bool,
) -> dict[str, Any]:
    all_errors = schema_errors + stop_rule_errors
    return {
        "status": "PASS" if passed else "BLOCKED",
        "exit_code": 0 if passed else 1,
        "error_count": len(all_errors),
        "schema_errors": schema_errors,
        "stop_rule_errors": stop_rule_errors,
        "errors": all_errors,
    }


def validate_package(
    package: dict[str, Any],
) -> dict[str, Any]:
    schema = load_schema()
    schema_errors = validate_against_schema(package, schema)

    stop_rule_errors: list[dict[str, Any]] = []
    if not schema_errors:
        check_secret_indicators(package, stop_rule_errors)
        check_forbidden_trading_state(package, stop_rule_errors)
        check_live_echtgeld_claims(package, stop_rule_errors)
        check_canon_read_evidence(package, stop_rule_errors)
        check_evidence_refs(package, stop_rule_errors)

    passed = len(schema_errors) == 0 and len(stop_rule_errors) == 0
    return build_report(schema_errors, stop_rule_errors, passed)


def format_agent_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    if report["status"] == "PASS":
        lines.append(f"[PASS] Context package validation passed. 0 errors.")
    else:
        lines.append(f"[BLOCKED] Context package validation FAILED — {report['error_count']} error(s).")
        lines.append("")
        lines.append("=== Schema Errors ===")
        for err in report["schema_errors"]:
            lines.append(f"  [{err['code']}] {err['path']}: {err['message']}")
        lines.append("")
        lines.append("=== Stop Rule Errors ===")
        for err in report["stop_rule_errors"]:
            lines.append(f"  [{err['code']}] {err['path']}: {err['message']}")
        lines.append("")
        lines.append("=== No secret values included in this report ===")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed validator for CDB Context Packages (#3288)",
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=str,
        help="Path to context package JSON file. Reads from stdin if omitted and --stdin is set.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read JSON from stdin instead of a file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON report instead of agent-readable text.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress agent-readable output. JSON report still available.",
    )
    args = parser.parse_args()

    if args.file:
        pkg_path = Path(args.file)
        try:
            with open(pkg_path, encoding="utf-8") as f:
                package = json.load(f)
        except FileNotFoundError:
            print(f"[FAIL] File not found: {args.file}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as e:
            print(f"[FAIL] Invalid JSON in {args.file}: {e}", file=sys.stderr)
            return 2
    elif args.stdin:
        try:
            package = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"[FAIL] Invalid JSON from stdin: {e}", file=sys.stderr)
            return 2
    else:
        parser.print_help()
        return 0

    report = validate_package(package)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    elif not args.quiet:
        print(format_agent_report(report))

    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
