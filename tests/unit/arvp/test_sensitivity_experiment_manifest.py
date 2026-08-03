"""Unit/contract tests for sensitivity experiment manifest (#4153).

test_id: tc_sensitivity_manifest_001
test_type: schutz|bauteil
cdb_area: arvp/validation-research
issue_ref: #4153
security_relevant: true
live_relevant: false
profitability_relevant: false
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.arvp_vacation.sensitivity_experiment_manifest import (
    SensitivityManifestError,
    assert_manifest_secret_safe,
    attach_fingerprint,
    fingerprint_manifest,
    load_manifest,
    load_manifest_schema,
    validate_manifest_schema,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "arvp" / "sensitivity"
VALID_MANIFEST = FIXTURE_DIR / "experiment_manifest_valid_v1.json"


@pytest.fixture()
def valid_manifest() -> dict:
    return load_manifest(VALID_MANIFEST)


def test_schema_loads() -> None:
    schema = load_manifest_schema()
    assert schema["properties"]["schema_version"]["const"] == (
        "cdb.sensitivity_experiment_manifest.v1"
    )


def test_valid_fixture_passes_schema(valid_manifest: dict) -> None:
    validate_manifest_schema(valid_manifest)
    assert valid_manifest["executable"] is False
    assert valid_manifest["lr_status"] == "NO-GO"


def test_identical_manifest_identical_fingerprint(valid_manifest: dict) -> None:
    a = fingerprint_manifest(valid_manifest)
    b = fingerprint_manifest(copy.deepcopy(valid_manifest))
    assert a == b
    assert len(a) == 64


def test_key_order_does_not_change_fingerprint(valid_manifest: dict) -> None:
    reordered = json.loads(json.dumps(valid_manifest, sort_keys=False))
    # Force different insertion order
    rebuilt = {
        "executable": reordered["executable"],
        "schema_version": reordered["schema_version"],
        **{
            k: v
            for k, v in reordered.items()
            if k not in {"executable", "schema_version"}
        },
    }
    assert fingerprint_manifest(valid_manifest) == fingerprint_manifest(rebuilt)


def test_semantic_change_changes_fingerprint(valid_manifest: dict) -> None:
    changed = copy.deepcopy(valid_manifest)
    changed["campaign_id"] = "arvp-sensitivity-4153-synth-v1-changed"
    assert fingerprint_manifest(changed) != fingerprint_manifest(valid_manifest)


def test_attach_fingerprint_excludes_self_from_hash(valid_manifest: dict) -> None:
    body = copy.deepcopy(valid_manifest)
    body.pop("manifest_fingerprint", None)
    attached = attach_fingerprint(body)
    assert attached["manifest_fingerprint"] == fingerprint_manifest(body)
    # Re-attaching must be stable
    again = attach_fingerprint(attached)
    assert again["manifest_fingerprint"] == attached["manifest_fingerprint"]


def test_schema_rejects_missing_required_field(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    del bad["parameter_families"]
    with pytest.raises(SensitivityManifestError, match="INVALID_EXPERIMENT_MANIFEST"):
        validate_manifest_schema(bad)


def test_schema_rejects_executable_true(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["executable"] = True
    with pytest.raises(SensitivityManifestError):
        validate_manifest_schema(bad)


def test_secret_fields_rejected(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["baseline"]["api_key"] = "should-not-appear"  # type: ignore[index]
    with pytest.raises(SensitivityManifestError, match="secret"):
        assert_manifest_secret_safe(bad)


def test_local_credential_path_rejected(valid_manifest: dict) -> None:
    bad = copy.deepcopy(valid_manifest)
    bad["dataset_identity"]["path"] = "C:/Users/secret/.cdb/creds"  # type: ignore[index]
    with pytest.raises(SensitivityManifestError, match="secret"):
        assert_manifest_secret_safe(bad)
