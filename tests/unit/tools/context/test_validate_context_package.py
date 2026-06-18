"""Unit tests for CDB Context Package fail-closed validator.

Covers: PASS, BLOCKED for schema/stop-rule violations,
deterministic report shape, secret value hiding.
#3288
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.context.validate_context_package import (
    validate_package,
    check_secret_indicators,
    check_forbidden_trading_state,
    check_live_echtgeld_claims,
    check_canon_read_evidence,
    check_evidence_refs,
    build_report,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "tools" / "context" / "schemas" / "context_package.schema.json"
VALID_RECORD = {
    "record_id": "rec_001",
    "record_type": "doc_record",
    "repo": "Claire_de_Binare",
    "source_path": "docs/example.md",
    "source_commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492",
    "source_hash": "abc123def456",
    "observed_at": "2026-06-17T12:00:00Z",
    "confidence": "high",
    "supersedes": None,
    "tags": ["example", "test"],
    "summary": "Example test record",
    "evidence_refs": [
        {"ref": "docs/example.md", "source": "repo"}
    ],
}

VALID_PACKAGE = {
    "package": {
        "package_id": "cdb-context-package-2026-06-17-001",
        "package_type": "context_package",
        "created_at": "2026-06-17T12:00:00Z",
        "source_commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492",
        "source_repo": "Claire_de_Binare",
        "records": [VALID_RECORD],
    },
    "meta": {
        "version": "1.0",
        "validator_ref": "tools/context/validate_context_package.py",
        "schema_ref": "tools/context/schemas/context_package.schema.json",
        "safety_boundaries": {
            "lr_status": "NO-GO",
            "board_stage_is_live_go": False,
            "real_money_go": False,
            "productive_db_writes_allowed": False,
            "secrets_in_outputs_allowed": False,
            "trading_state_ingestion_allowed": False,
        },
    },
}


def test_valid_minimal_package_pass() -> None:
    report = validate_package(VALID_PACKAGE)
    assert report["status"] == "PASS"
    assert report["exit_code"] == 0
    assert report["error_count"] == 0


def test_missing_source_hash_blocked() -> None:
    pkg = json.loads(json.dumps(VALID_PACKAGE))
    pkg["package"]["records"][0]["source_hash"] = ""
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    assert report["exit_code"] == 1
    codes = [e["code"] for e in report["errors"]]
    assert "min_length" in codes


def test_unknown_record_type_blocked() -> None:
    pkg = json.loads(json.dumps(VALID_PACKAGE))
    pkg["package"]["records"][0]["record_type"] = "unknown_type"
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    assert report["exit_code"] == 1
    codes = [e["code"] for e in report["errors"]]
    assert "invalid_enum" in codes


def test_secret_indicator_in_summary_blocked() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "summary": "Contains api_key=sk-test and some other text",
    }
    check_secret_indicators(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) >= 1
    assert errors[0]["code"] == "secret_indicator"
    assert "No secret values" in errors[0]["message"]


def test_secret_indicator_in_source_path_blocked() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "source_path": "secrets/REDIS_PASSWORD.txt",
    }
    check_secret_indicators(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) >= 1
    assert errors[0]["code"] == "secret_indicator"
    assert errors[0]["path"].endswith(".source_path")


def test_secret_value_not_in_output() -> None:
    pkg = json.loads(json.dumps(VALID_PACKAGE))
    pkg["package"]["records"][0]["summary"] = "Contains api_key=sk-test-secret-key"
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    report_str = json.dumps(report)
    assert "sk-test-secret-key" not in report_str
    assert "secret_key" not in report_str


def test_orders_fills_positions_blocked() -> None:
    errors: list = []
    for keyword in ["order data", "fill status", "position update", "live-risk-state"]:
        record = {**VALID_RECORD, "summary": f"Contains {keyword}"}
        errs: list = []
        check_forbidden_trading_state(
            {"package": {"records": [record]}}, errs
        )
        assert len(errs) >= 1, f"Should block on '{keyword}'"
        assert "BLOCKED" in errs[0]["message"]


def test_live_claim_without_lr_ssot_blocked() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "live_or_echtgeld_claim": {
            "lr_ssot_ref": "some/other/path.md",
            "claim_type": "lr_status",
        },
    }
    check_live_echtgeld_claims(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) >= 1
    assert errors[0]["code"] == "live_claim_without_lr_ssot"


def test_live_claim_with_valid_lr_ssot_allowed() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "live_or_echtgeld_claim": {
            "lr_ssot_ref": "docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",
            "claim_type": "lr_status",
        },
    }
    check_live_echtgeld_claims(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) == 0


def test_missing_canon_evidence_for_claim_blocked() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "record_type": "claim_record",
    }
    check_canon_read_evidence(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) >= 1
    assert errors[0]["code"] == "missing_canon_evidence"


def test_claim_with_canon_evidence_allowed() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "record_type": "claim_record",
        "canon_read_evidence": [
            {"path": "AGENTS.md", "commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492"}
        ],
    }
    check_canon_read_evidence(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) == 0


def test_non_claim_record_no_canon_evidence_required() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "record_type": "doc_record",
    }
    check_canon_read_evidence(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) == 0


def test_missing_evidence_refs_blocked() -> None:
    errors: list = []
    record = {
        **VALID_RECORD,
        "evidence_refs": [],
    }
    check_evidence_refs(
        {"package": {"records": [record]}}, errors
    )
    assert len(errors) >= 1
    assert errors[0]["code"] == "missing_evidence_refs"


def test_deterministic_report_shape() -> None:
    report_success = build_report([], [], True)
    assert set(report_success.keys()) == {"status", "exit_code", "error_count", "schema_errors", "stop_rule_errors", "errors"}
    assert report_success["status"] == "PASS"
    assert report_success["exit_code"] == 0

    report_fail = build_report(
        [{"path": "$.test", "code": "test_error", "message": "test"}],
        [],
        False,
    )
    assert report_fail["status"] == "BLOCKED"
    assert report_fail["exit_code"] == 1
    assert report_fail["error_count"] == 1


def test_empty_records_allowed() -> None:
    pkg = json.loads(json.dumps(VALID_PACKAGE))
    pkg["package"]["records"] = []
    report = validate_package(pkg)
    assert report["status"] == "PASS"


def test_multiple_valid_records_pass() -> None:
    pkg = json.loads(json.dumps(VALID_PACKAGE))
    record_types = [
        "doc_record", "code_snapshot", "decision_record",
        "evidence_record", "memory_record", "dependency_edge",
        "context_package_ref",
    ]
    pkg["package"]["records"] = []
    for i, rt in enumerate(record_types):
        rec = json.loads(json.dumps(VALID_RECORD))
        rec["record_id"] = f"rec_{i:03d}"
        rec["record_type"] = rt
        pkg["package"]["records"].append(rec)
    report = validate_package(pkg)
    assert report["status"] == "PASS"


@pytest.mark.parametrize("forbidden_type", [
    "order_record", "fill_record", "position_record",
    "risk_state", "live_trade", "echtgeld_order",
])
def test_nonexistent_record_types_blocked_by_schema(forbidden_type: str) -> None:
    pkg = json.loads(json.dumps(VALID_PACKAGE))
    pkg["package"]["records"][0]["record_type"] = forbidden_type
    report = validate_package(pkg)
    assert report["status"] == "BLOCKED"
    codes = [e["code"] for e in report["errors"]]
    assert "invalid_enum" in codes
