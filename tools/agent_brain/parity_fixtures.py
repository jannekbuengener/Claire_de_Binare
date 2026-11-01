"""Representative dual-run fixtures for Slice #18 parity.

One canonical semantic fixture expands into legacy-flat and Agent-Brain
ArtifactRef wire forms so both paths receive the same controlled inputs.
"""

from __future__ import annotations

from typing import Any

from tools.agent_brain.parity import DualRunCase

AS_OF = "2026-10-31T12:00:00Z"


def artifact_pair(
    *,
    artifact_id: str,
    artifact_type: str = "doc",
    summary: str,
    source_path: str,
    source_hash: str,
    payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    legacy = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "summary": summary,
        "source_path": source_path,
    }
    agent_brain = {
        "ref": {
            "schema_version": "artifact-ref/v1",
            "artifact_id": artifact_id,
            "source_id": "repo",
            "source_path": source_path,
            "source_hash": source_hash,
        },
        "artifact_type": artifact_type,
        "summary": summary,
        "payload": dict(payload or {}),
    }
    return legacy, agent_brain


def _case_from_pair(
    *,
    case_id: str,
    target_scope: str,
    summary: str,
    legacy_art: dict[str, Any],
    brain_art: dict[str, Any],
    tags: tuple[str, ...] = (),
) -> DualRunCase:
    return DualRunCase(
        case_id=case_id,
        target_scope=target_scope,
        summary=summary,
        legacy_artifacts=[legacy_art],
        agent_brain_artifacts=[brain_art],
        generated_at_or_as_of=AS_OF,
        tags=tags,
    )


def representative_dual_run_cases() -> list[DualRunCase]:
    """Mandatory representative cases for CLAIRE_PARITY_DUAL_RUN_GO."""
    cases: list[DualRunCase] = []

    leg, brain = artifact_pair(
        artifact_id="AGENTS.md",
        summary="current context",
        source_path="AGENTS.md",
        source_hash="hash-current",
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_current",
            target_scope="parity:current",
            summary="normal current context",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="docs/stale.md",
        summary="stale context marker",
        source_path="docs/stale.md",
        source_hash="hash-stale",
        payload={"freshness": "stale"},
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_stale_marker",
            target_scope="parity:stale",
            summary="stale context payload marker",
            legacy_art=leg,
            brain_art=brain,
            tags=("stale",),
        )
    )

    leg, brain = artifact_pair(
        artifact_id="docs/conflict.md",
        summary="contradictory evidence marker",
        source_path="docs/conflict.md",
        source_hash="hash-conflict",
        payload={"claim": "A", "counter_claim": "B"},
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_contradiction_marker",
            target_scope="parity:contradiction",
            summary="contradictory evidence marker in artifacts",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="scope/a.md",
        summary="scope isolation A",
        source_path="scope/a.md",
        source_hash="hash-scope-a",
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_scope_a",
            target_scope="parity:scope-a",
            summary="scope isolation A",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="scope/b.md",
        summary="scope isolation B",
        source_path="scope/b.md",
        source_hash="hash-scope-b",
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_scope_b",
            target_scope="parity:scope-b",
            summary="scope isolation B",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="memory/fresh.md",
        summary="memory freshness related context",
        source_path="memory/fresh.md",
        source_hash="hash-mem-fresh",
        payload={"memory_state": "CURRENT"},
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_memory_freshness_marker",
            target_scope="parity:memory-fresh",
            summary="memory freshness marker",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="memory/superseded.md",
        summary="superseded memory marker",
        source_path="memory/superseded.md",
        source_hash="hash-mem-superseded",
        payload={"memory_state": "SUPERSEDED"},
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_memory_superseded_marker",
            target_scope="parity:memory-superseded",
            summary="superseded memory marker",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="live/authority.md",
        summary="live-state newer than memory marker",
        source_path="live/authority.md",
        source_hash="hash-live",
        payload={"live_state": "github_live", "memory_state": "STALE"},
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_live_over_memory_marker",
            target_scope="parity:live-authority",
            summary="live-state authority marker",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    leg, brain = artifact_pair(
        artifact_id="empty/legitimate.md",
        summary="legitimate sparse result carrier",
        source_path="empty/legitimate.md",
        source_hash="hash-empty",
        payload={},
    )
    cases.append(
        _case_from_pair(
            case_id="ctx_legitimate_sparse",
            target_scope="parity:sparse",
            summary="legitimate sparse/minimal artifact",
            legacy_art=leg,
            brain_art=brain,
        )
    )

    return cases


__all__ = [
    "AS_OF",
    "artifact_pair",
    "representative_dual_run_cases",
]
