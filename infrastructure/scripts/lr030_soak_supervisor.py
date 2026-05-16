#!/usr/bin/env python3
"""LR-030 Shadow/Soak Early-Fail Supervisor.

Read-only gate. Inspects a soak artifact directory and reports status within
the first hour so a bad run is visible early, not after >24h review.

No runtime mutation. No Docker interaction. No GitHub writes.

Exit codes:
  0 — RUNNING_VALID  (all checks pass so far)
  1 — FAILED_EARLY | INCONCLUSIVE_EARLY | INVALID_EVIDENCE |
      MONITOR_DEAD | ARTIFACT_CONTRACT_BROKEN
  2 — CLI / usage error

Related: Issue #2440, PR #2484, PR #2485.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Status codes
# ---------------------------------------------------------------------------
RUNNING_VALID = "RUNNING_VALID"
FAILED_EARLY = "FAILED_EARLY"
INCONCLUSIVE_EARLY = "INCONCLUSIVE_EARLY"
INVALID_EVIDENCE = "INVALID_EVIDENCE"
MONITOR_DEAD = "MONITOR_DEAD"
ARTIFACT_CONTRACT_BROKEN = "ARTIFACT_CONTRACT_BROKEN"

_STATUS_SEVERITY: dict[str, int] = {
    ARTIFACT_CONTRACT_BROKEN: 5,
    FAILED_EARLY: 4,
    INCONCLUSIVE_EARLY: 3,
    INVALID_EVIDENCE: 2,
    MONITOR_DEAD: 1,
    RUNNING_VALID: 0,
}

# Each check name maps to the status it raises when the check fails.
_CHECK_STATUS: dict[str, str] = {
    "artifact_path_prefix_valid": ARTIFACT_CONTRACT_BROKEN,
    "run_intent_is_lr030": ARTIFACT_CONTRACT_BROKEN,
    "no_failed_marker": FAILED_EARLY,
    "no_hard_restart_patterns": FAILED_EARLY,
    "no_inconclusive_marker": INCONCLUSIVE_EARLY,
    "no_env_interruption_patterns": INCONCLUSIVE_EARLY,
    "no_template_placeholders": INVALID_EVIDENCE,
    "shadow_block_probe_valid": INVALID_EVIDENCE,
    "hourly_checks_log_present": MONITOR_DEAD,
    "hourly_checks_log_valid": MONITOR_DEAD,
}

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_HOURLY_DEADLINE_MINUTES = 75
SCHEMA_VERSION = "1.0"

# Artifact directory name must be exactly soak_lr030_YYYYMMDD_HHMMSS.
_DIR_NAME_RE = re.compile(r"^soak_lr030_(\d{8})_(\d{6})$")

# SUT_RESTART = explicitly classified SUT restart → always FAILED_EARLY.
_SUT_RESTART_RE = re.compile(r"SUT_RESTART", re.IGNORECASE)

# RESTART DETECTED: <service> is emitted by soak_monitor.sh for each container
# restart before the final classification is written.  When ENVIRONMENT_INTERRUPTION
# also appears in the same log the raw lines are precursors to the bulk-restart
# marker and must be treated as INCONCLUSIVE_EARLY context; when it is absent they
# indicate a standalone SUT restart → FAILED_EARLY.
_RAW_RESTART_RE = re.compile(r"RESTART DETECTED", re.IGNORECASE)

# ENVIRONMENT_INTERRUPTION = host-level OS/VM or bulk-Docker reboot → INCONCLUSIVE_EARLY.
_ENV_INTERRUPTION_RE = re.compile(r"ENVIRONMENT_INTERRUPTION", re.IGNORECASE)

# Hourly checkpoint line format written by soak_monitor.sh:
#   "2026-05-16 13:00:00 UTC - Hour 1: No restarts"
_HOUR_RE = re.compile(r"\bHour (\d+):")

# Exact un-expanded script-variable tokens that indicate broken checkpoint reporting.
# Not generic angle-bracket matching to avoid false positives on log content.
# Tokens from Issue #2440 old-run evidence backfill: <zero_execution_ok> and
# <execution_orders_filled_total=0.> are known unresolved placeholders from that run.
_PLACEHOLDER_RE = re.compile(
    r"\$runId|\$artifactDir|\$\{checkpoint\}|<checkpoint-1-ok>|<ja>|<nein>"
    r"|<zero_execution_ok>|<execution_orders_filled_total=0\.>"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_run_start(artifact_name: str) -> Optional[datetime]:
    m = _DIR_NAME_RE.match(artifact_name)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _elapsed_minutes(artifact_name: str, as_of: datetime) -> Optional[float]:
    start = _parse_run_start(artifact_name)
    if start is None or as_of < start:
        return None
    return (as_of - start).total_seconds() / 60.0


def _is_monotone_increasing(values: list[int]) -> bool:
    """True only when the sequence is non-empty and strictly increasing."""
    if not values:
        return False
    return all(values[i] < values[i + 1] for i in range(len(values) - 1))


def _find_placeholder_hits(artifact_path: Path) -> list[dict[str, str]]:
    """Scan .txt and .json files in the artifact directory for template tokens."""
    hits: list[dict[str, str]] = []
    for p in sorted(artifact_path.iterdir()):
        if not (p.is_file() and p.suffix in {".txt", ".json"}):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in _PLACEHOLDER_RE.finditer(text):
            hits.append({"file": p.name, "match": m.group()})
    return hits


def _check_shadow_probe(probe_file: Path) -> bool:
    """Return True when probe_file contains an auditable REJECTED result with zero fills."""
    if not probe_file.is_file():
        return False
    try:
        data = json.loads(probe_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    order_result_found = bool(data.get("order_result_found"))
    order_result = data.get("order_result")
    if not isinstance(order_result, dict):
        return False
    # A valid shadow-block proof must show the order was REJECTED *and* that
    # nothing was filled.  A non-zero filled_quantity would contradict the
    # zero-execution guarantee even if the status field reads "REJECTED".
    # Normalize to Decimal: Redis xrevrange returns stream field values as
    # strings ("0.0"), so a plain == 0 comparison would reject valid evidence.
    raw_fill = order_result.get("filled_quantity", 1)
    try:
        filled_qty = Decimal(str(raw_fill))
    except InvalidOperation:
        filled_qty = Decimal(1)  # fail-closed: unparseable → treat as non-zero
    return (
        order_result_found
        and order_result.get("status") == "REJECTED"
        and filled_qty == Decimal(0)
    )


def _determine_status(failures: list[dict[str, str]]) -> str:
    if not failures:
        return RUNNING_VALID
    worst_severity = max(
        _STATUS_SEVERITY.get(_CHECK_STATUS.get(f["check"], RUNNING_VALID), 0)
        for f in failures
    )
    return next(
        s
        for s, sev in sorted(_STATUS_SEVERITY.items(), key=lambda kv: -kv[1])
        if sev == worst_severity
    )


# ---------------------------------------------------------------------------
# Core evaluation (importable for unit tests)
# ---------------------------------------------------------------------------


def evaluate(
    artifact_path: Path,
    as_of: datetime,
    hourly_deadline_minutes: int = DEFAULT_HOURLY_DEADLINE_MINUTES,
    require_shadow_block_probe: bool = False,
) -> dict:
    """Evaluate artifact_path and return a result dict.

    Runs all checks unconditionally and accumulates failures; the overall
    status reflects the highest-severity failure found.
    """
    failures: list[dict[str, str]] = []
    checks: dict[str, Optional[bool]] = {}

    artifact_name = artifact_path.name
    elapsed = _elapsed_minutes(artifact_name, as_of)

    # 1. Artifact directory name must match soak_lr030_YYYYMMDD_HHMMSS.
    path_valid = bool(_DIR_NAME_RE.match(artifact_name))
    checks["artifact_path_prefix_valid"] = path_valid
    if not path_valid:
        failures.append(
            {
                "check": "artifact_path_prefix_valid",
                "detail": f"'{artifact_name}' does not match soak_lr030_YYYYMMDD_HHMMSS",
            }
        )

    # 2. run_intent.txt must contain exactly 'lr030'.
    intent_file = artifact_path / "run_intent.txt"
    run_intent: Optional[str] = None
    if intent_file.is_file():
        run_intent = intent_file.read_text(encoding="utf-8").strip()
    intent_valid = run_intent == "lr030"
    checks["run_intent_is_lr030"] = intent_valid
    if not intent_valid:
        failures.append(
            {
                "check": "run_intent_is_lr030",
                "detail": f"run_intent.txt contains {run_intent!r}, expected 'lr030'",
            }
        )

    # 3. Hard failure marker.
    failed_marker = (artifact_path / "soak_test_FAILED.txt").is_file()
    checks["no_failed_marker"] = not failed_marker
    if failed_marker:
        failures.append(
            {
                "check": "no_failed_marker",
                "detail": "soak_test_FAILED.txt is present",
            }
        )

    # 4. restart_alerts.log — split by severity.
    restart_log = artifact_path / "restart_alerts.log"
    hard_hits: list[str] = []
    soft_hits: list[str] = []
    if restart_log.is_file():
        content = restart_log.read_text(encoding="utf-8", errors="replace")
        sut_hits = list(set(_SUT_RESTART_RE.findall(content)))
        raw_hits = list(set(_RAW_RESTART_RE.findall(content)))
        env_hits = list(set(_ENV_INTERRUPTION_RE.findall(content)))
        if env_hits:
            # ENVIRONMENT_INTERRUPTION present: RESTART DETECTED lines are
            # precursors written by soak_monitor.sh before the bulk-restart
            # classification; treat them as part of the env-interruption context.
            hard_hits = sut_hits
            soft_hits = env_hits + raw_hits
        else:
            # No environment interruption: RESTART DETECTED is a standalone SUT restart.
            hard_hits = sut_hits + raw_hits
            soft_hits = []

    checks["no_hard_restart_patterns"] = not bool(hard_hits)
    if hard_hits:
        failures.append(
            {
                "check": "no_hard_restart_patterns",
                "detail": f"restart_alerts.log contains SUT_RESTART patterns: {hard_hits}",
            }
        )

    # 5. Inconclusive marker (environment-interruption class).
    inconclusive_marker = (artifact_path / "soak_test_INCONCLUSIVE.txt").is_file()
    checks["no_inconclusive_marker"] = not inconclusive_marker
    if inconclusive_marker:
        failures.append(
            {
                "check": "no_inconclusive_marker",
                "detail": "soak_test_INCONCLUSIVE.txt is present",
            }
        )

    # 6. Environment-interruption patterns in restart log.
    checks["no_env_interruption_patterns"] = not bool(soft_hits)
    if soft_hits:
        failures.append(
            {
                "check": "no_env_interruption_patterns",
                "detail": f"restart_alerts.log contains environment interruption patterns: {soft_hits}",
            }
        )

    # 7. Template placeholders in .txt / .json files.
    placeholder_hits = _find_placeholder_hits(artifact_path)
    checks["no_template_placeholders"] = not bool(placeholder_hits)
    if placeholder_hits:
        failures.append(
            {
                "check": "no_template_placeholders",
                "detail": (
                    f"un-expanded script variables in {len(placeholder_hits)} location(s): "
                    f"{placeholder_hits[:3]}"
                ),
            }
        )

    # 8. hourly_checks.log presence (required after deadline) and validity.
    hourly_log = artifact_path / "hourly_checks.log"
    hourly_present = hourly_log.is_file()
    past_deadline = elapsed is not None and elapsed >= hourly_deadline_minutes

    if hourly_present:
        hourly_text = hourly_log.read_text(encoding="utf-8", errors="replace")
        hourly_hours = [int(m) for m in _HOUR_RE.findall(hourly_text)]
        hourly_valid = _is_monotone_increasing(hourly_hours)
        checks["hourly_checks_log_present"] = True
        checks["hourly_checks_log_valid"] = hourly_valid
        if not hourly_valid:
            failures.append(
                {
                    "check": "hourly_checks_log_valid",
                    "detail": (
                        f"hourly_checks.log has no valid monotone Hour N sequence; "
                        f"hours found: {hourly_hours}"
                    ),
                }
            )
    else:
        hourly_hours = []
        checks["hourly_checks_log_present"] = False if past_deadline else None
        checks["hourly_checks_log_valid"] = None
        if past_deadline:
            failures.append(
                {
                    "check": "hourly_checks_log_present",
                    "detail": (
                        f"hourly_checks.log missing after {elapsed:.0f} min "
                        f"(deadline: {hourly_deadline_minutes} min)"
                    ),
                }
            )

    # 9. Optional shadow-block-probe.
    if require_shadow_block_probe:
        probe_valid = _check_shadow_probe(artifact_path / "shadow_block_probe.json")
        checks["shadow_block_probe_valid"] = probe_valid
        if not probe_valid:
            failures.append(
                {
                    "check": "shadow_block_probe_valid",
                    "detail": (
                        "shadow_block_probe.json missing or lacks auditable REJECTED result"
                    ),
                }
            )
    else:
        checks["shadow_block_probe_valid"] = None  # not required

    return {
        "schema_version": SCHEMA_VERSION,
        "status": _determine_status(failures),
        "artifact_path": str(artifact_path),
        "run_intent": run_intent,
        "elapsed_minutes": round(elapsed, 1) if elapsed is not None else None,
        "hourly_check_count": len(hourly_hours),
        "hourly_hours_logged": hourly_hours,
        "checks": checks,
        "failures": failures,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "LR-030 Shadow/Soak Early-Fail Supervisor. Read-only. "
            "Exit 0: RUNNING_VALID. Exit 1: failure state. Exit 2: CLI error."
        )
    )
    p.add_argument(
        "artifact_path",
        help=(
            "Path to the LR-030 soak run directory "
            "(must match artifacts/soak_lr030_YYYYMMDD_HHMMSS)."
        ),
    )
    p.add_argument(
        "--hourly-deadline-minutes",
        type=int,
        default=DEFAULT_HOURLY_DEADLINE_MINUTES,
        metavar="MINUTES",
        help=(
            f"Minutes after run start before hourly_checks.log is required "
            f"(default: {DEFAULT_HOURLY_DEADLINE_MINUTES})."
        ),
    )
    p.add_argument(
        "--require-shadow-block-probe",
        action="store_true",
        help="Require shadow_block_probe.json with an auditable REJECTED result.",
    )
    p.add_argument(
        "--as-of",
        default=None,
        metavar="ISO_TIMESTAMP",
        help=(
            "Treat this UTC ISO-8601 timestamp as 'now' for elapsed-time checks "
            "(testing convenience; default: current UTC time)."
        ),
    )
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    artifact_path = Path(args.artifact_path)
    if not artifact_path.is_dir():
        result: dict = {
            "schema_version": SCHEMA_VERSION,
            "status": ARTIFACT_CONTRACT_BROKEN,
            "artifact_path": str(artifact_path),
            "error": f"artifact directory does not exist: {artifact_path}",
            "failures": [
                {"check": "artifact_path_exists", "detail": "directory not found"}
            ],
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    if args.as_of is not None:
        try:
            raw = datetime.fromisoformat(args.as_of)
            as_of: datetime = (
                raw if raw.tzinfo is not None else raw.replace(tzinfo=timezone.utc)
            )
        except ValueError:
            print(f"ERROR: invalid --as-of value: {args.as_of!r}", file=sys.stderr)
            sys.exit(2)
    else:
        as_of = datetime.now(timezone.utc)

    result = evaluate(
        artifact_path=artifact_path,
        as_of=as_of,
        hourly_deadline_minutes=args.hourly_deadline_minutes,
        require_shadow_block_probe=args.require_shadow_block_probe,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["status"] == RUNNING_VALID else 1)


if __name__ == "__main__":
    main()
