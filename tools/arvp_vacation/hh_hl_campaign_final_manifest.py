"""hh_hl final (ratified) campaign manifest builder — execution-capable, not
authorized (#4374).

Consumes a Design-GO ratification receipt plus a PASS dataset receipt and the
immutable draft (source) manifest, and emits the frozen final manifest
``config/arvp/hh_hl_campaign_4374_v1.json``. The final manifest is
execution-*capable* (``execution_enabled=true``) but never
execution-*authorized* (``campaign_execution_authorized=false``); a live Owner
Execution-GO remains mandatory. It carries no Execution-GO data (no
execution_sha, surface fingerprint, or expiry) and no local absolute paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_REPLAY_PROFILE_ID,
    CampaignProfileError,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import (
    DatasetBindingReceipt,
    validate_pass_receipt,
)
from tools.arvp_vacation.hh_hl_campaign_design_authorization import (
    DesignRatificationReceipt,
)
from tools.arvp_vacation.hh_hl_campaign_grid import (
    GRID_PROVIDER_ID,
    expand_hh_hl_variants,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FINAL_MANIFEST_SCHEMA_VERSION = "cdb.hh_hl_campaign_manifest.v1"
DEFAULT_FINAL_MANIFEST_REL = Path("config/arvp/hh_hl_campaign_4374_v1.json")
SOURCE_MANIFEST_REL = "config/arvp/hh_hl_campaign_4374_draft_v1.json"

EXECUTION_MODE = "offline_replay_only"
EXPECTED_WINDOW_COUNT = 39
EXPECTED_VARIANT_COUNT = 1
EXPECTED_RUN_COUNT = 39
ANALYZER_PROFILE_ID = "hh_hl_analyzer_prep_v1"
REPRODUCTION_POLICY_ID = "hh_hl_reproduction_prep_v1"
GRID_STATUS_RATIFIED = "CAMPAIGN_GRID_OWNER_RATIFIED"

# Resource budget defaults (prompt P9). Conservative single-run replay bounds.
DEFAULT_RESOURCE_BUDGET: dict[str, int] = {
    "max_parallelism": 1,
    "max_in_flight_runs": 1,
    "max_attempts_per_run": 1,
    "max_run_wall_time_seconds": 3600,
    "max_campaign_wall_time_seconds": 172800,
    "max_artifact_bytes": 21474836480,
    "minimum_free_disk_bytes": 21474836480,
    "max_consecutive_failures": 3,
    "max_total_failures": 5,
    "log_retention_days": 30,
}

DEFAULT_RESUME_POLICY: dict[str, bool] = {
    "allow_resume": True,
    "skip_succeeded_identical_bindings": True,
    "retry_failed": True,
    "refuse_running_without_completion": True,
    "refuse_binding_mismatch": True,
}

_ABSOLUTE_PATH_MARKERS = (":\\", "/home/", "/Users/", "C:/", "D:/")


class HhHlFinalManifestError(ValueError):
    """Fail-closed final-manifest construction error."""


def _as_receipt_dict(receipt: DesignRatificationReceipt | Mapping[str, Any]) -> dict:
    if isinstance(receipt, DesignRatificationReceipt):
        return receipt.as_dict()
    if isinstance(receipt, Mapping):
        return dict(receipt)
    raise HhHlFinalManifestError("DESIGN_RECEIPT_INVALID_TYPE")


def _assert_no_absolute_paths(body: Mapping[str, Any]) -> None:
    blob = json.dumps(body, sort_keys=True)
    for marker in _ABSOLUTE_PATH_MARKERS:
        if marker in blob:
            raise HhHlFinalManifestError(f"FINAL_MANIFEST_ABSOLUTE_PATH:{marker}")


def _ratified_grid_block() -> dict[str, Any]:
    variants = expand_hh_hl_variants()
    return {
        "grid_provider_id": GRID_PROVIDER_ID,
        "status": GRID_STATUS_RATIFIED,
        "strategy_id": HH_HL_CONTINUATION_STRATEGY_ID,
        "variant_count": len(variants),
        "variants": [v.as_dict() for v in variants],
    }


def _output_contract_block(evidence_namespace: str) -> dict[str, Any]:
    return {
        "output_contract_version": "cdb.hh_hl_campaign_output.v1",
        "run_output_dir_template": (
            f"{evidence_namespace}/"
            "{campaign_id}/{manifest_fingerprint}/{authorization_id}/{run_key}"
        ),
        "required_run_artifacts": [
            "bound_run_envelope.json",
            "replay/",
        ],
        "campaign_summary_artifact": "campaign_summary.json",
        "metrics_contract_version": "cdb.hh_hl_campaign_metrics.v1",
        "absolute_paths_forbidden": True,
    }


def _reproduction_policy_block() -> dict[str, Any]:
    return {
        "reproduction_policy_id": REPRODUCTION_POLICY_ID,
        "reproduction_attempts": 1,
        "compare_on": [
            "physical_parameter_set_fingerprint",
            "dataset_content_fingerprint",
            "run_plan_fingerprint",
        ],
        "mismatch_action": "HOLD_REPRODUCTION_MISMATCH",
    }


def build_hh_hl_final_manifest(
    *,
    design_receipt: DesignRatificationReceipt | Mapping[str, Any],
    dataset_receipt: DatasetBindingReceipt | Mapping[str, Any],
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the frozen final manifest body (fingerprint included, deterministic)."""
    design = _as_receipt_dict(design_receipt)

    if isinstance(dataset_receipt, DatasetBindingReceipt):
        ds = validate_pass_receipt(dataset_receipt.as_dict())
    else:
        ds = validate_pass_receipt(dict(dataset_receipt))
    ds_dict = ds.as_dict()

    profile = load_profile(HH_HL_REPLAY_PROFILE_ID)

    src_fp = str(source_manifest.get("manifest_fingerprint") or "")
    if not src_fp:
        raise HhHlFinalManifestError("SOURCE_MANIFEST_FINGERPRINT_REQUIRED")
    if str(design.get("source_manifest_fingerprint") or "") != src_fp:
        raise HhHlFinalManifestError(
            "DESIGN_SOURCE_FINGERPRINT_MISMATCH:"
            f"{design.get('source_manifest_fingerprint')}!={src_fp}"
        )
    if str(design.get("source_manifest_path") or "") != SOURCE_MANIFEST_REL:
        raise HhHlFinalManifestError("DESIGN_SOURCE_PATH_MISMATCH")

    # Dataset digests must agree across design ratification + PASS receipt.
    if str(design.get("dataset_selection_sha256") or "") != ds.selection_sha256:
        raise HhHlFinalManifestError("DATASET_SELECTION_MISMATCH")
    if str(design.get("dataset_content_fingerprint_digest") or "") != str(
        ds.content_fingerprint_digest or ""
    ):
        raise HhHlFinalManifestError("DATASET_CONTENT_DIGEST_MISMATCH")

    if ds.window_count != EXPECTED_WINDOW_COUNT:
        raise HhHlFinalManifestError(f"DATASET_WINDOW_COUNT_MISMATCH:{ds.window_count}")
    if int(design.get("variant_count") or 0) != EXPECTED_VARIANT_COUNT:
        raise HhHlFinalManifestError("DESIGN_VARIANT_COUNT_MISMATCH")

    campaign_id = str(source_manifest.get("campaign_id") or profile.campaign_id)
    if campaign_id != profile.campaign_id:
        raise CampaignProfileError(
            f"PROFILE_CAMPAIGN_ID_MISMATCH:{campaign_id}!={profile.campaign_id}"
        )

    absolute_bans = dict(source_manifest.get("absolute_bans") or {})

    body: dict[str, Any] = {
        "schema_version": FINAL_MANIFEST_SCHEMA_VERSION,
        "campaign_id": campaign_id,
        "issue_number": 4374,
        "issue_ref": "#4374",
        "parent_issue": int(source_manifest.get("parent_issue") or 1900),
        "lineage_issues": list(source_manifest.get("lineage_issues") or [4372, 4374]),
        "lineage_prs": list(source_manifest.get("lineage_prs") or [4373]),
        "profile_id": profile.profile_id,
        "manifest_path": profile.manifest_path,
        "source_manifest_path": SOURCE_MANIFEST_REL,
        "source_manifest_fingerprint": src_fp,
        "strategy_set": [HH_HL_CONTINUATION_STRATEGY_ID],
        "strategy_version": profile.strategy_version,
        "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
        "execution_mode": EXECUTION_MODE,
        "planning_enabled": True,
        "execution_enabled": True,
        "campaign_execution_authorized": False,
        "requires_external_owner_go": True,
        "authorization_schema": profile.authorization_schema,
        "expected_window_count": EXPECTED_WINDOW_COUNT,
        "expected_variant_count": EXPECTED_VARIANT_COUNT,
        "expected_run_count": EXPECTED_RUN_COUNT,
        "design_ratification": design,
        "grid": _ratified_grid_block(),
        "grid_provider_id": GRID_PROVIDER_ID,
        "dataset_binding": ds_dict,
        "output_contract": _output_contract_block(profile.evidence_namespace),
        "resume_policy": dict(DEFAULT_RESUME_POLICY),
        "reproduction_policy": _reproduction_policy_block(),
        "analyzer_profile_id": ANALYZER_PROFILE_ID,
        "resource_budget_contract": dict(DEFAULT_RESOURCE_BUDGET),
        "evidence_namespace": profile.evidence_namespace,
        "artifact_root_template": profile.artifact_root_template,
        "absolute_bans": absolute_bans,
        "stage_b": False,
        "oos": False,
        "stress": False,
        "paper": False,
        "live": False,
        "echtgeld": False,
        "promotion": False,
        "lr_status": "NO-GO",
        "non_executable_without_owner_go": True,
    }
    _assert_no_absolute_paths(body)
    body["manifest_fingerprint"] = canonical_hash(body)
    return body


def load_source_manifest(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or PROJECT_ROOT
    path = root / SOURCE_MANIFEST_REL
    if not path.exists():
        raise HhHlFinalManifestError(f"SOURCE_MANIFEST_MISSING:{path.as_posix()}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise HhHlFinalManifestError("SOURCE_MANIFEST_ROOT_MUST_BE_OBJECT")
    return payload


def write_hh_hl_final_manifest(
    body: Mapping[str, Any],
    *,
    path: Path | None = None,
    repo_root: Path | None = None,
) -> Path:
    root = repo_root or PROJECT_ROOT
    target = path or (root / DEFAULT_FINAL_MANIFEST_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(body), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target
