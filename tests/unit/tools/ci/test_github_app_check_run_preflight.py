"""Unit tests for tools.ci.github_app_check_run_preflight (#4170 Phase B)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ci.github_app_check_run_preflight import (
    REASON_APP_MISSING,
    REASON_CHECKS_WRITE_MISSING,
    REASON_CHECK_RUN_MISSING,
    REASON_COMMIT_STATUS_NOT_APP_BOUND,
    REASON_INSTALLATION_MISSING,
    REASON_READY,
    VERDICT_NOT_READY,
    VERDICT_READY,
    evaluate_preflight,
    is_app_bound_check_run,
    is_app_bound_commit_status,
    redact_mapping,
    redact_text,
)

pytestmark = pytest.mark.unit


def _ready_evidence(**overrides: object) -> dict:
    base: dict = {
        "app": {
            "id": 424242,
            "permissions": {
                "checks": "write",
                "metadata": "read",
            },
        },
        "installation": {
            "id": 999001,
            "repository": "jannekbuengener/Claire_de_Binare",
        },
        "check_runs": [
            {
                "name": "cdb-local-ci-app-preview",
                "head_sha": "abc123",
                "conclusion": "success",
                "app": {"id": 424242},
            }
        ],
        "commit_statuses": [
            {
                "context": "cdb-local-ci",
                "state": "success",
                "app_id": None,
            }
        ],
    }
    base.update(overrides)
    return base


def test_app_missing_not_ready():
    evidence = _ready_evidence()
    evidence["app"] = {"permissions": {"checks": "write", "metadata": "read"}}
    result = evaluate_preflight(evidence)
    assert result.verdict == VERDICT_NOT_READY
    assert result.ready is False
    assert REASON_APP_MISSING in result.reasons


def test_checks_write_missing_not_ready():
    evidence = _ready_evidence()
    evidence["app"] = {
        "id": 424242,
        "permissions": {"checks": "read", "metadata": "read"},
    }
    result = evaluate_preflight(evidence)
    assert result.verdict == VERDICT_NOT_READY
    assert REASON_CHECKS_WRITE_MISSING in result.reasons


def test_installation_missing_not_ready():
    evidence = _ready_evidence()
    evidence["installation"] = {}
    result = evaluate_preflight(evidence)
    assert result.verdict == VERDICT_NOT_READY
    assert REASON_INSTALLATION_MISSING in result.reasons


def test_app_bound_check_run_ready_for_operator_smoke():
    result = evaluate_preflight(_ready_evidence())
    assert result.verdict == VERDICT_READY
    assert result.ready is True
    assert REASON_READY in result.reasons
    assert "cdb-local-ci-app-preview" in result.app_bound_check_run_names


def test_commit_status_app_id_null_not_app_bound():
    status = {"context": "cdb-local-ci", "state": "success", "app_id": None}
    assert is_app_bound_commit_status(status) is False

    result = evaluate_preflight(_ready_evidence())
    assert REASON_COMMIT_STATUS_NOT_APP_BOUND in result.reasons
    # Ready still allowed because App-bound Check Run evidence is present.
    assert result.ready is True

    # Without Check Run, Commit Status alone must not unlock READY.
    evidence = _ready_evidence(check_runs=[])
    blocked = evaluate_preflight(evidence)
    assert blocked.ready is False
    assert REASON_CHECK_RUN_MISSING in blocked.reasons
    assert (
        is_app_bound_check_run(
            {"name": "cdb-local-ci", "app_id": None}, expected_app_id=424242
        )
        is False
    )


def test_secrets_are_redacted():
    text = (
        "Authorization: Bearer ghp_abcdefghijklmnopqrstuvwxyz012345 "
        "and token=github_pat_ABCDEFGH12345678 and "
        "-----BEGIN PRIVATE KEY-----\nSECRET\n-----END PRIVATE KEY-----"
    )
    redacted = redact_text(text)
    assert "ghp_" not in redacted
    assert "github_pat_" not in redacted
    assert "SECRET" not in redacted
    assert "[REDACTED]" in redacted
    assert "[REDACTED_PRIVATE_KEY]" in redacted

    payload = {
        "token": "ghp_abcdefghijklmnopqrstuvwxyz012345",
        "nested": {
            "private_key": "-----BEGIN PRIVATE KEY-----\nx\n-----END PRIVATE KEY-----"
        },
        "safe": "app_id=424242",
    }
    cleaned = redact_mapping(payload)
    assert cleaned["token"] == "[REDACTED]"
    assert cleaned["nested"]["private_key"] == "[REDACTED]"
    assert cleaned["safe"] == "app_id=424242"

    result = evaluate_preflight(
        _ready_evidence(leak={"access_token": "ghs_abcdefghijklmnopqrstuvwxyz012345"})
    )
    dumped = json.dumps(result.to_dict())
    assert "ghs_" not in dumped


def test_prohibited_permissions_block_ready():
    evidence = _ready_evidence()
    evidence["app"]["permissions"]["administration"] = "write"
    result = evaluate_preflight(evidence)
    assert result.ready is False
    assert result.verdict == VERDICT_NOT_READY


def test_ambiguous_check_run_app_ids_not_ready():
    evidence = _ready_evidence(
        check_runs=[
            {"name": "cdb-local-ci-app-preview", "app": {"id": 424242}},
            {"name": "cdb-local-ci-app-preview", "app": {"id": 111111}},
        ]
    )
    result = evaluate_preflight(evidence)
    assert result.ready is False
    assert result.verdict == VERDICT_NOT_READY


def test_cli_main_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    from tools.ci.github_app_check_run_preflight import main

    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(_ready_evidence()), encoding="utf-8")
    code = main(["--evidence-file", str(path), "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == VERDICT_READY
