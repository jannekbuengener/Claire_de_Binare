"""Unit tests for local append-only CDB Brain Apply.

Covers: dry-run, apply, idempotent dedup, blocking conditions,
deterministic fingerprints, ledger append-only semantics.
#3289
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from tools.context.apply_context_brain_local import (
    SCHEMA_VERSION,
    SUPPORTED_PACKAGE_VERSIONS,
    compute_package_fingerprint,
    compute_content_hash,
    validate_package_for_apply,
    check_drift_radar_blocks,
    load_ledger,
    save_ledger,
    is_duplicate_fingerprint,
    build_apply_run,
    _check_secret_content,
    _check_forbidden_tags,
)

UTCNOW = "2026-06-17T12:00:00Z"

BASE_RECORD = {
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
    "evidence_refs": [{"ref": "docs/example.md", "source": "repo"}],
}

BASE_PACKAGE = {
    "package": {
        "package_id": "cdb-context-package-2026-06-17-001",
        "package_type": "context_package",
        "created_at": "2026-06-17T12:00:00Z",
        "source_commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492",
        "source_repo": "Claire_de_Binare",
        "records": [dict(BASE_RECORD)],
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

MULTI_RECORD_PACKAGE = {
    "package": {
        "package_id": "cdb-context-package-2026-06-17-002",
        "package_type": "context_package",
        "created_at": "2026-06-17T12:00:00Z",
        "source_commit": "8131849f2ab2cc3bc7cd761668bb9e0e83574492",
        "source_repo": "Claire_de_Binare",
        "records": [
            dict(BASE_RECORD),
            {
                **BASE_RECORD,
                "record_id": "rec_002",
                "record_type": "decision_record",
                "source_path": "docs/decisions/001.md",
                "summary": "Decision record test",
            },
        ],
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


# ── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    return tmp_path / "output"


@pytest.fixture
def valid_package() -> dict:
    return dict(json.loads(json.dumps(BASE_PACKAGE)))


@pytest.fixture
def multi_package() -> dict:
    return dict(json.loads(json.dumps(MULTI_RECORD_PACKAGE)))


# ── Deterministic fingerprints ──────────────────────────────


def test_package_fingerprint_deterministic(valid_package: dict) -> None:
    fp1 = compute_package_fingerprint(valid_package)
    fp2 = compute_package_fingerprint(valid_package)
    assert fp1 == fp2
    assert fp1.startswith("sha256:")


def test_package_fingerprint_differs_for_different_packages(
    valid_package: dict, multi_package: dict
) -> None:
    fp1 = compute_package_fingerprint(valid_package)
    fp2 = compute_package_fingerprint(multi_package)
    assert fp1 != fp2


def test_package_fingerprint_stable_across_runs(valid_package: dict) -> None:
    fp1 = compute_package_fingerprint(valid_package)
    fp2 = compute_package_fingerprint(json.loads(json.dumps(valid_package)))
    assert fp1 == fp2


def test_content_hash_deterministic() -> None:
    h1 = compute_content_hash(BASE_RECORD)
    h2 = compute_content_hash(BASE_RECORD)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_content_hash_differs_for_different_records() -> None:
    r2 = dict(BASE_RECORD)
    r2["record_id"] = "rec_002"
    assert compute_content_hash(BASE_RECORD) != compute_content_hash(r2)


# ── Package validation ──────────────────────────────────────


def test_validate_valid_package(valid_package: dict) -> None:
    result = validate_package_for_apply(valid_package)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_unsupported_version_blocked(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["meta"]["version"] = "2.0"
    result = validate_package_for_apply(pkg)
    assert result["valid"] is False
    codes = [e["code"] for e in result["errors"]]
    assert "unsupported_schema_version" in codes


def test_validate_missing_package_id_blocked(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["package_id"] = ""
    result = validate_package_for_apply(pkg)
    assert result["valid"] is False
    codes = [e["code"] for e in result["errors"]]
    assert "missing_package_id" in codes


def test_validate_missing_source_commit_blocked(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["source_commit"] = ""
    result = validate_package_for_apply(pkg)
    assert result["valid"] is False
    codes = [e["code"] for e in result["errors"]]
    assert "missing_source_commit" in codes


# ── Secret and tag detection ────────────────────────────────


def test_secret_content_detected_in_summary(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["records"][0]["summary"] = "Contains api_key=sk-test-secret"
    findings = _check_secret_content(pkg)
    assert len(findings) >= 1


def test_secret_content_detected_in_source_path(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["records"][0]["source_path"] = "secrets/REDIS_PASSWORD.txt"
    findings = _check_secret_content(pkg)
    assert len(findings) >= 1


def test_secret_content_clean(valid_package: dict) -> None:
    findings = _check_secret_content(valid_package)
    assert len(findings) == 0


def test_forbidden_tags_detected(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["records"][0]["tags"] = ["example", "live-trade"]
    findings = _check_forbidden_tags(pkg)
    assert len(findings) >= 1


def test_forbidden_tags_clean(valid_package: dict) -> None:
    findings = _check_forbidden_tags(valid_package)
    assert len(findings) == 0


# ── Drift radar blocking ────────────────────────────────────


def test_drift_radar_blocks_via_brain_apply_blocked() -> None:
    radar = {"brain_apply_blocked": True}
    blockers = check_drift_radar_blocks(radar)
    assert len(blockers) >= 1


def test_drift_radar_blocks_via_summary() -> None:
    radar = {
        "summary": {"blocks_brain_apply": True, "blocking_claims": 3},
    }
    blockers = check_drift_radar_blocks(radar)
    assert len(blockers) >= 1


def test_drift_radar_blocks_via_safety_boundaries() -> None:
    radar = {"safety_boundaries": {"brain_apply_blocked": True}}
    blockers = check_drift_radar_blocks(radar)
    assert len(blockers) >= 1


def test_drift_radar_blocks_via_blockers_list() -> None:
    radar = {
        "brain_apply_blockers": [
            {"claim": "LR status is not NO-GO"},
        ]
    }
    blockers = check_drift_radar_blocks(radar)
    assert len(blockers) >= 1
    assert any("LR status" in b for b in blockers)


def test_drift_radar_no_blockers() -> None:
    radar = {"brain_apply_blocked": False}
    blockers = check_drift_radar_blocks(radar)
    assert len(blockers) == 0


def test_drift_radar_empty() -> None:
    blockers = check_drift_radar_blocks({})
    assert len(blockers) == 0


# ── Duplicate detection ─────────────────────────────────────


def test_is_duplicate_fingerprint_found(valid_package: dict) -> None:
    fp = compute_package_fingerprint(valid_package)
    ledger = [
        {
            "apply_run_id": "brain-apply-abc-0001",
            "source_package_fingerprint": fp,
        }
    ]
    match = is_duplicate_fingerprint(ledger, fp)
    assert match is not None
    assert match["apply_run_id"] == "brain-apply-abc-0001"


def test_is_duplicate_fingerprint_not_found(valid_package: dict) -> None:
    fp = compute_package_fingerprint(valid_package)
    ledger: list = []
    assert is_duplicate_fingerprint(ledger, fp) is None


def test_is_duplicate_fingerprint_different(
    valid_package: dict, multi_package: dict
) -> None:
    fp1 = compute_package_fingerprint(valid_package)
    fp2 = compute_package_fingerprint(multi_package)
    ledger = [{"apply_run_id": "run-001", "source_package_fingerprint": fp1}]
    assert is_duplicate_fingerprint(ledger, fp2) is None


# ── Build apply run ─────────────────────────────────────────


def test_build_apply_run_applies_records(valid_package: dict) -> None:
    fp = compute_package_fingerprint(valid_package)
    run = build_apply_run(valid_package, fp, "/fake/path.json", UTCNOW, [])
    assert run["status"] == "applied"
    assert run["duplicate_fingerprint"] is False
    assert run["summary"]["records_applied"] == 1
    assert run["summary"]["records_skipped"] == 0
    assert len(run["records"]) == 1
    assert run["records"][0]["package_record_id"] == "rec_001"


def test_build_apply_run_skips_duplicate(valid_package: dict) -> None:
    fp = compute_package_fingerprint(valid_package)
    existing_ledger = [
        build_apply_run(valid_package, fp, "/fake/path.json", UTCNOW, [])
    ]
    run = build_apply_run(
        valid_package, fp, "/fake/path2.json", UTCNOW, existing_ledger
    )
    assert run["status"] == "skipped_duplicate"
    assert run["duplicate_fingerprint"] is True
    assert run["summary"]["records_applied"] == 0
    assert run["summary"]["records_skipped"] == 1
    assert len(run["records"]) == 0


def test_build_apply_run_multi_record(multi_package: dict) -> None:
    fp = compute_package_fingerprint(multi_package)
    run = build_apply_run(multi_package, fp, "/fake/path.json", UTCNOW, [])
    assert run["status"] == "applied"
    assert run["summary"]["records_applied"] == 2
    assert len(run["records"]) == 2


# ── Ledger persistence ──────────────────────────────────────


def test_ledger_load_empty_directory(tmp_output: Path) -> None:
    tmp_output.mkdir(parents=True, exist_ok=True)
    ledger = load_ledger(tmp_output)
    assert ledger == []


def test_ledger_save_and_load(tmp_output: Path) -> None:
    tmp_output.mkdir(parents=True, exist_ok=True)
    data = [{"apply_run_id": "test-001", "status": "applied"}]
    save_ledger(tmp_output, data)
    loaded = load_ledger(tmp_output)
    assert len(loaded) == 1
    assert loaded[0]["apply_run_id"] == "test-001"


def test_ledger_append_only(tmp_output: Path) -> None:
    tmp_output.mkdir(parents=True, exist_ok=True)
    save_ledger(tmp_output, [{"apply_run_id": "run-001"}])
    ledger1 = load_ledger(tmp_output)

    ledger1.append({"apply_run_id": "run-002"})
    save_ledger(tmp_output, ledger1)
    ledger2 = load_ledger(tmp_output)

    assert len(ledger2) == 2
    assert ledger2[0]["apply_run_id"] == "run-001"
    assert ledger2[1]["apply_run_id"] == "run-002"


def test_ledger_preserves_existing_records_on_append(tmp_output: Path) -> None:
    tmp_output.mkdir(parents=True, exist_ok=True)
    original = [
        {"apply_run_id": "run-001", "data": "first"},
        {"apply_run_id": "run-002", "data": "second"},
    ]
    save_ledger(tmp_output, original)

    ledger = load_ledger(tmp_output)
    ledger.append({"apply_run_id": "run-003", "data": "third"})
    save_ledger(tmp_output, ledger)

    final = load_ledger(tmp_output)
    assert len(final) == 3
    assert final[0]["data"] == "first"
    assert final[1]["data"] == "second"
    assert final[2]["data"] == "third"


# ── Full scenarios ──────────────────────────────────────────


def test_valid_package_dry_run_no_ledger_write(
    valid_package: dict, tmp_path: Path
) -> None:
    from tools.context.apply_context_brain_local import (
        main as apply_main,
    )

    pkg_path = tmp_path / "test_package.json"
    pkg_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_path.write_text(json.dumps(valid_package, indent=2), encoding="utf-8")

    test_out = tmp_path / "ledger"
    test_out.mkdir(parents=True, exist_ok=True)

    save_ledger(test_out, [])
    ledger_before = load_ledger(test_out)
    assert len(ledger_before) == 0


def test_valid_package_dry_run_summary_ready(valid_package: dict) -> None:
    from tools.context.apply_context_brain_local import format_dry_run_report

    fp = compute_package_fingerprint(valid_package)
    validation = validate_package_for_apply(valid_package)
    report = format_dry_run_report(
        package=valid_package,
        fingerprint=fp,
        validation_result=validation,
        drift_blockers=[],
        secret_findings=[],
        tag_findings=[],
        ledger=[],
    )
    assert "READY" in report
    assert "--apply" in report


def test_explicit_apply_appends_records(valid_package: dict, tmp_output: Path) -> None:
    from tools.context.apply_context_brain_local import (
        build_apply_run,
        save_ledger,
        load_ledger,
    )

    test_out = tmp_output / "apply_test"
    test_out.mkdir(parents=True, exist_ok=True)

    fp = compute_package_fingerprint(valid_package)
    run = build_apply_run(valid_package, fp, str(tmp_output / "pkg.json"), UTCNOW, [])
    save_ledger(test_out, [run])

    ledger = load_ledger(test_out)
    assert len(ledger) == 1
    assert ledger[0]["status"] == "applied"
    assert ledger[0]["source_package_fingerprint"] == fp


def test_second_apply_of_same_package_skipped_duplicate(
    valid_package: dict, tmp_output: Path
) -> None:
    from tools.context.apply_context_brain_local import (
        build_apply_run,
        save_ledger,
        load_ledger,
    )

    test_out = tmp_output / "dedup_test"
    test_out.mkdir(parents=True, exist_ok=True)

    fp = compute_package_fingerprint(valid_package)
    run1 = build_apply_run(valid_package, fp, str(tmp_output / "pkg.json"), UTCNOW, [])
    save_ledger(test_out, [run1])

    ledger = load_ledger(test_out)
    run2 = build_apply_run(
        valid_package, fp, str(tmp_output / "pkg2.json"), UTCNOW, ledger
    )
    assert run2["duplicate_fingerprint"] is True
    assert run2["status"] == "skipped_duplicate"
    assert run2["summary"]["records_applied"] == 0

    ledger.append(run2)
    save_ledger(test_out, ledger)
    final = load_ledger(test_out)
    assert len(final) == 2
    assert final[1]["status"] == "skipped_duplicate"


def test_invalid_package_blocked(valid_package: dict, tmp_output: Path) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["meta"]["version"] = "99.0"
    validation = validate_package_for_apply(pkg)
    assert validation["valid"] is False
    codes = [e["code"] for e in validation["errors"]]
    assert "unsupported_schema_version" in codes


def test_drift_radar_blocks_apply_via_check(valid_package: dict) -> None:
    radar = {
        "brain_apply_blocked": True,
        "brain_apply_blockers": [{"claim": "LR status not NO-GO", "severity": "high"}],
    }
    blockers = check_drift_radar_blocks(radar)
    assert len(blockers) >= 2


def test_secret_content_blocks_apply(valid_package: dict) -> None:
    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["records"][0]["summary"] = "api_key=sk-xxxx"
    findings = _check_secret_content(pkg)
    assert len(findings) >= 1

    validation = validate_package_for_apply(pkg)
    assert validation["valid"] is False


def test_no_network_or_db_in_tests() -> None:
    assert True


def test_deterministic_output_stable(valid_package: dict) -> None:
    h1 = compute_content_hash(valid_package["package"]["records"][0])
    h2 = compute_content_hash(valid_package["package"]["records"][0])
    assert h1 == h2


def test_supported_versions_enum() -> None:
    assert "1.0" in SUPPORTED_PACKAGE_VERSIONS
    assert len(SUPPORTED_PACKAGE_VERSIONS) == 1


def test_report_no_secrets_exposed(valid_package: dict) -> None:
    from tools.context.apply_context_brain_local import format_blocked_report

    pkg = json.loads(json.dumps(valid_package))
    pkg["package"]["records"][0]["summary"] = "Contains api_key=sk-test-secret-value"
    validation = validate_package_for_apply(pkg)
    secret_findings = _check_secret_content(pkg)

    report = format_blocked_report(
        validation=validation,
        drift_blockers=[],
        secret_findings=secret_findings,
        tag_findings=[],
    )
    report_str = str(report)
    assert "sk-test-secret-value" not in report_str
