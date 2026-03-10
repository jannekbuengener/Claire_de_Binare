"""Tests for core-secrets integrity validation and reporting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.core_secrets_integrity_report import (  # noqa: E402
    REASON_SCHEMA_GAP,
    build_report,
    generate_report,
    main,
)
from core.utils.governance_integrity import (  # noqa: E402
    CORE_SECRETS_INTEGRITY_KEY_ENV,
    REASON_HASH_MISMATCH,
    REASON_KEY_MISSING,
    REASON_VALIDATION_SKIPPED,
    compute_integrity_hash,
    seal_row,
)


def _core_secret_row() -> dict:
    return {
        "secret_name": "binance_api_key",
        "provider_ref": "vault://trading/binance_api_key",
        "fingerprint": "sha256:binance-api-key-v1",
        "created_at": "2026-03-01T12:15:00Z",
    }


def _write_fixture_rows(base_dir: Path, rows: list[dict], file_name: str) -> None:
    (base_dir / file_name).write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class TestCoreSecretsIntegrityHelper:
    def test_compute_integrity_hash_is_deterministic_for_field_order(self):
        key = "test-core-secrets-key"
        left = _core_secret_row()
        right = {
            "created_at": left["created_at"],
            "fingerprint": left["fingerprint"],
            "provider_ref": left["provider_ref"],
            "secret_name": left["secret_name"],
        }

        assert compute_integrity_hash(
            "core_secrets_metadata", left, key=key
        ) == compute_integrity_hash("core_secrets_metadata", right, key=key)


class TestCoreSecretsIntegrityReport:
    def test_build_report_marks_missing_key_as_forced_fail(self):
        row = seal_row("core_secrets_metadata", _core_secret_row(), key="fixture-key")

        report = build_report([row])

        assert report["status"] == "FAIL"
        assert report["reason_code"] == REASON_VALIDATION_SKIPPED
        assert report["entries"][0]["reason_code"] == REASON_KEY_MISSING

    def test_generate_report_supports_logical_alias_input(self, tmp_path):
        key = "test-core-secrets-key"
        row = seal_row("core_secrets", _core_secret_row(), key=key)
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [row], "core_secrets.json")

        out_dir = tmp_path / "out"
        report = generate_report(str(out_dir), input_dir=str(fixtures_dir), key=key)

        assert report["status"] == "PASS"
        assert report["failed_schema_checks"] == 0
        assert report["table"]["storage_table"] == "core_secrets"
        verification_md = (out_dir / "verification.md").read_text(encoding="utf-8")
        assert "`core_secrets`" in verification_md
        assert (
            "| `core_secrets` | `binance_api_key` | OK | `INTEGRITY_OK` |"
            in verification_md
        )

    def test_build_report_supports_service_secrets_storage_alias(self):
        key = "test-core-secrets-key"
        row = seal_row("service_secrets", _core_secret_row(), key=key)

        report = build_report([row], key=key, storage_table="service_secrets")

        assert report["status"] == "PASS"
        assert report["table"]["storage_table"] == "service_secrets"
        assert report["entries"][0]["status"] == "OK"

    def test_build_report_marks_schema_gap_when_fields_are_missing(self):
        key = "test-core-secrets-key"
        row = seal_row("core_secrets_metadata", _core_secret_row(), key=key)
        row.pop("integrity_version")

        report = build_report([row], key=key)

        assert report["status"] == "FAIL"
        assert report["schema_check"]["status"] == "GAP"
        assert report["schema_check"]["reason_code"] == REASON_SCHEMA_GAP

    def test_cli_exit_code_is_nonzero_on_tamper(self, tmp_path, monkeypatch):
        key = "test-core-secrets-key"
        monkeypatch.setenv(CORE_SECRETS_INTEGRITY_KEY_ENV, key)
        row = seal_row("core_secrets_metadata", _core_secret_row(), key=key)
        row["fingerprint"] = "sha256:binance-api-key-v2"
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [row], "core_secrets_metadata.json")

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
