"""Scheduled workflow cadence, noise and collision contract tests (#3851)."""

from __future__ import annotations

import pytest

from tests.unit.scripts import _workflow_contract_helpers as helpers

pytestmark = [pytest.mark.unit, pytest.mark.contract]

KNOWN_CRON_COLLISIONS = {
    "0 8 * * 1": ("weekly_digest.yml", "cdb-context-refresh-report.yml"),
}


def test_p1_scheduled_workflow_files_exist() -> None:
    missing = sorted(
        name
        for name in helpers.P1_SCHEDULED_WORKFLOW_FILES
        if not (helpers.WORKFLOWS_DIR / name).is_file()
    )
    assert missing == []


def test_schedule_map_is_deterministic_and_visible() -> None:
    first = helpers.build_p1_schedule_map()
    second = helpers.build_p1_schedule_map()
    assert first == second
    assert set(first) == helpers.P1_SCHEDULED_WORKFLOW_FILES


@pytest.mark.parametrize(
    "filename,expected_crons",
    [
        ("weekly_digest.yml", ("0 8 * * 1",)),
        (
            "cdb-daily-delta-triage.yml",
            ("20 6 * * 0", "20 6 * * 2", "20 6 * * 3", "20 6 * * 5"),
        ),
        (
            "cdb-weekly-control-hygiene-classifier.yml",
            ("30 7 * * 1", "30 7 * * 4", "30 7 * * 5"),
        ),
        ("cdb-context-refresh-report.yml", ("0 8 * * 1", "0 8 * * 4")),
        ("stale.yml", ("0 0 * * *",)),
        ("python-compat.yml", ("0 0 * * 0",)),
        ("e2e.yml", ("30 6 * * 0",)),
        ("e2e-tests.yml", ("0 6 * * 0",)),
        ("e2e-happy-path.yaml", ("30 5 * * 0",)),
    ],
)
def test_known_schedule_cron_classification(
    filename: str,
    expected_crons: tuple[str, ...],
) -> None:
    entry = helpers.build_schedule_entry(helpers.WORKFLOWS_DIR / filename)
    assert entry.crons == expected_crons


def test_weekly_digest_failure_alert_uses_workflow_run_not_schedule() -> None:
    entry = helpers.build_schedule_entry(
        helpers.WORKFLOWS_DIR / "weekly_digest_failure_alert.yml"
    )
    assert entry.has_schedule is False
    assert entry.has_workflow_run is True
    assert entry.has_workflow_dispatch is True


@pytest.mark.parametrize("filename", sorted(helpers.P1_SCHEDULED_WORKFLOW_FILES))
def test_scheduled_scope_workflows_keep_manual_dispatch_override(filename: str) -> None:
    entry = helpers.build_schedule_entry(helpers.WORKFLOWS_DIR / filename)
    if filename == "weekly_digest_failure_alert.yml":
        assert entry.has_workflow_dispatch is True
        return
    if entry.has_schedule:
        assert entry.has_workflow_dispatch is True


def test_cron_collisions_are_surfaced_as_explicit_findings() -> None:
    schedule_map = helpers.build_p1_schedule_map()
    collisions = helpers.find_cron_collisions(schedule_map)
    assert collisions
    for cron, expected_files in KNOWN_CRON_COLLISIONS.items():
        assert cron in collisions
        for filename in expected_files:
            assert filename in collisions[cron]


def test_weekly_digest_and_context_refresh_share_monday_08_utc_collision() -> None:
    schedule_map = helpers.build_p1_schedule_map()
    collisions = helpers.find_cron_collisions(schedule_map)
    assert "0 8 * * 1" in collisions
    assert "weekly_digest.yml" in collisions["0 8 * * 1"]
    assert "cdb-context-refresh-report.yml" in collisions["0 8 * * 1"]


def test_security_scan_uses_bimonthly_cron_not_weekly_monday() -> None:
    """#4275: security-scan cadence is bimonthly, not weekly Monday."""
    entry = helpers.build_schedule_entry(helpers.WORKFLOWS_DIR / "security-scan.yml")
    assert entry.has_schedule is True
    assert entry.has_workflow_dispatch is True
    assert entry.crons == ("0 2 1 2,4,6,8,10,12 *",)
    assert "0 2 * * 1" not in entry.crons
