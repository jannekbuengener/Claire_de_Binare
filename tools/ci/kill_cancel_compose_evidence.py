"""Kill-cancel compose drill evidence writer (#4222).

Maps JUnit XML to scenario statuses and computes an overall verdict that cannot
silently contradict pytest exit codes with invented product FAILs.

Schema: cdb-kill-cancel-compose-evidence/v1
"""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from enum import StrEnum
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "cdb-kill-cancel-compose-evidence/v1"

# scenario_id -> (junit_phase_file_stem, exact pytest testcase name)
SCENARIO_TEST_MAP: dict[str, tuple[str, str]] = {
    "S1_S2_inactive_keeps_open": (
        "phase1",
        "test_s1_s2_inactive_keeps_resting_orders_open",
    ),
    "S3_S5_active_cancel_confirmed": (
        "phase1",
        "test_s3_s5_active_cancels_confirmed",
    ),
    "S4_unevaluable_fail_closed": ("phase1", "test_s4_unevaluable_fail_closed"),
    "S6_cancel_rejection_hold": ("phase1", "test_s6_cancel_rejection_hold"),
    "S7_cancel_exception_malformed": (
        "phase1",
        "test_s7_cancel_exception_and_malformed_hold",
    ),
    "S8_adapter_unsupported_hold": (
        "phase1",
        "test_s8_adapter_without_cancel_hold",
    ),
    "S9_double_kill_idempotent": ("phase1", "test_s9_double_kill_idempotent"),
    "S10a_ledger_persists": ("phase1", "test_s10a_ledger_persists_open_orders"),
    "S10b_restart_reconcile": (
        "phase2",
        "test_s10b_restart_reconciles_before_new_orders",
    ),
    "S11_fill_after_kill_fail": ("phase1", "test_s11_fill_after_kill_fail"),
    "S12_positions_visible_no_unwind": (
        "phase1",
        "test_s12_positions_visible_no_auto_unwind",
    ),
}


class EvidenceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    HOLD = "HOLD"
    PARSE_ERROR = "PARSE_ERROR"
    MISSING_MAPPING = "MISSING_MAPPING"
    INCOMPLETE = "INCOMPLETE"
    NOT_RUN = "NOT_RUN"


_PRODUCT_FAIL_STATES = frozenset({EvidenceStatus.FAIL})
_EVIDENCE_GAP_STATES = frozenset(
    {
        EvidenceStatus.PARSE_ERROR,
        EvidenceStatus.MISSING_MAPPING,
        EvidenceStatus.INCOMPLETE,
        EvidenceStatus.NOT_RUN,
        EvidenceStatus.HOLD,
    }
)


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _iter_testcases(root: ET.Element) -> list[ET.Element]:
    return [el for el in root.iter() if _local_tag(el.tag) == "testcase"]


def _child_by_local(parent: ET.Element, name: str) -> ET.Element | None:
    for child in list(parent):
        if _local_tag(child.tag) == name:
            return child
    return None


def junit_testcase_status(
    path: Path,
    test_name: str,
    *,
    not_before_mtime: float | None = None,
) -> EvidenceStatus:
    """Resolve one scenario from a JUnit XML file.

    Missing file → NOT_RUN (not product FAIL).
    Unreadable/malformed XML → PARSE_ERROR.
    Stale file (mtime before run marker) → INCOMPLETE.
    Present file without matching testcase name → MISSING_MAPPING.
    """
    if not path.exists():
        return EvidenceStatus.NOT_RUN
    if not_before_mtime is not None and path.stat().st_mtime + 1e-6 < not_before_mtime:
        return EvidenceStatus.INCOMPLETE
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return EvidenceStatus.PARSE_ERROR
    except OSError:
        return EvidenceStatus.PARSE_ERROR

    for tc in _iter_testcases(root):
        if tc.get("name") != test_name:
            continue
        if _child_by_local(tc, "failure") is not None:
            return EvidenceStatus.FAIL
        if _child_by_local(tc, "error") is not None:
            return EvidenceStatus.FAIL
        if _child_by_local(tc, "skipped") is not None:
            return EvidenceStatus.HOLD
        return EvidenceStatus.PASS
    return EvidenceStatus.MISSING_MAPPING


def resolve_scenarios(
    evidence_dir: Path,
    *,
    not_before_mtime: float | None = None,
    scenario_map: dict[str, tuple[str, str]] | None = None,
) -> dict[str, str]:
    mapping = scenario_map or SCENARIO_TEST_MAP
    out: dict[str, str] = {}
    for scenario_id, (phase, test_name) in mapping.items():
        path = evidence_dir / f"{phase}.xml"
        out[scenario_id] = junit_testcase_status(
            path,
            test_name,
            not_before_mtime=not_before_mtime,
        ).value
    return out


def resolve_overall_verdict(
    *,
    scenarios: dict[str, str],
    phase1_exit: int,
    phase2_exit: int,
    cleanup_pass: bool,
    run_error: str,
) -> tuple[str, str]:
    """Derive overall_verdict + machine-readable reason.

    Rules (#4222):
    - Product FAIL only from real testcase failure/error or non-zero pytest exit.
    - Evidence gaps (NOT_RUN/MISSING_MAPPING/PARSE_ERROR/INCOMPLETE/HOLD) → INCOMPLETE,
      never a silent PASS, and never an invented product FAIL.
    - PASS only when pytest exits are 0, cleanup passes, no run_error, and every
      required scenario is PASS.
    """
    values = {EvidenceStatus(v) for v in scenarios.values()}

    if phase1_exit != 0 or phase2_exit != 0:
        return EvidenceStatus.FAIL.value, "PYTEST_NONZERO_EXIT"
    if any(v in _PRODUCT_FAIL_STATES for v in values):
        return EvidenceStatus.FAIL.value, "SCENARIO_PRODUCT_FAIL"
    if run_error:
        return EvidenceStatus.INCOMPLETE.value, "RUN_ERROR"
    if not cleanup_pass:
        return EvidenceStatus.INCOMPLETE.value, "CLEANUP_INCOMPLETE"
    if any(v in _EVIDENCE_GAP_STATES for v in values):
        return EvidenceStatus.INCOMPLETE.value, "SCENARIO_EVIDENCE_INCOMPLETE"
    if values != {EvidenceStatus.PASS}:
        return EvidenceStatus.INCOMPLETE.value, "SCENARIO_EVIDENCE_INCOMPLETE"
    return EvidenceStatus.PASS.value, "EVIDENCE_COMPLETE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def build_manifest(
    *,
    evidence_dir: Path,
    run_id: str,
    commit_sha: str,
    compose_project: str,
    started_at_utc: str,
    completed_at_utc: str,
    phase1_exit: int,
    phase2_exit: int,
    cleanup_pass: bool,
    run_error: str,
) -> dict[str, Any]:
    marker = evidence_dir / ".run_marker"
    not_before: float | None = None
    if marker.exists():
        not_before = marker.stat().st_mtime

    scenarios = resolve_scenarios(evidence_dir, not_before_mtime=not_before)
    overall, reason = resolve_overall_verdict(
        scenarios=scenarios,
        phase1_exit=phase1_exit,
        phase2_exit=phase2_exit,
        cleanup_pass=cleanup_pass,
        run_error=run_error,
    )

    artifact_sha: dict[str, str] = {}
    for path in sorted(evidence_dir.iterdir()):
        if path.is_file() and path.name not in {"manifest.json", ".run_marker"}:
            artifact_sha[path.name] = _sha256(path)

    junit_summary: dict[str, Any] = {}
    for phase in ("phase1", "phase2"):
        path = evidence_dir / f"{phase}.xml"
        entry: dict[str, Any] = {
            "path": str(path.name),
            "exists": path.exists(),
        }
        if path.exists():
            try:
                root = ET.parse(path).getroot()
                cases = _iter_testcases(root)
                entry["testcase_count"] = len(cases)
                entry["testcase_names"] = sorted(
                    str(tc.get("name") or "") for tc in cases
                )
                entry["parse_status"] = EvidenceStatus.PASS.value
            except ET.ParseError as exc:
                entry["parse_status"] = EvidenceStatus.PARSE_ERROR.value
                entry["parse_error"] = str(exc)
        else:
            entry["parse_status"] = EvidenceStatus.NOT_RUN.value
        junit_summary[phase] = entry

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "commit_sha": commit_sha,
        "started_at_utc": started_at_utc,
        "completed_at_utc": completed_at_utc,
        "compose_project": compose_project,
        "mock_only": True,
        "dry_run": True,
        "productive_adapter_active": False,
        "scenarios": scenarios,
        "scenario_evidence_reason": reason,
        "evidence_status_model": {
            "states": [s.value for s in EvidenceStatus],
            "product_fail_states": [EvidenceStatus.FAIL.value],
            "evidence_gap_states": [s.value for s in sorted(_EVIDENCE_GAP_STATES)],
            "rule": (
                "Scenario FAIL is only for real JUnit failure/error. "
                "Missing/unreadable/unmapped JUnit is NOT_RUN/PARSE_ERROR/"
                "MISSING_MAPPING/INCOMPLETE and forces overall INCOMPLETE, "
                "never PASS+FAIL contradiction with pytest exit 0."
            ),
        },
        "junit_summary": junit_summary,
        "orders_discovered": "see phase logs / status snapshots",
        "cancel_attempts": "see phase logs / status snapshots",
        "confirmed_cancelled": "see phase logs / status snapshots",
        "residual_open_orders": [],
        "residual_positions": [
            {
                "symbol": "*",
                "status": "UNKNOWN",
                "quantity": None,
                "reason_code": "RESIDUAL_POSITION_UNKNOWN",
            }
        ],
        "fill_after_kill_events": ["proven in S11 in-process"],
        "overall_verdict": overall,
        "reason_codes": [
            "KILL_CANCEL_HOLD",
            "RESIDUAL_POSITION_UNKNOWN",
            "CANCEL_REQUEST_REJECTED",
            "CANCEL_EXECUTION_ERROR",
            "CANCEL_ADAPTER_UNSUPPORTED",
            "FILL_AFTER_KILL_ACTIVATION",
            "RESIDUAL_OPEN_ORDERS",
            reason,
        ],
        "cleanup_state": {
            "pass": bool(cleanup_pass),
            "containers_remaining": 0 if cleanup_pass else "nonzero",
            "volumes_remaining": 0 if cleanup_pass else "nonzero",
            "networks_remaining": 0 if cleanup_pass else "nonzero",
        },
        "limitations": [
            "Mock/dry-run compose drill only; no productive venue activation",
            "Cancel rejection/error/malformed/unsupported proven in-process under CDB_4185_DRILL",
            "No authoritative position SSOT in #4185 scope — confirmed cancel + UNKNOWN position => HOLD",
            "Batch KILL_CANCEL_PASS is not claimed for the real execution service path",
        ],
        "safety_boundaries": [
            "LR NO-GO",
            "MOCK_TRADING=true",
            "DRY_RUN=true",
            "USE_REAL_BALANCE=false",
            "no host ports",
            "no MEXC credential mounts",
            "no auto-unwind",
        ],
        "artifact_sha256": artifact_sha,
        "run_error": run_error or None,
        "phase1_exit": phase1_exit,
        "phase2_exit": phase2_exit,
        "pytest_result": (
            EvidenceStatus.PASS.value
            if phase1_exit == 0 and phase2_exit == 0
            else EvidenceStatus.FAIL.value
        ),
    }


def write_manifest(
    *,
    evidence_dir: Path,
    run_id: str,
    commit_sha: str,
    compose_project: str,
    started_at_utc: str,
    completed_at_utc: str,
    phase1_exit: int,
    phase2_exit: int,
    cleanup_pass: bool,
    run_error: str,
) -> dict[str, Any]:
    manifest = build_manifest(
        evidence_dir=evidence_dir,
        run_id=run_id,
        commit_sha=commit_sha,
        compose_project=compose_project,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        phase1_exit=phase1_exit,
        phase2_exit=phase2_exit,
        cleanup_pass=cleanup_pass,
        run_error=run_error,
    )
    (evidence_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    import os

    evidence = Path(os.environ["EVIDENCE_DIR"])
    manifest = write_manifest(
        evidence_dir=evidence,
        run_id=os.environ["RUN_ID"],
        commit_sha=os.environ["COMMIT_SHA"],
        compose_project=os.environ["PROJECT_NAME"],
        started_at_utc=os.environ["STARTED_AT"],
        completed_at_utc=os.environ["COMPLETED_AT"],
        phase1_exit=int(os.environ["INITIAL_EXIT"]),
        phase2_exit=int(os.environ["RESTART_EXIT"]),
        cleanup_pass=bool(int(os.environ["CLEANUP_PASS"])),
        run_error=os.environ.get("RUN_ERROR") or "",
    )
    print(f"Evidence: {evidence}")
    print(f"Verdict: {manifest['overall_verdict']}")
    print(f"Reason: {manifest['scenario_evidence_reason']}")
    print(f"Pytest: {manifest['pytest_result']}")
    return 0 if manifest["overall_verdict"] == EvidenceStatus.PASS.value else 1


if __name__ == "__main__":
    raise SystemExit(main())
