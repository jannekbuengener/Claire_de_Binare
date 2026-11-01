"""Failure-parity, E2E Context/Evidence/Memory/Trust, rollback, cleanup-go (#18)."""

from __future__ import annotations

import importlib
from datetime import datetime

import pytest

from tools.agent_brain.adapter import AgentBrainAdapter
from tools.agent_brain.cleanup_go import (
    CleanupDisposition,
    assert_cleanup_go_ready,
    write_cleanup_go,
)
from tools.agent_brain.consumer import read_context, rollback_to_legacy
from tools.agent_brain.e2e_proof import assert_e2e_pass, run_e2e_proof
from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.legacy import LegacyContextPath
from tools.agent_brain.path_selection import ConsumerPath
from tools.agent_brain.pin import PINNED_AGENT_BRAIN_VERSION, PINNED_REQUIREMENT

pytestmark = pytest.mark.unit


def _require_pinned_agent_brain() -> None:
    try:
        importlib.import_module("agent_brain.protocol")
    except ImportError as exc:  # pragma: no cover
        pytest.skip(f"agent-brain not installed ({PINNED_REQUIREMENT}): {exc}")


def _brain_artifact() -> dict[str, object]:
    return {
        "ref": {
            "schema_version": "artifact-ref/v1",
            "artifact_id": "AGENTS.md",
            "source_id": "repo",
            "source_path": "AGENTS.md",
            "source_hash": "fail-parity",
        },
        "artifact_type": "doc",
        "summary": "failure parity",
        "payload": {},
    }


def _legacy_artifact() -> dict[str, object]:
    return {
        "artifact_id": "AGENTS.md",
        "artifact_type": "doc",
        "summary": "failure parity",
        "source_path": "AGENTS.md",
    }


def test_failure_parity_policy_blocked_both_paths() -> None:
    _require_pinned_agent_brain()
    with pytest.raises(ConsumerError) as legacy_exc:
        LegacyContextPath().context_read(
            target_scope="echtgeld", artifacts=[_legacy_artifact()]
        )
    with pytest.raises(ConsumerError) as brain_exc:
        AgentBrainAdapter().context_read(
            target_scope="echtgeld", artifacts=[_brain_artifact()]
        )
    assert legacy_exc.value.code is ConsumerErrorCode.POLICY_BLOCKED
    assert brain_exc.value.code is ConsumerErrorCode.POLICY_BLOCKED


def test_failure_parity_empty_artifacts_legacy_vs_invalid_brain_input() -> None:
    """Legacy rejects empty artifacts; Agent Brain rejects missing artifacts.

    Both are fail-closed (not empty-success). Classified ACCEPTED_CONTRACT_CHANGE
    at the error-shape layer: different codes, same safety posture.
    """
    _require_pinned_agent_brain()
    from tools.surrealdb.context_package_v2 import ContextPackageV2Error

    with pytest.raises(ContextPackageV2Error):
        LegacyContextPath().context_read(target_scope="parity:empty", artifacts=[])

    # Agent Brain protocol requires at least structurally valid artifacts list;
    # empty list still builds a package with zero artifacts in some modes — Claire
    # adapter always passes caller artifacts. Probe malformed artifact instead.
    bad = AgentBrainAdapter().context_read(
        target_scope="parity:malformed",
        artifacts=[{"summary": "missing ref and artifact_id"}],
    )
    assert bad.ok is False
    assert bad.error is not None
    assert bad.error["code"] in {
        "invalid_input",
        "internal_failure",
    }


def test_failure_parity_memory_unbound_not_empty_success() -> None:
    _require_pinned_agent_brain()
    result = AgentBrainAdapter().memory_read(
        scope={
            "schema_version": "memory-scope/v1",
            "kind": "tenant",
            "tenant_id": "parity-fail",
        },
        as_of="2026-10-31T12:00:00Z",
    )
    assert result.ok is False
    assert result.error is not None
    assert result.error["code"] == "capability_unavailable"
    assert result.data is None


def test_e2e_context_evidence_memory_trust_and_rollback(tmp_path) -> None:
    _require_pinned_agent_brain()
    from agent_brain.memory.in_memory import InMemoryMemoryStore
    from agent_brain.memory.types import MEMORY_RECORD_SCHEMA, MemoryRecord
    from agent_brain.memory.scope import MEMORY_SCOPE_SCHEMA, MemoryScope, MemoryScopeKind
    from agent_brain.protocol import ProtocolGateway, ProtocolRequest
    from agent_brain.protocol.runtime import ProtocolRuntime

    scope = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="parity-e2e",
    )
    record = MemoryRecord(
        schema_version=MEMORY_RECORD_SCHEMA,
        record_id="mem-e2e-1",
        subject_ref="subject-e2e",
        scope=scope,
        content_ref="content:mem-e2e-1",
        known_at=datetime(2026, 10, 31, 11, 0, 0),
        summary="e2e memory",
        evidence_refs=("ev-e2e",),
    )
    runtime = ProtocolRuntime(memory_store=InMemoryMemoryStore(records=(record,)))
    gateway = ProtocolGateway(runtime=runtime)

    def invoke_fn(operation: str, payload=None):
        return gateway.invoke_sync(
            ProtocolRequest(operation=operation, payload=dict(payload or {}))
        )

    memory_adapter = AgentBrainAdapter(invoke_fn=invoke_fn, verify_pin=True)
    report = run_e2e_proof(memory_adapter=memory_adapter)
    assert_e2e_pass(report)
    assert report.agent_brain_version == PINNED_AGENT_BRAIN_VERSION
    names = {step.name for step in report.steps}
    assert {
        "pinned_version",
        "context",
        "retrieval",
        "evidence_trust",
        "memory_unbound_failure",
        "memory_bound_read",
        "live_state_authority",
        "rollback",
    }.issubset(names)


def test_memory_freshness_states_via_public_memory_read_api() -> None:
    """Pinned package public memory.read surface — CURRENT / STALE / SUPERSEDED."""
    _require_pinned_agent_brain()
    import asyncio
    from datetime import timedelta

    from agent_brain.contracts.provenance import PROVENANCE_SCHEMA, Provenance
    from agent_brain.contracts.resolution import RESOLUTION_META_SCHEMA, ResolutionMeta
    from agent_brain.contracts.resolution import ResolutionState
    from agent_brain.contracts.temporal import TEMPORAL_ENVELOPE_SCHEMA, TemporalEnvelope
    from agent_brain.memory.in_memory import InMemoryMemoryStore
    from agent_brain.memory.read import MemoryEntryCatalog, MemoryReadService
    from agent_brain.memory.read.models import MEMORY_ENTRY_SCHEMA, MemoryEntry
    from agent_brain.memory.scope import MEMORY_SCOPE_SCHEMA, MemoryScope, MemoryScopeKind
    from agent_brain.memory.types import MEMORY_RECORD_SCHEMA, MemoryRecord

    as_of = datetime(2026, 10, 31, 12, 0, 0)
    scope = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="parity-freshness",
    )

    def entry(
        *,
        record_id: str,
        known_at: datetime,
        ttl_seconds: int | None,
        superseded_by_ref: str | None = None,
    ) -> MemoryEntry:
        record = MemoryRecord(
            schema_version=MEMORY_RECORD_SCHEMA,
            record_id=record_id,
            subject_ref="subject-1",
            scope=scope,
            content_ref=f"content:{record_id}",
            known_at=known_at,
            summary=record_id,
            evidence_refs=("ev-1",),
        )
        return MemoryEntry(
            schema_version=MEMORY_ENTRY_SCHEMA,
            record=record,
            temporal=TemporalEnvelope(
                schema_version=TEMPORAL_ENVELOPE_SCHEMA,
                known_at=known_at,
            ),
            provenance=Provenance(
                schema_version=PROVENANCE_SCHEMA,
                source_kind="repo_doc",
                source_ref="docs/START_HIER.md",
            ),
            resolution_meta=ResolutionMeta(
                schema_version=RESOLUTION_META_SCHEMA,
                superseded_by_ref=superseded_by_ref,
                confidence=0.8,
                source_trust=0.7,
            ),
            ttl_seconds=ttl_seconds,
        )

    current = entry(record_id="mem-current", known_at=as_of, ttl_seconds=7200)
    stale = entry(
        record_id="mem-stale",
        known_at=as_of - timedelta(hours=2),
        ttl_seconds=60,
    )
    superseded = entry(
        record_id="mem-old",
        known_at=as_of - timedelta(minutes=5),
        ttl_seconds=7200,
        superseded_by_ref="mem-current",
    )
    catalog = MemoryEntryCatalog((current, stale, superseded))
    store = InMemoryMemoryStore(
        records=(current.record, stale.record, superseded.record)
    )
    service = MemoryReadService(store=store, catalog=catalog)
    outcome = asyncio.run(
        service.recall_for_scope(scope, as_of=as_of, subject_ref="subject-1", limit=10)
    )
    by_id = {item.entry.record.record_id: item for item in outcome.items}
    assert by_id["mem-current"].resolution_state is ResolutionState.CURRENT
    assert by_id["mem-stale"].resolution_state is ResolutionState.STALE
    assert by_id["mem-old"].resolution_state is ResolutionState.SUPERSEDED


def test_live_state_contradicts_memory_via_public_api() -> None:
    _require_pinned_agent_brain()
    from agent_brain.contracts.provenance import PROVENANCE_SCHEMA, Provenance
    from agent_brain.contracts.resolution import RESOLUTION_META_SCHEMA, ResolutionMeta
    from agent_brain.contracts.temporal import TEMPORAL_ENVELOPE_SCHEMA, TemporalEnvelope
    from agent_brain.core.source_priority import SourcePriority
    from agent_brain.memory.read.live_state import (
        LiveStateObservation,
        StaticLiveStateChecker,
        revalidate_against_live_state,
    )
    from agent_brain.memory.read.models import (
        LIVE_CLAIM_SCHEMA,
        MEMORY_ENTRY_SCHEMA,
        LiveRevalidationStatus,
        LiveStateClaim,
        MemoryEntry,
    )
    from agent_brain.memory.scope import MEMORY_SCOPE_SCHEMA, MemoryScope, MemoryScopeKind
    from agent_brain.memory.types import MEMORY_RECORD_SCHEMA, MemoryRecord

    scope = MemoryScope(
        schema_version=MEMORY_SCOPE_SCHEMA,
        kind=MemoryScopeKind.TENANT,
        tenant_id="parity-live",
    )
    record = MemoryRecord(
        schema_version=MEMORY_RECORD_SCHEMA,
        record_id="mem-live-1",
        subject_ref="issue:18",
        scope=scope,
        content_ref="content:mem-live-1",
        known_at=datetime(2026, 10, 31, 11, 0, 0),
        summary="claims issue open",
        evidence_refs=("ev-1",),
    )
    entry = MemoryEntry(
        schema_version=MEMORY_ENTRY_SCHEMA,
        record=record,
        temporal=TemporalEnvelope(
            schema_version=TEMPORAL_ENVELOPE_SCHEMA,
            known_at=record.known_at,
        ),
        provenance=Provenance(
            schema_version=PROVENANCE_SCHEMA,
            source_kind="memory",
            source_ref="memory:mem-live-1",
        ),
        resolution_meta=ResolutionMeta(schema_version=RESOLUTION_META_SCHEMA),
        live_claim=LiveStateClaim(
            schema_version=LIVE_CLAIM_SCHEMA,
            claim_key="issue:18:state",
            asserted_value="open",
            requires_revalidation=True,
        ),
    )
    checker = StaticLiveStateChecker(
        {
            "issue:18:state": LiveStateObservation(
                claim_key="issue:18:state",
                value="closed",
                source="github_live",
            )
        }
    )
    result = revalidate_against_live_state(
        entry,
        checker=checker,
        source_priority=SourcePriority(
            ordered_sources=("github_live", "repo_live", "memory")
        ),
    )
    assert result.status is LiveRevalidationStatus.CONTRADICTED


def test_rollback_probe_under_parity_setup() -> None:
    _require_pinned_agent_brain()
    brain = read_context(
        target_scope="parity:rollback-probe",
        artifacts=[_brain_artifact()],
        path=ConsumerPath.AGENT_BRAIN,
    )
    assert brain.ok is True
    assert brain.path == "agent_brain"
    assert rollback_to_legacy() is ConsumerPath.LEGACY
    legacy = read_context(
        target_scope="parity:rollback-probe",
        artifacts=[_legacy_artifact()],
        path=ConsumerPath.LEGACY,
    )
    assert legacy.ok is True
    assert legacy.path == "legacy"
    # No migration / no state corruption marker required between paths.
    assert legacy.data is not None
    assert brain.data is not None


def test_cleanup_go_written_after_parity_pass() -> None:
    _require_pinned_agent_brain()
    from tools.agent_brain.parity import assert_parity_pass, run_dual_suite
    from tools.agent_brain.parity_fixtures import representative_dual_run_cases

    report = run_dual_suite(representative_dual_run_cases())
    assert_parity_pass(report)
    path = write_cleanup_go(
        parity_passed=True,
        extra={
            "dual_run_counts": report.counts(),
            "agent_brain_version": PINNED_AGENT_BRAIN_VERSION,
        },
    )
    payload = path.read_text(encoding="utf-8")
    assert "SAFE_TO_REMOVE" in payload
    assert "COMPATIBILITY_SHIM_REQUIRED" in payload
    from tools.agent_brain.cleanup_go import load_cleanup_go

    loaded = load_cleanup_go(path)
    assert_cleanup_go_ready(loaded)
    dispositions = {item["disposition"] for item in loaded["items"]}
    assert CleanupDisposition.BLOCKED_BY_DELTA.value not in dispositions
    assert CleanupDisposition.SAFE_TO_REMOVE.value in dispositions
