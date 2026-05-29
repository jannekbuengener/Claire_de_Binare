"""Cross-session memory rediscovery proof — #2720.

Proves that run-scoped ``agent_memory`` rows remain discoverable by
``memory_id`` + ``scope`` across process boundaries using a manifest handoff.

No productive writes. No MCP mutation. LR: NO-GO.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from core.utils.clock import utcnow as cdb_utcnow
from tools.mcp.surrealdb_adapter_factory import adapter_source
from tools.surrealdb.claim_evidence_at_rest import prove_claim_evidence_at_rest_db_v1
from tools.surrealdb.memory_contract import (
    MemoryContractError,
    validate_memory_id_matches_record,
    validate_memory_record,
)
from tools.surrealdb.memory_db_stale_scan import scan_agent_memory_stale_v1

SCHEMA_VERSION = "memory-cross-session-rediscovery/v1"
MANIFEST_SCHEMA_VERSION = "memory-cross-session-rediscovery-manifest/v1"

_SURQL_SAFE_RE = re.compile(r"^[a-zA-Z0-9/_.@:#+ \-]+$")

_DB_STRIP_FIELDS = frozenset(
    {
        "run_id",
        "schema_version",
        "id",
        "sensitivity",
    }
)

_SECRET_SUBSTRINGS = frozenset(
    {
        "SURREAL_PASS",
        "SURREAL_USER",
        "Authorization",
        "Basic ",
    }
)


class MemoryRediscoveryError(ValueError):
    """Raised when cross-session rediscovery proof fails."""


class MemoryRediscoveryAdapter(Protocol):
    status: str

    def execute(self, query: str) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class RediscoveryManifestEntry:
    memory_id: str
    scope: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class RediscoveryManifest:
    schema_version: str
    run_id: str
    seed_process_id: int
    entries: tuple[RediscoveryManifestEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "seed_process_id": self.seed_process_id,
            "entries": [
                {
                    "memory_id": entry.memory_id,
                    "scope": entry.scope,
                    "evidence_ids": list(entry.evidence_ids),
                }
                for entry in self.entries
            ],
        }


def rediscovery_manifest_dir(repo_root: Path, run_id: str) -> Path:
    return repo_root / ".cdb_memory_rediscovery" / run_id


def manifest_path_for_run(repo_root: Path, run_id: str) -> Path:
    return rediscovery_manifest_dir(repo_root, run_id) / "manifest.json"


def build_manifest_from_plan(
    *,
    run_id: str,
    scope: str,
    memory_ids: tuple[str, ...],
    evidence_ids: tuple[str, ...],
    seed_process_id: int,
) -> RediscoveryManifest:
    if not memory_ids:
        raise MemoryRediscoveryError("manifest requires at least one memory_id")
    entries = tuple(
        RediscoveryManifestEntry(
            memory_id=mid,
            scope=scope,
            evidence_ids=evidence_ids,
        )
        for mid in memory_ids
    )
    return RediscoveryManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id=run_id,
        seed_process_id=seed_process_id,
        entries=entries,
    )


def write_rediscovery_manifest(manifest: RediscoveryManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )


def load_rediscovery_manifest(path: Path) -> RediscoveryManifest:
    if not path.is_file():
        raise MemoryRediscoveryError(f"manifest missing: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise MemoryRediscoveryError("manifest schema_version mismatch")
    run_id = str(raw.get("run_id") or "").strip()
    if not run_id:
        raise MemoryRediscoveryError("manifest missing run_id")
    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise MemoryRediscoveryError("manifest entries empty")
    entries: list[RediscoveryManifestEntry] = []
    for item in entries_raw:
        if not isinstance(item, Mapping):
            raise MemoryRediscoveryError("manifest entry must be object")
        memory_id = str(item.get("memory_id") or "").strip()
        scope = str(item.get("scope") or "").strip()
        if not memory_id or not scope:
            raise MemoryRediscoveryError("manifest entry missing memory_id or scope")
        evidence_raw = item.get("evidence_ids") or []
        if not isinstance(evidence_raw, list):
            raise MemoryRediscoveryError("manifest evidence_ids must be list")
        evidence_ids = tuple(str(x).strip() for x in evidence_raw if str(x).strip())
        entries.append(
            RediscoveryManifestEntry(
                memory_id=memory_id,
                scope=scope,
                evidence_ids=evidence_ids,
            )
        )
    return RediscoveryManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        run_id=run_id,
        seed_process_id=int(raw.get("seed_process_id") or 0),
        entries=tuple(entries),
    )


def _safe_surql_str(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    return text if (text and _SURQL_SAFE_RE.match(text)) else None


def _strip_db_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in dict(row).items() if key not in _DB_STRIP_FIELDS
    }


def _fetch_memory_by_id_and_scope(
    adapter: MemoryRediscoveryAdapter,
    *,
    memory_id: str,
    scope: str,
) -> dict[str, Any]:
    safe_id = _safe_surql_str(memory_id)
    safe_scope = _safe_surql_str(scope)
    if not safe_id or not safe_scope:
        raise MemoryRediscoveryError("memory_id or scope not safe for SurrealQL")
    query = (
        f"SELECT * FROM agent_memory WHERE memory_id = '{safe_id}' "
        f"AND scope = '{safe_scope}' LIMIT 2"
    )
    rows = adapter.execute(query)
    matches: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, Mapping):
            matches.append(_strip_db_metadata(row))
    if len(matches) != 1:
        raise MemoryRediscoveryError(
            f"expected exactly one memory row for {memory_id!r} + {scope!r}, "
            f"found {len(matches)}"
        )
    record = matches[0]
    validate_memory_record(record)
    validate_memory_id_matches_record(record)
    if str(record.get("scope")) != scope:
        raise MemoryRediscoveryError("loaded row scope mismatch")
    return record


def prove_cross_session_rediscovery_from_manifest(
    adapter: MemoryRediscoveryAdapter,
    manifest: RediscoveryManifest,
    *,
    prove_process_id: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Prove phase: manifest + DB only (intended for a fresh subprocess)."""
    if prove_process_id == manifest.seed_process_id:
        raise MemoryRediscoveryError(
            "prove process must differ from seed process for cross-session proof"
        )

    ref_now = now or cdb_utcnow()
    if ref_now.tzinfo is None:
        ref_now = ref_now.replace(tzinfo=timezone.utc)

    scopes = {entry.scope for entry in manifest.entries}
    if len(scopes) != 1:
        raise MemoryRediscoveryError("manifest must use single scope for proof slice")
    scope = next(iter(scopes))

    memory_ids_found: list[str] = []
    records: list[dict[str, Any]] = []

    for entry in manifest.entries:
        if entry.scope != scope:
            raise MemoryRediscoveryError("manifest scope mismatch across entries")
        record = _fetch_memory_by_id_and_scope(
            adapter,
            memory_id=entry.memory_id,
            scope=entry.scope,
        )
        memory_ids_found.append(entry.memory_id)
        records.append(record)

    stale_scan = scan_agent_memory_stale_v1(
        adapter=adapter,
        scope=scope,
        limit=max(25, len(manifest.entries) * 4),
        now=ref_now,
    )

    claim_proof = prove_claim_evidence_at_rest_db_v1(
        adapter,
        scope=scope,
        limit=50,
    )

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "source": adapter_source(adapter),
        "adapter_status": adapter.status,
        "seed_process": manifest.seed_process_id,
        "prove_process": prove_process_id,
        "run_id": manifest.run_id,
        "scope": scope,
        "memory_ids_found": memory_ids_found,
        "record_count": len(records),
        "stale_preserved": {
            "stale_memory_ids": stale_scan.get("stale_memory_ids", []),
            "expired_memory_ids": stale_scan.get("expired_memory_ids", []),
            "record_count": stale_scan.get("record_count"),
        },
        "claim_evidence_at_rest": {
            "schema_version": claim_proof.get("schema_version"),
            "claim_count": claim_proof.get("claim_count"),
            "known_evidence_ids": claim_proof.get("known_evidence_ids"),
        },
        "trust": {
            "manifest_schema": MANIFEST_SCHEMA_VERSION,
            "lookup_keys": ["memory_id", "scope"],
            "read_only": True,
        },
        "limitations": _limitations(),
        "approval_semantics": _approval_semantics(),
    }
    _assert_no_secrets(envelope)
    return envelope


def cleanup_rediscovery_manifest(path: Path) -> None:
    directory = path.parent
    if path.is_file():
        path.unlink()
    if directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()
    parent = directory.parent
    if parent.is_dir() and parent.name == ".cdb_memory_rediscovery":
        try:
            if not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass


def _limitations() -> list[str]:
    return [
        "read_only_proof_no_writes",
        "cross_session_via_manifest_and_subprocess",
        "no_mcp_by_memory_id_surface",
        "lr_no_go",
    ]


def _approval_semantics() -> dict[str, Any]:
    return {
        "read_only": True,
        "no_write": True,
        "no_approval": True,
        "no_live_go": True,
        "no_echtgeld_go": True,
        "note": (
            "Cross-session rediscovery proof only. Does not authorize productive "
            "memory write or MCP mutation."
        ),
    }


def _assert_no_secrets(payload: Mapping[str, Any]) -> None:
    rendered = str(payload)
    for needle in _SECRET_SUBSTRINGS:
        if needle in rendered:
            raise MemoryRediscoveryError(
                "envelope contains forbidden secret-like substring"
            )
