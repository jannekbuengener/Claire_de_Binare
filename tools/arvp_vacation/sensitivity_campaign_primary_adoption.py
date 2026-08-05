"""Primary evidence adoption / inventory for #4153 (post-primary transition).

Schema: cdb.sensitivity_campaign_primary_evidence_adoption.v1
LR: NO-GO. Does not rewrite primary result.json artefacts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow

from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_ENVELOPE_NAME,
    CAMPAIGN_PHASE_BLOCKED,
    CAMPAIGN_PHASE_PLANNED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
    CampaignBindings,
    atomic_write_json,
    count_primary_succeeded,
    read_campaign_phase,
    read_json,
    update_campaign_phase,
)

ADOPTION_SCHEMA_VERSION = "cdb.sensitivity_campaign_primary_evidence_adoption.v1"
INVENTORY_NAME = "primary_evidence_inventory.json"

VERDICT_PRIMARY_COMPLETE = "PRIMARY_EVIDENCE_COMPLETE"
VERDICT_INCOMPLETE = "HOLD_PRIMARY_RESULT_SET_INCOMPLETE"
VERDICT_BINDING = "HOLD_PRIMARY_BINDING_MISMATCH"
VERDICT_FOREIGN = "HOLD_PRIMARY_FOREIGN_OR_DUPLICATE_RESULTS"
VERDICT_STATE = "HOLD_PRIMARY_STATE_INCONSISTENT"

ADOPT_WITH_RECORD = "ADOPT_PRIMARY_EVIDENCE_WITH_EXPLICIT_TRANSITION_RECORD"
REPRO_MAY_RUN = "REPRODUCTION_MAY_RUN_AGAINST_EXISTING_PRIMARY_NAMESPACE"
HOLD_BINDING = "HOLD_BINDING_DRIFT_UNRESOLVED"


class SensitivityAdoptionError(ValueError):
    """Fail-closed primary-evidence adoption error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {detail}" if detail else reason_code)


def run_key_digest(run_keys: Sequence[str]) -> str:
    """Canonical digest over sorted run keys (order-independent)."""
    body = "\n".join(sorted(str(k) for k in run_keys)).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def inventory_path(evidence_root: Path) -> Path:
    return Path(evidence_root) / INVENTORY_NAME


def _utcnow_iso() -> str:
    now = cdb_utcnow()
    return now.astimezone(now.tzinfo).isoformat().replace("+00:00", "Z")


def build_primary_evidence_inventory(
    *,
    evidence_root: Path,
    expected_run_keys: Sequence[str],
    bindings: CampaignBindings,
    reproduction_code_sha: str,
    power_off_recovery: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read-only inventory. Does not mutate primary results."""
    root = Path(evidence_root)
    expected = [str(k) for k in expected_run_keys]
    expected_set = set(expected)
    runs_dir = root / "runs"
    disk_dirs = (
        sorted(p.name for p in runs_dir.iterdir() if p.is_dir())
        if runs_dir.exists()
        else []
    )
    disk_set = set(disk_dirs)
    missing = sorted(expected_set - disk_set)
    extra = sorted(disk_set - expected_set)

    status_counts: dict[str, int] = {}
    attempt_hist: dict[str, int] = {}
    binding_mismatches = 0
    missing_completed = 0
    primary_results = 0

    for key in disk_dirs:
        env_path = runs_dir / key / "run_envelope.json"
        if not env_path.exists():
            binding_mismatches += 1
            continue
        env = read_json(env_path)
        st = str(env.get("status") or "")
        status_counts[st] = status_counts.get(st, 0) + 1
        att = str(env.get("attempt") or "")
        attempt_hist[att] = attempt_hist.get(att, 0) + 1
        for field, expected_val in (
            ("manifest_fingerprint", bindings.manifest_fingerprint),
            ("run_plan_fingerprint", bindings.run_plan_fingerprint),
            ("authorization_fingerprint", bindings.authorization_fingerprint),
            ("execution_sha", bindings.execution_sha),
            ("main_sha", bindings.main_sha),
        ):
            if env.get(field) != expected_val:
                binding_mismatches += 1
        rpath = runs_dir / key / "result.json"
        if rpath.exists():
            primary_results += 1
            result = read_json(rpath)
            for field, expected_val in (
                ("manifest_fingerprint", bindings.manifest_fingerprint),
                ("run_plan_fingerprint", bindings.run_plan_fingerprint),
                ("authorization_fingerprint", bindings.authorization_fingerprint),
            ):
                if result.get(field) != expected_val:
                    binding_mismatches += 1
        if not (runs_dir / key / "COMPLETED").exists():
            missing_completed += 1

    primary_verdict = VERDICT_PRIMARY_COMPLETE
    if missing or extra or primary_results != len(expected):
        primary_verdict = VERDICT_INCOMPLETE
    elif extra and not missing:
        primary_verdict = VERDICT_FOREIGN
    elif binding_mismatches:
        primary_verdict = VERDICT_BINDING
    elif (
        status_counts.get("RUNNING", 0)
        or status_counts.get("FAILED", 0)
        or status_counts.get("SUCCEEDED", 0) != len(expected)
        or missing_completed
    ):
        primary_verdict = VERDICT_STATE

    if primary_verdict == VERDICT_PRIMARY_COMPLETE:
        adoption_verdict = ADOPT_WITH_RECORD
    elif primary_verdict == VERDICT_BINDING:
        adoption_verdict = HOLD_BINDING
    else:
        adoption_verdict = primary_verdict

    digest = run_key_digest(expected)
    payload: dict[str, Any] = {
        "schema_version": ADOPTION_SCHEMA_VERSION,
        "primary_verdict": primary_verdict,
        "adoption_verdict": adoption_verdict,
        "campaign_id": bindings.campaign_id,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "bound_execution_sha": bindings.execution_sha,
        "bound_main_sha": bindings.main_sha,
        "reproduction_code_sha": reproduction_code_sha,
        "expected_run_count": len(expected),
        "observed_run_count": primary_results,
        "disk_run_dirs": len(disk_dirs),
        "run_key_digest": digest,
        "missing_key_count": len(missing),
        "extra_key_count": len(extra),
        "binding_mismatch_count": binding_mismatches,
        "missing_completed_count": missing_completed,
        "status_counts": status_counts,
        "attempt_hist": attempt_hist,
        "allowed_evidence_namespace": str(root),
        "forbidden_mixes": [
            "rewrite_primary_result_json",
            "commit_all_819_raw_runs_as_evidence_substitute",
            "foreign_authorization_namespace",
            "claim_campaign_completed_from_primary_cli_only",
            "full_primary_rerun_without_adoption_failure",
            "bind_new_main_sha_without_new_owner_go",
        ],
        "power_off_recovery": dict(power_off_recovery or {}),
        "inventory_fingerprint": "",
        "created_at_utc": _utcnow_iso(),
        "lr_status": "NO-GO",
        "reclassified_cli_completed": (
            "PRIMARY_EVIDENCE_COMPLETE_NOT_CAMPAIGN_PHASE_COMPLETED"
        ),
    }
    # Fingerprint excludes wall-clock created_at.
    fp_body = {
        k: v
        for k, v in payload.items()
        if k not in {"created_at_utc", "inventory_fingerprint"}
    }
    payload["inventory_fingerprint"] = canonical_hash(fp_body)
    return payload


def write_primary_evidence_inventory(
    evidence_root: Path, inventory: Mapping[str, Any]
) -> Path:
    path = inventory_path(evidence_root)
    if inventory.get("schema_version") != ADOPTION_SCHEMA_VERSION:
        raise SensitivityAdoptionError("ADOPT_SCHEMA_INVALID")
    atomic_write_json(path, inventory)
    return path


def load_primary_evidence_inventory(evidence_root: Path) -> dict[str, Any]:
    path = inventory_path(evidence_root)
    if not path.exists():
        raise SensitivityAdoptionError("ADOPT_INVENTORY_MISSING", str(path))
    body = read_json(path)
    if body.get("schema_version") != ADOPTION_SCHEMA_VERSION:
        raise SensitivityAdoptionError("ADOPT_SCHEMA_INVALID")
    return body


def assert_adoption_inventory_allows_reproduction(
    evidence_root: Path, *, bindings: CampaignBindings
) -> dict[str, Any]:
    """Fail-closed gate used by execute resume when relaxing null-expiry."""
    inv = load_primary_evidence_inventory(evidence_root)
    if inv.get("primary_verdict") != VERDICT_PRIMARY_COMPLETE:
        raise SensitivityAdoptionError(
            "ADOPT_PRIMARY_NOT_COMPLETE", str(inv.get("primary_verdict"))
        )
    if inv.get("adoption_verdict") not in {ADOPT_WITH_RECORD, REPRO_MAY_RUN}:
        raise SensitivityAdoptionError(
            "ADOPT_VERDICT_BLOCKS_REPRODUCTION", str(inv.get("adoption_verdict"))
        )
    for field, expected in (
        ("manifest_fingerprint", bindings.manifest_fingerprint),
        ("run_plan_fingerprint", bindings.run_plan_fingerprint),
        ("authorization_fingerprint", bindings.authorization_fingerprint),
        ("bound_execution_sha", bindings.execution_sha),
        ("bound_main_sha", bindings.main_sha),
    ):
        if inv.get(field) != expected:
            raise SensitivityAdoptionError(
                "ADOPT_INVENTORY_BINDING_MISMATCH", field
            )
    return inv


def adopt_primary_evidence(
    *,
    evidence_root: Path,
    expected_run_keys: Sequence[str],
    bindings: CampaignBindings,
    reproduction_code_sha: str,
    promote_to_primary_complete: bool = True,
    power_off_recovery: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write inventory and transition envelope into adoption phases.

    Never rewrites primary result.json / COMPLETED markers.
    """
    root = Path(evidence_root)
    envelope = root / CAMPAIGN_ENVELOPE_NAME
    if not envelope.exists():
        raise SensitivityAdoptionError("ADOPT_ENVELOPE_MISSING")

    inventory = build_primary_evidence_inventory(
        evidence_root=root,
        expected_run_keys=expected_run_keys,
        bindings=bindings,
        reproduction_code_sha=reproduction_code_sha,
        power_off_recovery=power_off_recovery,
    )
    if inventory["primary_verdict"] != VERDICT_PRIMARY_COMPLETE:
        raise SensitivityAdoptionError(
            "ADOPT_PRIMARY_AUDIT_FAILED", inventory["primary_verdict"]
        )

    confirmed = count_primary_succeeded(
        root, bindings=bindings, expected_run_keys=list(expected_run_keys)
    )
    if confirmed != len(expected_run_keys):
        raise SensitivityAdoptionError(
            "ADOPT_PRIMARY_SUCCESS_COUNT_MISMATCH",
            f"confirmed={confirmed} expected={len(expected_run_keys)}",
        )

    write_primary_evidence_inventory(root, inventory)

    current = read_campaign_phase(root)
    if current == CAMPAIGN_PHASE_PLANNED:
        update_campaign_phase(
            root,
            bindings=bindings,
            phase=CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
            extra={
                "primary_evidence_inventory_fingerprint": inventory[
                    "inventory_fingerprint"
                ],
                "adoption_verdict": ADOPT_WITH_RECORD,
            },
        )
        current = CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE
    elif current == CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE:
        update_campaign_phase(
            root,
            bindings=bindings,
            phase=CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
            extra={
                "primary_evidence_inventory_fingerprint": inventory[
                    "inventory_fingerprint"
                ],
                "adoption_verdict": ADOPT_WITH_RECORD,
            },
        )
    elif current in {
        CAMPAIGN_PHASE_PRIMARY_COMPLETE,
        CAMPAIGN_PHASE_BLOCKED,
    }:
        # Idempotent: inventory refreshed; do not regress phase.
        pass
    else:
        raise SensitivityAdoptionError(
            "ADOPT_PHASE_UNSUPPORTED", current
        )

    final_phase = current
    if promote_to_primary_complete and current == (
        CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE
    ):
        update_campaign_phase(
            root,
            bindings=bindings,
            phase=CAMPAIGN_PHASE_PRIMARY_COMPLETE,
            extra={
                "adoption_verdict": REPRO_MAY_RUN,
                "primary_evidence_inventory_fingerprint": inventory[
                    "inventory_fingerprint"
                ],
            },
        )
        final_phase = CAMPAIGN_PHASE_PRIMARY_COMPLETE
        inventory = dict(inventory)
        inventory["adoption_verdict"] = REPRO_MAY_RUN
        write_primary_evidence_inventory(root, inventory)

    return {
        "command": "adopt-primary-evidence",
        "status": "ADOPTED",
        "campaign_phase": final_phase,
        "adoption_verdict": inventory["adoption_verdict"],
        "primary_verdict": inventory["primary_verdict"],
        "inventory_fingerprint": inventory["inventory_fingerprint"],
        "run_key_digest": inventory["run_key_digest"],
        "evidence_root": str(root),
        "lr_status": "NO-GO",
    }
