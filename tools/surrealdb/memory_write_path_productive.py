"""Memory Write Path Productive — mock-proven contract boundary — G3b #2744.

Non-productive adapter/contract proof for future T3 productive audit trail.
Never performs real DB/network writes. PRODUCTIVE_ACTIVATED remains False.

Guardrails:
    - PERSIST_ALLOWED in memory_write_gate remains False (not flipped here).
    - Default mode is dry_run (zero persistence).
    - audit_persist_productive requires HG-P, env gate, and mock sink only.
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
from tools.surrealdb.memory_write_gate import (
    GATE_SCHEMA_VERSION,
    MemoryWriteAuthorization,
    PERSIST_ALLOWED,
    evaluate_memory_write_gate,
)

WRITE_PATH_PRODUCTIVE_SCHEMA_VERSION = "memory-write-path-productive/v1"
PRODUCTIVE_AUDIT_SCHEMA_VERSION = "productive-audit-path/v1"
PRODUCTIVE_TIER = "T3"
PRODUCTIVE_ACTIVATED = False
PRODUCTIVE_ENV_VAR = "CDB_PERSIST_PRODUCTIVE_AUDIT_TRAIL"
REQUIRED_HUMAN_GO_TIER = "HG-P"
ALLOWED_SINK_MODE = "mock"

ProductiveMode = Literal["dry_run", "audit_persist_productive"]
ProductivePathStatus = Literal[
    "evaluated_only",
    "refused",
    "mock_persisted_productive_audit",
]

_FORBIDDEN_KEYS = frozenset({"human_go_token", "human_go"})


class MemoryWritePathProductiveError(RuntimeError):
    """Raised when productive write path preconditions are not met."""


@dataclass(frozen=True)
class ProductiveWriteAuthorization:
    """Explicit human authorization for productive audit trail mock path."""

    human_go_token: str
    human_go_tier: str
    authorized_by: str
    authorized_at: str
    scope: str
    target_issue: str
    evidence_refs: tuple[str, ...]
    operation: Literal["create", "supersede"] = "create"


class ProductiveAuditSink(Protocol):
    """Mock-only sink abstraction for contract proof."""

    def mode(self) -> str: ...

    def upsert_audit_observation(
        self, observation_id: str, payload: Mapping[str, Any]
    ) -> None: ...

    def observation_exists(self, observation_id: str) -> bool: ...


def productive_env_enabled() -> bool:
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
    authorization: ProductiveWriteAuthorization,
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
    """Return a response-safe gate snapshot without forbidden keys."""
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
        raise MemoryWritePathProductiveError("forbidden key present in envelope")
    serialized = json.dumps(envelope, default=str)
    if '"human_go_token"' in serialized:
        raise MemoryWritePathProductiveError("human_go_token key leaked in envelope")
    if raw_token and _contains_raw_token(envelope, raw_token):
        raise MemoryWritePathProductiveError("raw human_go_token leaked in envelope")
    return envelope


def _refused_envelope(
    *,
    code: str,
    message: str,
    gate_envelope: dict[str, Any] | None = None,
    operation_mode_resolved: str,
    authorization: ProductiveWriteAuthorization | None = None,
) -> dict[str, Any]:
    gate = _public_gate_envelope(gate_envelope)
    limitations = [
        "memory_write_path_productive",
        "persist_allowed_false",
        "productive_not_activated",
        "lr_no_go",
        "no_agent_memory_write_in_productive_path",
        "mock_sink_only_in_g3b",
    ]
    payload: dict[str, Any] = {
        "schema_version": WRITE_PATH_PRODUCTIVE_SCHEMA_VERSION,
        "path_schema_version": PRODUCTIVE_AUDIT_SCHEMA_VERSION,
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "status": "refused",
        "code": code,
        "message": message,
        "path_status": "refused",
        "operation_mode_resolved": operation_mode_resolved,
        "productive_tier": PRODUCTIVE_TIER,
        "productive_activated": PRODUCTIVE_ACTIVATED,
        "productive_audit_status": "not_activated",
        "gate_status": gate.get("gate_status"),
        "persist_allowed": PERSIST_ALLOWED,
        "dry_run_only": True,
        "memory_id": gate.get("memory_id"),
        "gate": gate,
        "audit_observation": None,
        "tables_written": [],
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
    path_status: ProductivePathStatus,
    operation_mode_resolved: str,
    authorization: ProductiveWriteAuthorization | None = None,
    audit_observation: dict[str, Any] | None = None,
    tables_written: tuple[str, ...] = (),
    sink_mode: str | None = None,
    productive_audit_status: str = "not_activated",
) -> dict[str, Any]:
    limitations = list(gate_envelope.get("limitations") or [])
    limitations.extend(
        [
            "memory_write_path_productive",
            "persist_allowed_false",
            "productive_not_activated",
            "lr_no_go",
            "no_agent_memory_write_in_productive_path",
        ]
    )
    if path_status == "evaluated_only":
        limitations.append("path_dry_run_only")
    if path_status == "mock_persisted_productive_audit":
        limitations.extend(["mock_sink_only_in_g3b", "no_real_db_write_in_g3b"])

    payload: dict[str, Any] = {
        "schema_version": WRITE_PATH_PRODUCTIVE_SCHEMA_VERSION,
        "path_schema_version": PRODUCTIVE_AUDIT_SCHEMA_VERSION,
        "gate_schema_version": GATE_SCHEMA_VERSION,
        "status": "ok",
        "code": None,
        "message": None,
        "path_status": path_status,
        "operation_mode_resolved": operation_mode_resolved,
        "productive_tier": PRODUCTIVE_TIER,
        "productive_activated": PRODUCTIVE_ACTIVATED,
        "productive_audit_status": productive_audit_status,
        "gate_status": gate_envelope.get("gate_status"),
        "persist_allowed": PERSIST_ALLOWED,
        "dry_run_only": True,
        "memory_id": gate_envelope.get("memory_id"),
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


def run_memory_write_path_productive(
    record: Mapping[str, Any],
    authorization: ProductiveWriteAuthorization | None,
    *,
    mode: ProductiveMode = "dry_run",
    sink: ProductiveAuditSink | None = None,
    strict: bool = True,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate gate and optionally mock-persist audit_observation via sink.

    Fail-closed: no real DB/network writes. PRODUCTIVE_ACTIVATED remains False.
    """
    ref_now = _parse_now(now)

    if mode not in ("dry_run", "audit_persist_productive"):
        return _refused_envelope(
            code="operation_mode_invalid",
            message=f"unsupported productive write path mode: {mode!r}",
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
            message="Productive audit persist blocked: authorization is required.",
            operation_mode_resolved="audit_persist_productive",
        )

    tier = _normalize_tier(authorization.human_go_tier)
    if tier != REQUIRED_HUMAN_GO_TIER:
        return _refused_envelope(
            code="hg_p_required",
            message=(
                f"Productive audit persist blocked: human_go_tier must be "
                f"{REQUIRED_HUMAN_GO_TIER!r}."
            ),
            operation_mode_resolved="audit_persist_productive",
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
            message=(
                "Productive audit persist blocked: gate did not approve dry-run."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    if not PRODUCTIVE_ACTIVATED:
        pass  # G3b: mock path permitted while PRODUCTIVE_ACTIVATED is False

    if not productive_env_enabled():
        return _refused_envelope(
            code="productive_env_missing",
            message=(
                f"Productive audit persist blocked: {PRODUCTIVE_ENV_VAR} must be '1'."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    if sink is None:
        return _refused_envelope(
            code="mock_sink_required",
            message="Productive audit persist blocked: mock sink is required.",
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    if sink.mode() != ALLOWED_SINK_MODE:
        return _refused_envelope(
            code="mock_sink_invalid_mode",
            message=(
                f"Productive audit persist blocked: sink mode must be "
                f"{ALLOWED_SINK_MODE!r}."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    try:
        audit_row = materialize_audit_observation_from_gate(gate_envelope, now=ref_now)
    except AuditObservationMaterializeError as exc:
        return _refused_envelope(
            code="forbidden_key_present",
            message=f"Productive audit persist blocked: {exc}",
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    if not audit_observation_row_is_redacted(audit_row):
        return _refused_envelope(
            code="audit_row_not_redacted",
            message="Productive audit persist blocked: audit row is not redacted.",
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    observation_id = str(audit_row["observation_id"])
    if sink.observation_exists(observation_id):
        return _refused_envelope(
            code="duplicate_observation_id",
            message=(
                "Productive audit persist blocked: audit_observation already exists."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    sink.upsert_audit_observation(observation_id, audit_row)

    if not sink.observation_exists(observation_id):
        return _refused_envelope(
            code="internal_contract_violation",
            message=(
                "Productive audit persist failed: observation not found after mock "
                "upsert."
            ),
            gate_envelope=gate_envelope,
            operation_mode_resolved="audit_persist_productive",
            authorization=authorization,
        )

    return _success_envelope(
        gate_envelope,
        path_status="mock_persisted_productive_audit",
        operation_mode_resolved="audit_persist_productive",
        authorization=authorization,
        audit_observation=audit_row,
        tables_written=("audit_observation",),
        sink_mode=ALLOWED_SINK_MODE,
        productive_audit_status="mock_persisted",
    )
