"""Tests for build_shadow_evidence_package.py canonical shadow package logic."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from build_shadow_evidence_package import (
    build_shadow_evidence_package,
    validate_shadow_evidence_package,
)


def _write_evidence(
    tmp_path: Path,
    *,
    gate_status: str = "PASS",
    verdict: str = "PASS",
    omit: tuple[str, ...] = (),
) -> Path:
    evidence_dir = tmp_path / "evidence"
    endpoints_dir = evidence_dir / "endpoints"
    endpoints_dir.mkdir(parents=True)

    files = {
        "run_summary.json": {
            "run_id": "12345",
            "run_url": "https://github.com/owner/repo/actions/runs/12345",
            "ref": "refs/heads/main",
            "commit": "abc123def456",
            "mode": "full",
            "soak_minutes": 30,
            "gate_status": gate_status,
            "ended_at": "2026-03-09T12:00:00Z",
        },
        "shadow_block_probe.json": {
            "probe_order_id": "ci-shadow-probe-12345",
            "order_result_found": True,
            "order_result_source": "pubsub",
            "order_result": {"status": "REJECTED", "filled_quantity": 0.0},
        },
        "soak_gate_eval.json": {"verdict": verdict},
        "evidence_index.json": {
            "shadow_blocked_total": 1,
            "orders_filled": 0,
            "orders_approved": 0,
            "has_live_data": True,
            "risk_blocked_all": True,
            "trading_mode": "mock",
        },
        "endpoints/execution_metrics.txt": "execution_shadow_blocked_total 1\nexecution_orders_filled_total 0\n",
        "endpoints/risk_metrics.txt": "signals_received_total 12\norders_blocked_total 12\n",
        "endpoints/execution_status.json": {
            "mode": "mock",
            "service": "execution_service",
        },
        "endpoints/risk_status.json": {
            "risk_state": {"circuit_breaker": False, "total_exposure": 0.0},
            "status": "running",
        },
        "run_summary.md": "# Summary\n",
    }

    for relative_path, content in files.items():
        if relative_path in omit:
            continue
        path = evidence_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            path.write_text(json.dumps(content), encoding="utf-8")
        else:
            path.write_text(content, encoding="utf-8")

    return evidence_dir


def test_build_shadow_evidence_package_creates_canonical_copy(tmp_path: Path) -> None:
    evidence_dir = _write_evidence(tmp_path)

    manifest = build_shadow_evidence_package(evidence_dir)

    package_root = evidence_dir / manifest["canonical_package_root"]
    assert manifest["package_status"] == "PASS"
    assert manifest["package_id"] == "shadow-soak-12345-abc123def456-full"
    assert (evidence_dir / "package_manifest.json").is_file()
    assert (package_root / "manifest.json").is_file()
    assert (package_root / "run_summary.json").is_file()
    assert (package_root / "shadow_block_probe.json").is_file()
    assert (package_root / "endpoints" / "execution_metrics.txt").is_file()
    assert (package_root / "endpoints" / "execution_status.json").is_file()
    assert (package_root / "endpoints" / "risk_status.json").is_file()
    # Evidence summary carries hardened fields
    summary = manifest["evidence_summary"]
    assert summary["trading_mode"] == "mock"
    assert summary["has_live_data"] is True
    assert summary["risk_blocked_all"] is True
    assert summary["orders_approved"] == 0


def test_build_shadow_evidence_package_requires_pass_statuses(tmp_path: Path) -> None:
    evidence_dir = _write_evidence(tmp_path, gate_status="FAIL")
    with pytest.raises(ValueError, match="gate_status must be PASS"):
        build_shadow_evidence_package(evidence_dir)

    evidence_dir = _write_evidence(tmp_path / "other", verdict="FAIL")
    with pytest.raises(ValueError, match="soak_gate_eval verdict must be PASS"):
        build_shadow_evidence_package(evidence_dir)


def test_build_shadow_evidence_package_requires_required_files(tmp_path: Path) -> None:
    evidence_dir = _write_evidence(tmp_path, omit=("shadow_block_probe.json",))
    with pytest.raises(ValueError, match="required package files missing"):
        build_shadow_evidence_package(evidence_dir)


def test_build_fails_on_missing_execution_status(tmp_path: Path) -> None:
    evidence_dir = _write_evidence(tmp_path, omit=("endpoints/execution_status.json",))
    with pytest.raises(ValueError, match="required package files missing"):
        build_shadow_evidence_package(evidence_dir)


def test_build_fails_on_missing_risk_status(tmp_path: Path) -> None:
    evidence_dir = _write_evidence(tmp_path, omit=("endpoints/risk_status.json",))
    with pytest.raises(ValueError, match="required package files missing"):
        build_shadow_evidence_package(evidence_dir)


def test_validate_shadow_evidence_package_detects_tampering(tmp_path: Path) -> None:
    evidence_dir = _write_evidence(tmp_path)
    manifest = build_shadow_evidence_package(evidence_dir)
    package_root = evidence_dir / manifest["canonical_package_root"]
    (package_root / "run_summary.json").write_text("{}", encoding="utf-8")

    validation = validate_shadow_evidence_package(package_root)

    assert validation["valid"] is False
    assert "run_summary.json" in validation["checksum_mismatches"]


def test_validate_shadow_evidence_package_passes_for_clean_package(
    tmp_path: Path,
) -> None:
    evidence_dir = _write_evidence(tmp_path)
    manifest = build_shadow_evidence_package(evidence_dir)

    validation = validate_shadow_evidence_package(
        evidence_dir / manifest["canonical_package_root"]
    )

    assert validation["valid"] is True
    assert validation["missing_files"] == []
    assert validation["checksum_mismatches"] == []
