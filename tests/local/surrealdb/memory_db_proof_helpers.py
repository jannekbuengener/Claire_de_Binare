"""Helpers for #2606 Slice 4 local DB-backed memory read proof.

Test-local only. Run-scoped fixture materialization, pre/post DB checks,
seed via context_importer (local-dev, 127.0.0.1:8010), and targeted cleanup.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from tools.surrealdb.context_importer import EXPECTED_JSONL_FILES
from tools.surrealdb.gen_run_id import _timestamp_run_id
from tools.surrealdb.memory_contract import generate_memory_id

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "surrealdb" / "memory_db_proof"

LOCAL_SURR_URL = "http://127.0.0.1:8010"
LOCAL_NS = "cdb_context_local"
LOCAL_DB = "cdb_context_intel"
LOCAL_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

_BASE_SCOPE = "memory_db_proof"
_BASE_EVIDENCE_IDS = ("ev-mdbproof-base-001", "ev-mdbproof-base-002")

_ID_REFERENCE_FIELDS = frozenset(
    {
        "evidence_id",
        "memory_id",
        "evidence_refs",
        "source_refs",
    }
)


@dataclass(frozen=True)
class MemoryDbProofRecordPlan:
    run_id: str
    run_tag: str
    scope: str
    evidence_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]

    @property
    def records_by_table(self) -> tuple[tuple[str, str], ...]:
        rows: list[tuple[str, str]] = []
        rows.extend(("evidence_ref", item) for item in self.evidence_ids)
        rows.extend(("agent_memory", item) for item in self.memory_ids)
        return tuple(rows)


def resolve_memory_proof_run_id() -> str:
    override = os.environ.get("CDB_MEMORY_DB_PROOF_RUN_ID", "").strip()
    if override:
        return override
    return f"{_timestamp_run_id()}-{os.getpid()}"


def memory_proof_run_tag(run_id: str) -> str:
    tag = re.sub(r"[^a-zA-Z0-9]", "", run_id)
    if not tag:
        raise ValueError("run_id must contain at least one alphanumeric character")
    return tag[:24]


def build_memory_proof_record_plan(run_id: str) -> MemoryDbProofRecordPlan:
    tag = memory_proof_run_tag(run_id)
    scope = f"{_BASE_SCOPE}:{tag}"

    def _scoped_evidence(base: str) -> str:
        stem, suffix = base.rsplit("-", 1)
        return f"{stem}-{tag}-{suffix}"

    evidence_ids = tuple(_scoped_evidence(item) for item in _BASE_EVIDENCE_IDS)
    memory_ids = _compute_run_scoped_memory_ids(scope=scope, evidence_ids=evidence_ids)
    return MemoryDbProofRecordPlan(
        run_id=run_id,
        run_tag=tag,
        scope=scope,
        evidence_ids=evidence_ids,
        memory_ids=memory_ids,
    )


def _compute_run_scoped_memory_ids(
    *,
    scope: str,
    evidence_ids: tuple[str, ...],
) -> tuple[str, ...]:
    fresh_path = _FIXTURE_DIR / "agent_memories.jsonl"
    memory_ids: list[str] = []
    for index, raw_line in enumerate(
        fresh_path.read_text(encoding="utf-8").splitlines()
    ):
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        record["scope"] = scope
        record["namespace"] = scope
        record["evidence_refs"] = [evidence_ids[index]]
        record["memory_id"] = generate_memory_id(
            scope=record["scope"],
            namespace=record["namespace"],
            memory_type=record["memory_type"],
            created_by=record["created_by"],
            content=record["content"],
            source_refs=record["source_refs"],
        )
        memory_ids.append(record["memory_id"])
    return tuple(memory_ids)


def _id_remap(plan: MemoryDbProofRecordPlan) -> dict[str, str]:
    return {
        _BASE_EVIDENCE_IDS[0]: plan.evidence_ids[0],
        _BASE_EVIDENCE_IDS[1]: plan.evidence_ids[1],
    }


def _replace_value(value: Any, id_map: dict[str, str]) -> Any:
    if isinstance(value, str):
        return id_map.get(value, value)
    if isinstance(value, list):
        return [_replace_value(item, id_map) for item in value]
    return value


def _replace_record_fields(
    record: dict[str, Any],
    *,
    plan: MemoryDbProofRecordPlan,
    id_map: dict[str, str],
) -> dict[str, Any]:
    updated: dict[str, Any] = {}
    for key, value in record.items():
        if key in _ID_REFERENCE_FIELDS or key.endswith("_refs") or key.endswith("_by"):
            updated[key] = _replace_value(value, id_map)
        else:
            updated[key] = value
    updated["run_id"] = plan.run_id
    updated["scope"] = plan.scope
    updated["namespace"] = plan.scope
    updated["memory_id"] = generate_memory_id(
        scope=updated["scope"],
        namespace=updated["namespace"],
        memory_type=updated["memory_type"],
        created_by=updated["created_by"],
        content=updated["content"],
        source_refs=updated["source_refs"],
    )
    return updated


def materialize_memory_proof_records(
    filename: str,
    *,
    run_id: str,
    plan: MemoryDbProofRecordPlan,
) -> str:
    path = _FIXTURE_DIR / filename
    id_map = _id_remap(plan)
    records: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        if filename == "agent_memories.jsonl":
            record = _replace_record_fields(record, plan=plan, id_map=id_map)
        else:
            record["run_id"] = run_id
            record = {
                key: (
                    _replace_value(value, id_map)
                    if key in _ID_REFERENCE_FIELDS or key == "evidence_id"
                    else value
                )
                for key, value in record.items()
            }
        records.append(json.dumps(record, ensure_ascii=True, sort_keys=True))
    return "\n".join(records) + ("\n" if records else "")


def memory_proof_tmp_root(run_id: str) -> Path:
    return _REPO_ROOT / ".tmp" / "memory-db-proof" / run_id


def assert_memory_proof_tmp_absent(tmp_root: Path) -> None:
    if tmp_root.exists():
        raise AssertionError(
            "memory db proof tmp dir already exists; previous cleanup likely failed"
        )


def cleanup_memory_proof_tmp(tmp_root: Path) -> None:
    if tmp_root.exists():
        shutil.rmtree(tmp_root, ignore_errors=False)
    if tmp_root.exists():
        raise AssertionError("memory db proof tmp dir still present after cleanup")


def materialize_memory_proof_bundle(
    tmp_path: Path,
    *,
    run_id: str,
    plan: MemoryDbProofRecordPlan,
) -> Path:
    bundle_dir = tmp_path / "memory-db-proof-bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    seeded = frozenset({"evidence_refs.jsonl", "agent_memories.jsonl"})
    for filename in EXPECTED_JSONL_FILES.values():
        target = bundle_dir / filename
        if filename in seeded:
            target.write_text(
                materialize_memory_proof_records(filename, run_id=run_id, plan=plan),
                encoding="utf-8",
            )
        else:
            target.write_text("", encoding="utf-8")
    return bundle_dir


def _surql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


class MemoryDbProofSqlClient:
    """Minimal local-only /sql client for memory proof pre/post checks."""

    def __init__(
        self,
        *,
        surreal_url: str,
        namespace: str,
        database: str,
        user: str,
        password: str,
        timeout: int = 15,
    ) -> None:
        parsed = urllib.parse.urlparse(surreal_url)
        host = parsed.hostname or ""
        if host not in LOCAL_ALLOWED_HOSTS:
            raise ValueError("memory db proof SQL client is local-dev only")
        self._url = surreal_url.rstrip("/")
        self._namespace = namespace
        self._database = database
        self._auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        self._timeout = timeout

    @classmethod
    def from_secrets_dir(
        cls,
        secrets_dir: Path,
        *,
        surreal_url: str = LOCAL_SURR_URL,
        namespace: str = LOCAL_NS,
        database: str = LOCAL_DB,
    ) -> MemoryDbProofSqlClient:
        env_file = secrets_dir / "SURREALDB_ENV"
        if not env_file.is_file():
            raise FileNotFoundError("SURREALDB_ENV missing in secrets dir")
        user: str | None = None
        password: str | None = None
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("SURREAL_USER="):
                user = stripped.split("=", 1)[1]
            elif stripped.startswith("SURREAL_PASS="):
                password = stripped.split("=", 1)[1]
        if not user or not password:
            raise ValueError("SURREALDB_ENV missing SURREAL_USER or SURREAL_PASS")
        return cls(
            surreal_url=surreal_url,
            namespace=namespace,
            database=database,
            user=user,
            password=password,
        )

    def execute(self, sql: str) -> list[dict[str, Any]]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "text/plain",
            "Authorization": f"Basic {self._auth}",
            "surreal-ns": self._namespace,
            "surreal-db": self._database,
        }
        req = urllib.request.Request(
            f"{self._url}/sql",
            data=sql.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read()
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"local SurrealDB /sql request failed: {exc.reason}"
            ) from exc

        raw = body.decode("utf-8", errors="replace")
        if not raw.strip():
            raise RuntimeError("local SurrealDB /sql returned empty body")
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise RuntimeError("local SurrealDB /sql returned unexpected payload")
        for item in parsed:
            if isinstance(item, dict) and item.get("status") not in (None, "OK"):
                detail = item.get("detail") or item.get("result") or item
                raise RuntimeError(f"local SurrealDB /sql error: {detail!s}"[:400])
        return [item for item in parsed if isinstance(item, dict)]

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


def assert_memory_proof_records_absent(
    client: MemoryDbProofSqlClient, plan: MemoryDbProofRecordPlan
) -> None:
    id_fields = {"evidence_ref": "evidence_id", "agent_memory": "memory_id"}
    present = [
        f"{table}:{raw_id}"
        for table, raw_id in plan.records_by_table
        if client.record_exists(table, raw_id, id_field=id_fields[table])
    ]
    if present:
        raise AssertionError(
            "run-scoped memory db proof records already exist before import: "
            + ", ".join(present)
        )


def cleanup_memory_proof_records(
    client: MemoryDbProofSqlClient, plan: MemoryDbProofRecordPlan
) -> None:
    delete_order = (
        ("agent_memory", plan.memory_ids, "memory_id"),
        ("evidence_ref", plan.evidence_ids, "evidence_id"),
    )
    for table, ids, id_field in delete_order:
        for raw_id in ids:
            if client.record_exists(table, raw_id, id_field=id_field):
                client.delete_record(table, raw_id, id_field=id_field)
    assert_memory_proof_records_absent(client, plan)
