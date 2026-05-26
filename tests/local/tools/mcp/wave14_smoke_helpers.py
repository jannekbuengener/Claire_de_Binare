"""Helpers for Wave-14 local real-SurrealDB smoke (#2644).

Test-local only. Provides run-scoped record materialization, pre/post DB
assertions, and targeted cleanup via the local SurrealDB /sql endpoint.
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

from tools.surrealdb.context_importer import TABLE_BY_ARTIFACT
from tools.surrealdb.gen_run_id import _timestamp_run_id

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "surrealdb" / "wave14_real_smoke"

LOCAL_SURR_URL = "http://127.0.0.1:8010"
LOCAL_NS = "cdb_context_local"
LOCAL_DB = "cdb_context_intel"
LOCAL_ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

WAVE14_SMOKE_TABLES: tuple[str, ...] = tuple(
    TABLE_BY_ARTIFACT[artifact]
    for artifact in (
        "evidence_refs",
        "claims",
        "decision_events",
        "agent_memories",
    )
)

_BASE_EVIDENCE_ID = "ev-wave14-real-001"
_BASE_CLAIM_ID = "claim-wave14-real-001"
_BASE_MEMORY_ID = "mem-wave14-real-001"
_BASE_DECISION_IDS = ("dec-wave14-real-001", "dec-wave14-real-002")

_ID_REFERENCE_FIELDS = frozenset(
    {
        "evidence_id",
        "claim_id",
        "memory_id",
        "decision_id",
        "validates",
        "invalidates",
        "evidence_refs",
        "claim_refs",
        "related_artifacts",
        "related_decisions",
        "superseded_by",
        "invalidated_by",
        "source_refs",
    }
)


@dataclass(frozen=True)
class Wave14SmokeRecordPlan:
    run_id: str
    run_tag: str
    evidence_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    memory_ids: tuple[str, ...]
    decision_ids: tuple[str, ...]

    @property
    def records_by_table(self) -> tuple[tuple[str, str], ...]:
        rows: list[tuple[str, str]] = []
        rows.extend(("evidence_ref", item) for item in self.evidence_ids)
        rows.extend(("claim", item) for item in self.claim_ids)
        rows.extend(("agent_memory", item) for item in self.memory_ids)
        rows.extend(("decision_event", item) for item in self.decision_ids)
        return tuple(rows)


def resolve_smoke_run_id() -> str:
    override = os.environ.get("CDB_WAVE14_SMOKE_RUN_ID", "").strip()
    if override:
        return override
    return f"{_timestamp_run_id()}-{os.getpid()}"


def smoke_run_tag(run_id: str) -> str:
    tag = re.sub(r"[^a-zA-Z0-9]", "", run_id)
    if not tag:
        raise ValueError("run_id must contain at least one alphanumeric character")
    return tag[:24]


def build_record_plan(run_id: str) -> Wave14SmokeRecordPlan:
    tag = smoke_run_tag(run_id)

    def _scoped(base: str) -> str:
        stem, suffix = base.rsplit("-", 1)
        return f"{stem}-{tag}-{suffix}"

    return Wave14SmokeRecordPlan(
        run_id=run_id,
        run_tag=tag,
        evidence_ids=(_scoped(_BASE_EVIDENCE_ID),),
        claim_ids=(_scoped(_BASE_CLAIM_ID),),
        memory_ids=(_scoped(_BASE_MEMORY_ID),),
        decision_ids=tuple(_scoped(item) for item in _BASE_DECISION_IDS),
    )


def _id_remap(plan: Wave14SmokeRecordPlan) -> dict[str, str]:
    return {
        _BASE_EVIDENCE_ID: plan.evidence_ids[0],
        _BASE_CLAIM_ID: plan.claim_ids[0],
        _BASE_MEMORY_ID: plan.memory_ids[0],
        _BASE_DECISION_IDS[0]: plan.decision_ids[0],
        _BASE_DECISION_IDS[1]: plan.decision_ids[1],
    }


def _replace_value(value: Any, id_map: dict[str, str]) -> Any:
    if isinstance(value, str):
        return id_map.get(value, value)
    if isinstance(value, list):
        return [_replace_value(item, id_map) for item in value]
    return value


def _replace_record_fields(
    record: dict[str, Any], id_map: dict[str, str]
) -> dict[str, Any]:
    updated: dict[str, Any] = {}
    for key, value in record.items():
        if key in _ID_REFERENCE_FIELDS or key.endswith("_refs") or key.endswith("_by"):
            updated[key] = _replace_value(value, id_map)
        else:
            updated[key] = value
    return updated


def materialize_fixture_records(
    filename: str,
    *,
    run_id: str,
    plan: Wave14SmokeRecordPlan,
) -> str:
    path = _FIXTURE_DIR / filename
    id_map = _id_remap(plan)
    records: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        record = json.loads(raw_line)
        record["run_id"] = run_id
        record = _replace_record_fields(record, id_map)
        records.append(json.dumps(record, ensure_ascii=True, sort_keys=True))
    return "\n".join(records) + ("\n" if records else "")


def smoke_tmp_root(run_id: str) -> Path:
    return _REPO_ROOT / ".tmp" / "wave14-real-smoke" / run_id


def assert_tmp_root_absent(tmp_root: Path) -> None:
    if tmp_root.exists():
        raise AssertionError(
            "wave14 real-smoke tmp dir already exists; "
            "previous cleanup likely failed"
        )


def cleanup_tmp_root(tmp_root: Path) -> None:
    if tmp_root.exists():
        shutil.rmtree(tmp_root, ignore_errors=False)
    if tmp_root.exists():
        raise AssertionError("wave14 real-smoke tmp dir still present after cleanup")


_TABLE_ID_FIELD = {
    "evidence_ref": "evidence_id",
    "claim": "claim_id",
    "agent_memory": "memory_id",
    "decision_event": "decision_id",
}


def _table_id_field(table: str) -> str:
    try:
        return _TABLE_ID_FIELD[table]
    except KeyError as exc:
        raise ValueError("unsupported Wave-14 smoke table") from exc


def _surql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


class Wave14SmokeSqlClient:
    """Minimal local-only /sql client for smoke pre/post checks."""

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
            raise ValueError("wave14 smoke SQL client is local-dev only")
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
    ) -> Wave14SmokeSqlClient:
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

    def record_exists(self, table: str, raw_id: str) -> bool:
        id_field = _table_id_field(table)
        literal = _surql_string(raw_id)
        results = self.execute(f"SELECT * FROM {table} WHERE {id_field} = {literal};")
        for item in results:
            result = item.get("result")
            if isinstance(result, list) and result:
                return True
        return False

    def delete_record(self, table: str, raw_id: str) -> None:
        id_field = _table_id_field(table)
        literal = _surql_string(raw_id)
        self.execute(f"DELETE {table} WHERE {id_field} = {literal};")


def assert_run_records_absent(
    client: Wave14SmokeSqlClient, plan: Wave14SmokeRecordPlan
) -> None:
    present = [
        f"{table}:{raw_id}"
        for table, raw_id in plan.records_by_table
        if client.record_exists(table, raw_id)
    ]
    if present:
        raise AssertionError(
            "run-scoped Wave-14 smoke records already exist before import: "
            + ", ".join(present)
        )


def cleanup_run_records(
    client: Wave14SmokeSqlClient, plan: Wave14SmokeRecordPlan
) -> None:
    # Delete decisions first, then dependent rows.
    delete_order = (
        ("decision_event", plan.decision_ids),
        ("claim", plan.claim_ids),
        ("agent_memory", plan.memory_ids),
        ("evidence_ref", plan.evidence_ids),
    )
    for table, ids in delete_order:
        for raw_id in ids:
            if client.record_exists(table, raw_id):
                client.delete_record(table, raw_id)
    assert_run_records_absent(client, plan)
