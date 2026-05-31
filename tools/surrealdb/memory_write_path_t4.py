"""Memory Write Path T4 — mock-proven agent_memory scaffold — G4 #2759.

Non-productive adapter/contract proof for future T4 productive agent_memory write.
Never performs real DB/network writes. PRODUCTIVE_ACTIVATED remains False.

Guardrails:
    - PERSIST_ALLOWED in memory_write_gate remains False (not flipped here).
    - Productive memory branch requires approved_for_persist() (env + HG-W + #2759).
    - Default mode is dry_run (zero persistence).
    - agent_memory_persist_productive requires HG-W, env gate, and mock sink only.
    - Mandatory audit_observation before any agent_memory branch.
    - LR remains NO-GO.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Protocol

from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.audit_observation_from_gate import (
    AuditObservationMaterializeError,
    audit_observation_row_is_redacted,
    materialize_audit_observation_from_gate,
)
from tools.surrealdb.audit_trail_t3_common import guard_non_localhost
from tools.surrealdb.memory_write_gate import (
    GATE_SCHEMA_VERSION,
    MemoryWriteAuthorization,
    PERSIST_ALLOWED,
    PROOF_SCOPE_HGW_2759,
    approved_for_persist,
    evaluate_memory_write_gate,
    persist_env_enabled,
    target_issue_references_2759,
)

WRITE_PATH_T4_SCHEMA_VERSION = "memory-write-path-t4/v1"
PRODUCTIVE_MEMORY_SCHEMA_VERSION = "productive-memory-path-t4/v1"
PRODUCTIVE_TIER = "T4"
PRODUCTIVE_ACTIVATED = False
PRODUCTIVE_ENV_VAR = "CDB_PERSIST_PRODUCTIVE_AGENT_MEMORY"
REQUIRED_HUMAN_GO_TIER = "HG-W"
PROOF_SCOPE = PROOF_SCOPE_HGW_2759
ALLOWED_SINK_MODE = "mock"
ALLOWED_SINK_TABLES = frozenset({"audit_observation", "agent_memory"})

T4Mode = Literal["dry_run", "agent_memory_persist_productive"]
T4PathStatus = Literal[
    "evaluated_only",
    "refused",
    "mock_persisted_audit_only",
    "mock_persisted_productive_memory",
]

_FORBIDDEN_KEYS = frozenset({"human_go_token", "human_go"})


class MemoryWritePathT4Error(RuntimeError):
    """Raised when T4 write path preconditions are not met."""


@dataclass(frozen=True)
class T4WriteAuthorization:
    """Explicit human authorization for T4 agent_memory mock path."""

    human_go_token: str
    human_go_tier: str
    authorized_by: str
    authorized_at: str
    scope: str
    target_issue: str
    evidence_refs: tuple[str, ...]
    operation: Literal["create", "supersede"] = "create"


class T4AgentMemorySink(Protocol):
    """Mock-only sink abstraction for T4 contract proof."""

    def mode(self) -> str: ...

    def upsert_audit_observation(
        self, observation_id: str, payload: Mapping[str, Any]
    ) -> None: ...

    def observation_exists(self, observation_id: str) -> bool: ...

    def upsert_agent_memory(
        self, memory_id: str, payload: Mapping[str, Any]
    ) -> None: ...

    def memory_exists(self, memory_id: str) -> bool: ...


def t4_env_enabled() -> bool:
    return os.environ.get(PRODUCTIVE_ENV_VAR) == "1"


def _parse_now(value: datetime | None) -> datetime:
    effective = value if value is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def _token_fingerprint(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:16]}"


def _normalize_tier(tier: str | None) -> str:
    if tier is None:
        return ""
    return tier.strip().upper()


def _to_gate_authorization(
    authorization: T4WriteAuthorization,
) -> MemoryWriteAuthorization:
    return MemoryWriteAuthorization(
        human_go_token=authorization.human_go_token,
        authorized_by=authorization.authorized_by,
        authorized_at=authorization.authorized_at,
        scope=authorization.scope,
        target_issue=authorization.target_issue,
        evidence_refs=authorization.evidence_refs,
        operation=authorization.operation,
    )


def _contains_forbidden_keys(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in _FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_keys(nested):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_keys(item) for item in value)
    return False


def _contains_raw_token(value: Any, token: str) -> bool:
    if not token:
        return False
    if isinstance(value, str):
        return token in value
    if isinstance(value, Mapping):
        return any(_contains_raw_token(nested, token) for nested in value.values())
    if isinstance(value, list):
        return any(_contains_raw_token(item, token) for item in value)
    return False


def _public_gate_envelope(gate_envelope: Mapping[str, Any] | None) -> dict[str, Any]:
    if not gate_envelope:
        return {}

    def _clean(node: Any) -> Any:
        if isinstance(node, Mapping):
            cleaned: dict[str, Any] = {}
            for key, value in node.items():
                if key in _FORBIDDEN_KEYS:
                    continue
                public_key = (
                    "go_token_present" if key == "human_go_token_present" else key
                )
                cleaned[public_key] = _clean(value)
            return cleaned
        if isinstance(node, list):
            return [_clean(item) for item in node]
        return node

    return _clean(dict(gate_envelope))


def _sanitize_envelope(
    envelope: dict[str, Any],
    *,
    raw_token: str | None = None,
) -> dict[str, Any]:
    if _contains_forbidden_keys(envelope):
        raise MemoryWritePathT4Error("forbidden key present in envelope")
    serialized = json.dumps(envelope, default=str)
    if '"human_go_token"' in serialized:
        raise MemoryWritePathT4Error("human_go_token key leaked in envelope")
    if raw_token and _contains_raw_token(envelope, raw_token):
        raise MemoryWritePathT4Error("raw human_go_token leaked in envelope")
    return envelope


def _refused_envelope(
    *,
    code: str,
    message: str,
    gate_envelope: dict[str, Any] | None = None,
    operation_mode_resolved: str,
    authorization: T4WriteAuthorization | None = None,
    tables_written: tuple[str, ...] = (),
    audit_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = _public_gate_envelope(gate_envelope)
    limitations = [
        "memory_write_path_t4",
        "persist_allowed_false",
        "productive_not_activated",
        "lr_no_go",
        "mock_sink_only_in_g4_scaffold",
    ]
    payload: dict[str, Any] = {
        "schema_version": WRITE_PATH_T4_SCHEMA_VERSION,
        "path_schema_version": PRODUCTIVE_MEMORY_SCHEMA_VERSION,
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "status": "refused",
        "code": code,
        "message": message,
        "path_status": "refused",
        "operation_mode_resolved": operation_mode_resolved,
        "productive_tier": PRODUCTIVE_TIER,
        "productive_activated": PRODUCTIVE_ACTIVATED,
        "productive_memory_status": "not_activated",
        "gate_status": gate.get("gate_status"),
        "persist_allowed": PERSIST_ALLOWED,
        "dry_run_only": True,
        "memory_id": gate.get("memory_id"),
        "agent_memory_written": False,
        "gate": gate,
        "audit_observation": _public_audit_observation(audit_observation),
        "tables_written": list(tables_written),
        "sink_mode": None,
        "limitations": limitations,
        "approval_semantics": gate.get(
            "approval_semantics",
            {
                "read_only": True,
                "no_write": True,
                "dry_run_only": True,
                "no_approval": True,
                "no_live_go": True,
                "no_echtgeld_go": True,
            },
        ),
        "token_redaction": {
            "go_token_present": bool(
                authorization and authorization.human_go_token.strip()
            ),
            "go_token_fingerprint": (
                _token_fingerprint(authorization.human_go_token)
                if authorization and authorization.human_go_token.strip()
                else None
            ),
        },
    }
    return _sanitize_envelope(
        payload,
        raw_token=authorization.human_go_token if authorization else None,
    )


def _public_audit_observation(
    audit_observation: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if audit_observation is None:
        return None
    cleaned = _public_gate_envelope(audit_observation)
    return cleaned if isinstance(cleaned, dict) else dict(audit_observation)


def _success_envelope(
    gate_envelope: dict[str, Any],
    *,
    path_status: T4PathStatus,
    operation_mode_resolved: str,
    authorization: T4WriteAuthorization | None = None,
    audit_observation: dict[str, Any] | None = None,
    tables_written: tuple[str, ...] = (),
    sink_mode: str | None = None,
    productive_memory_status: str = "not_activated",
    agent_memory_written: bool = False,
) -> dict[str, Any]:
    limitations = list(gate_envelope.get("limitations") or [])
    limitations.extend(
        [
            "memory_write_path_t4",
            "lr_no_go",
        ]
    )
    if not PERSIST_ALLOWED:
        limitations.extend(["persist_allowed_false", "productive_not_activated"])
    if path_status == "evaluated_only":
        limitations.append("path_dry_run_only")
    if path_status in ("mock_persisted_audit_only", "mock_persisted_productive_memory"):
        limitations.extend(["mock_sink_only_in_g4_scaffold", "no_real_db_write_in_g4"])

    payload: dict[str, Any] = {
        "schema_version": WRITE_PATH_T4_SCHEMA_VERSION,
        "path_schema_version": PRODUCTIVE_MEMORY_SCHEMA_VERSION,
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "status": "ok",
        "code": None,
        "message": None,
        "path_status": path_status,
        "operation_mode_resolved": operation_mode_resolved,
        "productive_tier": PRODUCTIVE_TIER,
        "productive_activated": PRODUCTIVE_ACTIVATED,
        "productive_memory_status": productive_memory_status,
        "gate_status": gate_envelope.get("gate_status"),
        "persist_allowed": PERSIST_ALLOWED,
        "dry_run_only": not agent_memory_written,
        "memory_id": gate_envelope.get("memory_id"),
        "agent_memory_written": agent_memory_written,
        "gate": _public_gate_envelope(gate_envelope),
        "audit_observation": _public_audit_observation(audit_observation),
        "tables_written": list(tables_written),
        "sink_mode": sink_mode,
        "limitations": limitations,
        "approval_semantics": gate_envelope.get("approval_semantics"),
        "token_redaction": {
            "go_token_present": bool(
                authorization and authorization.human_go_token.strip()
            ),
            "go_token_fingerprint": (
                _token_fingerprint(authorization.human_go_token)
                if authorization and authorization.human_go_token.strip()
                else None
            ),
        },
    }
    return _sanitize_envelope(
        payload,
        raw_token=authorization.human_go_token if authorization else None,
    )


def _build_agent_memory_row(
    gate_envelope: Mapping[str, Any],
    audit_row: Mapping[str, Any],
) -> dict[str, Any]:
    validated = gate_envelope.get("validated_record") or {}
    memory_id = str(gate_envelope["memory_id"])
    observation_id = str(audit_row["observation_id"])
    return {
        "memory_id": memory_id,
        "scope": validated.get("scope") or PROOF_SCOPE,
        "namespace": validated.get("namespace"),
        "memory_type": validated.get("memory_type"),
        "content": validated.get("content"),
        "source_refs": list(validated.get("source_refs") or []),
        "evidence_refs": list(validated.get("evidence_refs") or []),
        "confidence": validated.get("confidence"),
        "ttl": validated.get("ttl"),
        "expires_at": validated.get("expires_at"),
        "created_by": validated.get("created_by"),
        "created_at": validated.get("created_at"),
        "audit_observation_id": observation_id,
        "subject_ref": f"agent_memory:{memory_id}",
        "related_memory": [memory_id],
    }


def run_memory_write_path_t4(
    record: Mapping[str, Any],
    authorization: T4WriteAuthorization | None,
    *,
    mode: T4Mode = "dry_run",
    sink: T4AgentMemorySink | None = None,
    strict: bool = True,
    now: datetime | None = None,
    endpoint_url: str | None = None,
) -> dict[str, Any]:
    """Evaluate gate and optionally mock-persist audit_observation (+ memory when allowed).

    Fail-closed: no real DB/network writes unless future G3 enables PERSIST_ALLOWED.
    """
    ref_now = _parse_now(now)

    if mode not in ("dry_run", "agent_memory_persist_productive"):
        return _refused_envelope(
            code="operation_mode_invalid",
            message=f"unsupported T4 write path mode: {mode!r}",
            operation_mode_resolved=str(mode),
            authorization=authorization,
        )

    if mode == "dry_run":
        gate_envelope = evaluate_memory_write_gate(
            record,
            _to_gate_authorization(authorization) if authorization else None,
            strict=strict,
            now=ref_now,
        )
        return _success_envelope(
            gate_envelope,
            path_status="evaluated_only",
            operation_mode_resolved="dry_run",
            authorization=authorization,
        )

    if authorization is None:
        return _refused_envelope(
            code="no_authorization",
            message="T4 agent_memory persist blocked: authorization is required.",
            operation_mode_resolved="agent_memory_persist_productive",
        )

    tier = _normalize_tier(authorization.human_go_tier)
    if tier != REQUIRED_HUMAN_GO_TIER:
        return _refused_envelope(
            code="hg_w_required",
            message=(
                f"T4 agent_memory persist blocked: human_go_tier must be "
                f"{REQUIRED_HUMAN_GO_TIER!r}."
            ),
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    gate_envelope = evaluate_memory_write_gate(
        record,
        _to_gate_authorization(authorization),
        strict=strict,
        now=ref_now,
    )

    if gate_envelope.get("gate_status") != "approved_dry_run":
        return _refused_envelope(
            code="gate_blocked",
            message="T4 agent_memory persist blocked: gate did not approve dry-run.",
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if not t4_env_enabled():
        return _refused_envelope(
            code="productive_env_missing",
            message=(
                f"T4 agent_memory persist blocked: {PRODUCTIVE_ENV_VAR} must be '1'."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    gate_auth = _to_gate_authorization(authorization)
    if not persist_env_enabled():
        return _refused_envelope(
            code="persist_env_missing",
            message=(
                "T4 agent_memory persist blocked: CDB_PERSIST_ALLOWED env gate "
                "required."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if not target_issue_references_2759(authorization.target_issue):
        return _refused_envelope(
            code="target_issue_mismatch",
            message=(
                "T4 agent_memory persist blocked: target_issue must reference #2759."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if authorization.scope.strip() != f"memory_write_path_t4:{PROOF_SCOPE}":
        return _refused_envelope(
            code="proof_scope_mismatch",
            message=(
                f"T4 agent_memory persist blocked: scope must match proof scope "
                f"{PROOF_SCOPE!r}."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if sink is None:
        return _refused_envelope(
            code="mock_sink_required",
            message="T4 agent_memory persist blocked: mock sink is required.",
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if sink.mode() != ALLOWED_SINK_MODE:
        return _refused_envelope(
            code="mock_sink_invalid_mode",
            message=(
                f"T4 agent_memory persist blocked: sink mode must be "
                f"{ALLOWED_SINK_MODE!r}."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if endpoint_url is not None:
        try:
            guard_non_localhost(endpoint_url)
        except ValueError as exc:
            return _refused_envelope(
                code="localhost_endpoint_refused",
                message=f"T4 agent_memory persist blocked: {exc}",
                gate_envelope=gate_envelope,
                operation_mode_resolved="agent_memory_persist_productive",
                authorization=authorization,
            )

    try:
        audit_row = materialize_audit_observation_from_gate(gate_envelope, now=ref_now)
    except AuditObservationMaterializeError as exc:
        return _refused_envelope(
            code="forbidden_key_present",
            message=f"T4 agent_memory persist blocked: {exc}",
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    if not audit_observation_row_is_redacted(audit_row):
        return _refused_envelope(
            code="audit_row_not_redacted",
            message="T4 agent_memory persist blocked: audit row is not redacted.",
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    observation_id = str(audit_row["observation_id"])
    if sink.observation_exists(observation_id):
        return _refused_envelope(
            code="duplicate_observation_id",
            message=(
                "T4 agent_memory persist blocked: audit_observation already exists."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    sink.upsert_audit_observation(observation_id, audit_row)

    if not sink.observation_exists(observation_id):
        return _refused_envelope(
            code="internal_contract_violation",
            message=(
                "T4 agent_memory persist failed: observation not found after mock "
                "upsert."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
        )

    memory_id = str(gate_envelope["memory_id"])

    persist_approved = approved_for_persist(
        gate_auth,
        human_go_tier=tier,
        proof_scope=PROOF_SCOPE,
    )

    if not persist_approved:
        return _success_envelope(
            gate_envelope,
            path_status="mock_persisted_audit_only",
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
            audit_observation=audit_row,
            tables_written=("audit_observation",),
            sink_mode=ALLOWED_SINK_MODE,
            productive_memory_status="mock_persisted_audit_only",
            agent_memory_written=False,
        )

    if sink.memory_exists(memory_id):
        return _refused_envelope(
            code="duplicate_memory_id",
            message="T4 agent_memory persist blocked: memory_id already exists.",
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
            tables_written=("audit_observation",),
            audit_observation=audit_row,
        )

    memory_row = _build_agent_memory_row(gate_envelope, audit_row)
    sink.upsert_agent_memory(memory_id, memory_row)

    if not sink.memory_exists(memory_id):
        return _refused_envelope(
            code="internal_contract_violation",
            message=(
                "T4 agent_memory persist failed: memory not found after mock upsert."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="agent_memory_persist_productive",
            authorization=authorization,
            tables_written=("audit_observation",),
            audit_observation=audit_row,
        )

    return _success_envelope(
        gate_envelope,
        path_status="mock_persisted_productive_memory",
        operation_mode_resolved="agent_memory_persist_productive",
        authorization=authorization,
        audit_observation=audit_row,
        tables_written=("audit_observation", "agent_memory"),
        sink_mode=ALLOWED_SINK_MODE,
        productive_memory_status="mock_persisted",
        agent_memory_written=True,
    )
