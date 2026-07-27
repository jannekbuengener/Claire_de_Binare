"""Append-only published-run ledger for anti-replay."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ci.lib.evidence import utc_now
from ci.publisher.exceptions import LedgerError

LEDGER_SCHEMA_VERSION = "cdb-local-ci-published-runs/v1"
REQUIRED_ENTRY_FIELDS = (
    "run_id",
    "commit_sha",
    "repository",
    "status_context",
    "manifest_sha256",
    "published_at_utc",
)


@dataclass(frozen=True)
class LedgerEntry:
    run_id: str
    commit_sha: str
    repository: str
    status_context: str
    manifest_sha256: str
    published_at_utc: str
    github_status_id: int | None = None
    state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_ledger_path(artifacts_root: Path) -> Path:
    return artifacts_root / "published-runs.json"


def _empty_ledger() -> dict[str, Any]:
    return {"schema_version": LEDGER_SCHEMA_VERSION, "entries": []}


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_ledger()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerError(
            f"Published-run ledger corrupted or unreadable: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise LedgerError("Published-run ledger root must be an object")
    if data.get("schema_version") != LEDGER_SCHEMA_VERSION:
        raise LedgerError(
            f"Unsupported ledger schema_version: {data.get('schema_version')!r}"
        )
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise LedgerError("Published-run ledger entries must be a list")
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise LedgerError(f"Ledger entry {idx} is not an object")
        for field in REQUIRED_ENTRY_FIELDS:
            if field not in entry or entry[field] in (None, ""):
                raise LedgerError(f"Ledger entry {idx} missing field {field!r}")
        # Hard rule: never persist tokens.
        blob = json.dumps(entry)
        if "ghp_" in blob or "github_pat_" in blob or "Bearer " in blob:
            raise LedgerError(
                "Ledger contains token-like material; publication blocked"
            )
    return data


def assert_run_id_not_reused(
    ledger: dict[str, Any],
    *,
    run_id: str,
    commit_sha: str,
) -> None:
    for entry in ledger.get("entries") or []:
        if entry.get("run_id") != run_id:
            continue
        prior_sha = str(entry.get("commit_sha"))
        if prior_sha != commit_sha:
            raise LedgerError(
                f"run_id {run_id!r} already published for SHA {prior_sha}, "
                f"refusing reuse for {commit_sha}"
            )


def append_entry(path: Path, entry: LedgerEntry) -> None:
    ledger = load_ledger(path)
    assert_run_id_not_reused(ledger, run_id=entry.run_id, commit_sha=entry.commit_sha)
    entries: list[dict[str, Any]] = list(ledger.get("entries") or [])
    entries.append(entry.to_dict())
    payload = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "entries": entries,
        "updated_at_utc": utc_now(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic-ish write: write temp then replace.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
