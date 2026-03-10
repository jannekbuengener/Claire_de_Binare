"""Tests for governance integrity validation and reporting."""

from __future__ import annotations

import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root / "scripts"))
sys.path.insert(0, str(repo_root))

from audit.governance_integrity_report import (  # noqa: E402
    build_report,
    generate_report,
    main,
)
from core.utils.governance_integrity import (  # noqa: E402
    INTEGRITY_KEY_ENV,
    REASON_HASH_MISMATCH,
    REASON_KEY_MISSING,
    REASON_OK,
    REASON_VALIDATION_SKIPPED,
    seal_row,
    validate_row_integrity,
)


def _audit_trail_row() -> dict:
    return {
        "id": 101,
        "service_name": "governance-api",
        "action_type": "policy.update",
        "actor_id": "alice",
        "payload": {"policy_id": "risk-policy-v1", "approved": True},
        "created_at": "2026-03-01T12:00:00Z",
    }


def _governance_event_row() -> dict:
    return {
        "id": 7,
        "event_type": "evidence.attached",
        "evidence_ref": "docs/governance/evidence/ISSUE-751-audit-integrity-guards.md",
        "created_at": "2026-03-01T12:05:00Z",
    }


def _write_fixture_rows(
    base_dir: Path, audit_rows: list[dict], event_rows: list[dict]
) -> None:
    (base_dir / "audit_trail.json").write_text(
        json.dumps(audit_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (base_dir / "governance_events.json").write_text(
        json.dumps(event_rows, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class TestValidateRowIntegrity:
    def test_valid_row_returns_ok(self):
        key = "test-integrity-key"
        row = seal_row("audit_trail", _audit_trail_row(), key=key)

        result = validate_row_integrity("audit_trail", row, key=key)

        assert result["status"] == "OK"
        assert result["reason_code"] == REASON_OK
        assert result["row_id"] == 101

    def test_tampered_field_without_hash_update_returns_fail(self):
        key = "test-integrity-key"
        row = seal_row("audit_trail", _audit_trail_row(), key=key)
        row["payload"]["approved"] = False

        result = validate_row_integrity("audit_trail", row, key=key)

        assert result["status"] == "FAIL"
        assert result["reason_code"] == REASON_HASH_MISMATCH
        assert result["stored_hash_prefix"] != result["expected_hash_prefix"]

    def test_missing_integrity_key_fails_closed(self, monkeypatch):
        monkeypatch.delenv(INTEGRITY_KEY_ENV, raising=False)
        row = seal_row("governance_events", _governance_event_row(), key="fixture-key")

        result = validate_row_integrity("governance_events", row)

        assert result["status"] == "FAIL"
        assert result["reason_code"] == REASON_KEY_MISSING


class TestGovernanceIntegrityReport:
    def test_build_report_marks_missing_key_as_forced_fail(self):
        row = seal_row("audit_trail", _audit_trail_row(), key="fixture-key")

        report = build_report({"audit_trail": [row], "governance_events": []})

        assert report["status"] == "FAIL"
        assert report["reason_code"] == REASON_VALIDATION_SKIPPED
        assert report["entries"][0]["reason_code"] == REASON_KEY_MISSING

    def test_generate_report_writes_entry_status_for_all_rows(self, tmp_path):
        key = "test-integrity-key"
        audit_row = seal_row("audit_trail", _audit_trail_row(), key=key)
        event_row = seal_row("governance_events", _governance_event_row(), key=key)
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [audit_row], [event_row])

        out_dir = tmp_path / "out"
        report = generate_report(str(out_dir), input_dir=str(fixtures_dir), key=key)

        assert report["status"] == "PASS"
        assert report["total_entries"] == 2
        verification_md = (out_dir / "verification.md").read_text(encoding="utf-8")
        assert "| `audit_trail` | `101` | OK | `INTEGRITY_OK` |" in verification_md
        assert "| `governance_events` | `7` | OK | `INTEGRITY_OK` |" in verification_md

    def test_cli_exit_code_is_nonzero_on_tamper(self, tmp_path, monkeypatch):
        key = "test-integrity-key"
        monkeypatch.setenv(INTEGRITY_KEY_ENV, key)
        audit_row = seal_row("audit_trail", _audit_trail_row(), key=key)
        audit_row["action_type"] = "policy.delete"
        event_row = seal_row("governance_events", _governance_event_row(), key=key)
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        _write_fixture_rows(fixtures_dir, [audit_row], [event_row])

        out_dir = tmp_path / "out"
        exit_code = main(
            [
                "--input-dir",
                str(fixtures_dir),
                "--out-dir",
                str(out_dir),
            ]
        )

        assert exit_code == 1
