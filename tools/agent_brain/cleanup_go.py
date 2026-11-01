"""Evidence-based Cleanup-Go matrix for agent-brain #19 (produced by #18).

#18 does not remove legacy code. It classifies each legacy surface so #19 may
only delete ``SAFE_TO_REMOVE`` entries.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLEANUP_GO_PATH = (
    REPO_ROOT / "docs" / "evidence" / "agent_brain_slice18_cleanup_go.v1.json"
)


class CleanupDisposition(StrEnum):
    SAFE_TO_REMOVE = "SAFE_TO_REMOVE"
    KEEP_FOR_NOW = "KEEP_FOR_NOW"
    BLOCKED_BY_DELTA = "BLOCKED_BY_DELTA"
    COMPATIBILITY_SHIM_REQUIRED = "COMPATIBILITY_SHIM_REQUIRED"


@dataclass(frozen=True, slots=True)
class CleanupItem:
    surface_id: str
    path_glob: str
    disposition: CleanupDisposition
    rationale: str
    evidence: str
    owner_issue: str = "agent-brain#19"


def default_cleanup_matrix(*, parity_passed: bool) -> list[CleanupItem]:
    """Build the #19 Cleanup-Go matrix from #18 evidence posture."""
    if not parity_passed:
        return [
            CleanupItem(
                surface_id="all_legacy_pending_parity",
                path_glob="tools/surrealdb/context_package_v2.py",
                disposition=CleanupDisposition.BLOCKED_BY_DELTA,
                rationale="Parity harness has not passed; no cleanup authorized",
                evidence="dual-run report unaccepted_delta > 0 or uncomparable > 0",
            )
        ]

    return [
        CleanupItem(
            surface_id="legacy_context_path_facade",
            path_glob="tools/agent_brain/legacy.py",
            disposition=CleanupDisposition.COMPATIBILITY_SHIM_REQUIRED,
            rationale=(
                "Selectable legacy facade still required until #19 completes "
                "genericity proof and explicit removal wave"
            ),
            evidence="path_selection + dual-run harness + rollback probe",
        ),
        CleanupItem(
            surface_id="path_selection_dual_path",
            path_glob="tools/agent_brain/path_selection.py",
            disposition=CleanupDisposition.COMPATIBILITY_SHIM_REQUIRED,
            rationale="Dual-path switch is the rollback and parity control plane",
            evidence="rollback probe + consumer_cutover.v1.json",
        ),
        CleanupItem(
            surface_id="consumer_cutover_config_default_legacy",
            path_glob="config/agent-brain/consumer_cutover.v1.json",
            disposition=CleanupDisposition.KEEP_FOR_NOW,
            rationale="Default remains legacy until #19 flips cutover after cleanup",
            evidence="consumer_cutover.v1.json consumer_path=legacy",
        ),
        CleanupItem(
            surface_id="claire_context_package_v2_builder",
            path_glob="tools/surrealdb/context_package_v2.py",
            disposition=CleanupDisposition.KEEP_FOR_NOW,
            rationale=(
                "Still the live legacy builder; removable only after dual-run "
                "consumers migrate fully and #19 genericity proof lands"
            ),
            evidence="LegacyContextPath + dual-run EXACT/SEMANTIC fields",
        ),
        CleanupItem(
            surface_id="claire_surrealdb_mcp_context_tools",
            path_glob="tools/mcp/**/*context*",
            disposition=CleanupDisposition.KEEP_FOR_NOW,
            rationale=(
                "MCP presentation/consumer tools remain Claire-owned; not proven "
                "redundant by #18 dual-run alone"
            ),
            evidence="PARITY_GATES.md Slice 13/14 ownership notes",
        ),
        CleanupItem(
            surface_id="agent_brain_adapter_public_only",
            path_glob="tools/agent_brain/adapter.py",
            disposition=CleanupDisposition.KEEP_FOR_NOW,
            rationale="New path — retain; not cleanup target",
            evidence="consumer smoke + E2E proof",
        ),
        CleanupItem(
            surface_id="duplicate_flat_artifact_helpers_if_any",
            path_glob="tools/agent_brain/parity_fixtures.py::legacy_flat_only",
            disposition=CleanupDisposition.SAFE_TO_REMOVE,
            rationale=(
                "After #19 migrates remaining Claire callers to ArtifactRef, "
                "legacy-flat expansion helpers may be deleted"
            ),
            evidence=(
                "ACCEPTED_CONTRACT_CHANGE artifact_wire_shape; only remove once "
                "no production caller uses flat artifact_id"
            ),
        ),
        CleanupItem(
            surface_id="slice13_temporary_notes_in_cutover_doc",
            path_glob="docs/onboarding/agent_brain_consumer_cutover.md",
            disposition=CleanupDisposition.SAFE_TO_REMOVE,
            rationale="Non-goals / temporary #13 wording can be collapsed after #19",
            evidence="docs superseded by parity + cleanup evidence packs",
        ),
    ]


def write_cleanup_go(
    *,
    parity_passed: bool,
    path: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    out = path or DEFAULT_CLEANUP_GO_PATH
    items = default_cleanup_matrix(parity_passed=parity_passed)
    payload: dict[str, Any] = {
        "schema_version": "agent-brain-cleanup-go/v1",
        "source_issue": "agent-brain#18",
        "follow_up_issue": "agent-brain#19",
        "claire_tracking_issue": 4615,
        "parity_passed": parity_passed,
        "cleanup_go": parity_passed,
        "rule": "#19 may only remove SAFE_TO_REMOVE surfaces",
        "items": [
            {
                **asdict(item),
                "disposition": item.disposition.value,
            }
            for item in items
        ],
    }
    if extra:
        payload.update(extra)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def load_cleanup_go(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_CLEANUP_GO_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def assert_cleanup_go_ready(payload: Mapping[str, Any]) -> None:
    data = dict(payload)
    if data.get("cleanup_go") is not True:
        raise AssertionError("cleanup_go is not granted")
    if data.get("parity_passed") is not True:
        raise AssertionError("cleanup_go requires parity_passed")
    items = data.get("items") or []
    blocked = [
        item
        for item in items
        if isinstance(item, dict)
        and item.get("disposition") == CleanupDisposition.BLOCKED_BY_DELTA.value
    ]
    if blocked:
        raise AssertionError(f"cleanup blocked by deltas: {blocked}")

__all__ = [
    "DEFAULT_CLEANUP_GO_PATH",
    "CleanupDisposition",
    "CleanupItem",
    "assert_cleanup_go_ready",
    "default_cleanup_matrix",
    "load_cleanup_go",
    "write_cleanup_go",
]
