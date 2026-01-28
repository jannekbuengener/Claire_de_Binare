"""SurrealDB ledger importer (idempotent, append-only mirror).

Reads decision-event YAML files and maps them into SurrealDB records.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
import yaml


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


def load_ledger_events(path: Path) -> list[dict[str, Any]]:
    data = path.read_text(encoding="utf-8")
    events: list[dict[str, Any]] = []
    for doc in yaml.safe_load_all(data):
        if doc is None:
            continue
        if isinstance(doc, list):
            for entry in doc:
                if isinstance(entry, dict):
                    events.append(entry)
        elif isinstance(doc, dict):
            events.append(doc)
    return events


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
        agent = event.get("agent") or {}
        agent_id = str(agent.get("id", "unknown"))
        action = event.get("action") or {}
        action_type = str(action.get("type", "unknown"))
        event_kind = SUPPORTED_ACTIONS.get(action_type, "other")

        prev_event_id = agent_latest.get(agent_id)
        agent_latest[agent_id] = event_id

        evidence = event.get("evidence") or []
        evidence_list = [str(item) for item in evidence] if isinstance(evidence, list) else [str(evidence)]

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
                "source": {
                    "path": source_path,
                    "sha256": source_hash,
                },
            }
        )

    return normalized


def build_surrealql(records: list[dict[str, Any]]) -> str:
    statements: list[str] = []
    for record in records:
        payload = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        statements.append(f"UPSERT {record['surreal_id']} MERGE {payload}")
    return ";\n".join(statements) + ";"


def post_surrealql(config: ImportConfig, query: str) -> None:
    headers = {
        "NS": config.namespace,
        "DB": config.database,
    }
    if config.auth_header:
        headers["Authorization"] = config.auth_header
    elif config.auth_user and config.auth_pass:
        token = f"{config.auth_user}:{config.auth_pass}".encode("utf-8")
        b64 = base64.b64encode(token).decode("utf-8")
        headers["Authorization"] = f"Basic {b64}"

    response = requests.post(config.url, headers=headers, data=query, timeout=10)
    response.raise_for_status()


def _iter_yaml_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted([p for p in path.rglob("*.yml")] + [p for p in path.rglob("*.yaml")])


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ledger YAML into SurrealDB.")
    parser.add_argument("path", type=Path, help="Ledger file or directory")
    parser.add_argument("--dry-run", action="store_true", help="Print SQL instead of executing")
    parser.add_argument("--namespace", default="cdb", help="SurrealDB namespace")
    parser.add_argument("--database", default="cdb", help="SurrealDB database")
    parser.add_argument("--url", default="http://localhost:8000/sql", help="SurrealDB SQL endpoint")
    parser.add_argument("--auth-user", default=None, help="SurrealDB auth user")
    parser.add_argument("--auth-pass", default=None, help="SurrealDB auth pass")
    parser.add_argument("--auth-header", default=None, help="Authorization header value")
    args = parser.parse_args()

    yaml_files = _iter_yaml_files(args.path)
    all_records: list[dict[str, Any]] = []

    for file_path in yaml_files:
        events = load_ledger_events(file_path)
        source_hash = _hash_text(file_path.read_text(encoding="utf-8"))
        all_records.extend(normalize_events(events, str(file_path), source_hash))

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
    post_surrealql(config, sql)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
