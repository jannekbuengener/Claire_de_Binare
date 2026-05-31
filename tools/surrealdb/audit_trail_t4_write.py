"""HG-W governed T4 agent_memory proof write — operator-only (#2759 Phase B/C).

Executes exactly one scoped proof write on the governed non-localhost T4 endpoint
when explicit env gates are set. Never logs raw human_go_token values.
"""

from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from core.utils.clock import utcnow as cdb_utcnow
from tools.surrealdb.audit_observation_from_gate import (
    AuditObservationMaterializeError,
    audit_observation_row_is_redacted,
    materialize_audit_observation_from_gate,
)
from tools.surrealdb.audit_trail_t3_common import (
    AuditTrailEnv,
    check_statement_results,
    sql_request,
)
from tools.surrealdb.audit_trail_t4_common import T4_PROOF_SCOPE
from tools.surrealdb.memory_contract import generate_memory_id
from tools.surrealdb.memory_db_proof_local_dev import _JSONL_STRIP_FIELDS, _surql_string
from tools.surrealdb.memory_write_gate import (
    PERSIST_ENV_VAR,
    MemoryWriteAuthorization,
    approved_for_persist,
    evaluate_memory_write_gate,
    persist_env_enabled,
    target_issue_references_2759,
)
from tools.surrealdb.memory_write_path_t4 import (
    PRODUCTIVE_ENV_VAR as T4_PRODUCTIVE_MODE_ENV_VAR,
    REQUIRED_HUMAN_GO_TIER,
    T4WriteAuthorization,
    _build_agent_memory_row,
)

HGW_TOKEN_ENV_VAR = "CDB_T4_HGW_HUMAN_GO_TOKEN"
HGW_AUTHORIZED_BY_ENV_VAR = "CDB_T4_HGW_AUTHORIZED_BY"
PROOF_CONTENT = (
    "HG-W governed T4 agent_memory proof row for #2759 "
    "(run-scoped; mandatory rollback)."
)
PROOF_SOURCE_REF = "docs/surrealdb/memory-write-path-t4-runbook-v1.md"
PROOF_EVIDENCE_REF = "github:issue/2759"


class AuditTrailT4WriteError(RuntimeError):
    """Raised when T4 HG-W proof write preconditions fail."""


class AuditTrailT4SqlClient:
    """Minimal HTTPS /sql client for governed T4 audit trail endpoint."""

    def __init__(
        self,
        env: AuditTrailEnv,
        *,
        ssl_context: ssl.SSLContext,
    ) -> None:
        self._env = env
        self._ssl_context = ssl_context

    def execute(self, sql: str) -> list[dict[str, Any]]:
        status, body = sql_request(
            self._env,
            sql,
            ssl_context=self._ssl_context,
        )
        if status != 200:
            raise AuditTrailT4WriteError(f"T4 /sql request failed with HTTP {status}")
        return check_statement_results(body)

    def record_exists(self, table: str, raw_id: str, *, id_field: str) -> bool:
        literal = _surql_string(raw_id)
        results = self.execute(f"SELECT * FROM {table} WHERE {id_field} = {literal};")
        for item in results:
            result = item.get("result")
            if isinstance(result, list) and result:
                return True
        return False

    def delete_record(self, table: str, raw_id: str, *, id_field: str) -> None:
        literal = _surql_string(raw_id)
        self.execute(f"DELETE {table} WHERE {id_field} = {literal};")

    @staticmethod
    def _surql_record_id(table: str, record_id: str) -> str:
        escaped = record_id.replace("\u27e9", "\\u27e9")
        return f"{table}:\u27e8{escaped}\u27e9"

    def create_audit_observation_proof(
        self,
        observation_id: str,
        audit_row: Mapping[str, Any],
        *,
        memory_id: str,
    ) -> None:
        mem_ref = self._surql_record_id("agent_memory", memory_id)
        evidence_refs = json.dumps(list(audit_row.get("evidence_refs") or []))
        related_memory = json.dumps(list(audit_row.get("related_memory") or []))
        related_claims = json.dumps(list(audit_row.get("related_claims") or []))
        related_decisions = json.dumps(list(audit_row.get("related_decisions") or []))
        sql = (
            "CREATE audit_observation SET "
            f"observation_id = {_surql_string(observation_id)}, "
            f"observation_type = {_surql_string(str(audit_row['observation_type']))}, "
            f"subject_ref = {mem_ref}, "
            f"message = {_surql_string(str(audit_row['message']))}, "
            f"evidence_refs = {evidence_refs}, "
            f"confidence = {float(audit_row.get('confidence', 1.0))}, "
            f"observed_by = {_surql_string(str(audit_row['observed_by']))}, "
            "observed_at = time::now(), "
            f"comment = {_surql_string(str(audit_row['comment']))}, "
            f"severity = {_surql_string(str(audit_row['severity']))}, "
            f"related_claims = {related_claims}, "
            f"related_decisions = {related_decisions}, "
            f"related_memory = {related_memory}, "
            f"status = {_surql_string(str(audit_row.get('status', 'open')))}, "
            "created_at = time::now();"
        )
        self.execute(sql)

    def upsert_create(
        self, table: str, record_id: str, payload: dict[str, Any]
    ) -> None:
        from tools.surrealdb.context_importer import (
            _payload_to_surql_content,
            _remap_record_refs_for_db_payload,
        )

        rid = self._surql_record_id(table, record_id)
        db_payload = _remap_record_refs_for_db_payload(table, dict(payload))
        for field in _JSONL_STRIP_FIELDS:
            db_payload.pop(field, None)
        payload_json = _payload_to_surql_content(db_payload)
        self.execute(f"UPSERT {rid} CONTENT {payload_json};")


def hgw_proof_env_authorized() -> bool:
    """Return True when all HG-W proof env gates are satisfied (fail-closed)."""
    token = os.environ.get(HGW_TOKEN_ENV_VAR, "").strip()
    if not token:
        return False
    if not persist_env_enabled():
        return False
    if os.environ.get(T4_PRODUCTIVE_MODE_ENV_VAR) != "1":
        return False
    return True


def _parse_now(value: datetime | None) -> datetime:
    effective = value if value is not None else cdb_utcnow()
    if effective.tzinfo is None:
        return effective.replace(tzinfo=timezone.utc)
    return effective.astimezone(timezone.utc)


def build_hgw_proof_record(*, now: datetime | None = None) -> dict[str, Any]:
    ref_now = _parse_now(now)
    scope = f"memory_write_path_t4:{T4_PROOF_SCOPE}"
    namespace = scope
    memory_type = "semantic_memory"
    created_by = "audit_trail_t4_proof"
    source_refs = [PROOF_SOURCE_REF]
    evidence_refs = [PROOF_EVIDENCE_REF]
    created_at = ref_now.isoformat()
    expires_at = (ref_now + timedelta(hours=1)).isoformat()
    run_stamp = ref_now.strftime("%Y%m%dT%H%M%SZ")
    content = f"{PROOF_CONTENT} run={run_stamp}"
    memory_id = generate_memory_id(
        scope=scope,
        namespace=namespace,
        memory_type=memory_type,
        created_by=created_by,
        content=content,
        source_refs=source_refs,
    )
    return {
        "memory_id": memory_id,
        "scope": scope,
        "namespace": namespace,
        "memory_type": memory_type,
        "content": content,
        "source_refs": source_refs,
        "evidence_refs": evidence_refs,
        "confidence": 1.0,
        "ttl": 3600,
        "expires_at": expires_at,
        "created_by": created_by,
        "created_at": created_at,
    }


def build_hgw_proof_authorization(
    *, now: datetime | None = None
) -> T4WriteAuthorization:
    token = os.environ.get(HGW_TOKEN_ENV_VAR, "").strip()
    if not token:
        raise AuditTrailT4WriteError(
            f"{HGW_TOKEN_ENV_VAR} is required for HG-W proof write"
        )
    authorized_by = os.environ.get(HGW_AUTHORIZED_BY_ENV_VAR, "operator").strip()
    if not authorized_by:
        raise AuditTrailT4WriteError(
            f"{HGW_AUTHORIZED_BY_ENV_VAR} must be non-empty when set"
        )
    ref_now = _parse_now(now)
    return T4WriteAuthorization(
        human_go_token=token,
        human_go_tier=REQUIRED_HUMAN_GO_TIER,
        authorized_by=authorized_by,
        authorized_at=ref_now.isoformat(),
        scope=f"memory_write_path_t4:{T4_PROOF_SCOPE}",
        target_issue="2759",
        evidence_refs=(PROOF_EVIDENCE_REF,),
        operation="create",
    )


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


_AUDIT_TRAIL_OBSERVATION_FIELDS = frozenset(
    {
        "observation_id",
        "observation_type",
        "subject_ref",
        "message",
        "evidence_refs",
        "confidence",
        "observed_by",
        "observed_at",
        "comment",
        "severity",
        "related_claims",
        "related_decisions",
        "related_memory",
        "status",
        "created_at",
    }
)

_AUDIT_TRAIL_AGENT_MEMORY_FIELDS = frozenset(
    {
        "memory_id",
        "scope",
        "namespace",
        "memory_type",
        "content",
        "source_refs",
        "evidence_refs",
        "confidence",
        "ttl",
        "expires_at",
        "stale_after",
        "superseded_by",
        "created_by",
        "comment",
        "created_at",
    }
)


def _normalize_surql_datetime(value: Any) -> Any:
    if isinstance(value, str) and value.endswith("+00:00"):
        return value.replace("+00:00", "Z")
    return value


def _filter_fields(row: dict[str, Any], allowed: frozenset[str]) -> dict[str, Any]:
    return {
        key: _normalize_surql_datetime(value)
        for key, value in row.items()
        if key in allowed
    }


def _enrich_audit_row_for_audit_trail_db(
    audit_row: dict[str, Any], *, memory_id: str
) -> dict[str, Any]:
    enriched = dict(audit_row)
    enriched.setdefault(
        "comment", "HG-W T4 proof audit_observation (#2759; run-scoped)."
    )
    enriched.setdefault("related_claims", [])
    enriched.setdefault("related_decisions", [])
    enriched.setdefault("confidence", 1.0)
    enriched["subject_ref"] = f"agent_memory:\u27e8{memory_id}\u27e9"
    return _filter_fields(enriched, _AUDIT_TRAIL_OBSERVATION_FIELDS)


def _enrich_memory_row_for_audit_trail_db(memory_row: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(memory_row)
    enriched.setdefault("comment", "HG-W T4 proof agent_memory (#2759; run-scoped).")
    return _filter_fields(enriched, _AUDIT_TRAIL_AGENT_MEMORY_FIELDS)


def execute_hgw_proof_write(
    env: AuditTrailEnv,
    *,
    ssl_context: ssl.SSLContext,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Perform one governed T4 proof write (audit_observation then agent_memory)."""
    if not hgw_proof_env_authorized():
        raise AuditTrailT4WriteError("HG-W proof env gates not satisfied")

    ref_now = _parse_now(now)
    authorization = build_hgw_proof_authorization(now=ref_now)
    record = build_hgw_proof_record(now=ref_now)
    gate_auth = _to_gate_authorization(authorization)

    tier = authorization.human_go_tier.strip().upper()
    if tier != REQUIRED_HUMAN_GO_TIER:
        raise AuditTrailT4WriteError("human_go_tier must be HG-W")

    if not target_issue_references_2759(authorization.target_issue):
        raise AuditTrailT4WriteError("target_issue must reference #2759")

    gate_envelope = evaluate_memory_write_gate(
        record,
        gate_auth,
        strict=True,
        now=ref_now,
    )
    if gate_envelope.get("gate_status") != "approved_dry_run":
        raise AuditTrailT4WriteError(
            f"gate blocked: {gate_envelope.get('gate_status')!r}"
        )

    try:
        audit_row = materialize_audit_observation_from_gate(gate_envelope, now=ref_now)
    except AuditObservationMaterializeError as exc:
        raise AuditTrailT4WriteError(str(exc)) from exc

    if not audit_observation_row_is_redacted(audit_row):
        raise AuditTrailT4WriteError("audit row is not redacted")

    memory_id = str(gate_envelope["memory_id"])
    expected_subject_ref = f"agent_memory:{memory_id}"
    if audit_row.get("subject_ref") != expected_subject_ref:
        raise AuditTrailT4WriteError(
            "audit_observation.subject_ref chain mismatch "
            f"(expected {expected_subject_ref!r})"
        )

    audit_row = _enrich_audit_row_for_audit_trail_db(audit_row, memory_id=memory_id)

    if not approved_for_persist(
        gate_auth,
        human_go_tier=tier,
        proof_scope=T4_PROOF_SCOPE,
    ):
        raise AuditTrailT4WriteError("approved_for_persist returned false")

    client = AuditTrailT4SqlClient(env, ssl_context=ssl_context)
    observation_id = str(audit_row["observation_id"])

    if client.record_exists(
        "audit_observation", observation_id, id_field="observation_id"
    ):
        raise AuditTrailT4WriteError("duplicate audit_observation proof row")

    if client.record_exists("agent_memory", memory_id, id_field="memory_id"):
        raise AuditTrailT4WriteError("duplicate agent_memory proof row")

    audit_written = False
    memory_written = False
    try:
        client.create_audit_observation_proof(
            observation_id, audit_row, memory_id=memory_id
        )
        audit_written = True
        if not client.record_exists(
            "audit_observation", observation_id, id_field="observation_id"
        ):
            raise AuditTrailT4WriteError("audit_observation read-back failed")

        memory_row = _enrich_memory_row_for_audit_trail_db(
            _build_agent_memory_row(gate_envelope, audit_row)
        )
        client.upsert_create("agent_memory", memory_id, memory_row)
        memory_written = True
        if not client.record_exists("agent_memory", memory_id, id_field="memory_id"):
            raise AuditTrailT4WriteError("agent_memory read-back failed")
    except AuditTrailT4WriteError:
        if audit_written or memory_written:
            try:
                rollback_hgw_proof_write(
                    env,
                    ssl_context=ssl_context,
                    memory_id=memory_id,
                    observation_id=observation_id,
                )
            except AuditTrailT4WriteError:
                pass
        raise
    except Exception as exc:
        if audit_written or memory_written:
            try:
                rollback_hgw_proof_write(
                    env,
                    ssl_context=ssl_context,
                    memory_id=memory_id,
                    observation_id=observation_id,
                )
            except AuditTrailT4WriteError:
                pass
        raise AuditTrailT4WriteError(str(exc)) from exc

    return {
        "memory_id": memory_id,
        "observation_id": observation_id,
        "subject_ref": expected_subject_ref,
        "audit_observation_written": "yes",
        "agent_memory_written": "yes",
        "proof_row_written": "yes",
        "persist_env_var": PERSIST_ENV_VAR,
        "productive_env_var": T4_PRODUCTIVE_MODE_ENV_VAR,
    }


def rollback_hgw_proof_write(
    env: AuditTrailEnv,
    *,
    ssl_context: ssl.SSLContext,
    memory_id: str,
    observation_id: str,
) -> dict[str, str]:
    """Delete run-scoped proof rows and verify absence."""
    client = AuditTrailT4SqlClient(env, ssl_context=ssl_context)
    if client.record_exists("agent_memory", memory_id, id_field="memory_id"):
        client.delete_record("agent_memory", memory_id, id_field="memory_id")
    if client.record_exists(
        "audit_observation", observation_id, id_field="observation_id"
    ):
        client.delete_record(
            "audit_observation", observation_id, id_field="observation_id"
        )

    memory_gone = not client.record_exists(
        "agent_memory", memory_id, id_field="memory_id"
    )
    observation_gone = not client.record_exists(
        "audit_observation", observation_id, id_field="observation_id"
    )
    if not memory_gone or not observation_gone:
        raise AuditTrailT4WriteError("rollback verification failed")

    return {
        "rollback_status": "ok",
        "agent_memory_deleted": "yes" if memory_gone else "no",
        "audit_observation_deleted": "yes" if observation_gone else "no",
    }


def redact_write_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-safe result without forbidden keys."""
    cleaned = dict(result)
    for key in ("human_go_token", "human_go"):
        cleaned.pop(key, None)
    serialized = json.dumps(cleaned, default=str)
    if '"human_go_token"' in serialized:
        raise AuditTrailT4WriteError("forbidden key leaked in write result")
    return cleaned
