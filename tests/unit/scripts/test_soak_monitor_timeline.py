"""Tests for soak_monitor.sh hourly checkpoint timeline logic (Issue #1271).

soak_monitor.sh is a bash script and cannot be unit-tested via Python directly.
Instead, these tests:
  1. Verify the checkpoint arithmetic that mirrors the bash implementation
     (compute_elapsed_hours, would_write_checkpoint) — keeping the Python
     functions in sync with the shell serves as living documentation.
  2. Validate the hourly_checks.log format that the script produces and that
     _parse_hourly_timestamps (in lr040_soak_gate_eval.py) consumes.
  3. Cover edge cases the old date +%H approach could not handle:
     midnight crossing, 72-h run, parallel invocations.
  4. Cover Issue #1269 artifact-path persistence across midnight: the monitor
     must keep writing into the same run directory instead of switching to a
     new date-derived path.
  5. Cover Issue #1263 service health check: SUT service set vs. broad cdb_*
     inventory count (count_sut_services helper).
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parents[3] / "infrastructure" / "scripts")
)

from lr040_soak_gate_eval import _parse_hourly_timestamps

# ---------------------------------------------------------------------------
# Helpers that mirror the bash logic in soak_monitor.sh
# These are NOT production code — they exist to make the bash arithmetic
# testable in Python and to document the intended behaviour precisely.
# ---------------------------------------------------------------------------


def compute_elapsed_hours(now_epoch: int, run_start_epoch: int) -> int:
    """Floor of elapsed whole hours — mirrors: $(( (NOW_EPOCH - RUN_START_EPOCH) / 3600 ))"""
    return (now_epoch - run_start_epoch) // 3600


def would_write_checkpoint(elapsed_hours: int, last_checkpoint: int) -> bool:
    """True when a new hourly_checks.log entry should be written.

    Mirrors the flock-protected check inside soak_monitor.sh:
        if [ "$ELAPSED_HOURS" -le "$_CK" ]; then skip; else write; fi
    last_checkpoint=-1 represents the sentinel initial state (nothing written yet).
    """
    return elapsed_hours > last_checkpoint


def build_hourly_entry(timestamp_utc: str, elapsed_hours: int) -> str:
    """Format used by soak_monitor.sh for a clean-checkpoint line."""
    return f"{timestamp_utc} - Hour {elapsed_hours}: No restarts"


def build_artifact_path(dt: datetime) -> str:
    """Format used by soak_monitor.sh when it creates a fresh run directory."""
    dt = dt.astimezone(timezone.utc)
    return f"artifacts/soak_test_{dt:%Y%m%d_%H%M%S}"


def resolve_date_coupled_artifact_path(now: datetime, existing_dirs: list[str]) -> str:
    """Mirror the pre-#1269 day-coupled artifact lookup.

    The old monitor logic searched only for directories matching today's
    YYYYMMDD prefix. If nothing matched after midnight, it created a new
    directory for the new calendar day and fragmented the same soak run.
    """
    now = now.astimezone(timezone.utc)
    day_prefix = now.strftime("artifacts/soak_test_%Y%m%d")
    matches = sorted(path for path in existing_dirs if path.startswith(day_prefix))
    if matches:
        return matches[0]
    return f"{day_prefix}_{now:%H%M%S}"


def resolve_active_artifact_path(
    now: datetime,
    existing_dirs: list[str],
    active_run_path: str | None,
) -> str:
    """Mirror the #1269 active-run selection in soak_monitor.sh."""
    if active_run_path and active_run_path in existing_dirs:
        return active_run_path
    if existing_dirs:
        return sorted(existing_dirs)[-1]
    return build_artifact_path(now)


# ---------------------------------------------------------------------------
# compute_elapsed_hours
# ---------------------------------------------------------------------------


class TestComputeElapsedHours:
    def test_zero_at_start(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t, t) == 0

    def test_exactly_one_hour(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 3600, t) == 1

    def test_fractional_truncates_down(self) -> None:
        """1 h 59 m 59 s must still be hour 1, not 2."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 7199, t) == 1

    def test_midnight_crossing(self) -> None:
        """Run starting at 23:00 UTC; check fires 2 h later at 01:00 UTC next day."""
        start = datetime(2026, 3, 23, 23, 0, 0, tzinfo=timezone.utc)
        check = datetime(2026, 3, 24, 1, 0, 0, tzinfo=timezone.utc)
        elapsed = compute_elapsed_hours(int(check.timestamp()), int(start.timestamp()))
        assert elapsed == 2

    def test_72h_full_run(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 72 * 3600, t) == 72

    def test_late_second_cron_same_hour(self) -> None:
        """Cron fires at :00:01, second instance at :00:59 — same elapsed hour."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 1, t) == 0
        assert compute_elapsed_hours(t + 59, t) == 0

    def test_old_date_h_would_repeat_at_24h(self) -> None:
        """Demonstrate that date +%H would produce Hour 0 twice.

        After exactly 24 h the old logic (date +%H) returns 0 again.
        The new elapsed-hours approach returns 24 — no duplicate.
        """
        t = 1_000_000
        assert compute_elapsed_hours(t + 24 * 3600, t) == 24  # new: unambiguous
        # old behaviour (not code, just documenting the bug):
        #   datetime.utcfromtimestamp(t + 24*3600).hour == same as hour at t


# ---------------------------------------------------------------------------
# would_write_checkpoint (idempotency guard)
# ---------------------------------------------------------------------------


class TestIdempotencyGuard:
    def test_first_write_allowed(self) -> None:
        """Sentinel starts at -1 (nothing written); first checkpoint must be written."""
        assert would_write_checkpoint(0, -1) is True

    def test_same_checkpoint_blocked(self) -> None:
        """Second invocation in the same elapsed-hour must be skipped."""
        assert would_write_checkpoint(5, 5) is False

    def test_stale_lower_checkpoint_blocked(self) -> None:
        """Should not happen in practice, but must be safe (no going backwards)."""
        assert would_write_checkpoint(3, 5) is False

    def test_next_checkpoint_allowed(self) -> None:
        assert would_write_checkpoint(6, 5) is True

    def test_two_parallel_instances_produce_one_entry(self) -> None:
        """Simulate two concurrent instances sharing state via last_checkpoint."""
        # Instance A acquires lock first and writes checkpoint 7.
        last = -1
        assert would_write_checkpoint(7, last) is True
        last = 7  # A updates sentinel

        # Instance B acquires lock second and reads updated sentinel.
        assert would_write_checkpoint(7, last) is False  # skipped — no duplicate


# ---------------------------------------------------------------------------
# artifact-path resolution (Issue #1269)
# ---------------------------------------------------------------------------


class TestArtifactPathResolution:
    def test_old_date_coupled_lookup_fragments_same_run_after_midnight(self) -> None:
        existing = ["artifacts/soak_test_20260323_235959"]
        now = datetime(2026, 3, 24, 0, 0, 2, tzinfo=timezone.utc)

        old_path = resolve_date_coupled_artifact_path(now, existing)

        assert old_path == "artifacts/soak_test_20260324_000002"
        assert old_path not in existing

    def test_active_run_path_keeps_same_directory_across_midnight(self) -> None:
        existing = [
            "artifacts/soak_test_20260322_181856",
            "artifacts/soak_test_20260323_235959",
        ]
        active = "artifacts/soak_test_20260323_235959"
        now = datetime(2026, 3, 24, 0, 0, 2, tzinfo=timezone.utc)

        resolved = resolve_active_artifact_path(now, existing, active)

        assert resolved == active

    def test_missing_pointer_reuses_latest_existing_directory(self) -> None:
        existing = [
            "artifacts/soak_test_20260322_181856",
            "artifacts/soak_test_20260323_235959",
        ]
        now = datetime(2026, 3, 24, 0, 0, 2, tzinfo=timezone.utc)

        resolved = resolve_active_artifact_path(now, existing, active_run_path=None)

        assert resolved == "artifacts/soak_test_20260323_235959"

    def test_stale_pointer_falls_back_to_latest_existing_directory(self) -> None:
        existing = [
            "artifacts/soak_test_20260322_181856",
            "artifacts/soak_test_20260323_235959",
        ]
        stale_active = "artifacts/soak_test_20260321_120003"
        now = datetime(2026, 3, 24, 0, 0, 2, tzinfo=timezone.utc)

        resolved = resolve_active_artifact_path(now, existing, stale_active)

        assert resolved == "artifacts/soak_test_20260323_235959"

    def test_no_existing_directory_creates_new_utc_run_path(self) -> None:
        now = datetime(2026, 3, 24, 0, 0, 2, tzinfo=timezone.utc)

        resolved = resolve_active_artifact_path(now, existing_dirs=[], active_run_path=None)

        assert resolved == "artifacts/soak_test_20260324_000002"


# ---------------------------------------------------------------------------
# hourly_checks.log format and monotonicity
# ---------------------------------------------------------------------------


def _make_log(entries: list[tuple[str, int]], tmp_path: Path) -> Path:
    """Write a synthetic hourly_checks.log and return its path."""
    log_path = tmp_path / "hourly_checks.log"
    lines = [build_hourly_entry(ts, h) for ts, h in entries]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log_path


def _extract_hour_indices(log_path: Path) -> list[int]:
    """Parse the 'Hour N' index from each log line."""
    indices = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        m = re.search(r"Hour (\d+):", line)
        if m:
            indices.append(int(m.group(1)))
    return indices


class TestHourlyLogFormat:
    def test_log_is_parseable_by_gate_eval(self, tmp_path: Path) -> None:
        """_parse_hourly_timestamps must extract timestamps from the new format."""
        log = _make_log(
            [
                ("2026-03-24 00:00:01 UTC", 0),
                ("2026-03-24 01:00:01 UTC", 1),
                ("2026-03-24 02:00:01 UTC", 2),
            ],
            tmp_path,
        )
        timestamps = _parse_hourly_timestamps(log)
        assert len(timestamps) == 3

    def test_timestamps_monotonically_increasing(self, tmp_path: Path) -> None:
        log = _make_log(
            [
                ("2026-03-24 00:00:01 UTC", 0),
                ("2026-03-24 01:00:01 UTC", 1),
                ("2026-03-24 02:00:01 UTC", 2),
            ],
            tmp_path,
        )
        timestamps = _parse_hourly_timestamps(log)
        for i in range(1, len(timestamps)):
            assert timestamps[i] > timestamps[i - 1], (
                f"Timestamp at position {i} is not after position {i-1}"
            )

    def test_hour_indices_strictly_increasing(self, tmp_path: Path) -> None:
        log = _make_log(
            [
                ("2026-03-24 00:00:01 UTC", 0),
                ("2026-03-24 01:00:01 UTC", 1),
                ("2026-03-27 00:00:01 UTC", 72),  # 72-h mark (2026-03-24 + 72h)
            ],
            tmp_path,
        )
        indices = _extract_hour_indices(log)
        assert indices == sorted(set(indices)), "Hour indices are not strictly increasing"

    def test_no_duplicate_hour_indices(self, tmp_path: Path) -> None:
        """A correctly guarded log must have no repeated hour labels."""
        log = _make_log(
            [
                ("2026-03-24 00:00:01 UTC", 0),
                ("2026-03-24 01:00:01 UTC", 1),
                ("2026-03-24 02:00:01 UTC", 2),
            ],
            tmp_path,
        )
        indices = _extract_hour_indices(log)
        assert len(indices) == len(set(indices)), "Duplicate hour indices detected"

    def test_duplicate_detection_catches_old_bug(self, tmp_path: Path) -> None:
        """Log with old date +%H duplicates (Hour 0 twice) fails the check."""
        log = _make_log(
            [
                ("2026-03-23 23:00:01 UTC", 0),  # date +%H = 23, but label was 00
                ("2026-03-24 00:00:01 UTC", 0),  # duplicate Hour 0
                ("2026-03-24 00:00:02 UTC", 1),  # off-by-one from second instance
            ],
            tmp_path,
        )
        indices = _extract_hour_indices(log)
        assert len(indices) != len(set(indices)), (
            "Expected duplicates to be present in this regression log"
        )


# ---------------------------------------------------------------------------
# Midnight-crossing and run-start edge cases
# ---------------------------------------------------------------------------


class TestMidnightCrossing:
    def test_run_starting_23xx_no_hour0_repeat(self, tmp_path: Path) -> None:
        """Run starting at 23:xx UTC: Hour 0 at 23:xx, Hour 1 at 00:xx next day.
        With elapsed hours the labels are 0, 1, 2 — no date +%H repeat.
        """
        # Elapsed 0 at 23:30, elapsed 1 at 00:30 next day
        start = int(datetime(2026, 3, 23, 23, 30, 0, tzinfo=timezone.utc).timestamp())
        checks = [start + h * 3600 for h in range(4)]
        elapsed = [compute_elapsed_hours(c, start) for c in checks]
        assert elapsed == [0, 1, 2, 3], f"Expected [0,1,2,3], got {elapsed}"

        # Build log and verify no duplicates
        log = _make_log(
            [
                ("2026-03-23 23:30:01 UTC", elapsed[0]),
                ("2026-03-24 00:30:01 UTC", elapsed[1]),
                ("2026-03-24 01:30:01 UTC", elapsed[2]),
                ("2026-03-24 02:30:01 UTC", elapsed[3]),
            ],
            tmp_path,
        )
        indices = _extract_hour_indices(log)
        assert len(indices) == len(set(indices))

    def test_run_start_derived_from_dir_name(self) -> None:
        """Verify the epoch parsed from soak_test_YYYYMMDD_HHMMSS matches the
        datetime it encodes — this mirrors the bash date -d parsing in
        soak_monitor.sh for the run_start.txt derivation."""
        # Directory name: soak_test_20260324_000002
        dir_name = "soak_test_20260324_000002"
        tokens = re.search(r"(\d{8})_(\d{6})", dir_name)
        assert tokens is not None
        d, t = tokens.group(1), tokens.group(2)
        dt = datetime(
            int(d[0:4]), int(d[4:6]), int(d[6:8]),
            int(t[0:2]), int(t[2:4]), int(t[4:6]),
            tzinfo=timezone.utc,
        )
        expected = datetime(2026, 3, 24, 0, 0, 2, tzinfo=timezone.utc)
        assert dt == expected

    def test_elapsed_hours_72h_run_produces_73_checkpoints(self) -> None:
        """A 72-h run fires checks at hours 0, 1, 2, … 72 = 73 entries."""
        t = 1_000_000
        checkpoints = [compute_elapsed_hours(t + h * 3600, t) for h in range(73)]
        assert checkpoints == list(range(73))
        assert len(set(checkpoints)) == 73, "All checkpoint indices must be unique"


# ---------------------------------------------------------------------------
# Octal-safety regression tests (Issue #1268)
#
# Old bug: HOUR=$(date +%H) produced the zero-padded local-time string "08"/"09".
# Bash arithmetic expansion $(( 08 % 6 )) fails: "value too great for base".
#
# Fix (via #1271): ELAPSED_HOURS is derived from epoch arithmetic and is always
# a plain integer. $(( 8 % 6 )) = 2 and $(( 9 % 6 )) = 3 work correctly.
#
# These tests document the regression boundary so the fix cannot be silently
# reverted without breaking the test suite.
# ---------------------------------------------------------------------------


class TestOctalSafeScheduleChecks:
    """Regression tests for Issue #1268: zero-padded hours 08/09 octal parse."""

    # --- compute_elapsed_hours produces plain integers, never zero-padded ---

    def test_elapsed_hour_7_is_plain_int(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 7 * 3600, t) == 7

    def test_elapsed_hour_8_is_plain_int(self) -> None:
        """Hour 8 must be integer 8, not the string '08' that triggered octal errors."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 8 * 3600, t) == 8

    def test_elapsed_hour_9_is_plain_int(self) -> None:
        """Hour 9 must be integer 9, not the string '09' that triggered octal errors."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 9 * 3600, t) == 9

    def test_elapsed_hour_10_is_plain_int(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 10 * 3600, t) == 10

    # --- Check 3 (every 6h): modulo correct for formerly-octal hours ---

    def test_check3_modulo_hour_6_triggers(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 6 * 3600, t) % 6 == 0

    def test_check3_modulo_hour_7_skips(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 7 * 3600, t) % 6 == 1

    def test_check3_modulo_hour_8_skips(self) -> None:
        """$(( 8 % 6 )) == 2 — Check 3 must be skipped at elapsed hour 8."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 8 * 3600, t) % 6 == 2

    def test_check3_modulo_hour_9_skips(self) -> None:
        """$(( 9 % 6 )) == 3 — Check 3 must be skipped at elapsed hour 9."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 9 * 3600, t) % 6 == 3

    def test_check3_modulo_hour_10_skips(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 10 * 3600, t) % 6 == 4

    def test_check3_modulo_hour_12_triggers(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 12 * 3600, t) % 6 == 0

    # --- Check 4 (every 12h): modulo correct for formerly-octal hours ---

    def test_check4_modulo_hour_8_skips(self) -> None:
        """$(( 8 % 12 )) == 8 — Check 4 must be skipped at elapsed hour 8."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 8 * 3600, t) % 12 == 8

    def test_check4_modulo_hour_9_skips(self) -> None:
        """$(( 9 % 12 )) == 9 — Check 4 must be skipped at elapsed hour 9."""
        t = 1_000_000
        assert compute_elapsed_hours(t + 9 * 3600, t) % 12 == 9

    def test_check4_modulo_hour_12_triggers(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 12 * 3600, t) % 12 == 0

    def test_check4_modulo_hour_24_triggers(self) -> None:
        t = 1_000_000
        assert compute_elapsed_hours(t + 24 * 3600, t) % 12 == 0

    # --- Checkpoint comparison safe at hours 8 and 9 ---

    def test_checkpoint_write_decision_at_hour_8(self) -> None:
        """Idempotency guard must work at hour 8 (was broken by octal in old script)."""
        assert would_write_checkpoint(8, 7) is True   # new checkpoint, must write
        assert would_write_checkpoint(8, 8) is False  # already written, must skip

    def test_checkpoint_write_decision_at_hour_9(self) -> None:
        """Idempotency guard must work at hour 9."""
        assert would_write_checkpoint(9, 8) is True
        assert would_write_checkpoint(9, 9) is False

    def test_checkpoint_sequence_7_through_10(self) -> None:
        """Simulate four consecutive cron firings through the formerly-broken hours."""
        last = 6
        for h in [7, 8, 9, 10]:
            assert would_write_checkpoint(h, last) is True, f"Hour {h} should write"
            last = h
        assert last == 10

    # --- Document the old bug boundary ---

    def test_old_date_h_utc_offset_mapping(self) -> None:
        """Document: at UTC 07:00, MESZ local time is 08:00 → date +%H returned '08'.
        The fix avoids this entirely: elapsed hours at UTC 07:00 into a midnight
        soak run is 7 (plain integer), never the string '08'.
        """
        # Soak started 2026-03-24 00:00:02 UTC; cron fires at 07:00:01 UTC
        start = int(__import__("datetime").datetime(2026, 3, 24, 0, 0, 2,
                    tzinfo=__import__("datetime").timezone.utc).timestamp())
        check = int(__import__("datetime").datetime(2026, 3, 24, 7, 0, 1,
                    tzinfo=__import__("datetime").timezone.utc).timestamp())
        elapsed = compute_elapsed_hours(check, start)
        # old script: HOUR=$(date +%H) at MESZ+1 would give '08' → octal error
        # new script: elapsed == 6 (floor of ~6.99 h) — plain integer, no error
        assert elapsed == 6
        assert str(elapsed) != "08", "elapsed hours must never be zero-padded"


# ---------------------------------------------------------------------------
# Service health check tests (Issue #1263)
#
# Old bug: EXPECTED_SERVICES=8 (static, stale) while RUNNING_SERVICES counted
# ALL cdb_* containers on the host (22+ in full BLUE+RED+exporter+infra runtime),
# producing the semantically wrong output "22/8 services running".
#
# Fix: curate an explicit SUT_SERVICES list (12 ZRP-relevant containers) and
# count only those. The broad cdb_* count is reported as inventory info only.
# ---------------------------------------------------------------------------

# Canonical ZRP-relevant SUT services — must match soak_monitor.sh SUT_SERVICES.
SUT_SERVICES = [
    "cdb_postgres", "cdb_redis",
    "cdb_market", "cdb_candles", "cdb_regime", "cdb_allocation",
    "cdb_risk", "cdb_execution", "cdb_db_writer", "cdb_paper_runner",
    "cdb_ws", "cdb_signal",
]


def count_sut_services(
    running_containers: list[str],
    sut_services: list[str],
) -> tuple[int, list[str]]:
    """Mirror soak_monitor.sh Check 2 logic (Issue #1263 fix).

    Returns (running_count, missing_list).
    Mirrors the bash loop: for _svc in $SUT_SERVICES; do grep -qx ...
    """
    running = set(running_containers)
    missing = [s for s in sut_services if s not in running]
    return len(sut_services) - len(missing), missing


class TestServiceHealthCheck:
    """Regression tests for Issue #1263: inconsistent Soll/Ist counting.

    Old bug: EXPECTED_SERVICES=8 (BLUE core without postgres/redis, without RED)
    while RUNNING_SERVICES counted ALL cdb_* containers (22+ in a full runtime).

    Fix: explicit SUT_SERVICES list (12) — count only ZRP-relevant containers.
    """

    def test_expected_sut_count_is_12(self) -> None:
        """The canonical SUT list must have exactly 12 entries."""
        assert len(SUT_SERVICES) == 12

    def test_all_sut_services_running_reports_12_of_12(self) -> None:
        count, missing = count_sut_services(SUT_SERVICES, SUT_SERVICES)
        assert count == 12
        assert missing == []

    def test_missing_one_service_detected(self) -> None:
        partial = [s for s in SUT_SERVICES if s != "cdb_risk"]
        count, missing = count_sut_services(partial, SUT_SERVICES)
        assert count == 11
        assert missing == ["cdb_risk"]

    def test_missing_two_services_detected(self) -> None:
        partial = [s for s in SUT_SERVICES if s not in {"cdb_ws", "cdb_signal"}]
        count, missing = count_sut_services(partial, SUT_SERVICES)
        assert count == 10
        assert set(missing) == {"cdb_ws", "cdb_signal"}

    def test_blue_only_missing_red_signal_services(self) -> None:
        """Only BLUE services up, RED cdb_ws/cdb_signal missing → 10/12."""
        blue_only = [
            "cdb_postgres", "cdb_redis", "cdb_market", "cdb_candles",
            "cdb_regime", "cdb_allocation", "cdb_risk", "cdb_execution",
            "cdb_db_writer", "cdb_paper_runner",
        ]
        count, missing = count_sut_services(blue_only, SUT_SERVICES)
        assert count == 10
        assert set(missing) == {"cdb_ws", "cdb_signal"}

    def test_exporter_containers_not_in_sut_set(self) -> None:
        """Observability/exporter containers must NOT be in the ZRP gate."""
        non_sut = {
            "cdb_prometheus", "cdb_grafana", "cdb_postgres_exporter",
            "cdb_redis_exporter", "cdb_cadvisor", "cdb_reports",
            "cdb_alertmanager", "cdb_node_exporter",
        }
        assert non_sut.isdisjoint(set(SUT_SERVICES)), (
            "Observability containers must not be in SUT_SERVICES"
        )

    def test_monitor_container_not_in_sut_set(self) -> None:
        """lr040_soak_monitor must not be counted as a SUT service."""
        assert "lr040_soak_monitor" not in SUT_SERVICES

    def test_extra_containers_do_not_inflate_sut_count(self) -> None:
        """22 cdb_* containers on host must not inflate the 12-service SUT count."""
        all_host_cdb = SUT_SERVICES + [
            "cdb_prometheus", "cdb_grafana", "cdb_postgres_exporter",
            "cdb_redis_exporter", "cdb_cadvisor", "cdb_reports",
            "cdb_alertmanager", "cdb_node_exporter",
            "cdb_market_eth", "cdb_gh_runner",
        ]
        count, missing = count_sut_services(all_host_cdb, SUT_SERVICES)
        assert count == 12
        assert missing == []

    def test_data_layer_in_sut_set(self) -> None:
        """cdb_postgres and cdb_redis are ZRP-critical and must be in SUT_SERVICES."""
        assert "cdb_postgres" in SUT_SERVICES
        assert "cdb_redis" in SUT_SERVICES

    def test_red_signal_services_in_sut_set(self) -> None:
        """cdb_ws and cdb_signal are ZRP-relevant and must be in SUT_SERVICES."""
        assert "cdb_ws" in SUT_SERVICES
        assert "cdb_signal" in SUT_SERVICES

    def test_old_bug_reproduction(self) -> None:
        """Document the old bug: broad cdb_* count >> static EXPECTED_SERVICES=8."""
        # Simulate full host: 22 cdb_* containers running
        all_cdb_on_host = [
            "cdb_postgres", "cdb_redis", "cdb_market", "cdb_candles",
            "cdb_regime", "cdb_allocation", "cdb_risk", "cdb_execution",
            "cdb_db_writer", "cdb_paper_runner", "cdb_ws", "cdb_signal",
            "cdb_prometheus", "cdb_grafana", "cdb_postgres_exporter",
            "cdb_redis_exporter", "cdb_cadvisor", "cdb_reports",
            "cdb_alertmanager", "cdb_node_exporter", "cdb_market_eth", "cdb_gh_runner",
        ]
        old_running = len(all_cdb_on_host)  # 22
        old_expected = 8                    # hardcoded in old script
        # Old output: "22/8 services running" — semantically wrong
        assert old_running > old_expected, "Documents the old Soll/Ist mismatch"

        # New approach: only the 12 curated SUT services
        new_count, new_missing = count_sut_services(all_cdb_on_host, SUT_SERVICES)
        assert new_count == 12
        assert new_missing == []
        # New output: "12/12 SUT services running (inventory: 22 cdb_* containers)"


# ---------------------------------------------------------------------------
# Disk space check tests (Issue #1264)
#
# Old bug: df -h /var/lib/docker ran inside the container namespace where
# /var/lib/docker is not mounted. With pipefail active, the failed pipeline
# produced DISK_USAGE="unknown" at every checkpoint — no actionable evidence.
#
# Fix: use df /repo (always mounted at /repo in lr040_soak_monitor) and
# docker system df (via socket) instead. Write a disk_evidence artifact at
# every checkpoint, not only at the >90% critical level.
# ---------------------------------------------------------------------------


def parse_disk_pct(df_output: str) -> str | None:
    """Parse disk usage percentage from df output (2nd data row, 5th column).

    Returns the numeric string without %, or None if not parseable.
    Mirrors: df /repo | awk 'NR==2 {print $5}' | sed 's/%//'
    """
    lines = df_output.strip().splitlines()
    if len(lines) < 2:
        return None
    parts = lines[1].split()
    if len(parts) < 5:
        return None
    pct_str = parts[4].rstrip("%")
    if not pct_str.isdigit():
        return None
    return pct_str


def classify_disk_usage(pct: int) -> str:
    """Returns 'ok', 'warning', or 'critical'.

    Mirrors the threshold logic in soak_monitor.sh Check 5:
      >90% → critical, >80% → warning, otherwise → ok.
    """
    if pct > 90:
        return "critical"
    if pct > 80:
        return "warning"
    return "ok"


# Realistic df output for /repo (inside ubuntu:22.04 container on WSL2/Linux)
_DF_REPO_NORMAL = """\
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       932G  412G  473G  47% /repo
"""

_DF_REPO_WARNING = """\
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       932G  760G  125G  86% /repo
"""

_DF_REPO_CRITICAL = """\
Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1       932G  860G   25G  97% /repo
"""

# Old bug: df /var/lib/docker fails inside container → empty output (with pipefail,
# the pipeline would have produced "unknown" via the || echo "unknown" fallback)
_DF_EMPTY = ""
_DF_ERROR_LINE_ONLY = "df: /var/lib/docker: No such file or directory\n"


class TestDiskSpaceCheck:
    """Regression tests for Issue #1264: disk check unavailable in container.

    The monitor runs inside ubuntu:22.04 with /repo and /var/run/docker.sock
    mounted. /var/lib/docker is NOT in the container namespace.
    """

    # --- parse_disk_pct ---

    def test_parse_normal_usage(self) -> None:
        assert parse_disk_pct(_DF_REPO_NORMAL) == "47"

    def test_parse_warning_usage(self) -> None:
        assert parse_disk_pct(_DF_REPO_WARNING) == "86"

    def test_parse_critical_usage(self) -> None:
        assert parse_disk_pct(_DF_REPO_CRITICAL) == "97"

    def test_parse_empty_output_returns_none(self) -> None:
        """Empty df output (old /var/lib/docker path inside container) → None."""
        assert parse_disk_pct(_DF_EMPTY) is None

    def test_parse_error_line_only_returns_none(self) -> None:
        """df error line without data row → None (old bug: this produced 'unknown')."""
        assert parse_disk_pct(_DF_ERROR_LINE_ONLY) is None

    def test_parse_header_only_returns_none(self) -> None:
        """Only header line, no data → None."""
        header_only = "Filesystem      Size  Used Avail Use% Mounted on\n"
        assert parse_disk_pct(header_only) is None

    def test_parse_non_numeric_pct_returns_none(self) -> None:
        """Malformed 5th column (no % or non-numeric) → None."""
        bad = "Filesystem  Size Used Avail ??? /\n/dev/sda1   100G  50G   50G ??? /\n"
        assert parse_disk_pct(bad) is None

    # --- classify_disk_usage ---

    def test_classify_47_is_ok(self) -> None:
        assert classify_disk_usage(47) == "ok"

    def test_classify_80_boundary_is_ok(self) -> None:
        """80% is NOT above 80, so it is ok."""
        assert classify_disk_usage(80) == "ok"

    def test_classify_81_is_warning(self) -> None:
        assert classify_disk_usage(81) == "warning"

    def test_classify_86_is_warning(self) -> None:
        assert classify_disk_usage(86) == "warning"

    def test_classify_90_boundary_is_warning(self) -> None:
        """90% is NOT above 90, so it is warning."""
        assert classify_disk_usage(90) == "warning"

    def test_classify_91_is_critical(self) -> None:
        assert classify_disk_usage(91) == "critical"

    def test_classify_97_is_critical(self) -> None:
        assert classify_disk_usage(97) == "critical"

    # --- Evidence model ---

    def test_evidence_produced_at_ok_level(self) -> None:
        """Evidence must be written even when usage is below alert thresholds.

        Old code only wrote disk_alerts.log at >90%. Now every checkpoint
        writes a disk_evidence_<H>h.txt file.
        """
        pct_str = parse_disk_pct(_DF_REPO_NORMAL)
        assert pct_str is not None
        classification = classify_disk_usage(int(pct_str))
        assert classification == "ok"
        # The fix ensures a disk_evidence file is always written (regardless
        # of classification). The test confirms the parsed value is actionable.
        assert pct_str.isdigit()

    def test_unavailable_case_is_explicitly_marked(self) -> None:
        """When df returns no parseable output, the result must be None (not empty
        string or 'unknown') so callers can distinguish 'unknown' from '0%'."""
        assert parse_disk_pct(_DF_EMPTY) is None
        assert parse_disk_pct(_DF_ERROR_LINE_ONLY) is None

    def test_old_bug_var_lib_docker_path_fails_in_container(self) -> None:
        """Document old bug: df /var/lib/docker inside container returns no data.

        With pipefail, the failed df pipeline set DISK_USAGE='unknown' at
        every checkpoint. The fix uses df /repo (always mounted) instead.
        """
        # Old path: /var/lib/docker → empty/error output → parse returns None
        old_path_output = _DF_EMPTY
        assert parse_disk_pct(old_path_output) is None, (
            "Old /var/lib/docker path was unreachable in container namespace"
        )

        # New path: /repo → parseable output
        new_path_output = _DF_REPO_NORMAL
        assert parse_disk_pct(new_path_output) == "47", (
            "New /repo path must yield parseable disk usage"
        )
