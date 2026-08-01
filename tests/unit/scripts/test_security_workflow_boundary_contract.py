"""Security workflow dry-run/live boundary contract tests (#3850)."""

from __future__ import annotations

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_security_workflow_files_exist() -> None:
    missing = sorted(
        name
        for name in helpers.SECURITY_WORKFLOW_FILES
        if not (helpers.WORKFLOWS_DIR / name).is_file()
    )
    assert missing == []


@pytest.mark.parametrize("filename", sorted(helpers.SECURITY_WORKFLOW_FILES))
def test_security_workflows_expose_manual_dispatch(filename: str) -> None:
    row = helpers.build_security_boundary_row(helpers.WORKFLOWS_DIR / filename)
    assert row.has_workflow_dispatch is True


@pytest.mark.parametrize(
    "filename,expected_schedule",
    [
        ("trivy.yml", True),
        ("gitleaks.yml", True),
        ("codeql-python.yml", True),
        ("security-scan.yml", True),
        ("security-alert-readout.yml", True),
    ],
)
def test_security_workflows_declare_schedule_trigger(
    filename: str,
    expected_schedule: bool,
) -> None:
    row = helpers.build_security_boundary_row(helpers.WORKFLOWS_DIR / filename)
    assert row.has_schedule is expected_schedule


@pytest.mark.parametrize(
    "filename,expected_write_permissions",
    [
        ("trivy.yml", ()),
        ("gitleaks.yml", ()),
        ("codeql-python.yml", ()),
        ("security-scan.yml", ()),
        ("security-alert-readout.yml", ("issues:write", "pull-requests:write")),
    ],
)
def test_security_workflow_write_permissions_are_classified(
    filename: str,
    expected_write_permissions: tuple[str, ...],
) -> None:
    row = helpers.build_security_boundary_row(helpers.WORKFLOWS_DIR / filename)
    assert row.write_permissions == expected_write_permissions


def test_security_alert_readout_manual_publish_defaults_to_dry_run() -> None:
    workflow = helpers.load_workflow_yaml(
        helpers.WORKFLOWS_DIR / "security-alert-readout.yml"
    )
    on_triggers = workflow.get("on") or workflow.get(True) or {}
    inputs = (on_triggers.get("workflow_dispatch") or {}).get("inputs") or {}
    publish_mode = inputs.get("publish_mode") or {}
    issue_live = inputs.get("issue_automation_live") or {}
    assert str(publish_mode.get("default")).lower() == "dry_run"
    assert str(issue_live.get("default")).lower() == "false"


def test_gitleaks_does_not_upload_raw_secret_scan_artifacts() -> None:
    row = helpers.build_security_boundary_row(helpers.WORKFLOWS_DIR / "gitleaks.yml")
    assert row.forbids_secret_artifact_upload is True
    content = (helpers.WORKFLOWS_DIR / "gitleaks.yml").read_text(encoding="utf-8")
    assert "upload-sarif" in content.lower() or "upload sarif" in content.lower()


def test_security_scan_uses_summary_artifacts_not_secret_payloads() -> None:
    content = (helpers.WORKFLOWS_DIR / "security-scan.yml").read_text(encoding="utf-8")
    assert "TRIVY_SUMMARY_MAX" in content
    assert "secrets.json" not in content


def test_security_scan_bimonthly_trigger_contract() -> None:
    """#4275: no push/PR noise; bimonthly schedule + manual dispatch only."""
    path = helpers.WORKFLOWS_DIR / "security-scan.yml"
    row = helpers.build_security_boundary_row(path)
    schedule = helpers.build_schedule_entry(path)
    assert row.has_workflow_dispatch is True
    assert row.has_schedule is True
    assert "push" not in row.triggers
    assert "pull_request" not in row.triggers
    assert set(row.triggers) == {"schedule", "workflow_dispatch"}
    assert schedule.crons == ("0 2 1 2,4,6,8,10,12 *",)


def test_security_alert_readout_scheduled_vs_manual_boundary_is_documented() -> None:
    content = (
        helpers.WORKFLOWS_DIR / "security-alert-readout.yml"
    ).read_text(encoding="utf-8")
    assert 'LIVE_MODE="true"' in content
    assert 'if [[ "${GITHUB_EVENT_NAME}" == "workflow_dispatch" ]]; then' in content
