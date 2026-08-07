"""hh_hl campaign-level summary + PRIMARY_COMPLETE persistence (#4404).

Future write-path only: never mutates existing run evidence trees. After a
successful primary campaign (all expected runs SUCCEEDED or contract-identical
resume skips, 0 failed, 0 blocked), persist:

1. ``campaign_summary.json`` (atomic)
2. campaign envelope lifecycle ``PRIMARY_COMPLETE`` (atomic phase transition)

Order is fail-closed: summary must land before ``PRIMARY_COMPLETE``. A summary
write failure leaves the campaign non-terminal. Idempotent when already
``PRIMARY_COMPLETE`` with a binding-matched summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
    frozen_hh_hl_parameters,
)
from tools.arvp_vacation.hh_hl_campaign_grid import (
    _physical_fingerprint as _hh_hl_grid_physical_fingerprint,
)
from tools.arvp_vacation.hh_hl_campaign_lifecycle import HH_HL_EXPECTED_RUN_COUNT
from tools.arvp_vacation.sensitivity_campaign_state import (
    CAMPAIGN_ENVELOPE_NAME,
    CAMPAIGN_PHASE_BLOCKED,
    CAMPAIGN_PHASE_PLANNED,
    CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE,
    CAMPAIGN_PHASE_PRIMARY_RUNNING,
    CampaignBindings,
    SensitivityStateError,
    atomic_write_json,
    completion_marker_path,
    count_primary_succeeded,
    fs_dirname_for_run_key,
    read_campaign_phase,
    read_json,
    run_envelope_path,
    update_campaign_phase,
)

CAMPAIGN_SUMMARY_NAME = "campaign_summary.json"
CAMPAIGN_SUMMARY_SCHEMA_VERSION = "cdb.hh_hl_campaign_summary.v1"
VARIANT_SLOT_ID = "hh_hl_baseline_001"


class HhHlCampaignSummaryError(ValueError):
    """Fail-closed campaign summary / primary-completion error."""

    def __init__(self, reason_code: str, detail: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(reason_code if not detail else f"{reason_code}: {detail}")


@dataclass(frozen=True, slots=True)
class PrimaryRunCounts:
    expected: int
    succeeded: int
    skipped: int
    failed: int
    blocked: int
    missing: int
    unexpected_extra: int = 0

    @property
    def covered(self) -> int:
        return self.succeeded + self.skipped

    @property
    def is_primary_complete(self) -> bool:
        return (
            self.expected == HH_HL_EXPECTED_RUN_COUNT
            and self.covered == self.expected
            and self.failed == 0
            and self.blocked == 0
            and self.missing == 0
            and self.unexpected_extra == 0
            and self.succeeded + self.skipped + self.failed + self.blocked
            == self.expected
        )


def campaign_summary_path(root: Path) -> Path:
    return Path(root) / CAMPAIGN_SUMMARY_NAME


def physical_parameter_set_fingerprint() -> str:
    """Bind to the same strategy_id+param_set hash as grid / bound_run_envelope.

    Historical #4374 evidence and ``hh_hl_campaign_grid._physical_fingerprint``
    use ``canonical_hash({strategy_id, param_set})``. Hashing only the param
    dict diverges (``76036390…`` vs historical ``9067cd6a…``) and must not be
    reintroduced (#4410 / #4409).
    """
    return _hh_hl_grid_physical_fingerprint(frozen_hh_hl_parameters())


def _assert_bindings_match(
    existing: Mapping[str, Any], bindings: CampaignBindings
) -> None:
    checks = {
        "campaign_id": bindings.campaign_id,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "execution_sha": bindings.execution_sha,
        "main_sha": bindings.main_sha,
    }
    for key, expected in checks.items():
        if existing.get(key) != expected:
            raise HhHlCampaignSummaryError(
                "HOLD_CAMPAIGN_SUMMARY_BINDING_MISMATCH", key
            )


def inspect_primary_run_counts(
    root: Path,
    *,
    bindings: CampaignBindings,
    expected_run_keys: Sequence[str],
    skipped_run_keys: Sequence[str] | None = None,
) -> PrimaryRunCounts:
    """Classify expected primary runs without mutating any run artifacts.

    ``skipped_run_keys`` are contract-identical resume skips observed in the
    current execute loop. On disk they appear as SUCCEEDED; they contribute to
    ``skipped`` when listed, otherwise to ``succeeded``.
    """
    expected = tuple(str(k) for k in expected_run_keys)
    if len(expected) != HH_HL_EXPECTED_RUN_COUNT:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_RUN_COUNT_MISMATCH",
            f"{len(expected)}!={HH_HL_EXPECTED_RUN_COUNT}",
        )
    if len(set(expected)) != len(expected):
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_RUN_KEYS_NOT_UNIQUE")

    skip_set = {str(k) for k in (skipped_run_keys or ())}
    unknown_skips = skip_set - set(expected)
    if unknown_skips:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_SKIP_KEY_UNKNOWN",
            ",".join(sorted(unknown_skips)),
        )

    succeeded = 0
    skipped = 0
    failed = 0
    blocked = 0
    missing = 0

    for run_key in expected:
        env_path = run_envelope_path(root, run_key)
        if not env_path.exists():
            missing += 1
            continue
        existing = read_json(env_path)
        _assert_bindings_match(existing, bindings)
        status = str(existing.get("status") or "")
        if status == "SUCCEEDED":
            marker = completion_marker_path(root, run_key)
            if not marker.exists():
                raise HhHlCampaignSummaryError(
                    "HOLD_CAMPAIGN_SUMMARY_PARTIAL_SUCCESS", run_key
                )
            if run_key in skip_set:
                skipped += 1
            else:
                succeeded += 1
            continue
        if status == "FAILED":
            failed += 1
            continue
        if status == "BLOCKED":
            blocked += 1
            continue
        if status == "RUNNING":
            raise HhHlCampaignSummaryError(
                "HOLD_CAMPAIGN_SUMMARY_RUN_STILL_RUNNING", run_key
            )
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_RUN_STATUS_UNSUPPORTED",
            f"{run_key}:{status}",
        )

    # Fail-closed on unexpected extra run dirs under runs/.
    # Directory names may be fs-safe encodings (#4384), not raw logical keys.
    runs_root = Path(root) / "runs"
    unexpected_extra = 0
    if runs_root.is_dir():
        expected_dirnames = {fs_dirname_for_run_key(k) for k in expected} | set(
            expected
        )
        on_disk = {p.name for p in runs_root.iterdir() if p.is_dir()}
        unexpected_extra = len(on_disk - expected_dirnames)

    # Binding-matched SUCCEEDED ledger must equal covered SUCCEEDED rows.
    try:
        confirmed = count_primary_succeeded(
            root, bindings=bindings, expected_run_keys=expected
        )
    except SensitivityStateError as exc:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_SUCCESS_LEDGER_INVALID", str(exc)
        ) from exc
    covered_succeeded = succeeded + skipped
    if confirmed != covered_succeeded:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_SUCCESS_COUNT_MISMATCH",
            f"confirmed={confirmed} covered={covered_succeeded}",
        )

    return PrimaryRunCounts(
        expected=len(expected),
        succeeded=succeeded,
        skipped=skipped,
        failed=failed,
        blocked=blocked,
        missing=missing,
        unexpected_extra=unexpected_extra,
    )


def build_campaign_summary(
    *,
    bindings: CampaignBindings,
    evidence_root: Path,
    counts: PrimaryRunCounts,
    dataset_selection_sha256: str,
    dataset_content_fingerprint_digest: str,
    github_comment_id: int | None = None,
    authorizing_github_login: str | None = None,
    owner_go_status: str | None = None,
    adapter_id: str = BATCH_B_SHADOW_ADAPTER_ID,
    strategy_id: str = HH_HL_CONTINUATION_STRATEGY_ID,
    variant_slot_id: str = VARIANT_SLOT_ID,
) -> dict[str, Any]:
    """Build the canonical campaign_summary.json body (no I/O)."""
    if not counts.is_primary_complete:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_NOT_PRIMARY_COMPLETE",
            (
                f"succeeded={counts.succeeded} skipped={counts.skipped} "
                f"failed={counts.failed} blocked={counts.blocked} "
                f"missing={counts.missing} unexpected_extra={counts.unexpected_extra}"
            ),
        )
    if not dataset_selection_sha256 or not dataset_content_fingerprint_digest:
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_DATASET_BINDING_REQUIRED")

    body: dict[str, Any] = {
        "schema_version": CAMPAIGN_SUMMARY_SCHEMA_VERSION,
        "campaign_id": bindings.campaign_id,
        "campaign_phase": CAMPAIGN_PHASE_PRIMARY_COMPLETE,
        "lifecycle_status": CAMPAIGN_PHASE_PRIMARY_COMPLETE,
        "terminal_completion_status": CAMPAIGN_PHASE_PRIMARY_COMPLETE,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "execution_sha": bindings.execution_sha,
        "main_sha": bindings.main_sha,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "dataset_selection_sha256": str(dataset_selection_sha256),
        "dataset_content_fingerprint_digest": str(dataset_content_fingerprint_digest),
        "strategy_id": strategy_id,
        "adapter_id": adapter_id,
        "variant_slot_id": variant_slot_id,
        "physical_parameter_set_fingerprint": physical_parameter_set_fingerprint(),
        "expected_run_count": counts.expected,
        "succeeded_count": counts.succeeded,
        "resumed_skipped_count": counts.skipped,
        "failed_count": counts.failed,
        "blocked_count": counts.blocked,
        "evidence_root": Path(evidence_root).as_posix(),
        "lr_status": "NO-GO",
    }
    if github_comment_id is not None:
        body["github_comment_id"] = int(github_comment_id)
    if authorizing_github_login:
        body["authorizing_github_login"] = str(authorizing_github_login)
    if owner_go_status:
        body["owner_go_status"] = str(owner_go_status)
    body["summary_fingerprint"] = canonical_hash(
        {k: v for k, v in body.items() if k != "summary_fingerprint"}
    )
    return body


def write_campaign_summary(root: Path, summary: Mapping[str, Any]) -> Path:
    """Atomically persist campaign_summary.json; never touches run trees."""
    if str(summary.get("schema_version") or "") != CAMPAIGN_SUMMARY_SCHEMA_VERSION:
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_SCHEMA_INVALID")
    if str(summary.get("campaign_phase") or "") != CAMPAIGN_PHASE_PRIMARY_COMPLETE:
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_PHASE_INVALID")
    path = campaign_summary_path(root)
    atomic_write_json(path, summary)
    return path


def _assert_summary_matches_bindings(
    summary: Mapping[str, Any], bindings: CampaignBindings
) -> None:
    checks = {
        "campaign_id": bindings.campaign_id,
        "manifest_fingerprint": bindings.manifest_fingerprint,
        "run_plan_fingerprint": bindings.run_plan_fingerprint,
        "authorization_fingerprint": bindings.authorization_fingerprint,
        "execution_sha": bindings.execution_sha,
        "main_sha": bindings.main_sha,
    }
    for key, expected in checks.items():
        if summary.get(key) != expected:
            raise HhHlCampaignSummaryError(
                "HOLD_CAMPAIGN_SUMMARY_BINDING_MISMATCH", key
            )


def persist_hh_hl_primary_completion(
    root: Path,
    *,
    bindings: CampaignBindings,
    expected_run_keys: Sequence[str],
    dataset_selection_sha256: str,
    dataset_content_fingerprint_digest: str,
    skipped_run_keys: Sequence[str] | None = None,
    github_comment_id: int | None = None,
    authorizing_github_login: str | None = None,
    owner_go_status: str | None = None,
    adapter_id: str = BATCH_B_SHADOW_ADAPTER_ID,
    strategy_id: str = HH_HL_CONTINUATION_STRATEGY_ID,
    variant_slot_id: str = VARIANT_SLOT_ID,
) -> dict[str, Any]:
    """Write campaign_summary.json then transition envelope to PRIMARY_COMPLETE.

    Safe for resume and for campaign-level backfill: run evidence is read-only.
    """
    root = Path(root)
    envelope_path = root / CAMPAIGN_ENVELOPE_NAME
    if not envelope_path.exists():
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_ENVELOPE_MISSING")

    existing_envelope = read_json(envelope_path)
    _assert_bindings_match(existing_envelope, bindings)

    counts = inspect_primary_run_counts(
        root,
        bindings=bindings,
        expected_run_keys=expected_run_keys,
        skipped_run_keys=skipped_run_keys,
    )
    if not counts.is_primary_complete:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_PRIMARY_INCOMPLETE",
            (
                f"succeeded={counts.succeeded} skipped={counts.skipped} "
                f"failed={counts.failed} blocked={counts.blocked} "
                f"missing={counts.missing} unexpected_extra={counts.unexpected_extra}"
            ),
        )

    summary = build_campaign_summary(
        bindings=bindings,
        evidence_root=root,
        counts=counts,
        dataset_selection_sha256=dataset_selection_sha256,
        dataset_content_fingerprint_digest=dataset_content_fingerprint_digest,
        github_comment_id=github_comment_id,
        authorizing_github_login=authorizing_github_login,
        owner_go_status=owner_go_status,
        adapter_id=adapter_id,
        strategy_id=strategy_id,
        variant_slot_id=variant_slot_id,
    )

    current = read_campaign_phase(root)
    summary_path = campaign_summary_path(root)

    if current == CAMPAIGN_PHASE_PRIMARY_COMPLETE and summary_path.exists():
        existing_summary = read_json(summary_path)
        _assert_summary_matches_bindings(existing_summary, bindings)
        if existing_summary.get("summary_fingerprint") == summary.get(
            "summary_fingerprint"
        ):
            return {
                "ok": True,
                "idempotent": True,
                "campaign_phase": CAMPAIGN_PHASE_PRIMARY_COMPLETE,
                "campaign_summary_path": summary_path.as_posix(),
                "summary": existing_summary,
                "counts": {
                    "expected": counts.expected,
                    "succeeded": counts.succeeded,
                    "skipped": counts.skipped,
                    "failed": counts.failed,
                    "blocked": counts.blocked,
                },
            }
        # Fingerprint drift with PRIMARY_COMPLETE already set → fail closed.
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_STALE_OR_DRIFTED",
            "existing PRIMARY_COMPLETE summary fingerprint mismatch",
        )

    if current == CAMPAIGN_PHASE_BLOCKED:
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_CAMPAIGN_BLOCKED")

    if current == CAMPAIGN_PHASE_PLANNED:
        update_campaign_phase(
            root, bindings=bindings, phase=CAMPAIGN_PHASE_PRIMARY_RUNNING
        )
        current = CAMPAIGN_PHASE_PRIMARY_RUNNING
    elif current == CAMPAIGN_PHASE_PRIMARY_EVIDENCE_COMPLETE:
        # Adoption path may land here; promote via PRIMARY_COMPLETE below.
        pass
    elif current not in {
        CAMPAIGN_PHASE_PRIMARY_RUNNING,
        CAMPAIGN_PHASE_PRIMARY_COMPLETE,
    }:
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_PHASE_UNSUPPORTED", current
        )

    # Summary first — never leave PRIMARY_COMPLETE without a durable summary.
    try:
        write_campaign_summary(root, summary)
    except Exception as exc:  # noqa: BLE001 — re-wrap as fail-closed HOLD
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_WRITE_FAILED", type(exc).__name__
        ) from exc

    if not summary_path.exists():
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_WRITE_MISSING")

    try:
        update_campaign_phase(
            root,
            bindings=bindings,
            phase=CAMPAIGN_PHASE_PRIMARY_COMPLETE,
            extra={
                "campaign_summary_artifact": CAMPAIGN_SUMMARY_NAME,
                "campaign_summary_fingerprint": summary["summary_fingerprint"],
                "primary_succeeded_count": counts.succeeded,
                "primary_skipped_count": counts.skipped,
                "primary_failed_count": counts.failed,
                "primary_blocked_count": counts.blocked,
            },
        )
    except SensitivityStateError as exc:
        # Summary exists but phase transition failed — leave non-terminal phase.
        raise HhHlCampaignSummaryError(
            "HOLD_CAMPAIGN_SUMMARY_PHASE_UPDATE_FAILED", str(exc)
        ) from exc

    if read_campaign_phase(root) != CAMPAIGN_PHASE_PRIMARY_COMPLETE:
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_PHASE_NOT_PERSISTED")

    return {
        "ok": True,
        "idempotent": False,
        "campaign_phase": CAMPAIGN_PHASE_PRIMARY_COMPLETE,
        "campaign_summary_path": summary_path.as_posix(),
        "summary": summary,
        "counts": {
            "expected": counts.expected,
            "succeeded": counts.succeeded,
            "skipped": counts.skipped,
            "failed": counts.failed,
            "blocked": counts.blocked,
        },
    }


def read_campaign_summary(root: Path) -> dict[str, Any]:
    path = campaign_summary_path(root)
    if not path.exists():
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_MISSING")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HhHlCampaignSummaryError("HOLD_CAMPAIGN_SUMMARY_INVALID_ROOT")
    return payload
