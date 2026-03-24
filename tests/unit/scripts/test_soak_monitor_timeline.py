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
