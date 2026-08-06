"""hh_hl draft campaign manifest builder — non-executable (#4374)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.replay.canonical_json import canonical_hash
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
)
from tools.arvp_vacation.campaign_profile import (
    HH_HL_PREP_PROFILE_ID,
    load_profile,
)
from tools.arvp_vacation.hh_hl_campaign_dataset import build_dataset_binding_receipt
from tools.arvp_vacation.hh_hl_campaign_grid import (
    DESIGN_GO_NAME,
    GRID_STATUS,
    grid_draft_report,
)

MANIFEST_SCHEMA_VERSION = "cdb.hh_hl_campaign_manifest.v1.draft"
DEFAULT_MANIFEST_REL = Path("config/arvp/hh_hl_campaign_4374_draft_v1.json")


def build_hh_hl_draft_manifest() -> dict[str, Any]:
    profile = load_profile(HH_HL_PREP_PROFILE_ID)
    receipt = build_dataset_binding_receipt()
    grid = grid_draft_report()
    body: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "campaign_id": profile.campaign_id,
        "issue_number": profile.issue_number,
        "issue_ref": f"#{profile.issue_number}",
        "parent_issue": 1900,
        "lineage_issues": [4372, 4374],
        "lineage_prs": [4373],
        "manifest_path": profile.manifest_path,
        "profile_id": profile.profile_id,
        "strategy_set": [HH_HL_CONTINUATION_STRATEGY_ID],
        "strategy_version": profile.strategy_version,
        "adapter_id": BATCH_B_SHADOW_ADAPTER_ID,
        "planning_enabled": True,
        "execution_enabled": False,
        "campaign_execution_authorized": False,
        "requires_external_owner_go": True,
        "grid_status": GRID_STATUS,
        "grid_provider_id": profile.grid_provider_id,
        "grid_draft": {
            "variant_count": grid["variant_count"],
            "variants": grid["variants"],
            "forbidden_variants": grid["forbidden_variants"],
            "design_go_template_name": DESIGN_GO_NAME,
        },
        "dataset_binding": receipt.as_dict(),
        "evidence_namespace": profile.evidence_namespace,
        "artifact_root_template": profile.artifact_root_template,
        "absolute_bans": dict(profile.absolute_bans),
        "stage_b": False,
        "oos": False,
        "stress": False,
        "paper": False,
        "live": False,
        "echtgeld": False,
        "promotion": False,
        "lr_status": "NO-GO",
        "non_executable_reasons": [
            GRID_STATUS,
            receipt.quality_gate_status,
            "campaign_execution_authorized=false",
            "execution_enabled=false",
            "missing Owner Design-GO and Execution-GO",
        ],
    }
    body["manifest_fingerprint"] = canonical_hash(body)
    return body


def write_hh_hl_draft_manifest(
    path: Path | None = None,
    *,
    repo_root: Path | None = None,
) -> Path:
    root = repo_root or Path(__file__).resolve().parents[2]
    target = path or (root / DEFAULT_MANIFEST_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_hh_hl_draft_manifest()
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target
