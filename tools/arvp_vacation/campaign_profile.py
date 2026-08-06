"""Campaign Profile contract — immutable, fail-closed instance binding (#4374).

Profiles sit *beside* the frozen #4153 sensitivity stack. Unknown profiles,
manifest mismatches, and planning-only execute attempts fail closed.
Does not authorize campaign execution, paper, live, or echtgeld.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from core.replay.batch_b_strategy_registry import BATCH_B_STRATEGY_REGISTRY
from core.replay.hh_hl_continuation_common import (
    BATCH_B_SHADOW_ADAPTER_ID,
    HH_HL_CONTINUATION_STRATEGY_ID,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"
PROFILE_SCHEMA_PATH = CONTRACTS_DIR / "cdb_campaign_profile.v1.schema.json"
PROFILE_SCHEMA_VERSION = "cdb.campaign_profile.v1"
PROFILES_DIR = PROJECT_ROOT / "config" / "arvp" / "campaign_profiles"

LEGACY_4153_PROFILE_ID = "legacy_4153_pb1"
HH_HL_PREP_PROFILE_ID = "hh_hl_continuation_prep_v1"

KNOWN_PROFILE_IDS = frozenset({LEGACY_4153_PROFILE_ID, HH_HL_PREP_PROFILE_ID})

REQUIRED_PROFILE_FIELDS = (
    "profile_schema_version",
    "profile_id",
    "issue_number",
    "campaign_id",
    "manifest_path",
    "manifest_schema_version",
    "strategy_id",
    "strategy_version",
    "adapter_id",
    "grid_provider_id",
    "run_plan_provider_id",
    "executor_provider_id",
    "analyzer_profile_id",
    "evidence_namespace",
    "artifact_root_template",
    "authorization_schema",
    "reproduction_policy_id",
    "execution_enabled",
    "planning_enabled",
    "absolute_bans",
    "lr_status",
)

ABSOLUTE_BAN_KEYS = (
    "stage_b",
    "oos",
    "stress",
    "paper",
    "live",
    "echtgeld",
    "promotion",
    "orders",
    "exchange_execution",
)

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None  # type: ignore


class CampaignProfileError(ValueError):
    """Fail-closed campaign profile violation."""


@dataclass(frozen=True, slots=True)
class CampaignProfile:
    profile_schema_version: str
    profile_id: str
    issue_number: int
    campaign_id: str
    manifest_path: str
    manifest_schema_version: str
    strategy_id: str
    strategy_version: str
    adapter_id: str
    grid_provider_id: str
    run_plan_provider_id: str
    executor_provider_id: str
    analyzer_profile_id: str
    evidence_namespace: str
    artifact_root_template: str
    authorization_schema: str
    reproduction_policy_id: str
    execution_enabled: bool
    planning_enabled: bool
    absolute_bans: Mapping[str, bool]
    lr_status: str
    campaign_authorized: bool = False
    requires_external_owner_go: bool = True
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_schema_version": self.profile_schema_version,
            "profile_id": self.profile_id,
            "issue_number": self.issue_number,
            "campaign_id": self.campaign_id,
            "manifest_path": self.manifest_path,
            "manifest_schema_version": self.manifest_schema_version,
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "adapter_id": self.adapter_id,
            "grid_provider_id": self.grid_provider_id,
            "run_plan_provider_id": self.run_plan_provider_id,
            "executor_provider_id": self.executor_provider_id,
            "analyzer_profile_id": self.analyzer_profile_id,
            "evidence_namespace": self.evidence_namespace,
            "artifact_root_template": self.artifact_root_template,
            "authorization_schema": self.authorization_schema,
            "reproduction_policy_id": self.reproduction_policy_id,
            "execution_enabled": self.execution_enabled,
            "planning_enabled": self.planning_enabled,
            "campaign_authorized": self.campaign_authorized,
            "requires_external_owner_go": self.requires_external_owner_go,
            "absolute_bans": dict(self.absolute_bans),
            "lr_status": self.lr_status,
            "notes": self.notes,
        }


def load_profile_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or PROFILE_SCHEMA_PATH
    if not schema_path.exists():
        raise CampaignProfileError(f"PROFILE_SCHEMA_MISSING:{schema_path}")
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CampaignProfileError("PROFILE_SCHEMA_ROOT_MUST_BE_OBJECT")
    return payload


def validate_profile_payload(payload: Mapping[str, Any]) -> None:
    if jsonschema is None:
        raise CampaignProfileError(
            "jsonschema is required to validate campaign profiles"
        )
    missing = [k for k in REQUIRED_PROFILE_FIELDS if k not in payload]
    if missing:
        raise CampaignProfileError(f"PROFILE_FIELDS_MISSING:{missing}")
    try:
        jsonschema.validate(instance=dict(payload), schema=load_profile_schema())
    except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
        raise CampaignProfileError(f"INVALID_CAMPAIGN_PROFILE:{exc.message}") from exc

    profile_id = str(payload["profile_id"])
    if profile_id not in KNOWN_PROFILE_IDS:
        raise CampaignProfileError(f"UNKNOWN_CAMPAIGN_PROFILE:{profile_id}")

    if payload.get("lr_status") != "NO-GO":
        raise CampaignProfileError("PROFILE_LR_MUST_BE_NO_GO")

    bans = payload.get("absolute_bans") or {}
    for key in ABSOLUTE_BAN_KEYS:
        if bans.get(key) is not False:
            raise CampaignProfileError(f"PROFILE_ABSOLUTE_BAN_VIOLATION:{key}")

    if not payload.get("planning_enabled"):
        raise CampaignProfileError("PROFILE_PLANNING_MUST_BE_ENABLED_FOR_PREP")


def _assert_strategy_adapter_binding(payload: Mapping[str, Any]) -> None:
    strategy_id = str(payload["strategy_id"])
    adapter_id = str(payload["adapter_id"])
    profile_id = str(payload["profile_id"])

    if profile_id == LEGACY_4153_PROFILE_ID:
        if strategy_id != "primary_breakout_v1":
            raise CampaignProfileError(
                f"PROFILE_STRATEGY_MISMATCH:{profile_id}:{strategy_id}"
            )
        if adapter_id != "primary_breakout_runner_v1":
            raise CampaignProfileError(
                f"PROFILE_ADAPTER_MISMATCH:{profile_id}:{adapter_id}"
            )
        return

    if profile_id == HH_HL_PREP_PROFILE_ID:
        if strategy_id != HH_HL_CONTINUATION_STRATEGY_ID:
            raise CampaignProfileError(
                f"PROFILE_STRATEGY_MISMATCH:{profile_id}:{strategy_id}"
            )
        if adapter_id != BATCH_B_SHADOW_ADAPTER_ID:
            raise CampaignProfileError(
                f"PROFILE_ADAPTER_MISMATCH:{profile_id}:{adapter_id}"
            )
        record = BATCH_B_STRATEGY_REGISTRY.get(strategy_id)
        if record is None:
            raise CampaignProfileError(f"HOLD_REGISTRY_PROVIDER_MISSING:{strategy_id}")
        if not record.executable:
            raise CampaignProfileError(
                f"HOLD_REGISTRY_STRATEGY_NOT_EXECUTABLE:{strategy_id}"
            )
        return

    raise CampaignProfileError(f"UNKNOWN_CAMPAIGN_PROFILE:{profile_id}")


def profile_from_mapping(payload: Mapping[str, Any]) -> CampaignProfile:
    validate_profile_payload(payload)
    _assert_strategy_adapter_binding(payload)
    return CampaignProfile(
        profile_schema_version=str(payload["profile_schema_version"]),
        profile_id=str(payload["profile_id"]),
        issue_number=int(payload["issue_number"]),
        campaign_id=str(payload["campaign_id"]),
        manifest_path=str(payload["manifest_path"]),
        manifest_schema_version=str(payload["manifest_schema_version"]),
        strategy_id=str(payload["strategy_id"]),
        strategy_version=str(payload["strategy_version"]),
        adapter_id=str(payload["adapter_id"]),
        grid_provider_id=str(payload["grid_provider_id"]),
        run_plan_provider_id=str(payload["run_plan_provider_id"]),
        executor_provider_id=str(payload["executor_provider_id"]),
        analyzer_profile_id=str(payload["analyzer_profile_id"]),
        evidence_namespace=str(payload["evidence_namespace"]),
        artifact_root_template=str(payload["artifact_root_template"]),
        authorization_schema=str(payload["authorization_schema"]),
        reproduction_policy_id=str(payload["reproduction_policy_id"]),
        execution_enabled=bool(payload["execution_enabled"]),
        planning_enabled=bool(payload["planning_enabled"]),
        absolute_bans=dict(payload["absolute_bans"]),
        lr_status=str(payload["lr_status"]),
        campaign_authorized=bool(payload.get("campaign_authorized", False)),
        requires_external_owner_go=bool(
            payload.get("requires_external_owner_go", True)
        ),
        notes=str(payload.get("notes") or ""),
    )


def load_profile(
    profile_id: str,
    *,
    profiles_dir: Path | None = None,
) -> CampaignProfile:
    if profile_id not in KNOWN_PROFILE_IDS:
        raise CampaignProfileError(f"UNKNOWN_CAMPAIGN_PROFILE:{profile_id}")
    root = profiles_dir or PROFILES_DIR
    path = root / f"{profile_id}.json"
    if not path.exists():
        raise CampaignProfileError(f"PROFILE_FILE_MISSING:{path.as_posix()}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CampaignProfileError("PROFILE_ROOT_MUST_BE_OBJECT")
    if str(payload.get("profile_id")) != profile_id:
        raise CampaignProfileError(
            f"PROFILE_ID_FILE_MISMATCH:{payload.get('profile_id')!r}!={profile_id!r}"
        )
    return profile_from_mapping(payload)


def assert_profile_manifest_bind(
    profile: CampaignProfile,
    *,
    issue_number: int | None = None,
    campaign_id: str | None = None,
    strategy_id: str | None = None,
    adapter_id: str | None = None,
    manifest_path: str | None = None,
) -> None:
    if issue_number is not None and int(issue_number) != profile.issue_number:
        raise CampaignProfileError(
            f"PROFILE_ISSUE_MISMATCH:{issue_number}!={profile.issue_number}"
        )
    if campaign_id is not None and campaign_id != profile.campaign_id:
        raise CampaignProfileError(
            f"PROFILE_CAMPAIGN_ID_MISMATCH:{campaign_id!r}!={profile.campaign_id!r}"
        )
    if strategy_id is not None and strategy_id != profile.strategy_id:
        raise CampaignProfileError(
            f"PROFILE_STRATEGY_MISMATCH:{strategy_id!r}!={profile.strategy_id!r}"
        )
    if adapter_id is not None and adapter_id != profile.adapter_id:
        raise CampaignProfileError(
            f"PROFILE_ADAPTER_MISMATCH:{adapter_id!r}!={profile.adapter_id!r}"
        )
    if manifest_path is not None and manifest_path != profile.manifest_path:
        raise CampaignProfileError(
            f"PROFILE_MANIFEST_PATH_MISMATCH:{manifest_path!r}!={profile.manifest_path!r}"
        )


def assert_execution_allowed(profile: CampaignProfile) -> None:
    """Fail closed for planning-only profiles before any replay path."""
    if not profile.execution_enabled:
        raise CampaignProfileError(
            f"PLANNING_ONLY_EXECUTE_FORBIDDEN:{profile.profile_id}"
        )
    if profile.campaign_authorized:
        raise CampaignProfileError(
            "PROFILE_MUST_NOT_SELF_AUTHORIZE_CAMPAIGN:" f"{profile.profile_id}"
        )
    if profile.lr_status != "NO-GO":
        raise CampaignProfileError("PROFILE_LR_MUST_BE_NO_GO")
