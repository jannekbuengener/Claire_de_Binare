"""SurrealDB ledger importer (strict append-only).

Reads decision-event YAML files and maps them into SurrealDB records.
Uses CREATE (not UPSERT/MERGE) so re-importing the same event_id fails
deterministically — the first write is immutable.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import re
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
import yaml

from core.replay.canonical_json import canonical_hash, canonical_json_dumps

logger = logging.getLogger(__name__)


SUPPORTED_ACTIONS = {
    "work.start": "work_start",
    "branch.create": "branch_create",
    "pr.create": "pr_create",
    "pr.merge": "pr_merge",
    "issue.close": "issue_close",
}

REDACT_PATTERNS = [
    re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*[:=]\s*[^\s]+"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
]

LEDGER_IMPORT_DUPLICATE_EVENT_ID = "LEDGER_IMPORT_DUPLICATE_EVENT_ID"
LEDGER_IMPORT_HASH_MISMATCH = "LEDGER_IMPORT_HASH_MISMATCH"
LEDGER_IMPORT_SIGNATURE_INVALID = "LEDGER_IMPORT_SIGNATURE_INVALID"
LEDGER_IMPORT_SIGNATURE_UNSUPPORTED = "LEDGER_IMPORT_SIGNATURE_UNSUPPORTED"

_HASH_FIELD_CANDIDATES = (
    ("event_hash",),
    ("hash",),
    ("sha256",),
    ("integrity", "event_hash"),
    ("integrity", "hash"),
    ("integrity", "sha256"),
)
_SIGNATURE_FIELD_CANDIDATES = (
    ("signature",),
    ("event_signature",),
    ("integrity", "signature"),
)


@dataclass(frozen=True)
class ImportConfig:
    namespace: str
    database: str
    url: str
    auth_user: str | None = None
    auth_pass: str | None = None
    auth_header: str | None = None


def _parse_timestamp(value: str) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


class ImportIntegrityError(Exception):
    """Raised when importer preflight rejects the batch before any writes."""

    def __init__(
        self,
        code: str,
        reason: str,
        event_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.reason = reason
        self.event_ids = event_ids or []
        self.metadata = metadata or {}
        super().__init__(f"{code}: {reason}")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _deterministic_id(event: dict[str, Any]) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
    return _hash_text(payload)


def _redact_text(value: str) -> str:
    redacted = value
    for pattern in REDACT_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def _redact_evidence(evidence: Iterable[str]) -> list[str]:
    return [_redact_text(item) for item in evidence]


def _json_safe_for_hash(value: Any) -> Any:
    """Normalize values into canonical JSON primitives for hash computation."""
    if isinstance(value, dict):
        return {str(key): _json_safe_for_hash(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_for_hash(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_for_hash(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _event_payload_for_hash(event: dict[str, Any]) -> dict[str, Any]:
    """Strip self-referential integrity fields before canonical hashing."""
    payload = deepcopy(event)
    for key in ("event_hash", "hash", "sha256", "signature", "event_signature"):
        payload.pop(key, None)

    integrity = payload.get("integrity")
    if isinstance(integrity, dict):
        trimmed_integrity = dict(integrity)
        for key in ("event_hash", "hash", "sha256", "signature", "event_signature"):
            trimmed_integrity.pop(key, None)
        if trimmed_integrity:
            payload["integrity"] = trimmed_integrity
        else:
            payload.pop("integrity", None)

    return _json_safe_for_hash(payload)


def _extract_field(
    event: dict[str, Any], candidates: tuple[tuple[str, ...], ...]
) -> tuple[bool, Any, str | None]:
    for path in candidates:
        current: Any = event
        found = True
        for segment in path[:-1]:
            if not isinstance(current, dict) or segment not in current:
                found = False
                break
            current = current[segment]
        if not found or not isinstance(current, dict) or path[-1] not in current:
            continue
        return True, current[path[-1]], ".".join(path)
    return False, None, None


def _normalize_declared_hash(value: Any) -> str:
    normalized = str(value).strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized.split(":", 1)[1]
    return normalized


def _compute_event_integrity_hash(event: dict[str, Any]) -> str:
    return canonical_hash(_event_payload_for_hash(event))


def _validate_event_integrity(event: dict[str, Any], event_id: str) -> tuple[str, bool]:
    payload_hash = _compute_event_integrity_hash(event)
    hash_present, declared_hash, hash_field = _extract_field(
        event, _HASH_FIELD_CANDIDATES
    )
    if hash_present and _normalize_declared_hash(declared_hash) != payload_hash:
        raise ImportIntegrityError(
            LEDGER_IMPORT_HASH_MISMATCH,
            f"declared hash at {hash_field} does not match canonical payload hash",
            event_ids=[event_id],
        )

    signature_present, signature_value, signature_field = _extract_field(
        event, _SIGNATURE_FIELD_CANDIDATES
    )
    if signature_present:
        if not isinstance(signature_value, str) or not signature_value.strip():
            raise ImportIntegrityError(
                LEDGER_IMPORT_SIGNATURE_INVALID,
                f"signature at {signature_field} is empty or malformed",
                event_ids=[event_id],
            )
        raise ImportIntegrityError(
            LEDGER_IMPORT_SIGNATURE_UNSUPPORTED,
            f"signature at {signature_field} is present but no verifier is configured",
            event_ids=[event_id],
        )

    return payload_hash, hash_present


def _build_import_correlation_id(source_descriptors: list[dict[str, str]]) -> str:
    if not source_descriptors:
        return "imp-empty"
    ordered_sources = sorted(
        (
            {
                "path": descriptor["path"],
                "sha256": descriptor["sha256"],
            }
            for descriptor in source_descriptors
        ),
        key=lambda item: item["path"],
    )
    return f"imp-{canonical_hash(ordered_sources)[:16]}"


def _short_event_id(event_id: str) -> str:
    if len(event_id) <= 20:
        return event_id
    return f"{event_id[:12]}...{event_id[-4:]}"


def _log_import_rejection(
    code: str,
    import_correlation_id: str,
    reason: str,
    event_ids: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    normalized_ids = sorted(
        {_strip_record_prefix(str(event_id)) for event_id in (event_ids or [])}
    )
    payload: dict[str, Any] = {
        "event": "ledger_import_rejected",
        "code": code,
        "import_correlation_id": import_correlation_id,
        "reason": reason,
        "event_ids_count": len(normalized_ids),
        "event_ids_sample": [
            _short_event_id(event_id) for event_id in normalized_ids[:10]
        ],
    }
    if metadata:
        payload["metadata"] = metadata
    logger.error("%s", canonical_json_dumps(payload))


def load_ledger_events(path: Path) -> list[dict[str, Any]]:
    return load_ledger_events_from_text(path.read_text(encoding="utf-8"))


def load_ledger_events_from_text(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for doc in yaml.safe_load_all(text):
        if doc is None:
            continue
        if isinstance(doc, list):
            events.extend([entry for entry in doc if isinstance(entry, dict)])
        elif isinstance(doc, dict):
            events.append(doc)
    return events


def normalize_events(
    events: list[dict[str, Any]],
    source_path: str,
    source_hash: str,
) -> list[dict[str, Any]]:
    agent_latest: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []

    sorted_events = sorted(
        events,
        key=lambda e: (
            _parse_timestamp(str(e.get("timestamp", ""))),
            str(e.get("event_id", "")),
        ),
    )

    for event in sorted_events:
        event_id = str(event.get("event_id") or _deterministic_id(event))
        integrity_hash, hash_verified = _validate_event_integrity(event, event_id)
        agent = event.get("agent") or {}
        agent_id = str(agent.get("id", "unknown"))
        action = event.get("action") or {}
        action_type = str(action.get("type", "unknown"))
        event_kind = SUPPORTED_ACTIONS.get(action_type, "other")

        prev_event_id = agent_latest.get(agent_id)
        agent_latest[agent_id] = event_id

        evidence = event.get("evidence") or []
        evidence_list = (
            [str(item) for item in evidence]
            if isinstance(evidence, list)
            else [str(evidence)]
        )

        normalized.append(
            {
                "record_id": event_id,
                "surreal_id": f"ledger_event:{event_id}",
                "event_id": event_id,
                "event_kind": event_kind,
                "timestamp": event.get("timestamp"),
                "agent": {
                    "id": agent_id,
                    "vendor": agent.get("vendor"),
                    "role": agent.get("role"),
                },
                "action": {
                    "type": action_type,
                    "summary": action.get("summary"),
                    "reversible": action.get("reversible"),
                },
                "scope": event.get("scope") or {},
                "uncertainty": event.get("uncertainty") or {},
                "policy_refs": event.get("policy_refs") or [],
                "evidence": _redact_evidence(evidence_list),
                "prev_event_id": prev_event_id,
                "integrity": {
                    "sha256": integrity_hash,
                    "hash_verified": hash_verified,
                },
                "source": {
                    "path": source_path,
                    "sha256": source_hash,
                },
            }
        )

    return normalized


class DuplicateEventError(Exception):
    """Raised when a CREATE fails because the record already exists."""

    def __init__(self, event_ids: list[str]) -> None:
        self.event_ids = event_ids
        super().__init__(
            f"append-only violation: {len(event_ids)} duplicate event(s): "
            + ", ".join(event_ids[:10])
        )


def build_surrealql(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""

    statements: list[str] = []
    statements.append("BEGIN TRANSACTION")
    for record in records:
        payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        statements.append(f"CREATE {record['surreal_id']} CONTENT {payload}")
    statements.append("COMMIT TRANSACTION")
    return ";\n".join(statements) + ";"


_DUPLICATE_NEEDLE = "already exists"


def _parse_duplicate_ids(results: list[dict[str, Any]]) -> list[str]:
    """Extract record ids from SurrealDB statement results that failed with duplicate errors."""
    ids: list[str] = []
    for entry in results:
        status = entry.get("status", "")
        detail = str(entry.get("result", "") or entry.get("detail", ""))
        if status == "ERR" and _DUPLICATE_NEEDLE in detail:
            # SurrealDB error: "Database record `<table>:<id>` already exists"
            # Match any table name, not just ledger_event.
            match = re.search(r"`(\w+:\S+?)`", detail)
            if match:
                ids.append(_strip_record_prefix(match.group(1)))
            else:
                ids.append("<unknown>")
    return ids


def _strip_record_prefix(value: str) -> str:
    if value.startswith("ledger_event:"):
        return value.split(":", 1)[1]
    return value


def _build_headers(config: ImportConfig) -> dict[str, str]:
    headers = {
        "NS": config.namespace,
        "DB": config.database,
        "Accept": "application/json",
    }
    if config.auth_header:
        headers["Authorization"] = config.auth_header
    elif config.auth_user and config.auth_pass:
        token = f"{config.auth_user}:{config.auth_pass}".encode("utf-8")
        b64 = base64.b64encode(token).decode("utf-8")
        headers["Authorization"] = f"Basic {b64}"
    return headers


def _execute_surrealql(
    config: ImportConfig, query: str, *, require_json: bool = False
) -> list[dict[str, Any]] | None:
    response = requests.post(
        config.url, headers=_build_headers(config), data=query, timeout=10
    )
    response.raise_for_status()
    try:
        return response.json()
    except (ValueError, TypeError) as exc:
        if require_json:
            raise RuntimeError(
                "SurrealDB returned non-JSON response for preflight query"
            ) from exc
        return None


def lookup_existing_event_ids(config: ImportConfig, event_ids: list[str]) -> list[str]:
    unique_event_ids = sorted(
        {str(event_id) for event_id in event_ids if str(event_id).strip()}
    )
    if not unique_event_ids:
        return []

    quoted_event_ids = json.dumps(
        unique_event_ids, ensure_ascii=False, separators=(",", ":")
    )
    query = (
        f"SELECT VALUE event_id FROM ledger_event WHERE event_id IN {quoted_event_ids};"
    )
    results = _execute_surrealql(config, query, require_json=True)
    if not isinstance(results, list) or not results:
        raise RuntimeError("Unexpected response for ledger import preflight lookup")

    result = results[0].get("result")
    if not isinstance(result, list):
        raise RuntimeError("Preflight lookup result was not a list")

    existing_ids: list[str] = []
    for item in result:
        if isinstance(item, str):
            existing_ids.append(_strip_record_prefix(item))
        elif isinstance(item, dict):
            value = item.get("event_id") or item.get("id")
            if value is not None:
                existing_ids.append(_strip_record_prefix(str(value)))

    return sorted(set(existing_ids))


def preflight_records(
    records: list[dict[str, Any]], config: ImportConfig | None = None
) -> None:
    event_ids = [str(record["event_id"]) for record in records]
    duplicate_ids = sorted(
        event_id for event_id, count in Counter(event_ids).items() if count > 1
    )
    if duplicate_ids:
        raise ImportIntegrityError(
            LEDGER_IMPORT_DUPLICATE_EVENT_ID,
            "duplicate event_id detected in import batch",
            event_ids=duplicate_ids,
            metadata={"scope": "batch"},
        )

    if config is None:
        return

    existing_ids = lookup_existing_event_ids(config, event_ids)
    if existing_ids:
        raise ImportIntegrityError(
            LEDGER_IMPORT_DUPLICATE_EVENT_ID,
            "event_id already exists in ledger_event",
            event_ids=existing_ids,
            metadata={"scope": "database"},
        )


def post_surrealql(config: ImportConfig, query: str) -> None:
    results = _execute_surrealql(config, query)
    if results is None:
        return  # non-JSON response (e.g. older SurrealDB) — HTTP 200 is success enough

    if not isinstance(results, list):
        return

    dup_ids = _parse_duplicate_ids(results)
    if dup_ids:
        raise DuplicateEventError(dup_ids)


def _iter_yaml_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted([p for p in path.rglob("*.yml")] + [p for p in path.rglob("*.yaml")])


def main() -> int:
    logging.basicConfig(format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Import ledger YAML into SurrealDB.")
    parser.add_argument("path", type=Path, help="Ledger file or directory")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print SQL instead of executing"
    )
    parser.add_argument("--namespace", default="cdb", help="SurrealDB namespace")
    parser.add_argument("--database", default="cdb", help="SurrealDB database")
    parser.add_argument(
        "--url", default="http://localhost:8000/sql", help="SurrealDB SQL endpoint"
    )
    parser.add_argument("--auth-user", default=None, help="SurrealDB auth user")
    parser.add_argument("--auth-pass", default=None, help="SurrealDB auth pass")
    parser.add_argument(
        "--auth-header", default=None, help="Authorization header value"
    )
    args = parser.parse_args()

    yaml_files = _iter_yaml_files(args.path)
    all_records: list[dict[str, Any]] = []
    source_descriptors: list[dict[str, str]] = []

    try:
        for file_path in yaml_files:
            file_text = file_path.read_text(encoding="utf-8")
            source_hash = _hash_text(file_text)
            source_descriptors.append({"path": str(file_path), "sha256": source_hash})
            events = load_ledger_events_from_text(file_text)
            all_records.extend(normalize_events(events, str(file_path), source_hash))

        preflight_records(all_records)
        sql = build_surrealql(all_records)
        if args.dry_run or not sql.strip():
            print(sql)
            return 0

        config = ImportConfig(
            namespace=args.namespace,
            database=args.database,
            url=args.url,
            auth_user=args.auth_user,
            auth_pass=args.auth_pass,
            auth_header=args.auth_header,
        )
        preflight_records(all_records, config=config)
        try:
            post_surrealql(config, sql)
        except DuplicateEventError as exc:
            _log_import_rejection(
                LEDGER_IMPORT_DUPLICATE_EVENT_ID,
                _build_import_correlation_id(source_descriptors),
                "surrealdb_create_conflict_after_preflight",
                exc.event_ids,
                {"scope": "database"},
            )
            return 1
    except ImportIntegrityError as exc:
        _log_import_rejection(
            exc.code,
            _build_import_correlation_id(source_descriptors),
            exc.reason,
            exc.event_ids,
            exc.metadata,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
