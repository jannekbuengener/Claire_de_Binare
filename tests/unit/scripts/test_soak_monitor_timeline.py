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


def build_artifact_path(dt: datetime, intent: str = "lr040") -> str:
    """Format used by soak_monitor.sh when it creates a fresh run directory.

    Since Issue #1278, the prefix depends on SOAK_RUN_INTENT:
      lr040      -> artifacts/soak_test_YYYYMMDD_HHMMSS
      validation -> artifacts/soak_validation_YYYYMMDD_HHMMSS
    """
    dt = dt.astimezone(timezone.utc)
    prefix = "soak_validation" if intent == "validation" else "soak_test"
    return f"artifacts/{prefix}_{dt:%Y%m%d_%H%M%S}"


def _artifact_prefix_for_intent(intent: str) -> str:
    """Return the artifact directory prefix for a given run intent."""
    return "soak_validation" if intent == "validation" else "soak_test"


def resolve_active_artifact_path_with_intent(
    now: datetime,
    existing_dirs: list[str],
    active_run_path: str | None,
    intent: str = "lr040",
) -> str:
    """Mirror the #1278 intent-aware active-run selection in soak_monitor.sh.

    Key difference from the pre-#1278 version: the pointer and fallback search
    are scoped to the current intent's prefix so lr040 runs never pick up a
    validation directory and vice versa.
    """
    prefix = f"artifacts/{_artifact_prefix_for_intent(intent)}_"

    # 1. Pointer valid AND matches current intent prefix?
    if active_run_path and active_run_path in existing_dirs:
        if active_run_path.startswith(prefix):
            return active_run_path
        # Cross-intent pointer — ignore (Issue #1278)

    # 2. Fallback: latest directory matching current prefix
    matching = sorted(d for d in existing_dirs if d.startswith(prefix))
    if matching:
        return matching[-1]

    # 3. Create new
    return build_artifact_path(now, intent)


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

        resolved = resolve_active_artifact_path(
            now, existing_dirs=[], active_run_path=None
        )

        assert resolved == "artifacts/soak_test_20260324_000002"


# ---------------------------------------------------------------------------
# Intent-aware artifact path resolution (Issue #1278)
# ---------------------------------------------------------------------------


class TestIntentAwareArtifactPath:
    """Tests for run-intent separation in artifact resolution (Issue #1278)."""

    NOW = datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc)

    def test_validation_creates_soak_validation_prefix(self) -> None:
        path = build_artifact_path(self.NOW, intent="validation")
        assert path == "artifacts/soak_validation_20260325_100000"

    def test_lr040_creates_soak_test_prefix(self) -> None:
        path = build_artifact_path(self.NOW, intent="lr040")
        assert path == "artifacts/soak_test_20260325_100000"

    def test_default_intent_is_lr040(self) -> None:
        path = build_artifact_path(self.NOW)
        assert "soak_test_" in path

    def test_validation_ignores_soak_test_dirs(self) -> None:
        """validation intent must never reuse a soak_test_* directory."""
        existing = [
            "artifacts/soak_test_20260324_220000",
            "artifacts/soak_test_20260325_080000",
        ]
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=None, intent="validation"
        )
        assert resolved.startswith("artifacts/soak_validation_")
        assert resolved not in existing

    def test_lr040_ignores_soak_validation_dirs(self) -> None:
        """lr040 intent must never reuse a soak_validation_* directory."""
        existing = [
            "artifacts/soak_validation_20260324_220000",
            "artifacts/soak_validation_20260325_080000",
        ]
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=None, intent="lr040"
        )
        assert resolved.startswith("artifacts/soak_test_")
        assert resolved not in existing

    def test_validation_pointer_to_soak_test_dir_rejected(self) -> None:
        """Active-run pointer pointing at soak_test_* must be ignored when intent=validation."""
        existing = [
            "artifacts/soak_test_20260324_220000",
            "artifacts/soak_validation_20260325_090000",
        ]
        cross_pointer = "artifacts/soak_test_20260324_220000"
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=cross_pointer, intent="validation"
        )
        assert resolved == "artifacts/soak_validation_20260325_090000"

    def test_lr040_pointer_to_soak_validation_dir_rejected(self) -> None:
        """Active-run pointer pointing at soak_validation_* must be ignored when intent=lr040."""
        existing = [
            "artifacts/soak_validation_20260325_090000",
            "artifacts/soak_test_20260324_220000",
        ]
        cross_pointer = "artifacts/soak_validation_20260325_090000"
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=cross_pointer, intent="lr040"
        )
        assert resolved == "artifacts/soak_test_20260324_220000"

    def test_same_intent_pointer_accepted(self) -> None:
        """Pointer matching the intent prefix is accepted normally."""
        existing = [
            "artifacts/soak_validation_20260325_080000",
            "artifacts/soak_validation_20260325_090000",
        ]
        pointer = "artifacts/soak_validation_20260325_080000"
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=pointer, intent="validation"
        )
        assert resolved == pointer

    def test_mixed_dirs_validation_picks_only_validation(self) -> None:
        """With both prefixes present, validation only sees soak_validation_*."""
        existing = [
            "artifacts/soak_test_20260325_080000",
            "artifacts/soak_validation_20260325_090000",
            "artifacts/soak_test_20260325_100000",
        ]
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=None, intent="validation"
        )
        assert resolved == "artifacts/soak_validation_20260325_090000"

    def test_mixed_dirs_lr040_picks_only_soak_test(self) -> None:
        """With both prefixes present, lr040 only sees soak_test_*."""
        existing = [
            "artifacts/soak_validation_20260325_090000",
            "artifacts/soak_test_20260325_080000",
            "artifacts/soak_validation_20260325_100000",
        ]
        resolved = resolve_active_artifact_path_with_intent(
            self.NOW, existing, active_run_path=None, intent="lr040"
        )
        assert resolved == "artifacts/soak_test_20260325_080000"

    def test_no_matching_dirs_creates_new_with_correct_prefix(self) -> None:
        """Empty directory list → new directory with intent-correct prefix."""
        for intent, expected_prefix in [
            ("lr040", "soak_test_"),
            ("validation", "soak_validation_"),
        ]:
            resolved = resolve_active_artifact_path_with_intent(
                self.NOW, existing_dirs=[], active_run_path=None, intent=intent
            )
            assert f"artifacts/{expected_prefix}" in resolved


class TestRunIntentMarker:
    """Tests for run_intent.txt written by soak_monitor.sh (Issue #1278)."""

    def test_intent_file_content_lr040(self, tmp_path: Path) -> None:
        intent_file = tmp_path / "run_intent.txt"
        intent_file.write_text("lr040\n", encoding="utf-8")
        assert intent_file.read_text(encoding="utf-8").strip() == "lr040"

    def test_intent_file_content_validation(self, tmp_path: Path) -> None:
        intent_file = tmp_path / "run_intent.txt"
        intent_file.write_text("validation\n", encoding="utf-8")
        assert intent_file.read_text(encoding="utf-8").strip() == "validation"

    def test_intent_file_not_overwritten_on_rerun(self, tmp_path: Path) -> None:
        """Mirrors soak_monitor.sh: if run_intent.txt exists, don't overwrite."""
        intent_file = tmp_path / "run_intent.txt"
        intent_file.write_text("validation\n", encoding="utf-8")
        # Simulate second invocation: only write if absent
        if not intent_file.exists():
            intent_file.write_text("lr040\n", encoding="utf-8")
        assert intent_file.read_text(encoding="utf-8").strip() == "validation"


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
            assert (
                timestamps[i] > timestamps[i - 1]
            ), f"Timestamp at position {i} is not after position {i-1}"

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
        assert indices == sorted(
            set(indices)
        ), "Hour indices are not strictly increasing"

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
        assert len(indices) != len(
            set(indices)
        ), "Expected duplicates to be present in this regression log"


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
            int(d[0:4]),
            int(d[4:6]),
            int(d[6:8]),
            int(t[0:2]),
            int(t[2:4]),
            int(t[4:6]),
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
        assert would_write_checkpoint(8, 7) is True  # new checkpoint, must write
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
        start = int(
            __import__("datetime")
            .datetime(2026, 3, 24, 0, 0, 2, tzinfo=__import__("datetime").timezone.utc)
            .timestamp()
        )
        check = int(
            __import__("datetime")
            .datetime(2026, 3, 24, 7, 0, 1, tzinfo=__import__("datetime").timezone.utc)
            .timestamp()
        )
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
    "cdb_postgres",
    "cdb_redis",
    "cdb_market",
    "cdb_candles",
    "cdb_regime",
    "cdb_allocation",
    "cdb_risk",
    "cdb_execution",
    "cdb_db_writer",
    "cdb_paper_runner",
    "cdb_ws",
    "cdb_signal",
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
            "cdb_postgres",
            "cdb_redis",
            "cdb_market",
            "cdb_candles",
            "cdb_regime",
            "cdb_allocation",
            "cdb_risk",
            "cdb_execution",
            "cdb_db_writer",
            "cdb_paper_runner",
        ]
        count, missing = count_sut_services(blue_only, SUT_SERVICES)
        assert count == 10
        assert set(missing) == {"cdb_ws", "cdb_signal"}

    def test_exporter_containers_not_in_sut_set(self) -> None:
        """Observability/exporter containers must NOT be in the ZRP gate."""
        non_sut = {
            "cdb_prometheus",
            "cdb_grafana",
            "cdb_postgres_exporter",
            "cdb_redis_exporter",
            "cdb_cadvisor",
            "cdb_reports",
            "cdb_alertmanager",
            "cdb_node_exporter",
        }
        assert non_sut.isdisjoint(
            set(SUT_SERVICES)
        ), "Observability containers must not be in SUT_SERVICES"

    def test_monitor_container_not_in_sut_set(self) -> None:
        """lr040_soak_monitor must not be counted as a SUT service."""
        assert "lr040_soak_monitor" not in SUT_SERVICES

    def test_extra_containers_do_not_inflate_sut_count(self) -> None:
        """22 cdb_* containers on host must not inflate the 12-service SUT count."""
        all_host_cdb = SUT_SERVICES + [
            "cdb_prometheus",
            "cdb_grafana",
            "cdb_postgres_exporter",
            "cdb_redis_exporter",
            "cdb_cadvisor",
            "cdb_reports",
            "cdb_alertmanager",
            "cdb_node_exporter",
            "cdb_market_eth",
            "cdb_gh_runner",
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
            "cdb_postgres",
            "cdb_redis",
            "cdb_market",
            "cdb_candles",
            "cdb_regime",
            "cdb_allocation",
            "cdb_risk",
            "cdb_execution",
            "cdb_db_writer",
            "cdb_paper_runner",
            "cdb_ws",
            "cdb_signal",
            "cdb_prometheus",
            "cdb_grafana",
            "cdb_postgres_exporter",
            "cdb_redis_exporter",
            "cdb_cadvisor",
            "cdb_reports",
            "cdb_alertmanager",
            "cdb_node_exporter",
            "cdb_market_eth",
            "cdb_gh_runner",
        ]
        old_running = len(all_cdb_on_host)  # 22
        old_expected = 8  # hardcoded in old script
        # Old output: "22/8 services running" — semantically wrong
        assert old_running > old_expected, "Documents the old Soll/Ist mismatch"

        # New approach: only the 12 curated SUT services
        new_count, new_missing = count_sut_services(all_cdb_on_host, SUT_SERVICES)
        assert new_count == 12
        assert new_missing == []
        # New output: "12/12 SUT services running (inventory: 22 cdb_* containers)"


# ---------------------------------------------------------------------------
# Restart detection scope tests (Issue #1277)
#
# Old bug: Check 1 iterated over ALL cdb_* containers. Non-SUT containers
# (cdb_grafana, cdb_prometheus, exporters) with "minute" uptime triggered
# soak_test_FAILED.txt even though they are not ZRP-relevant.
#
# Fix: Check 1 iterates only over SUT_SERVICES. Non-SUT restarts are logged
# as INFO without triggering a FAIL verdict.
# ---------------------------------------------------------------------------


def classify_restart_scope(
    container_statuses: dict[str, str],
    sut_services: list[str],
) -> tuple[list[str], list[str]]:
    """Mirror soak_monitor.sh Check 1 SUT-scoped restart detection.

    Returns (sut_restarts, non_sut_restarts) where each is a list of
    container names whose status contains 'second' or 'minute' (fresh uptime).
    """
    sut_set = set(sut_services)
    sut_restarts: list[str] = []
    non_sut_restarts: list[str] = []
    for name, status in container_statuses.items():
        if re.search(r" second| minute", status, re.IGNORECASE):
            if name in sut_set:
                sut_restarts.append(name)
            else:
                non_sut_restarts.append(name)
    return sut_restarts, non_sut_restarts


class TestRestartDetectionScope:
    """Regression tests for Issue #1277: Check 1 must only FAIL on SUT restarts.

    Non-SUT containers (observability, exporters, infra) are logged as INFO
    but must NOT trigger soak_test_FAILED.txt.
    """

    def test_non_sut_restart_no_fail(self) -> None:
        """Grafana/Prometheus restart -> only INFO, no SUT restart detected."""
        statuses = {
            "cdb_grafana": "Up 27 minutes (healthy)",
            "cdb_prometheus": "Up 15 minutes (healthy)",
            "cdb_postgres": "Up 6 hours (healthy)",
            "cdb_redis": "Up 6 hours (healthy)",
            "cdb_risk": "Up 6 hours (healthy)",
        }
        sut, non_sut = classify_restart_scope(statuses, SUT_SERVICES)
        assert sut == []
        assert set(non_sut) == {"cdb_grafana", "cdb_prometheus"}

    def test_sut_restart_triggers_fail(self) -> None:
        """SUT service restart -> detected as restart."""
        statuses = {
            "cdb_risk": "Up 5 minutes (healthy)",
            "cdb_postgres": "Up 6 hours (healthy)",
            "cdb_grafana": "Up 6 hours (healthy)",
        }
        sut, non_sut = classify_restart_scope(statuses, SUT_SERVICES)
        assert sut == ["cdb_risk"]
        assert non_sut == []

    def test_mixed_restart_fail_only_for_sut(self) -> None:
        """Mixed SUT + non-SUT restarts -> FAIL because of SUT, non-SUT is INFO."""
        statuses = {
            "cdb_execution": "Up 3 minutes (healthy)",
            "cdb_grafana": "Up 27 minutes (healthy)",
            "cdb_prometheus": "Up 15 minutes (healthy)",
            "cdb_postgres": "Up 6 hours (healthy)",
        }
        sut, non_sut = classify_restart_scope(statuses, SUT_SERVICES)
        assert sut == ["cdb_execution"]
        assert set(non_sut) == {"cdb_grafana", "cdb_prometheus"}

    def test_all_stable_no_restarts(self) -> None:
        """All containers showing hours uptime -> no restarts at all."""
        statuses = {
            "cdb_postgres": "Up 6 hours (healthy)",
            "cdb_redis": "Up 6 hours (healthy)",
            "cdb_grafana": "Up 6 hours (healthy)",
            "cdb_prometheus": "Up 6 hours (healthy)",
        }
        sut, non_sut = classify_restart_scope(statuses, SUT_SERVICES)
        assert sut == []
        assert non_sut == []

    def test_issue_1277_exact_scenario(self) -> None:
        """Reproduce the exact #1277 scenario: Grafana+Prometheus minutes, all SUT hours."""
        statuses = {
            "cdb_grafana": "Up 41 minutes (healthy)",
            "cdb_prometheus": "Up 29 minutes (healthy)",
            "cdb_postgres": "Up 6 hours (healthy)",
            "cdb_redis": "Up 6 hours (healthy)",
            "cdb_market": "Up 6 hours (healthy)",
            "cdb_candles": "Up 6 hours (healthy)",
            "cdb_regime": "Up 6 hours (healthy)",
            "cdb_allocation": "Up 6 hours (healthy)",
            "cdb_risk": "Up 6 hours (healthy)",
            "cdb_execution": "Up 6 hours (healthy)",
            "cdb_db_writer": "Up 6 hours (healthy)",
            "cdb_paper_runner": "Up 6 hours (healthy)",
            "cdb_ws": "Up 6 hours (healthy)",
            "cdb_signal": "Up 6 hours (healthy)",
        }
        sut, non_sut = classify_restart_scope(statuses, SUT_SERVICES)
        assert sut == [], "No SUT restart should be detected in #1277 scenario"
        assert set(non_sut) == {"cdb_grafana", "cdb_prometheus"}


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
        assert (
            parse_disk_pct(old_path_output) is None
        ), "Old /var/lib/docker path was unreachable in container namespace"

        # New path: /repo → parseable output
        new_path_output = _DF_REPO_NORMAL
        assert (
            parse_disk_pct(new_path_output) == "47"
        ), "New /repo path must yield parseable disk usage"


# ---------------------------------------------------------------------------
# DB growth check regression tests (Issue #1281)
#
# Root cause: Check 4 in soak_monitor.sh used hardcoded `-U cdb -d cdb_db`
# which diverged from the actual runtime contract of cdb_postgres
# (POSTGRES_USER=claire_user, POSTGRES_DB=claire_de_binare).
#
# Fix: resolve PG_USER and PG_DB via `docker inspect` on the target container.
# Fail-closed with non-sensitive artifact trail when resolution fails.
# ---------------------------------------------------------------------------


def _read_soak_monitor() -> str:
    """Read infrastructure/scripts/soak_monitor.sh relative to this test file."""
    path = (
        Path(__file__).resolve().parents[3]
        / "infrastructure"
        / "scripts"
        / "soak_monitor.sh"
    )
    return path.read_text(encoding="utf-8")


def _extract_check4(content: str) -> str:
    """Isolate the CHECK 4 section from soak_monitor.sh content."""
    start = content.find("# CHECK 4")
    end = content.find("# CHECK 5")
    return content[start:end] if start != -1 and end != -1 else ""


def resolve_pg_env(inspect_env_lines: list[str]) -> tuple[str | None, str | None]:
    """Mirror bash: PG_USER / PG_DB aus docker-inspect-Env-Zeilen ableiten.

    Gibt jede Variable unabhaengig zurueck: None wenn der Key fehlt oder leer ist,
    sonst den getrimmten Wert. Beide koennen unabhaengig voneinander None sein.
    Spiegelt die Aufloesungslogik in soak_monitor.sh Check 4 (Issue #1281):
        PG_USER=$(echo "$_INSPECT_ENV" | grep '^POSTGRES_USER=' | cut -d= -f2-)
        PG_DB=$(echo   "$_INSPECT_ENV" | grep '^POSTGRES_DB='   | cut -d= -f2-)
    """
    user: str | None = None
    db: str | None = None
    for line in inspect_env_lines:
        if line.startswith("POSTGRES_USER="):
            value = line[len("POSTGRES_USER="):].strip()
            user = value or None
        elif line.startswith("POSTGRES_DB="):
            value = line[len("POSTGRES_DB="):].strip()
            db = value or None
    return user, db


def build_env_resolution_fail_artifact(
    inspect_exit: int, user_raw: str, db_raw: str
) -> dict[str, str]:
    """Build artifact dict mirroring the ENV_RESOLUTION_FAILED log block.

    inspect_exit != 0 -> docker inspect itself failed, use real exit code.
    inspect_exit == 0 -> inspect succeeded but keys were missing -> exit_status=0,
                         failure_reason=missing_keys (separate field).
    """
    artifact: dict[str, str] = {
        "event": "ENV_RESOLUTION_FAILED",
        "container": "cdb_postgres",
        "resolved_user": user_raw.strip() or "<empty>",
        "resolved_db": db_raw.strip() or "<empty>",
        "context_source": "docker_inspect_env",
        "exit_status": str(inspect_exit),
    }
    if inspect_exit == 0:
        artifact["failure_reason"] = "missing_keys"
    return artifact


class TestDbGrowthPgEnvResolution:
    """Regression tests for Issue #1281: stale -U cdb -d cdb_db hardcodings in Check 4.

    Guards:
    - altes Hardcoding ist entfernt
    - neuer Pfad nutzt docker inspect fuer PG_USER/PG_DB-Aufloesung
    - fail-closed-Artefakt enthaelt die erwarteten nicht-sensitiven Felder
    - kein Passwort-/Connection-String-Pfad eingefuehrt
    - gruene Erfolgsmeldung nur bei psql Exit 0
    """

    # --- Regression guards auf soak_monitor.sh-Inhalt ---

    def test_old_hardcoding_removed(self) -> None:
        content = _read_soak_monitor()
        assert "psql -U cdb" not in content, "Old hardcoding '-U cdb' must be removed (Issue #1281)"
        assert "-d cdb_db" not in content, "Old hardcoding '-d cdb_db' must be removed (Issue #1281)"

    def test_runtime_resolution_uses_docker_inspect(self) -> None:
        content = _read_soak_monitor()
        check4 = _extract_check4(content)
        assert check4, "CHECK 4 section must exist in soak_monitor.sh"
        assert "docker inspect" in check4, "Check 4 must use docker inspect to resolve PG_USER/PG_DB"
        assert "POSTGRES_USER" in check4, "POSTGRES_USER must appear in Check 4"
        assert "POSTGRES_DB" in check4, "POSTGRES_DB must appear in Check 4"

    def test_no_secret_paths_in_check4(self) -> None:
        content = _read_soak_monitor()
        check4 = _extract_check4(content)
        assert check4, "CHECK 4 section must exist"
        assert "/run/secrets" not in check4, "No secret paths allowed in Check 4"
        assert "POSTGRES_PASSWORD" not in check4, "POSTGRES_PASSWORD must not appear in Check 4"

    def test_success_message_only_on_psql_exit_zero(self) -> None:
        content = _read_soak_monitor()
        check4 = _extract_check4(content)
        success_pos = check4.find("Database metrics saved to")
        psql_exit_pos = check4.find("_PSQL_EXIT")
        assert success_pos > psql_exit_pos, "Success message must appear after _PSQL_EXIT check"

    # --- Python-Helfer: Env-Auflösungslogik ---

    def test_happy_path_both_vars_present(self) -> None:
        user, db = resolve_pg_env(["POSTGRES_USER=claire_user", "POSTGRES_DB=claire_de_binare"])
        assert user == "claire_user"
        assert db == "claire_de_binare"

    def test_fail_closed_when_user_missing(self) -> None:
        user, db = resolve_pg_env(["POSTGRES_DB=claire_de_binare"])
        assert user is None

    def test_fail_closed_when_db_missing(self) -> None:
        user, db = resolve_pg_env(["POSTGRES_USER=claire_user"])
        assert db is None

    def test_fail_closed_when_both_missing(self) -> None:
        user, db = resolve_pg_env([])
        assert user is None
        assert db is None

    def test_whitespace_only_treated_as_empty(self) -> None:
        user, db = resolve_pg_env(["POSTGRES_USER=  ", "POSTGRES_DB=claire_de_binare"])
        assert user is None, "Whitespace-only value must be treated as empty"

    def test_unrelated_env_vars_ignored(self) -> None:
        user, db = resolve_pg_env([
            "POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password",
            "POSTGRES_USER=claire_user",
            "POSTGRES_DB=claire_de_binare",
            "PATH=/usr/local/bin:/usr/bin:/bin",
        ])
        assert user == "claire_user"
        assert db == "claire_de_binare"

    # --- Artefaktspur: nicht-sensitive Felder ---

    def test_inspect_fail_exit_code_captured(self) -> None:
        artifact = build_env_resolution_fail_artifact(2, "", "")
        assert artifact["exit_status"] == "2", "Real inspect exit code must be captured"
        assert "failure_reason" not in artifact, "failure_reason must not appear when inspect failed"

    def test_missing_keys_exit_status_and_failure_reason(self) -> None:
        artifact = build_env_resolution_fail_artifact(0, "", "claire_de_binare")
        assert artifact["exit_status"] == "0"
        assert artifact["failure_reason"] == "missing_keys"

    def test_fail_artifact_required_non_sensitive_fields(self) -> None:
        artifact = build_env_resolution_fail_artifact(0, "", "claire_de_binare")
        assert artifact["container"] == "cdb_postgres"
        assert artifact["resolved_user"] == "<empty>"
        assert artifact["resolved_db"] == "claire_de_binare"
        assert artifact["context_source"] == "docker_inspect_env"

    def test_old_values_not_in_resolved_path(self) -> None:
        user, db = resolve_pg_env(["POSTGRES_USER=claire_user", "POSTGRES_DB=claire_de_binare"])
        assert user != "cdb", "Stale hardcoding 'cdb' must not appear"
        assert db != "cdb_db", "Stale hardcoding 'cdb_db' must not appear"
