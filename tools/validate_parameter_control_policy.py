#!/usr/bin/env python3
"""Validate CDB Parameter Control Policy register v1.

Canonical JSON:
  config/parameter-control/v1/CDB_PARAMETER_CONTROL_POLICY.json

Fingerprints:
  - register_fingerprint: SHA-256 over deterministically normalized ``rules`` only
    (sort_keys=True, separators=(',', ':'), UTF-8). The fingerprint field itself
    is not part of the hashed body.
  - canonical_json_sha256 (YAML pointer): SHA-256 over the full canonical JSON
    file bytes as stored on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT / "config" / "parameter-control" / "v1" / "CDB_PARAMETER_CONTROL_POLICY.json"
)
SCHEMA_PATH = (
    ROOT
    / "config"
    / "parameter-control"
    / "v1"
    / "CDB_PARAMETER_CONTROL_POLICY.schema.json"
)
YAML_PATH = (
    ROOT / "config" / "parameter-control" / "v1" / "CDB_PARAMETER_CONTROL_POLICY.yaml"
)

CHANGE_AUTHORITIES = {
    "RESEARCH_ALLOWED",
    "CONDITIONAL_AFTER_EVIDENCE",
    "FROZEN_UNTIL_CONTRACT",
    "GOVERNANCE_ONLY",
    "MUST_NOT_OPTIMIZE",
    "FORBIDDEN",
}
LIFECYCLE = {
    "active",
    "implicit",
    "duplicated",
    "dead",
    "documented-only",
    "invariant",
}
CONTEXTS = {"replay", "paper", "runtime", "live", "docs", "tests"}
REQUIRED_RULE_FIELDS = (
    "parameter_id",
    "exact_name",
    "aliases",
    "system_area",
    "owner",
    "repository_paths",
    "consumers",
    "effective_default",
    "override_precedence",
    "unit",
    "allowed_range",
    "main_class",
    "technical_adjustability",
    "change_authority",
    "context_validity",
    "safety_classification",
    "snapshot_and_provenance_requirement",
    "test_and_evidence_requirement",
    "lifecycle_status",
)


def canonical_rules_bytes(rules: list[dict[str, Any]]) -> bytes:
    return json.dumps(
        rules,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_register_fingerprint(doc: dict[str, Any]) -> str:
    return sha256_hex(canonical_rules_bytes(doc["rules"]))


def compute_canonical_json_sha256(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def _yaml_value(text: str, key: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(key)}:\s*(\S+)\s*$", text)
    return match.group(1) if match else None


def walk_unresolved(obj: Any) -> int:
    if isinstance(obj, dict):
        if obj.get("resolution_status") == "unresolved":
            return 1
        return sum(walk_unresolved(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(walk_unresolved(v) for v in obj)
    return 0


def validate(
    policy_path: Path = POLICY_PATH, schema_path: Path = SCHEMA_PATH
) -> list[str]:
    errors: list[str] = []
    if not policy_path.is_file():
        return [f"missing policy: {policy_path}"]
    if not schema_path.is_file():
        return [f"missing schema: {schema_path}"]

    raw = policy_path.read_text(encoding="utf-8")
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"invalid schema JSON: {exc}"]

    if jsonschema is not None:
        try:
            jsonschema.validate(instance=doc, schema=schema)
        except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
            errors.append(f"schema validation failed: {exc.message}")
    else:
        errors.append(
            "jsonschema package not installed; structural schema check skipped"
        )

    if doc.get("schema_version") != "cdb.parameter_control_policy.register.v1":
        errors.append("unexpected schema_version")

    rules = doc.get("rules")
    if not isinstance(rules, list):
        errors.append("rules must be a list")
        return errors

    if doc.get("rule_count") != len(rules):
        errors.append(
            f"rule_count mismatch: declared={doc.get('rule_count')} actual={len(rules)}"
        )
    if len(rules) != 56:
        errors.append(f"expected exactly 56 rules, found {len(rules)}")

    # stable sort by parameter_id
    ids = [r.get("parameter_id") for r in rules if isinstance(r, dict)]
    if ids != sorted(x for x in ids if isinstance(x, str)):
        errors.append("rules are not sorted by parameter_id")
    if len(ids) != len(set(ids)):
        errors.append("duplicate parameter_id values")

    expected_ids = [f"CDB-{i:03d}" for i in range(1, 57)]
    if ids != expected_ids:
        errors.append("parameter_id sequence must be CDB-001..CDB-056 without gaps")

    names: list[str] = []
    aliases: list[str] = []
    for rule in rules:
        if not isinstance(rule, dict):
            errors.append("rule entry is not an object")
            continue
        for field in REQUIRED_RULE_FIELDS:
            if field not in rule:
                errors.append(f"{rule.get('parameter_id')}: missing field {field}")
        pid = rule.get("parameter_id")
        name = rule.get("exact_name")
        if isinstance(name, str):
            names.append(name)
        for alias in rule.get("aliases") or []:
            if isinstance(alias, str):
                aliases.append(alias)
        authority = rule.get("change_authority")
        if authority not in CHANGE_AUTHORITIES:
            errors.append(f"{pid}: unknown change_authority={authority!r}")
        lifecycle = rule.get("lifecycle_status")
        if lifecycle not in LIFECYCLE:
            errors.append(f"{pid}: unknown lifecycle_status={lifecycle!r}")
        main_class = rule.get("main_class")
        allowed_classes = set(doc.get("enums", {}).get("main_class") or [])
        if allowed_classes and main_class not in allowed_classes:
            errors.append(f"{pid}: unknown main_class={main_class!r}")
        ctx = rule.get("context_validity") or {}
        for key in ("allowed", "forbidden"):
            for code in ctx.get(key) or []:
                if code not in CONTEXTS:
                    errors.append(f"{pid}: unknown context {key}={code!r}")

    if len(names) != len(set(names)):
        errors.append("duplicate exact_name values")

    # alias collisions against other exact names or other aliases (same-rule aliases ok)
    name_set = set(names)
    alias_owners: dict[str, str] = {}
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        pid = str(rule.get("parameter_id"))
        for alias in rule.get("aliases") or []:
            if alias in name_set and alias != rule.get("exact_name"):
                errors.append(f"{pid}: alias {alias!r} collides with an exact_name")
            prev = alias_owners.get(alias)
            if prev and prev != pid:
                errors.append(f"alias collision {alias!r} between {prev} and {pid}")
            alias_owners[alias] = pid

    computed_fp = compute_register_fingerprint(doc)
    declared_fp = doc.get("register_fingerprint")
    if declared_fp != computed_fp:
        errors.append(
            "register_fingerprint drift: "
            f"declared={declared_fp} computed={computed_fp}"
        )

    unresolved = walk_unresolved(rules)
    if doc.get("unresolved_count") != unresolved:
        errors.append(
            "unresolved_count drift: "
            f"declared={doc.get('unresolved_count')} computed={unresolved}"
        )

    if YAML_PATH.is_file():
        yaml_text = YAML_PATH.read_text(encoding="utf-8")
        yaml_fp = _yaml_value(yaml_text, "register_fingerprint")
        yaml_sha = _yaml_value(yaml_text, "canonical_json_sha256")
        file_sha = compute_canonical_json_sha256(policy_path)
        if yaml_fp != computed_fp:
            errors.append(
                "YAML register_fingerprint drift: "
                f"yaml={yaml_fp} computed={computed_fp}"
            )
        if yaml_sha != file_sha:
            errors.append(
                "YAML canonical_json_sha256 drift: "
                f"yaml={yaml_sha} computed={file_sha}"
            )
    else:
        errors.append(f"missing YAML pointer: {YAML_PATH}")

    # Safety posture smoke: at least one MUST_NOT_OPTIMIZE / GOVERNANCE_ONLY
    authorities = {r.get("change_authority") for r in rules if isinstance(r, dict)}
    if "MUST_NOT_OPTIMIZE" not in authorities:
        errors.append("expected at least one MUST_NOT_OPTIMIZE rule")
    if "GOVERNANCE_ONLY" not in authorities and "MUST_NOT_OPTIMIZE" not in authorities:
        errors.append("expected governance/safety frozen authorities")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--schema", type=Path, default=SCHEMA_PATH)
    args = parser.parse_args(argv)
    errors = validate(args.policy, args.schema)
    if errors:
        print("FAIL: parameter control policy validation")
        for err in errors:
            print(f" - {err}")
        return 1
    doc = json.loads(args.policy.read_text(encoding="utf-8"))
    print("PASS: parameter control policy validation")
    print(f" status={doc.get('status')}")
    print(f" rule_count={doc.get('rule_count')}")
    print(f" unresolved_count={doc.get('unresolved_count')}")
    print(f" register_fingerprint={doc.get('register_fingerprint')}")
    print(f" canonical_json_sha256={compute_canonical_json_sha256(args.policy)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
