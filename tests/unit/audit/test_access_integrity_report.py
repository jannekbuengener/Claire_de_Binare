"""Tests for access-domain integrity validation and reporting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.access_integrity_report import (  # noqa: E402
    REASON_SCHEMA_GAP,
    build_report,
    generate_report,
    main,
)
from core.utils.governance_integrity import (  # noqa: E402
    ACCESS_INTEGRITY_KEY_ENV,
    REASON_HASH_MISMATCH,
    REASON_KEY_MISSING,
    REASON_VALIDATION_SKIPPED,
    compute_integrity_hash,
    seal_row,
)


def _system_config_row() -> dict:
    return {
        "config_key": "risk_limits",
        "config_scope": "global",
        "value_ref": "docs/governance/config/risk_limits.yaml",
        "value_hash": "sha256:risk-limits-v1",
        "source_path": "infrastructure/config/risk_limits.yaml",
        "observed_at": "2026-03-01T12:00:00Z",
    }


def _security_policy_row() -> dict:
    return {
        "policy_id": "access-policy-v1",
        "version_hash": "sha256:policy-v1",
        "docs_path": "docs/security/policies/access-policy.md",
        "observed_at": "2026-03-01T12:05:00Z",
    }


def _write_fixture_rows(
    base_dir: Path, system_rows: list[dict], security_rows: list[dict]
) -> None:
    (base_dir / "system_config.json").write_text(
        json.dumps(system_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (base_dir / "security_policies.json").write_text(
        json.dumps(security_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class TestAccessIntegrityHelper:
    def test_compute_integrity_hash_is_deterministic_for_field_order(self):
        key = "test-access-key"
        left = _system_config_row()
        right = {
            "observed_at": left["observed_at"],
            "source_path": left["source_path"],
            "value_hash": left["value_hash"],
            "value_ref": left["value_ref"],
            "config_scope": left["config_scope"],
            "config_key": left["config_key"],
        }

        assert compute_integrity_hash(
            "system_config", left, key=key
        ) == compute_integrity_hash("system_config", right, key=key)


class TestAccessIntegrityReport:
    def test_build_report_marks_missing_key_as_forced_fail(self):
        row = seal_row("system_config", _system_config_row(), key="fixture-key")

        report = build_report({"system_config": [row], "security_policy_refs": []})

        assert report["status"] == "FAIL"
        assert report["reason_code"] == REASON_VALIDATION_SKIPPED
        assert report["entries"][0]["reason_code"] == REASON_KEY_MISSING

    def test_generate_report_supports_security_policy_alias_input(self, tmp_path):
        key = "test-access-key"
        system_row = seal_row("system_config", _system_config_row(), key=key)
        security_row = seal_row("security_policy_refs", _security_policy_row(), key=key)
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [system_row], [security_row])

        out_dir = tmp_path / "out"
        report = generate_report(str(out_dir), input_dir=str(fixtures_dir), key=key)

        assert report["status"] == "PASS"
        assert report["failed_schema_checks"] == 0
        verification_md = (out_dir / "verification.md").read_text(encoding="utf-8")
        assert "`security_policies`" in verification_md
        assert "`system_config`" in verification_md
        assert (
            "| `security_policies` | `access-policy-v1` | OK | `INTEGRITY_OK` |"
            in verification_md
        )

    def test_build_report_marks_schema_gap_when_fields_are_missing(self):
        key = "test-access-key"
        row = seal_row("security_policy_refs", _security_policy_row(), key=key)
        row.pop("integrity_version")

        report = build_report(
            {"system_config": [], "security_policy_refs": [row]},
            key=key,
        )

        assert report["status"] == "FAIL"
        assert report["schema_checks"]["security_policy_refs"]["status"] == "GAP"
        assert (
            report["schema_checks"]["security_policy_refs"]["reason_code"]
            == REASON_SCHEMA_GAP
        )

    def test_cli_exit_code_is_nonzero_on_tamper(self, tmp_path, monkeypatch):
        key = "test-access-key"
        monkeypatch.setenv(ACCESS_INTEGRITY_KEY_ENV, key)
        system_row = seal_row("system_config", _system_config_row(), key=key)
        system_row["value_hash"] = "sha256:risk-limits-v2"
        security_row = seal_row("security_policy_refs", _security_policy_row(), key=key)
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [system_row], [security_row])

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
