"""Deterministic, fail-closed archive contract for #4422 event logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
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
APPLY_SCHEMA_VERSION = "cdb.log-archive-apply-result/v1"
ISSUE_REF = "#4422"
DEFAULT_HOT_DAYS = 30
EVENT_FILE_PATTERN = r"events_(\d{8})\.jsonl"


class LogArchiveError(ValueError):
    """Raised when a log archive plan cannot be safely constructed or verified."""


def _normalised_absolute(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _paths_overlap(first: Path, second: Path) -> bool:
    """Return whether either path contains the other, without resolving links."""
    left = _normalised_absolute(first)
    right = _normalised_absolute(second)
    try:
        common = os.path.commonpath([left, right])
    except ValueError:
        return False
    return common == left or common == right


def _reject_overlap(first: Path, second: Path, reason: str) -> None:
    if _paths_overlap(first, second):
        raise LogArchiveError(reason)


def _is_reparse_point(path: Path) -> bool:
    try:
        stat_result = path.lstat()
    except FileNotFoundError:
        return False
    attributes = getattr(stat_result, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse_flag) or path.is_symlink()


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


def _entry_for(
    source_root: Path, destination_root: Path, path: Path, cutoff: datetime
) -> dict[str, Any]:
    _reject_reparse_components(path)
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
    _reject_reparse_components(destination)
    entry.update(classification="ARCHIVE_CANDIDATE", destination_state="ABSENT")
    if destination.exists():
        if not destination.is_file():
            entry.update(
                classification="HOLD", reason_code="DESTINATION_COLLISION_NON_FILE"
            )
        elif (
            destination.stat().st_size != stat_result.st_size
            or _sha256(destination) != entry["sha256"]
        ):
            entry.update(
                classification="HOLD", reason_code="DESTINATION_COLLISION_HASH_MISMATCH"
            )
        else:
            entry["destination_state"] = "RESUMABLE_IDENTICAL"
    return entry


def _fingerprint(plan: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        plan, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_excluded_subtree(source_root: Path, path: Path) -> bool:
    """Return whether a path resides under an excluded source subtree."""
    return any(
        component.startswith("_archive_") or component == "_quarantine"
        for component in path.relative_to(source_root).parts[:-1]
    )


def _candidate_files(source_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if _is_excluded_subtree(source_root, path):
            continue
        _reject_reparse_components(path)
        if path.is_file():
            files.append(path)
    return sorted(files, key=lambda path: path.as_posix())


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
    _reject_overlap(source_root, destination_root, "SOURCE_DESTINATION_OVERLAP")
    cutoff = as_of - timedelta(days=hot_days)
    entries = [
        _entry_for(source_root, destination_root, path, cutoff)
        for path in _candidate_files(source_root)
    ]
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
    _reject_reparse_components(source)
    if (
        not source.is_file()
        or source.stat().st_size != entry["size_bytes"]
        or _sha256(source) != entry["sha256"]
    ):
        raise LogArchiveError("SOURCE_CHANGED_AFTER_PLANNING")


def verify_copied_file(source: Path, destination: Path) -> None:
    """Require byte and hash equality; callers must not unlink on failure."""
    _reject_reparse_components(source)
    _reject_reparse_components(destination)
    if not destination.is_file() or _sha256(source) != _sha256(destination):
        raise LogArchiveError("COPY_HASH_MISMATCH")
    if source.stat().st_size != destination.stat().st_size:
        raise LogArchiveError("COPY_SIZE_MISMATCH")


def _plan_fingerprint(plan: Mapping[str, Any]) -> str:
    unsigned = dict(plan)
    unsigned.pop("plan_fingerprint", None)
    return _fingerprint(unsigned)


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if (
        path.is_absolute()
        or not value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise LogArchiveError("APPLY_RELATIVE_PATH_INVALID")
    if any(
        part.startswith("_archive_") or part == "_quarantine" for part in path.parts
    ):
        raise LogArchiveError("APPLY_EXCLUDED_SUBTREE")
    if not fullmatch(EVENT_FILE_PATTERN, path.name):
        raise LogArchiveError("APPLY_CANDIDATE_NAME_INVALID")
    return path


def _write_evidence(path: Path, evidence: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _held_evidence_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "relative_path": entry.get("relative_path"),
        "expected_size_bytes": entry.get("size_bytes"),
        "expected_sha256": entry.get("sha256"),
        "destination_path": None,
        "disposition": "HELD_PLAN_ENTRY",
        "source_verified_pre_copy": False,
        "destination_verified": False,
        "source_verified_pre_delete": False,
        "source_deleted": False,
        "failure_reason": entry.get("reason_code", "PLAN_HOLD"),
    }


def _validate_apply_roots(
    plan: Mapping[str, Any], evidence_output_path: Path
) -> tuple[Path, Path]:
    source_root = Path(str(plan["source_root"]))
    destination_root = Path(str(plan["destination_root"]))
    if not source_root.is_dir() or not destination_root.is_dir():
        raise LogArchiveError("APPLY_ROOT_REQUIRED")
    canonical_destination = resolve_bulk_storage_path("logs") / "events"
    if _normalised_absolute(destination_root) != _normalised_absolute(
        canonical_destination
    ):
        raise LogArchiveError("APPLY_DESTINATION_ROOT_INVALID")
    _reject_reparse_components(source_root)
    _reject_reparse_components(destination_root)
    _reject_overlap(source_root, destination_root, "SOURCE_DESTINATION_OVERLAP")
    _reject_overlap(evidence_output_path, source_root, "EVIDENCE_PATH_OVERLAP")
    _reject_overlap(evidence_output_path, destination_root, "EVIDENCE_PATH_OVERLAP")
    return source_root, destination_root


def apply_log_archive_plan(
    plan: Mapping[str, Any], expected_fingerprint: str, evidence_output_path: Path
) -> dict[str, Any]:
    """Apply a previously bound plan; never derive or expand its candidate scope."""
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    planned_entries = list(plan.get("entries", []))
    planned = [
        entry
        for entry in planned_entries
        if entry.get("classification") == "ARCHIVE_CANDIDATE"
    ]
    held = [
        entry for entry in planned_entries if entry.get("classification") == "HOLD"
    ]
    entries: list[dict[str, Any]] = [_held_evidence_entry(entry) for entry in held]
    evidence: dict[str, Any] = {
        "schema_version": APPLY_SCHEMA_VERSION,
        "issue_ref": ISSUE_REF,
        "plan_fingerprint": plan.get("plan_fingerprint"),
        "source_root": plan.get("source_root"),
        "destination_root": plan.get("destination_root"),
        "started_at_utc": started,
        "planned_file_count": len(planned),
        "planned_bytes": sum(int(entry.get("size_bytes", 0)) for entry in planned),
        "copied_file_count": 0,
        "copied_bytes": 0,
        "resumed_file_count": 0,
        "verified_file_count": 0,
        "verified_bytes": 0,
        "deleted_source_count": 0,
        "deleted_source_bytes": 0,
        "held_file_count": len(held),
        "result": "BLOCKED",
        "apply_status": "PRECHECK",
        "entries": entries,
    }
    evidence_path_safe = False
    try:
        if (
            not expected_fingerprint
            or plan.get("schema_version") != SCHEMA_VERSION
            or plan.get("issue_ref") != ISSUE_REF
        ):
            raise LogArchiveError("APPLY_PLAN_INVALID")
        if (
            plan.get("plan_fingerprint") != expected_fingerprint
            or _plan_fingerprint(plan) != expected_fingerprint
        ):
            raise LogArchiveError("APPLY_FINGERPRINT_MISMATCH")
        source_root, destination_root = _validate_apply_roots(
            plan, evidence_output_path
        )
        evidence_path_safe = True
        if (
            plan.get("destination_root_exists") is False
            or plan.get("hold_reasons")
            or held
        ):
            raise LogArchiveError("APPLY_PLAN_HELD")
        evidence["apply_status"] = "APPLY_STARTED"
        try:
            _write_evidence(evidence_output_path, evidence)
        except OSError as exc:
            raise LogArchiveError("EVIDENCE_JOURNAL_INIT_FAILED") from exc
        for planned_entry in planned:
            relative = _safe_relative_path(str(planned_entry.get("relative_path", "")))
            event_date = datetime.strptime(
                relative.stem.removeprefix("events_"), "%Y%m%d"
            ).date()
            if event_date >= datetime.fromisoformat(str(plan["cutoff_date"])).date():
                raise LogArchiveError("APPLY_HOT_ENTRY_FORBIDDEN")
            source, destination = source_root / relative, destination_root / relative
            entry = {
                "relative_path": relative.as_posix(),
                "expected_size_bytes": planned_entry.get("size_bytes"),
                "expected_sha256": planned_entry.get("sha256"),
                "destination_path": str(destination),
                "disposition": None,
                "source_verified_pre_copy": False,
                "destination_verified": False,
                "source_verified_pre_delete": False,
                "source_deleted": False,
                "failure_reason": None,
            }
            entries.append(entry)
            try:
                _reject_reparse_components(source)
                _reject_reparse_components(destination)
                verify_planned_source(source, planned_entry)
                entry["source_verified_pre_copy"] = True
                if destination.exists():
                    if (
                        not destination.is_file()
                        or destination.stat().st_size != source.stat().st_size
                        or _sha256(destination) != planned_entry["sha256"]
                    ):
                        raise LogArchiveError("DESTINATION_COLLISION")
                    entry["disposition"] = "RESUMED_VERIFIED_DELETED"
                    evidence["resumed_file_count"] += 1
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
                    entry["disposition"] = "COPIED_VERIFIED_DELETED"
                    evidence["copied_file_count"] += 1
                    evidence["copied_bytes"] += int(planned_entry["size_bytes"])
                verify_copied_file(source, destination)
                entry["destination_verified"] = True
                evidence["verified_file_count"] += 1
                evidence["verified_bytes"] += int(planned_entry["size_bytes"])
                verify_planned_source(source, planned_entry)
                entry["source_verified_pre_delete"] = True
                evidence["apply_status"] = "DELETE_PENDING"
                _write_evidence(evidence_output_path, evidence)
                source.unlink()
                entry["source_deleted"] = True
                evidence["deleted_source_count"] += 1
                evidence["deleted_source_bytes"] += int(planned_entry["size_bytes"])
                evidence["apply_status"] = "APPLY_IN_PROGRESS"
                _write_evidence(evidence_output_path, evidence)
            except LogArchiveError as exc:
                entry["failure_reason"] = str(exc)
                entry["disposition"] = (
                    "HELD_DESTINATION_COLLISION"
                    if str(exc) == "DESTINATION_COLLISION"
                    else "HELD_SOURCE_DRIFT"
                )
                evidence["held_file_count"] += 1
                evidence["failure_reason"] = str(exc)
                break
        if evidence["held_file_count"] == 0:
            evidence["result"] = "SUCCESS"
    except LogArchiveError as exc:
        evidence["failure_reason"] = str(exc)
    if evidence.get("failure_reason") == "EVIDENCE_JOURNAL_INIT_FAILED":
        raise LogArchiveError("EVIDENCE_JOURNAL_INIT_FAILED")
    evidence["completed_at_utc"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    evidence["apply_status"] = "APPLY_COMPLETED"
    if evidence_path_safe:
        _write_evidence(evidence_output_path, evidence)
    return evidence


def _parse_as_of(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("as_of_utc must be ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("as_of_utc must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _canonical_event_source() -> Path:
    return Path(__file__).resolve().parents[2] / "logs" / "events"


def _require_canonical_cli_source(source_root: Path) -> None:
    if _normalised_absolute(source_root) != _normalised_absolute(
        _canonical_event_source()
    ):
        raise LogArchiveError("SOURCE_ROOT_NON_CANONICAL")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed CDB event-log archival")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="create a read-only archive plan")
    plan_parser.add_argument("--source-root", type=Path, required=True)
    plan_parser.add_argument("--as-of-utc", type=_parse_as_of, required=True)
    plan_parser.add_argument("--hot-days", type=int, default=DEFAULT_HOT_DAYS)
    apply_parser = subparsers.add_parser("apply", help="apply a bound archive plan")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--expected-fingerprint", required=True)
    apply_parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "apply":
            plan = json.loads(args.plan.read_text(encoding="utf-8"))
            _require_canonical_cli_source(Path(str(plan.get("source_root", ""))))
            result = apply_log_archive_plan(
                plan, args.expected_fingerprint, args.evidence_output
            )
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0 if result["result"] == "SUCCESS" else 2
        _require_canonical_cli_source(args.source_root)
        plan = build_log_archive_plan(
            args.source_root, as_of_utc=args.as_of_utc, hot_days=args.hot_days
        )
    except LogArchiveError as exc:
        print(
            json.dumps({"status": "BLOCKED", "reason_code": str(exc)}, sort_keys=True)
        )
        return 2
    print(json.dumps(plan, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())