from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.validate_parameter_control_policy import (
    compute_canonical_json_sha256,
    compute_register_fingerprint,
    validate,
)

ROOT = Path(__file__).resolve().parents[3]
POLICY = (
    ROOT / "config" / "parameter-control" / "v1" / "CDB_PARAMETER_CONTROL_POLICY.json"
)
SCHEMA = (
    ROOT
    / "config"
    / "parameter-control"
    / "v1"
    / "CDB_PARAMETER_CONTROL_POLICY.schema.json"
)
YAML = (
    ROOT / "config" / "parameter-control" / "v1" / "CDB_PARAMETER_CONTROL_POLICY.yaml"
)

REQUIRED_FIELDS = (
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


@pytest.mark.unit
def test_parameter_control_policy_files_exist() -> None:
    assert POLICY.is_file()
    assert SCHEMA.is_file()
    assert YAML.is_file()


@pytest.mark.unit
def test_parameter_control_policy_validator_passes() -> None:
    errors = validate(POLICY, SCHEMA)
    assert errors == [], errors


@pytest.mark.unit
def test_register_has_56_rules_and_19_fields() -> None:
    doc = json.loads(POLICY.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "cdb.parameter_control_policy.register.v1"
    assert doc["rule_count"] == 56
    assert len(doc["rules"]) == 56
    assert doc["unresolved_count"] == 0
    for rule in doc["rules"]:
        for field in REQUIRED_FIELDS:
            assert field in rule, f"{rule['parameter_id']} missing {field}"


@pytest.mark.unit
def test_register_fingerprint_is_rules_only_and_stable() -> None:
    doc = json.loads(POLICY.read_text(encoding="utf-8"))
    fp1 = compute_register_fingerprint(doc)
    assert fp1 == doc["register_fingerprint"]
    # mutating fingerprint field must not change computed hash
    doc["register_fingerprint"] = "0" * 64
    fp2 = compute_register_fingerprint(doc)
    assert fp1 == fp2
    # mutating a rule must change hash
    doc["rules"][0]["exact_name"] = doc["rules"][0]["exact_name"] + " X"
    fp3 = compute_register_fingerprint(doc)
    assert fp3 != fp1


@pytest.mark.unit
def test_yaml_pointer_hashes_match() -> None:
    doc = json.loads(POLICY.read_text(encoding="utf-8"))
    yaml_text = YAML.read_text(encoding="utf-8")
    assert doc["register_fingerprint"] in yaml_text
    file_sha = compute_canonical_json_sha256(POLICY)
    assert file_sha in yaml_text


@pytest.mark.unit
def test_safety_surfaces_are_frozen() -> None:
    doc = json.loads(POLICY.read_text(encoding="utf-8"))
    by_id = {r["parameter_id"]: r for r in doc["rules"]}
    for pid in ("CDB-034", "CDB-035", "CDB-045", "CDB-056"):
        assert by_id[pid]["change_authority"] in {
            "MUST_NOT_OPTIMIZE",
            "GOVERNANCE_ONLY",
            "FORBIDDEN",
        }
    assert by_id["CDB-047"]["change_authority"] == "GOVERNANCE_ONLY"
    assert by_id["CDB-008"]["lifecycle_status"] == "dead"


@pytest.mark.unit
def test_no_ml_rl_surfaces_in_register() -> None:
    text = POLICY.read_text(encoding="utf-8").lower()
    for needle in (
        "machine learning",
        "reinforcement learning",
        "ml_model",
        "rl_agent",
        "neural network",
    ):
        assert needle not in text
