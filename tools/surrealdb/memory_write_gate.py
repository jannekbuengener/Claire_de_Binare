"""Human-GO memory write gate — #2606 Memory Reality Slice 5.

Fail-closed gate and dry-run envelope for agent_memory write intents.
No DB access. No MCP. No persistence. No side effects.

Guardrails:
    - PERSIST_ALLOWED is always False in this slice.
    - Gate pass yields approved_dry_run only; no importer/adapter calls.
    - LR remains NO-GO. Board stage trade-capable is not live-go.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping

from core.replay.canonical_json import canonical_hash
from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.memory_contract import (
    MemoryContractError,
    SCHEMA_VERSION as MEMORY_CONTRACT_SCHEMA_VERSION,
    validate_memory_record,
)

GATE_SCHEMA_VERSION = "memory-write-gate/v1"
OBSERVED_BY = "memory_write_gate/v1"
PERSIST_ALLOWED = False

OBSERVATION_ID_NAMESPACE = uuid.UUID("c8f2a1b0-4d3e-4f5a-9b6c-7d8e9f0a1b2c")

HumanGoTokenPattern = re.compile(r"^GO-\d{4}-\d{2}-\d{2}(?:-[A-Za-z0-9._-]+)?$")

MemoryWriteOperation = Literal["create", "supersede"]

_FORBIDDEN_RECORD_GO_FIELDS = frozenset({"human_go", "human_go_token"})


class MemoryWriteGateError(ValueError):
    """Raised when a memory write gate contract is violated."""


@dataclass(frozen=True)
class MemoryWriteAuthorization:
    """Explicit human authorization for a scoped memory write intent."""

    human_go_token: str
    authorized_by: str
    authorized_at: str
    scope: str
    target_issue: str
    evidence_refs: tuple[str, ...]
    operation: MemoryWriteOperation = "create"


def _parse_observed_at(value: datetime | None) -> datetime:
    effective = value if value is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def _is_valid_human_go_token(token: str) -> bool:
    text = token.strip()
    return bool(text) and bool(HumanGoTokenPattern.match(text))


def _merge_evidence_refs(
    record_refs: list[str],
    auth_refs: tuple[str, ...],
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for ref in (*record_refs, *auth_refs):
        if not isinstance(ref, str):
            continue
        cleaned = ref.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            merged.append(cleaned)
    return merged


def _build_observation_id(
    *,
    memory_id: str | None,
    gate_status: str,
    block_reason: str,
    authorization: MemoryWriteAuthorization | None,
) -> str:
    payload = {
        "gate_schema": GATE_SCHEMA_VERSION,
        "memory_id": memory_id or "",
        "gate_status": gate_status,
        "block_reason": block_reason,
        "target_issue": authorization.target_issue if authorization else "",
        "scope": authorization.scope if authorization else "",
        "operation": authorization.operation if authorization else "",
    }
    return str(uuid.uuid5(OBSERVATION_ID_NAMESPACE, canonical_hash(payload)))


def _blocked_envelope(
    *,
    block_reason: str,
    message: str,
    authorization: MemoryWriteAuthorization | None,
    memory_id: str | None,
    observed_at: datetime,
    limitations: list[str],
) -> dict[str, Any]:
    gate_status = f"blocked_{block_reason}"
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "memory_contract_schema_version": MEMORY_CONTRACT_SCHEMA_VERSION,
        "gate_status": gate_status,
        "persist_allowed": False,
        "dry_run_only": True,
        "memory_id": memory_id,
        "authorization_scope": authorization.scope if authorization else None,
        "target_issue": authorization.target_issue if authorization else None,
        "audit": {
            "observation_type": "memory_write_gate_evaluation",
            "observation_id": _build_observation_id(
                memory_id=memory_id,
                gate_status=gate_status,
                block_reason=block_reason,
                authorization=authorization,
            ),
            "subject_ref": memory_id,
            "message": message,
            "evidence_refs": (
                list(authorization.evidence_refs)
                if authorization and authorization.evidence_refs
                else []
            ),
            "observed_by": OBSERVED_BY,
            "observed_at": observed_at.isoformat(),
            "severity": "blocking",
            "related_memory": [memory_id] if memory_id else [],
            "gate_status": gate_status,
            "human_go_token_present": bool(
                authorization and _is_valid_human_go_token(authorization.human_go_token)
            ),
            "authorization_scope": authorization.scope if authorization else None,
            "target_issue": authorization.target_issue if authorization else None,
        },
        "limitations": limitations,
        "approval_semantics": {
            "read_only": True,
            "no_write": True,
            "dry_run_only": True,
            "no_approval": True,
            "no_live_go": True,
            "no_echtgeld_go": True,
            "note": (
                "Memory write gate blocked. No persistence. No Human-GO authorization "
                "for write execution."
            ),
        },
    }


def _approved_dry_run_envelope(
    *,
    validated_record: dict[str, Any],
    authorization: MemoryWriteAuthorization,
    observed_at: datetime,
) -> dict[str, Any]:
    memory_id = str(validated_record["memory_id"])
    evidence_refs = _merge_evidence_refs(
        validated_record.get("evidence_refs") or [],
        authorization.evidence_refs,
    )
    gate_status = "approved_dry_run"
    limitations = [
        "gate_pass_does_not_persist",
        "persist_allowed_false",
        "lr_no_go",
        "no_db_write_in_slice_5",
        "no_mcp_write_in_slice_5",
    ]
    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "memory_contract_schema_version": MEMORY_CONTRACT_SCHEMA_VERSION,
        "gate_status": gate_status,
        "persist_allowed": False,
        "dry_run_only": True,
        "memory_id": memory_id,
        "validated_record": validated_record,
        "authorization_scope": authorization.scope,
        "target_issue": authorization.target_issue,
        "operation": authorization.operation,
        "audit": {
            "observation_type": "memory_write_gate_evaluation",
            "observation_id": _build_observation_id(
                memory_id=memory_id,
                gate_status=gate_status,
                block_reason="none",
                authorization=authorization,
            ),
            "subject_ref": memory_id,
            "message": (
                "Memory write gate approved for dry-run evaluation only. "
                "No persistence performed."
            ),
            "evidence_refs": evidence_refs,
            "observed_by": OBSERVED_BY,
            "observed_at": observed_at.isoformat(),
            "severity": "info",
            "related_memory": [memory_id],
            "gate_status": gate_status,
            "human_go_token_present": True,
            "authorization_scope": authorization.scope,
            "target_issue": authorization.target_issue,
        },
        "limitations": limitations,
        "approval_semantics": {
            "read_only": True,
            "no_write": True,
            "dry_run_only": True,
            "no_approval": True,
            "no_live_go": True,
            "no_echtgeld_go": True,
            "note": (
                "Dry-run gate pass only. Memory write gate does not persist records. "
                "Operator Human-GO is required for any future write slice."
            ),
        },
    }


def evaluate_memory_write_gate(
    record: Mapping[str, Any],
    authorization: MemoryWriteAuthorization | None,
    *,
    strict: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate a memory write intent against Human-GO and contract rules.

    Fail-closed: always returns a gate envelope; never performs persistence.

    Args:
        record: Raw agent_memory record candidate.
        authorization: Explicit human authorization, or None.
        strict: Passed to validate_memory_record.
        now: Injectable reference time for audit observed_at.

    Returns:
        Gate envelope with gate_status, audit block, and approval_semantics.
    """
    observed_at = _parse_observed_at(now)
    base_limitations = [
        "persist_allowed_false",
        "lr_no_go",
        "no_db_write_in_slice_5",
    ]

    if authorization is None:
        return _blocked_envelope(
            block_reason="no_authorization",
            message="Memory write blocked: authorization is required.",
            authorization=None,
            memory_id=None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if not _is_valid_human_go_token(authorization.human_go_token):
        return _blocked_envelope(
            block_reason="no_human_go",
            message="Memory write blocked: human_go_token is missing or invalid.",
            authorization=authorization,
            memory_id=None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if not authorization.authorized_by.strip():
        return _blocked_envelope(
            block_reason="missing_authorized_by",
            message="Memory write blocked: authorized_by is required.",
            authorization=authorization,
            memory_id=None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if not authorization.authorized_at.strip():
        return _blocked_envelope(
            block_reason="missing_authorized_at",
            message="Memory write blocked: authorized_at is required.",
            authorization=authorization,
            memory_id=None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if not authorization.target_issue.strip():
        return _blocked_envelope(
            block_reason="missing_evidence",
            message="Memory write blocked: target_issue is required.",
            authorization=authorization,
            memory_id=None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if not authorization.evidence_refs or not any(
        ref.strip() for ref in authorization.evidence_refs
    ):
        return _blocked_envelope(
            block_reason="missing_evidence",
            message="Memory write blocked: authorization evidence_refs is required.",
            authorization=authorization,
            memory_id=None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    forbidden_go_fields = sorted(
        field for field in _FORBIDDEN_RECORD_GO_FIELDS if field in record
    )
    if forbidden_go_fields:
        return _blocked_envelope(
            block_reason="agent_self_asserted_go",
            message=(
                "Memory write blocked: record must not carry agent GO fields "
                f"{forbidden_go_fields}."
            ),
            authorization=authorization,
            memory_id=str(record.get("memory_id")) if record.get("memory_id") else None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    try:
        validated = validate_memory_record(dict(record), strict=strict)
    except MemoryContractError as exc:
        return _blocked_envelope(
            block_reason="contract_violation",
            message=f"Memory write blocked: {exc}",
            authorization=authorization,
            memory_id=str(record.get("memory_id")) if record.get("memory_id") else None,
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if authorization.scope.strip() != str(validated["scope"]).strip():
        return _blocked_envelope(
            block_reason="scope_mismatch",
            message=(
                "Memory write blocked: authorization scope does not match record scope."
            ),
            authorization=authorization,
            memory_id=str(validated["memory_id"]),
            observed_at=observed_at,
            limitations=base_limitations,
        )

    if authorization.operation == "supersede":
        superseded_by = validated.get("superseded_by")
        if not isinstance(superseded_by, str) or not superseded_by.strip():
            return _blocked_envelope(
                block_reason="supersede_requires_target",
                message=(
                    "Memory write blocked: supersede operation requires "
                    "non-empty superseded_by on the record."
                ),
                authorization=authorization,
                memory_id=str(validated["memory_id"]),
                observed_at=observed_at,
                limitations=base_limitations,
            )

    return _approved_dry_run_envelope(
        validated_record=validated,
        authorization=authorization,
        observed_at=observed_at,
    )


def run_memory_write_gate_harness(
    record: Mapping[str, Any],
    authorization: MemoryWriteAuthorization | None,
    write_executor: Any | None = None,
    *,
    strict: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate the gate for harness tests. Never invokes write_executor in Slice 5."""
    _ = write_executor
    return evaluate_memory_write_gate(
        record,
        authorization,
        strict=strict,
        now=now,
    )
