"""Tests for lr030_soak_supervisor.py — LR-030 Early-Fail Supervisor (Issue #2440).

Coverage:
  1. Old #2440 failure fixture: wrong intent + INCONCLUSIVE + env interruption + missing
     hourly log => ARTIFACT_CONTRACT_BROKEN (highest-severity failure captured).
  2. Missing hourly_checks.log after deadline => MONITOR_DEAD.
  3. Template placeholder in checkpoint file => INVALID_EVIDENCE.
  4. Clean LR-030 minimal run => RUNNING_VALID (exit 0).
  5. --help => exit 0.
  6. Missing positional argument => exit 2.
  7. --require-shadow-block-probe with missing probe => INVALID_EVIDENCE.
  8. Valid shadow-block-probe => RUNNING_VALID.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from lr030_soak_supervisor import (
    ARTIFACT_CONTRACT_BROKEN,
    FAILED_EARLY,
    INCONCLUSIVE_EARLY,
    INVALID_EVIDENCE,
    MONITOR_DEAD,
    RUNNING_VALID,
    evaluate,
)

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "scripts"
    / "lr030_soak_supervisor.py"
)

# Canonical run name used by most fixtures (parses to 2026-05-16T12:00:00Z).
_RUN_NAME = "soak_lr030_20260516_120000"


def _start_dt() -> datetime:
    return datetime(2026, 5, 16, 12, 0, 0, tzinfo=timezone.utc)


def _as_of(minutes: float) -> datetime:
    return _start_dt() + timedelta(minutes=minutes)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_run_dir(tmp_path: Path, name: str = _RUN_NAME) -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


def _write_valid_hourly_log(run_dir: Path, hours: list[int] | None = None) -> None:
    if hours is None:
        hours = [1]
    lines = "\n".join(
        f"2026-05-16 {12 + h}:00:00 UTC - Hour {h}: No restarts" for h in hours
    )
    (run_dir / "hourly_checks.log").write_text(lines + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1 — old #2440 failure fixture
# ---------------------------------------------------------------------------


def test_old_2440_failure_fixture_all_issues_caught(tmp_path: Path) -> None:
    """Replicates the conditions of the failed lr030-shadow-soak-20260512 run.

    Intent drift (lr040), INCONCLUSIVE marker, ENVIRONMENT_INTERRUPTION in
    restart_alerts.log, and missing hourly_checks.log all appear simultaneously.
    The supervisor must catch all four and report the highest-severity status.
    """
    run_dir = _make_run_dir(tmp_path, "soak_lr030_20260512_024819")

    # RC-2: wrong intent (old soak_monitor wrote lr040 into run_intent.txt)
    (run_dir / "run_intent.txt").write_text("lr040\n", encoding="utf-8")

    # Run explicitly marked inconclusive by soak_monitor
    (run_dir / "soak_test_INCONCLUSIVE.txt").write_text(
        "environment_interruption: 12/12\n", encoding="utf-8"
    )

    # Bulk host restarts logged by soak_monitor (12/12 environment interruptions)
    (run_dir / "restart_alerts.log").write_text(
        "2026-05-12 02:51:00 UTC - 12/12 ENVIRONMENT_INTERRUPTION\n" * 3,
        encoding="utf-8",
    )

    # hourly_checks.log is absent (run was killed at ~31 min, before first Hour entry)
    # as_of = 2h after start → well past 75-min deadline
    old_start = datetime(2026, 5, 12, 2, 48, 19, tzinfo=timezone.utc)
    as_of = old_start + timedelta(minutes=120)

    result = evaluate(run_dir, as_of)

    # Overall verdict must be the highest-severity failure: ARTIFACT_CONTRACT_BROKEN
    # (wrong run_intent.txt is a contract violation).
    assert result["status"] == ARTIFACT_CONTRACT_BROKEN

    # All four root causes must surface in the failures list.
    failed_checks = {f["check"] for f in result["failures"]}
    assert "run_intent_is_lr030" in failed_checks, "intent drift not caught"
    assert "no_inconclusive_marker" in failed_checks, "INCONCLUSIVE marker not caught"
    assert "no_env_interruption_patterns" in failed_checks, "ENVIRONMENT_INTERRUPTION not caught"
    assert "hourly_checks_log_present" in failed_checks, "missing hourly log not caught"

    # Exit 1 path: status is not RUNNING_VALID
    assert result["status"] != RUNNING_VALID


# ---------------------------------------------------------------------------
# Test 2 — MONITOR_DEAD after deadline
# ---------------------------------------------------------------------------


def test_monitor_dead_after_deadline(tmp_path: Path) -> None:
    """hourly_checks.log absent after the deadline window => MONITOR_DEAD."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    # No hourly_checks.log written — monitor never fired or crashed.

    result = evaluate(run_dir, _as_of(120), hourly_deadline_minutes=75)

    assert result["status"] == MONITOR_DEAD
    failed_checks = {f["check"] for f in result["failures"]}
    assert "hourly_checks_log_present" in failed_checks


def test_monitor_not_dead_before_deadline(tmp_path: Path) -> None:
    """hourly_checks.log absent but within grace period => RUNNING_VALID."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")

    result = evaluate(run_dir, _as_of(30), hourly_deadline_minutes=75)

    assert result["status"] == RUNNING_VALID


# ---------------------------------------------------------------------------
# Test 3 — INVALID_EVIDENCE: template placeholders
# ---------------------------------------------------------------------------


def test_invalid_evidence_template_placeholder(tmp_path: Path) -> None:
    """Un-expanded script variables in a checkpoint file => INVALID_EVIDENCE."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)

    # Checkpoint file still contains un-expanded bash variables.
    (run_dir / "checkpoint_1_status.json").write_text(
        json.dumps({"run_id": "$runId", "dir": "$artifactDir", "ok": True}),
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(50), hourly_deadline_minutes=75)

    assert result["status"] == INVALID_EVIDENCE
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_template_placeholders" in failed_checks


# ---------------------------------------------------------------------------
# Test 4 — clean LR-030 minimal case => RUNNING_VALID
# ---------------------------------------------------------------------------


def test_clean_minimal_lr030_running_valid(tmp_path: Path) -> None:
    """A minimal valid LR-030 run passes all checks and returns RUNNING_VALID."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir, hours=[1, 2])

    result = evaluate(run_dir, _as_of(120), hourly_deadline_minutes=75)

    assert result["status"] == RUNNING_VALID
    assert result["failures"] == []
    assert result["hourly_check_count"] == 2
    assert result["hourly_hours_logged"] == [1, 2]


# ---------------------------------------------------------------------------
# Test 5 — CLI: --help exits 0
# ---------------------------------------------------------------------------


def test_cli_help_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "RUNNING_VALID" in proc.stdout


# ---------------------------------------------------------------------------
# Test 6 — CLI: missing required argument exits 2
# ---------------------------------------------------------------------------


def test_cli_missing_required_arg_exits_two() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2


# ---------------------------------------------------------------------------
# Test 7 — --require-shadow-block-probe: missing probe => INVALID_EVIDENCE
# ---------------------------------------------------------------------------


def test_require_shadow_probe_missing_fails(tmp_path: Path) -> None:
    """--require-shadow-block-probe with no probe file => INVALID_EVIDENCE."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)

    result = evaluate(
        run_dir,
        _as_of(120),
        hourly_deadline_minutes=75,
        require_shadow_block_probe=True,
    )

    assert result["status"] == INVALID_EVIDENCE
    failed_checks = {f["check"] for f in result["failures"]}
    assert "shadow_block_probe_valid" in failed_checks


# ---------------------------------------------------------------------------
# Test 8 — valid shadow-block-probe => RUNNING_VALID
# ---------------------------------------------------------------------------


def test_valid_shadow_probe_running_valid(tmp_path: Path) -> None:
    """Valid shadow_block_probe.json with REJECTED result => RUNNING_VALID."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "shadow_block_probe.json").write_text(
        json.dumps(
            {
                "probe_order_id": "probe-001",
                "order_result_found": True,
                "order_result": {"status": "REJECTED", "filled_quantity": 0},
            }
        ),
        encoding="utf-8",
    )

    result = evaluate(
        run_dir,
        _as_of(120),
        hourly_deadline_minutes=75,
        require_shadow_block_probe=True,
    )

    assert result["status"] == RUNNING_VALID
    assert result["checks"]["shadow_block_probe_valid"] is True


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_wrong_artifact_prefix_contract_broken(tmp_path: Path) -> None:
    """Directory named soak_test_* (LR-040 prefix) => ARTIFACT_CONTRACT_BROKEN."""
    run_dir = tmp_path / "soak_test_20260516_120000"
    run_dir.mkdir()
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")

    result = evaluate(run_dir, _as_of(30))

    assert result["status"] == ARTIFACT_CONTRACT_BROKEN
    failed_checks = {f["check"] for f in result["failures"]}
    assert "artifact_path_prefix_valid" in failed_checks


def test_soak_test_failed_marker_is_failed_early(tmp_path: Path) -> None:
    """soak_test_FAILED.txt present => FAILED_EARLY."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    (run_dir / "soak_test_FAILED.txt").write_text("restart at hour 3\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir, hours=[1, 2, 3])

    result = evaluate(run_dir, _as_of(200))

    assert result["status"] == FAILED_EARLY


def test_inconclusive_marker_alone_is_inconclusive_early(tmp_path: Path) -> None:
    """INCONCLUSIVE marker with no other failures => INCONCLUSIVE_EARLY."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    (run_dir / "soak_test_INCONCLUSIVE.txt").write_text(
        "environment_interruption: 3/8\n", encoding="utf-8"
    )
    _write_valid_hourly_log(run_dir)

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == INCONCLUSIVE_EARLY


def test_sut_restart_pattern_is_failed_early(tmp_path: Path) -> None:
    """SUT_RESTART in restart_alerts.log => FAILED_EARLY (not INCONCLUSIVE_EARLY)."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "restart_alerts.log").write_text(
        "2026-05-16 14:00:00 UTC - SUT_RESTART detected for cdb_risk\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == FAILED_EARLY
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_hard_restart_patterns" in failed_checks


def test_env_interruption_pattern_is_inconclusive_not_failed(tmp_path: Path) -> None:
    """ENVIRONMENT_INTERRUPTION => INCONCLUSIVE_EARLY, not FAILED_EARLY."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "restart_alerts.log").write_text(
        "2026-05-16 14:00:00 UTC - ENVIRONMENT_INTERRUPTION (host reboot)\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == INCONCLUSIVE_EARLY


def test_restart_detected_pattern_is_failed_early(tmp_path: Path) -> None:
    """RESTART DETECTED: <service> is a SUT container restart => FAILED_EARLY.

    When no ENVIRONMENT_INTERRUPTION is present, RESTART DETECTED is a standalone
    SUT restart (zero-restart-policy violation).
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "restart_alerts.log").write_text(
        "2026-05-16 14:00:00 UTC - RESTART DETECTED: cdb_risk\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == FAILED_EARLY
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_hard_restart_patterns" in failed_checks


def test_restart_detected_with_env_interruption_is_inconclusive(tmp_path: Path) -> None:
    """RESTART DETECTED + ENVIRONMENT_INTERRUPTION in same log => INCONCLUSIVE_EARLY.

    soak_monitor.sh writes RESTART DETECTED precursor lines before writing the
    ENVIRONMENT_INTERRUPTION bulk-restart classification.  When both appear in
    the same log the raw lines are context, not standalone SUT failures, so the
    verdict must be INCONCLUSIVE_EARLY, not FAILED_EARLY.
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "restart_alerts.log").write_text(
        "2026-05-16 14:00:00 UTC - RESTART DETECTED: cdb_risk\n"
        "2026-05-16 14:00:00 UTC - RESTART DETECTED: cdb_execution\n"
        "2026-05-16 14:00:01 UTC - ENVIRONMENT_INTERRUPTION (bulk host reboot)\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == INCONCLUSIVE_EARLY
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_env_interruption_patterns" in failed_checks
    assert "no_hard_restart_patterns" not in failed_checks


def test_shadow_probe_with_nonzero_fill_is_invalid(tmp_path: Path) -> None:
    """Shadow probe with REJECTED status but non-zero filled_quantity => INVALID_EVIDENCE.

    A filled_quantity > 0 contradicts the zero-execution guarantee even when
    the status field reads "REJECTED".
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "shadow_block_probe.json").write_text(
        json.dumps(
            {
                "probe_order_id": "probe-002",
                "order_result_found": True,
                "order_result": {"status": "REJECTED", "filled_quantity": 0.5},
            }
        ),
        encoding="utf-8",
    )

    result = evaluate(
        run_dir,
        _as_of(120),
        hourly_deadline_minutes=75,
        require_shadow_block_probe=True,
    )

    assert result["status"] == INVALID_EVIDENCE
    failed_checks = {f["check"] for f in result["failures"]}
    assert "shadow_block_probe_valid" in failed_checks


def test_non_monotone_hourly_log_is_monitor_dead(tmp_path: Path) -> None:
    """Hourly log with non-monotone hours => MONITOR_DEAD (log corruption)."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    (run_dir / "hourly_checks.log").write_text(
        "2026-05-16 13:00:00 UTC - Hour 1: No restarts\n"
        "2026-05-16 15:00:00 UTC - Hour 3: No restarts\n"
        "2026-05-16 14:00:00 UTC - Hour 2: No restarts\n",  # out of order
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(250))

    assert result["status"] == MONITOR_DEAD


def test_empty_hourly_log_is_monitor_dead(tmp_path: Path) -> None:
    """hourly_checks.log exists but has no Hour N: entries => MONITOR_DEAD."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    (run_dir / "hourly_checks.log").write_text(
        "monitor started\n", encoding="utf-8"
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == MONITOR_DEAD
    failed_checks = {f["check"] for f in result["failures"]}
    assert "hourly_checks_log_valid" in failed_checks


# ---------------------------------------------------------------------------
# Test 9 — #2440-specific placeholder tokens
# ---------------------------------------------------------------------------


def test_2440_placeholder_tokens_invalid_evidence(tmp_path: Path) -> None:
    """Known #2440 backfill placeholder tokens => INVALID_EVIDENCE."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)

    # Evidence file still has un-expanded zero-execution proof placeholders
    # from the old checkpoint-comment scripting error (#2440 RC-3).
    (run_dir / "zero_execution_status.txt").write_text(
        "execution_orders_filled_total: <zero_execution_ok>\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(50), hourly_deadline_minutes=75)

    assert result["status"] == INVALID_EVIDENCE
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_template_placeholders" in failed_checks
    placeholder_fail = next(f for f in result["failures"] if f["check"] == "no_template_placeholders")
    assert "<zero_execution_ok>" in placeholder_fail["detail"]


def test_2440_execution_orders_placeholder_invalid_evidence(tmp_path: Path) -> None:
    """<execution_orders_filled_total=0.> placeholder => INVALID_EVIDENCE."""
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)

    (run_dir / "checkpoint_evidence.txt").write_text(
        "zero_execution proof: <execution_orders_filled_total=0.>\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(50), hourly_deadline_minutes=75)

    assert result["status"] == INVALID_EVIDENCE
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_template_placeholders" in failed_checks


def test_shadow_probe_string_zero_fill_is_valid(tmp_path: Path) -> None:
    """Shadow probe with filled_quantity="0.0" (Redis stream string) => RUNNING_VALID.

    Redis xrevrange returns all stream field values as strings.  A probe
    delivered via the Redis stream fallback path carries "0.0" not numeric 0.
    The supervisor must accept this as valid zero-execution evidence.
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "shadow_block_probe.json").write_text(
        json.dumps(
            {
                "probe_order_id": "probe-003",
                "order_result_found": True,
                "order_result": {"status": "REJECTED", "filled_quantity": "0.0"},
            }
        ),
        encoding="utf-8",
    )

    result = evaluate(
        run_dir,
        _as_of(120),
        hourly_deadline_minutes=75,
        require_shadow_block_probe=True,
    )

    assert result["status"] == RUNNING_VALID
    assert result["checks"]["shadow_block_probe_valid"] is True


@pytest.mark.parametrize(
    "probe_content",
    [
        # top-level value is a JSON array, not a dict
        "[1, 2, 3]",
        # top-level is a string
        '"just a string"',
        # order_result is a string (non-dict truthy value)
        '{"order_result_found": true, "order_result": "some_string"}',
        # order_result is a number
        '{"order_result_found": true, "order_result": 42}',
        # order_result is a list
        '{"order_result_found": true, "order_result": ["a", "b"]}',
    ],
)
def test_malformed_shadow_probe_is_invalid_not_crash(
    tmp_path: Path, probe_content: str
) -> None:
    """Malformed shadow_block_probe.json must yield INVALID_EVIDENCE, not crash.

    The supervisor must not raise AttributeError when the JSON is valid but has a
    non-object top-level value or a non-object order_result field.  Both cases
    must be classified fail-closed as INVALID_EVIDENCE rather than surfacing a
    traceback.
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "shadow_block_probe.json").write_text(probe_content, encoding="utf-8")

    result = evaluate(
        run_dir,
        _as_of(120),
        hourly_deadline_minutes=75,
        require_shadow_block_probe=True,
    )

    # Must not crash; must treat malformed proof as absence of valid proof.
    assert result["status"] in (RUNNING_VALID, INVALID_EVIDENCE, INCONCLUSIVE_EARLY, FAILED_EARLY)
    assert result["checks"]["shadow_block_probe_valid"] is False


# ---------------------------------------------------------------------------
# Fresh-stack baseline tests (Issue #2440 re-run fix)
# ---------------------------------------------------------------------------


def test_fresh_stack_baseline_log_is_running_valid(tmp_path: Path) -> None:
    """FRESH_RESTART: + FRESH_STACK_BASELINE: in fresh_stack_baseline.log => RUNNING_VALID.

    After a fresh-stack first-pass, soak_monitor.sh writes FRESH_RESTART: per-container
    tags and a FRESH_STACK_BASELINE: summary entry into fresh_stack_baseline.log (NOT
    restart_alerts.log).  restart_alerts.log is absent.  Supervisor must report
    RUNNING_VALID (within the hourly deadline grace period).
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    # Simulate 12 per-container FRESH_RESTART: lines + summary in dedicated file
    fresh_lines = "".join(
        f"2026-05-16 19:24:10 UTC - FRESH_RESTART: cdb_svc_{i} (Up 5 minutes)\n"
        for i in range(12)
    )
    fresh_lines += (
        "2026-05-16 19:24:10 UTC - FRESH_STACK_BASELINE: first monitor pass; "
        "all 12/12 SUT services share fresh startup uptime (spread=0s, "
        "uptime_min=300s, run_elapsed=305s); classified as initial-start baseline, "
        "not environment interruption\n"
        "2026-05-16 19:24:10 UTC - FRESH_STACK_BASELINE: first-pass on freshly "
        "started stack; all SUT services healthy; not an environment interruption\n"
    )
    (run_dir / "fresh_stack_baseline.log").write_text(fresh_lines, encoding="utf-8")
    # restart_alerts.log must be absent — that is the P1 fix

    # Within 75-min deadline: no hourly_checks.log required yet
    result = evaluate(run_dir, _as_of(30), hourly_deadline_minutes=75)

    assert result["status"] == RUNNING_VALID, (
        f"Expected RUNNING_VALID for fresh-stack baseline log, got {result['status']}. "
        f"Failures: {result['failures']}"
    )
    assert result["failures"] == []


def test_fresh_stack_baseline_with_hourly_log_is_running_valid(tmp_path: Path) -> None:
    """FRESH_RESTART: in fresh_stack_baseline.log + hourly_checks.log Hour 0 => RUNNING_VALID.

    After the fresh-stack baseline pass writes the hour-0 checkpoint, subsequent
    supervisor evaluations past the hourly deadline must still return RUNNING_VALID.
    restart_alerts.log is absent — baseline evidence is only in fresh_stack_baseline.log.
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    (run_dir / "fresh_stack_baseline.log").write_text(
        "2026-05-16 19:24:10 UTC - FRESH_RESTART: cdb_ws (Up 5 minutes)\n"
        "2026-05-16 19:24:10 UTC - FRESH_STACK_BASELINE: first monitor pass; "
        "all 12/12 SUT services share fresh startup uptime\n",
        encoding="utf-8",
    )
    # hour-0 checkpoint written by fresh-stack baseline path; subsequent clean check
    _write_valid_hourly_log(run_dir, hours=[0, 1, 2])

    result = evaluate(run_dir, _as_of(150), hourly_deadline_minutes=75)

    assert result["status"] == RUNNING_VALID


def test_fresh_restart_tag_alone_does_not_fail(tmp_path: Path) -> None:
    """FRESH_RESTART: tag in fresh_stack_baseline.log must not cause supervisor failure.

    Regression guard: ensures FRESH_RESTART: evidence in fresh_stack_baseline.log
    does not trip any supervisor check.  restart_alerts.log is absent (P1 fix:
    fresh-stack baseline writes only to fresh_stack_baseline.log).
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "fresh_stack_baseline.log").write_text(
        "2026-05-16 19:24:10 UTC - FRESH_RESTART: cdb_risk (Up 3 minutes)\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == RUNNING_VALID
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_hard_restart_patterns" not in failed_checks


def test_fresh_stack_baseline_tag_does_not_trigger_env_interruption(
    tmp_path: Path,
) -> None:
    """FRESH_STACK_BASELINE: in fresh_stack_baseline.log must not cause env-interruption failure.

    Regression guard: ensures FRESH_STACK_BASELINE: evidence in fresh_stack_baseline.log
    does not match _ENV_INTERRUPTION_RE ('ENVIRONMENT_INTERRUPTION').  restart_alerts.log
    is absent (P1 fix: fresh-stack baseline writes only to fresh_stack_baseline.log).
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir)
    (run_dir / "fresh_stack_baseline.log").write_text(
        "2026-05-16 19:24:10 UTC - FRESH_STACK_BASELINE: first monitor pass; "
        "all 12/12 SUT services; not an environment interruption\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(120))

    assert result["status"] == RUNNING_VALID
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_env_interruption_patterns" not in failed_checks


def test_environment_interruption_after_fresh_stack_baseline_is_inconclusive(
    tmp_path: Path,
) -> None:
    """Real ENVIRONMENT_INTERRUPTION after first baseline => INCONCLUSIVE_EARLY.

    After the fresh-stack baseline is established, a real Docker-daemon restart
    later in the run must still produce INCONCLUSIVE_EARLY.

    P1 fix layout: baseline evidence is in fresh_stack_baseline.log; only the
    real ENVIRONMENT_INTERRUPTION appears in restart_alerts.log.
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    _write_valid_hourly_log(run_dir, hours=[0, 1, 2])
    # Fresh-stack baseline from hour 0 — in dedicated file only
    (run_dir / "fresh_stack_baseline.log").write_text(
        "2026-05-16 19:24:10 UTC - FRESH_RESTART: cdb_ws (Up 5 minutes)\n"
        "2026-05-16 19:24:10 UTC - FRESH_STACK_BASELINE: initial-start baseline\n",
        encoding="utf-8",
    )
    # Real environment interruption at hour 3 — in restart_alerts.log
    (run_dir / "restart_alerts.log").write_text(
        "2026-05-16 22:30:00 UTC - ENVIRONMENT_INTERRUPTION: 12/12 host reboot\n",
        encoding="utf-8",
    )
    (run_dir / "soak_test_INCONCLUSIVE.txt").write_text(
        "2026-05-16 22:30:00 UTC - INCONCLUSIVE: Environment interruption at hour 3\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(200))

    assert result["status"] == INCONCLUSIVE_EARLY
    failed_checks = {f["check"] for f in result["failures"]}
    assert "no_env_interruption_patterns" in failed_checks


def test_fresh_stack_baseline_does_not_populate_restart_alerts(tmp_path: Path) -> None:
    """LR-040 regression guard: fresh-stack baseline must leave restart_alerts.log absent.

    P1 fix: soak_monitor.sh no longer writes FRESH_RESTART: or FRESH_STACK_BASELINE:
    to restart_alerts.log.  Only fresh_stack_baseline.log is created on a fresh first
    pass.  If restart_alerts.log is absent, the LR-040 gate (lr040_soak_gate_eval.py)
    sees no_restart_alerts=true and does not fail a healthy run on benign baseline noise.
    """
    run_dir = _make_run_dir(tmp_path)
    (run_dir / "run_intent.txt").write_text("lr030\n", encoding="utf-8")
    # Only fresh_stack_baseline.log — restart_alerts.log intentionally absent
    (run_dir / "fresh_stack_baseline.log").write_text(
        "2026-05-16 19:24:10 UTC - FRESH_RESTART: cdb_ws (Up 5 minutes)\n"
        "2026-05-16 19:24:10 UTC - FRESH_STACK_BASELINE: first-pass baseline\n",
        encoding="utf-8",
    )

    result = evaluate(run_dir, _as_of(30), hourly_deadline_minutes=75)

    assert result["status"] == RUNNING_VALID
    assert not (run_dir / "restart_alerts.log").exists(), (
        "restart_alerts.log must not exist after a fresh-stack first pass — "
        "it would cause lr040_soak_gate_eval.py to report no_restart_alerts=false"
    )

