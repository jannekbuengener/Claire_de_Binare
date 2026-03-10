"""Tests for deployment-domain integrity validation and reporting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.deployment_integrity_report import (  # noqa: E402
    REASON_SCHEMA_GAP,
    build_report,
    generate_report,
    main,
)
from core.utils.governance_integrity import (  # noqa: E402
    DEPLOYMENT_INTEGRITY_KEY_ENV,
    REASON_HASH_MISMATCH,
    REASON_KEY_MISSING,
    REASON_VALIDATION_SKIPPED,
    compute_integrity_hash,
    seal_row,
)


def _deployment_row() -> dict:
    return {
        "pr_id": "911",
        "commit_sha": "a" * 40,
        "yaml_evidence_path": "governance/DELIVERY_APPROVED.yaml",
        "created_at": "2026-03-01T12:10:00Z",
    }


def _write_fixture_rows(
    base_dir: Path, rows: list[dict], *, alias: bool = False
) -> None:
    file_name = (
        "deployment_approvals.json" if alias else "deployment_approvals_mirror.json"
    )
    (base_dir / file_name).write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class TestDeploymentIntegrityHelper:
    def test_compute_integrity_hash_is_deterministic_for_field_order(self):
        key = "test-deployment-key"
        left = _deployment_row()
        right = {
            "created_at": left["created_at"],
            "yaml_evidence_path": left["yaml_evidence_path"],
            "commit_sha": left["commit_sha"],
            "pr_id": left["pr_id"],
        }

        assert compute_integrity_hash(
            "deployment_approvals_mirror", left, key=key
        ) == compute_integrity_hash("deployment_approvals_mirror", right, key=key)


class TestDeploymentIntegrityReport:
    def test_build_report_marks_missing_key_as_forced_fail(self):
        row = seal_row(
            "deployment_approvals_mirror",
            _deployment_row(),
            key="fixture-key",
        )

        report = build_report([row])

        assert report["status"] == "FAIL"
        assert report["reason_code"] == REASON_VALIDATION_SKIPPED
        assert report["entries"][0]["reason_code"] == REASON_KEY_MISSING

    def test_generate_report_supports_logical_alias_input(self, tmp_path):
        key = "test-deployment-key"
        row = seal_row("deployment_approvals_mirror", _deployment_row(), key=key)
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [row], alias=True)

        out_dir = tmp_path / "out"
        report = generate_report(str(out_dir), input_dir=str(fixtures_dir), key=key)

        assert report["status"] == "PASS"
        assert report["failed_schema_checks"] == 0
        verification_md = (out_dir / "verification.md").read_text(encoding="utf-8")
        assert "`deployment_approvals`" in verification_md
        assert "`deployment_approvals_mirror`" in verification_md
        assert (
            "| `deployment_approvals` | `911:"
            + ("a" * 40)
            + "` | OK | `INTEGRITY_OK` |"
            in verification_md
        )

    def test_build_report_marks_schema_gap_when_fields_are_missing(self):
        key = "test-deployment-key"
        row = seal_row("deployment_approvals_mirror", _deployment_row(), key=key)
        row.pop("integrity_version")

        report = build_report([row], key=key)

        assert report["status"] == "FAIL"
        assert report["schema_check"]["status"] == "GAP"
        assert report["schema_check"]["reason_code"] == REASON_SCHEMA_GAP

    def test_cli_exit_code_is_nonzero_on_tamper(self, tmp_path, monkeypatch):
        key = "test-deployment-key"
        monkeypatch.setenv(DEPLOYMENT_INTEGRITY_KEY_ENV, key)
        row = seal_row("deployment_approvals_mirror", _deployment_row(), key=key)
        row["yaml_evidence_path"] = "governance/DELIVERY_APPROVED_v2.yaml"
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [row])

        out_dir = tmp_path / "out"
        exit_code = main(
            [
                "--input-dir",
                str(fixtures_dir),
                "--out-dir",
                str(out_dir),
            ]
        )
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))

        assert exit_code == 1
        assert report["status"] == "FAIL"
        assert report["entries"][0]["reason_code"] == REASON_HASH_MISMATCH
