"""
tests/test_control_plane.py

CI integration for the .github control-plane manifest validator.
Calls control_plane_validate.py as a subprocess so that the validator's
full path-resolution and real-YAML cross-checking logic runs unmodified.

This file is discovered by pytest via standard test discovery and is
therefore wired into ci.yml automatically (pytest runs all tests/ files).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / ".github" / "scripts" / "control_plane_validate.py"
COLLECTION_DIR = REPO_ROOT / ".github" / "control-plane" / "src"
GENERATED_DIR = REPO_ROOT / ".github" / "control-plane" / "generated"


def _run_validator(*extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--repo-root", str(REPO_ROOT)] + list(extra_args),
        capture_output=True,
        text=True,
    )


@pytest.mark.unit
def test_validator_script_exists():
    assert VALIDATOR.exists(), f"Validator not found: {VALIDATOR}"


@pytest.mark.unit
def test_collection_dir_exists():
    assert COLLECTION_DIR.exists(), f"Collection dir not found: {COLLECTION_DIR}"


@pytest.mark.unit
def test_all_units_pass_validation():
    """All manifest units must pass validator with exit code 0."""
    result = _run_validator()
    assert result.returncode == 0, (
        f"Validator FAIL (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "unit_id",
    [
        "cdb-control-followup-classifier",
        "cdb-post-merge-followup-scanner",
        "cdb-daily-delta-triage",
    ],
)
def test_unit_passes_validation(unit_id: str):
    """Each named unit must pass single-unit validation."""
    result = _run_validator("--unit-id", unit_id)
    assert result.returncode == 0, (
        f"Unit {unit_id!r} FAIL (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "unit_id",
    [
        "cdb-control-followup-classifier",
        "cdb-post-merge-followup-scanner",
        "cdb-daily-delta-triage",
    ],
)
def test_unit_manifest_has_required_fields(unit_id: str):
    """Quick sanity: each manifest.yaml has the expected top-level keys."""
    import yaml  # type: ignore[import]

    manifest_path = COLLECTION_DIR / unit_id / "manifest.yaml"
    assert manifest_path.exists(), f"manifest.yaml not found for {unit_id}"

    with manifest_path.open() as fh:
        m = yaml.safe_load(fh)

    required = {"id", "kind", "status", "workflow", "purpose", "control", "discovery", "tests"}
    missing = required - set(m.keys())
    assert not missing, f"[{unit_id}] manifest.yaml missing fields: {missing}"
    assert m["id"] == unit_id, f"manifest id {m['id']!r} does not match dir name {unit_id!r}"


@pytest.mark.unit
def test_generate_produces_valid_register(tmp_path: Path):
    """--generate must produce a parseable JSON register with correct structure."""
    output = tmp_path / "workflow-register.json"
    result = _run_validator("--generate", "--output", str(output))
    assert result.returncode == 0, (
        f"Validator --generate FAIL:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert output.exists(), "workflow-register.json was not produced"

    with output.open() as fh:
        register = json.load(fh)

    assert register.get("schema_version") == "1"
    assert register.get("coverage") == "partial"
    assert register.get("generated_from") == "manifests"
    assert isinstance(register.get("units"), list)
    assert register.get("unit_count") == len(register["units"])
    assert register["unit_count"] >= 3

    ids = [u["id"] for u in register["units"]]
    assert "cdb-control-followup-classifier" in ids
    assert "cdb-post-merge-followup-scanner" in ids
    assert "cdb-daily-delta-triage" in ids

    # Units must be sorted by id for determinism
    assert ids == sorted(ids), f"Register units not sorted by id: {ids}"


@pytest.mark.unit
def test_register_no_duplicate_ids(tmp_path: Path):
    """Generated register must have no duplicate unit ids."""
    output = tmp_path / "workflow-register.json"
    result = _run_validator("--generate", "--output", str(output))
    assert result.returncode == 0

    with output.open() as fh:
        register = json.load(fh)

    ids = [u["id"] for u in register["units"]]
    assert len(ids) == len(set(ids)), f"Duplicate ids in register: {ids}"
