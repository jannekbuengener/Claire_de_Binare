"""E2E proof runner: Claire adapter → agent_brain.protocol → core surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from tools.agent_brain.adapter import AgentBrainAdapter, ConsumerResult
from tools.agent_brain.consumer import read_context, rollback_to_legacy
from tools.agent_brain.path_selection import ConsumerPath
from tools.agent_brain.pin import PINNED_AGENT_BRAIN_VERSION, verify_runtime_pin


@dataclass
class E2EStepResult:
    name: str
    ok: bool
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class E2EProofReport:
    steps: list[E2EStepResult]
    agent_brain_version: str | None = None

    def passed(self) -> bool:
        return all(step.ok for step in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed(),
            "agent_brain_version": self.agent_brain_version,
            "steps": [
                {"name": s.name, "ok": s.ok, "detail": s.detail} for s in self.steps
            ],
        }


def _index_record() -> dict[str, Any]:
    return {
        "schema_version": "index-record/v1",
        "record_id": "rec-parity-e2e-1",
        "record_type": "doc",
        "source": {
            "schema_version": "artifact-ref/v1",
            "artifact_id": "AGENTS.md",
            "source_id": "repo",
            "source_path": "AGENTS.md",
            "source_hash": "e2e-hash",
        },
        "content_hash": "e2e-content",
        "attributes": {"title": "agents", "text": "agent brain consumer e2e"},
    }


def run_e2e_proof(
    *,
    adapter: AgentBrainAdapter | None = None,
    memory_adapter: AgentBrainAdapter | None = None,
) -> E2EProofReport:
    """Prove Context / Retrieval / Evidence(Trust) / Memory / Rollback / Live authority.

    ``memory_adapter`` may bind an in-memory ProtocolRuntime via invoke_fn so
    memory_read is exercised without mocks at the Claire↔protocol boundary.
    """
    steps: list[E2EStepResult] = []
    brain = adapter or AgentBrainAdapter()

    try:
        version = verify_runtime_pin()
        steps.append(
            E2EStepResult(
                "pinned_version",
                version == PINNED_AGENT_BRAIN_VERSION,
                {"version": version},
            )
        )
    except Exception as exc:  # noqa: BLE001 - evidence capture
        steps.append(E2EStepResult("pinned_version", False, {"error": str(exc)}))
        return E2EProofReport(steps=steps)

    health = brain.health()
    steps.append(
        E2EStepResult(
            "health",
            health.ok is True,
            {"data_keys": sorted((health.data or {}).keys())},
        )
    )

    caps = brain.capabilities()
    cap_names = []
    if caps.ok and caps.data:
        for item in caps.data.get("capabilities") or []:
            if isinstance(item, Mapping):
                cap_names.append(str(item.get("capability")))
    steps.append(
        E2EStepResult(
            "capabilities",
            caps.ok
            and {"context_read", "retrieval", "evidence"}.issubset(set(cap_names)),
            {"capabilities": cap_names},
        )
    )

    artifact = {
        "ref": {
            "schema_version": "artifact-ref/v1",
            "artifact_id": "AGENTS.md",
            "source_id": "repo",
            "source_path": "AGENTS.md",
            "source_hash": "e2e-hash",
        },
        "artifact_type": "doc",
        "summary": "e2e context",
        "payload": {"note": "read-only"},
    }
    context = brain.context_read(
        target_scope="parity:e2e-context",
        artifacts=[artifact],
        generated_at_or_as_of="2026-10-31T12:00:00Z",
    )
    package = (context.data or {}).get("package") if context.data else None
    source_priority = list((package or {}).get("source_priority") or [])
    live_authority = (
        bool(source_priority)
        and source_priority[0] == "github_live"
        and "memory" in source_priority
        and source_priority.index("github_live") < source_priority.index("memory")
    )
    steps.append(
        E2EStepResult(
            "context",
            context.ok is True and isinstance(package, Mapping),
            {
                "scope": (package or {}).get("target_scope") if package else None,
                "schema_version": (
                    (package or {}).get("schema_version") if package else None
                ),
            },
        )
    )
    steps.append(
        E2EStepResult(
            "live_state_authority",
            live_authority,
            {"source_priority": source_priority},
        )
    )

    retrieval = brain.retrieval(
        query={
            "schema_version": "retrieval-query/v1",
            "query_id": "e2e-q1",
            "query_text": "agent",
            "source_id": "repo",
        },
        records=[_index_record()],
        source_priority=["repo"],
    )
    retrieval_result = (retrieval.data or {}).get("result") if retrieval.data else None
    retrieval_candidates = (
        list((retrieval_result or {}).get("candidates") or [])
        if isinstance(retrieval_result, Mapping)
        else []
    )
    retrieval_record_ids = [
        str(item.get("record_id"))
        for item in retrieval_candidates
        if isinstance(item, Mapping) and item.get("record_id")
    ]
    retrieval_ok = (
        retrieval.ok is True
        and isinstance(retrieval_result, Mapping)
        and (retrieval_result or {}).get("query_id") == "e2e-q1"
        and "rec-parity-e2e-1" in retrieval_record_ids
    )
    steps.append(
        E2EStepResult(
            "retrieval",
            retrieval_ok,
            {
                "query_id": (
                    (retrieval_result or {}).get("query_id")
                    if retrieval_result
                    else None
                ),
                "record_ids": retrieval_record_ids,
            },
        )
    )

    evidence = brain.evidence(scope="parity:e2e-evidence", topic="trust")
    trust = (evidence.data or {}).get("trust_summary") if evidence.data else None
    steps.append(
        E2EStepResult(
            "evidence_trust",
            evidence.ok is True and isinstance(trust, Mapping),
            {
                "trust_level": (trust or {}).get("trust_level") if trust else None,
                "limitations_present": (
                    bool((trust or {}).get("limitations")) if trust else False
                ),
            },
        )
    )

    # Default unbound memory must be distinguishable failure (not empty success).
    unbound = brain.memory_read(
        scope={
            "schema_version": "memory-scope/v1",
            "kind": "tenant",
            "tenant_id": "parity-e2e",
        },
        as_of="2026-10-31T12:00:00Z",
    )
    unbound_ok = (
        unbound.ok is False
        and unbound.error is not None
        and unbound.error.get("code")
        in {"capability_unavailable", "backend_unavailable"}
    )
    steps.append(
        E2EStepResult(
            "memory_unbound_failure",
            unbound_ok,
            {"error": unbound.error},
        )
    )

    if memory_adapter is not None:
        bound = memory_adapter.memory_read(
            scope={
                "schema_version": "memory-scope/v1",
                "kind": "tenant",
                "tenant_id": "parity-e2e",
            },
            as_of="2026-10-31T12:00:00Z",
            subject_ref="subject-e2e",
        )
        result = (bound.data or {}).get("result") if bound.data else None
        items = list((result or {}).get("items") or []) if result else []
        record_ids: list[str] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            entry = item.get("entry") if isinstance(item.get("entry"), Mapping) else {}
            record = (
                entry.get("record") if isinstance(entry.get("record"), Mapping) else {}
            )
            if record.get("record_id"):
                record_ids.append(str(record["record_id"]))
        memory_ok = (
            bound.ok is True
            and isinstance(result, Mapping)
            and (result or {}).get("availability") == "available"
            and "mem-e2e-1" in record_ids
        )
        steps.append(
            E2EStepResult(
                "memory_bound_read",
                memory_ok,
                {
                    "availability": (
                        (result or {}).get("availability") if result else None
                    ),
                    "item_count": len(items),
                    "record_ids": record_ids,
                },
            )
        )
    else:
        steps.append(
            E2EStepResult(
                "memory_bound_read",
                False,
                {"error": "memory_adapter not provided"},
            )
        )

    # Claire policy fail-closed for live/echtgeld scopes.
    try:
        brain.context_read(target_scope="live-trade", artifacts=[artifact])
        steps.append(
            E2EStepResult(
                "policy_live_blocked",
                False,
                {"error": "expected ConsumerError"},
            )
        )
    except Exception as exc:  # noqa: BLE001 - structured policy probe
        steps.append(
            E2EStepResult(
                "policy_live_blocked",
                "policy_blocked" in str(exc),
                {"error": str(exc)},
            )
        )

    # Rollback probe under E2E setup.
    active = read_context(
        target_scope="parity:e2e-rollback",
        artifacts=[artifact],
        path=ConsumerPath.AGENT_BRAIN,
        adapter=brain,
    )
    rolled = rollback_to_legacy()
    legacy = read_context(
        target_scope="parity:e2e-rollback",
        artifacts=[
            {
                "artifact_id": "AGENTS.md",
                "artifact_type": "doc",
                "summary": "rollback legacy",
                "source_path": "AGENTS.md",
            }
        ],
        path=ConsumerPath.LEGACY,
    )
    steps.append(
        E2EStepResult(
            "rollback",
            active.ok is True
            and rolled is ConsumerPath.LEGACY
            and legacy.ok is True
            and legacy.path == "legacy",
            {
                "agent_brain_ok": active.ok,
                "rollback_path": str(rolled),
                "legacy_ok": legacy.ok,
            },
        )
    )

    return E2EProofReport(steps=steps, agent_brain_version=PINNED_AGENT_BRAIN_VERSION)


def assert_e2e_pass(report: E2EProofReport) -> None:
    if report.passed():
        return
    failed = [s.name for s in report.steps if not s.ok]
    raise AssertionError(f"E2E proof failed steps: {failed}")


__all__ = [
    "E2EProofReport",
    "E2EStepResult",
    "assert_e2e_pass",
    "run_e2e_proof",
]
