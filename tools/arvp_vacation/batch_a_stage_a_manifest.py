"""Batch-A Stage-A campaign manifest builder (#4032).

Builds the locked 780-scenario-run development screening matrix:
10 strategies × 39 development windows × 2 scenarios
(``baseline``, ``pessimistic_execution``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.replay.batch_a_strategy_registry import batch_a_strategy_ids
from core.replay.canonical_json import canonical_hash
from tools.arvp_vacation.contract import build_job_fingerprint, build_job_id
from tools.market_data.development_window_selector import (
    LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
    LOCKED_DEVELOPMENT_SELECTION_SHA256,
    DevelopmentSelectionError,
    default_window_bank_manifest_path,
    load_window_bank_manifest,
    select_batch_a_development_windows,
)

MANIFEST_SCHEMA_VERSION = "batch_a_stage_a_campaign_manifest.v1"
STAGE_A_SCENARIOS: tuple[str, ...] = ("baseline", "pessimistic_execution")
EXPECTED_STRATEGY_COUNT = 10
EXPECTED_WINDOW_COUNT = 39
EXPECTED_SCENARIO_RUN_COUNT = 780
EXPECTED_JOB_COUNT = 390


class StageAManifestError(ValueError):
    """Fail-closed Stage-A manifest builder violation."""


@dataclass(frozen=True, slots=True)
class StageACampaignManifest:
    schema_version: str
    campaign_kind: str
    source_issue: str
    strategy_count: int
    window_count: int
    scenario_count: int
    job_count: int
    scenario_run_count: int
    development_selection_sha256: str
    manifest_sha256: str
    scenarios: tuple[str, ...]
    strategy_ids: tuple[str, ...]
    window_ids: tuple[str, ...]
    jobs: tuple[Mapping[str, Any], ...]


def _window_rows_by_id(
    selection_windows: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    return {str(row["window_id"]): row for row in selection_windows}


def build_stage_a_campaign_manifest(
    *,
    campaign_id: str,
    source_sha: str,
    manifest_path: Path | None = None,
    repo_root: Path | None = None,
    strategy_ids: Sequence[str] | None = None,
) -> StageACampaignManifest:
    """Build the locked Stage-A campaign manifest fail-closed."""
    if not campaign_id.strip():
        raise StageAManifestError("campaign_id is required")
    if not _is_sha256(source_sha):
        raise StageAManifestError("source_sha must be a 64-char lowercase hex digest")

    root = repo_root or Path(__file__).resolve().parents[2]
    manifest_file = manifest_path or default_window_bank_manifest_path(root)
    if not manifest_file.exists():
        raise StageAManifestError(f"Window bank manifest missing: {manifest_file}")

    bank_manifest = load_window_bank_manifest(manifest_file, repo_root=root)
    try:
        selection = select_batch_a_development_windows(bank_manifest)
    except DevelopmentSelectionError as exc:
        raise StageAManifestError(str(exc)) from exc

    strategies = tuple(strategy_ids or batch_a_strategy_ids())
    if len(strategies) != EXPECTED_STRATEGY_COUNT:
        raise StageAManifestError(
            f"expected {EXPECTED_STRATEGY_COUNT} strategies, got {len(strategies)}"
        )
    if selection.window_count != EXPECTED_WINDOW_COUNT:
        raise StageAManifestError(
            f"expected {EXPECTED_WINDOW_COUNT} development windows, "
            f"got {selection.window_count}"
        )
    if selection.selection_sha256 != LOCKED_DEVELOPMENT_SELECTION_SHA256:
        raise StageAManifestError("development selection SHA mismatch against #4030 lock")

    windows_by_id = _window_rows_by_id(selection.windows)
    jobs: list[dict[str, Any]] = []
    for strategy_id in strategies:
        for window_id in LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS:
            window = windows_by_id.get(window_id)
            if window is None:
                raise StageAManifestError(f"missing development window row: {window_id}")
            dataset_fingerprint = str(window.get("dataset_fingerprint") or "")
            if not _is_sha256(dataset_fingerprint):
                raise StageAManifestError(
                    f"window {window_id} missing dataset_fingerprint"
                )
            job_id = build_job_id(strategy_id, window_id)
            fingerprint = build_job_fingerprint(
                source_sha=source_sha,
                strategy_id=strategy_id,
                dataset_fingerprint=dataset_fingerprint,
                scenarios=list(STAGE_A_SCENARIOS),
                speedup_profile="instant",
            )
            jobs.append(
                {
                    "job_id": job_id,
                    "strategy_id": strategy_id,
                    "window_id": window_id,
                    "dataset_id": window_id,
                    "dataset_fingerprint": dataset_fingerprint,
                    "purpose": "development",
                    "overlap_class": "monthly",
                    "scenarios": list(STAGE_A_SCENARIOS),
                    "scenario_run_count": len(STAGE_A_SCENARIOS),
                    "fingerprint": fingerprint,
                    "campaign_id": campaign_id,
                    "evidence_class": "historical_cross_venue_research",
                }
            )

    jobs.sort(key=lambda row: (row["strategy_id"], row["window_id"]))
    scenario_run_count = len(jobs) * len(STAGE_A_SCENARIOS)
    if scenario_run_count != EXPECTED_SCENARIO_RUN_COUNT:
        raise StageAManifestError(
            f"expected {EXPECTED_SCENARIO_RUN_COUNT} scenario runs, got {scenario_run_count}"
        )
    if len(jobs) != EXPECTED_JOB_COUNT:
        raise StageAManifestError(
            f"expected {EXPECTED_JOB_COUNT} jobs, got {len(jobs)}"
        )

    manifest_payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "campaign_kind": "batch_a_stage_a_development_screening",
        "source_issue": "#4032",
        "campaign_id": campaign_id,
        "source_sha": source_sha.lower(),
        "strategy_count": len(strategies),
        "window_count": selection.window_count,
        "scenario_count": len(STAGE_A_SCENARIOS),
        "job_count": len(jobs),
        "scenario_run_count": scenario_run_count,
        "development_selection_sha256": selection.selection_sha256,
        "scenarios": list(STAGE_A_SCENARIOS),
        "strategy_ids": list(strategies),
        "window_ids": list(LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS),
        "jobs": jobs,
    }
    manifest_sha = canonical_hash(manifest_payload)

    return StageACampaignManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        campaign_kind="batch_a_stage_a_development_screening",
        source_issue="#4032",
        strategy_count=len(strategies),
        window_count=selection.window_count,
        scenario_count=len(STAGE_A_SCENARIOS),
        job_count=len(jobs),
        scenario_run_count=scenario_run_count,
        development_selection_sha256=selection.selection_sha256,
        manifest_sha256=manifest_sha,
        scenarios=STAGE_A_SCENARIOS,
        strategy_ids=strategies,
        window_ids=LOCKED_BATCH_A_DEVELOPMENT_WINDOW_IDS,
        jobs=tuple(jobs),
    )


def manifest_to_dict(manifest: StageACampaignManifest) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "campaign_kind": manifest.campaign_kind,
        "source_issue": manifest.source_issue,
        "strategy_count": manifest.strategy_count,
        "window_count": manifest.window_count,
        "scenario_count": manifest.scenario_count,
        "job_count": manifest.job_count,
        "scenario_run_count": manifest.scenario_run_count,
        "development_selection_sha256": manifest.development_selection_sha256,
        "manifest_sha256": manifest.manifest_sha256,
        "scenarios": list(manifest.scenarios),
        "strategy_ids": list(manifest.strategy_ids),
        "window_ids": list(manifest.window_ids),
        "jobs": list(manifest.jobs),
    }


def write_stage_a_campaign_manifest(
    path: Path,
    *,
    campaign_id: str,
    source_sha: str,
    manifest_path: Path | None = None,
    repo_root: Path | None = None,
) -> StageACampaignManifest:
    manifest = build_stage_a_campaign_manifest(
        campaign_id=campaign_id,
        source_sha=source_sha,
        manifest_path=manifest_path,
        repo_root=repo_root,
    )
    payload = manifest_to_dict(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _is_sha256(value: str) -> bool:
    token = value.strip().lower()
    if len(token) != 64:
        return False
    try:
        int(token, 16)
    except ValueError:
        return False
    return True
