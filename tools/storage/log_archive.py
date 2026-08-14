"""Deterministic, plan-only archive contract for #4422 event logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from re import fullmatch
from typing import Any, Mapping, Sequence

from tools.storage.bulk_storage_contract import (
    BulkStorageContractError,
    resolve_bulk_storage_path,
)

SCHEMA_VERSION = "cdb.log-archive-plan/v1"
ISSUE_REF = "#4422"
DEFAULT_HOT_DAYS = 30
EVENT_FILE_PATTERN = r"events_(\d{8})\.jsonl"


class LogArchiveError(ValueError):
    """Raised when a log archive plan cannot be safely constructed or verified."""


def _is_reparse_point(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except AttributeError:
        return path.is_symlink()


def _reject_reparse_components(path: Path) -> None:
    current = path
    while True:
        if _is_reparse_point(current):
            raise LogArchiveError("LOG_ARCHIVE_REPARSE_POINT")
        parent = current.parent
        if parent == current:
            return
        current = parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise LogArchiveError("AS_OF_UTC_REQUIRED")
    return value.astimezone(timezone.utc)


def _entry_for(source_root: Path, destination_root: Path, path: Path, cutoff: datetime) -> dict[str, Any]:
    relative_path = path.relative_to(source_root).as_posix()
    stat_result = path.stat()
    last_write = datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc)
    entry: dict[str, Any] = {
        "relative_path": relative_path,
        "size_bytes": stat_result.st_size,
        "sha256": _sha256(path),
        "last_write_utc": last_write.isoformat().replace("+00:00", "Z"),
    }
    match = fullmatch(EVENT_FILE_PATTERN, path.name)
    if not match:
        entry.update(classification="EXCLUDE_UNKNOWN", reason_code="NAME_EXCLUDED")
        return entry
    try:
        event_date = datetime.strptime(match.group(1), "%Y%m%d").date()
    except ValueError:
        entry.update(classification="EXCLUDE_UNKNOWN", reason_code="EVENT_DATE_INVALID")
        return entry
    if event_date >= cutoff.date():
        entry.update(classification="KEEP_HOT", reason_code="WITHIN_HOT_WINDOW")
        return entry

    destination = destination_root / relative_path
    _reject_reparse_components(destination.parent)
    entry.update(classification="ARCHIVE_CANDIDATE", destination_state="ABSENT")
    if destination.exists():
        if not destination.is_file():
            entry.update(classification="HOLD", reason_code="DESTINATION_COLLISION_NON_FILE")
        elif destination.stat().st_size != stat_result.st_size or _sha256(destination) != entry["sha256"]:
            entry.update(classification="HOLD", reason_code="DESTINATION_COLLISION_HASH_MISMATCH")
        else:
            entry["destination_state"] = "RESUMABLE_IDENTICAL"
    return entry


def _fingerprint(plan: Mapping[str, Any]) -> str:
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_log_archive_plan(
    source_root: Path,
    *,
    environ: Mapping[str, str] | None = None,
    as_of_utc: datetime,
    hot_days: int = DEFAULT_HOT_DAYS,
) -> dict[str, Any]:
    """Return a deterministic read-only archive plan; never copy or delete."""
    if hot_days < 1:
        raise LogArchiveError("HOT_DAYS_INVALID")
    as_of = _utc(as_of_utc)
    if not source_root.is_dir():
        raise LogArchiveError("SOURCE_ROOT_REQUIRED")
    _reject_reparse_components(source_root)
    try:
        logs_root = resolve_bulk_storage_path("logs", environ=environ)
    except BulkStorageContractError as exc:
        raise LogArchiveError(str(exc)) from exc
    destination_root = logs_root / "events"
    _reject_reparse_components(destination_root)
    cutoff = as_of - timedelta(days=hot_days)
    files = sorted((path for path in source_root.rglob("*") if path.is_file()), key=lambda path: path.as_posix())
    entries = [_entry_for(source_root, destination_root, path, cutoff) for path in files]
    plan: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "issue_ref": ISSUE_REF,
        "source_root": str(source_root),
        "destination_root": str(destination_root),
        "as_of_utc": as_of.isoformat().replace("+00:00", "Z"),
        "hot_days": hot_days,
        "cutoff_date": cutoff.date().isoformat(),
        "destination_root_exists": destination_root.is_dir(),
        "entries": entries,
    }
    if not plan["destination_root_exists"]:
        plan["hold_reasons"] = ["DESTINATION_ROOT_REQUIRED"]
    plan["plan_fingerprint"] = _fingerprint(plan)
    return plan


def verify_planned_source(source: Path, entry: Mapping[str, Any]) -> None:
    """Reject a source whose planned size or hash has changed before an apply."""
    if not source.is_file() or source.stat().st_size != entry["size_bytes"] or _sha256(source) != entry["sha256"]:
        raise LogArchiveError("SOURCE_CHANGED_AFTER_PLANNING")


def verify_copied_file(source: Path, destination: Path) -> None:
    """Require byte and hash equality; callers must not unlink on failure."""
    if not destination.is_file() or _sha256(source) != _sha256(destination):
        raise LogArchiveError("COPY_HASH_MISMATCH")
    if source.stat().st_size != destination.stat().st_size:
        raise LogArchiveError("COPY_SIZE_MISMATCH")


def _parse_as_of(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("as_of_utc must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("as_of_utc must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan-only CDB event-log archival")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="create a read-only archive plan")
    plan_parser.add_argument("--source-root", type=Path, required=True)
    plan_parser.add_argument("--as-of-utc", type=_parse_as_of, required=True)
    plan_parser.add_argument("--hot-days", type=int, default=DEFAULT_HOT_DAYS)
    args = parser.parse_args(argv)
    try:
        plan = build_log_archive_plan(
            args.source_root, as_of_utc=args.as_of_utc, hot_days=args.hot_days
        )
    except LogArchiveError as exc:
        print(json.dumps({"status": "BLOCKED", "reason_code": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(plan, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
