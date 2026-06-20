from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from core.utils.clock import utcnow as cdb_utcnow

from .alerts import ALERT_REPORT_SCHEMA_VERSION
from .runner import HEARTBEAT_SCHEMA, STATE_SCHEMA
from .snapshot import SNAPSHOT_SCHEMA_VERSION
from .watchdog import WATCHDOG_REPORT_SCHEMA

COLLECTOR_REPORT_SCHEMA = "evidence_harvester.collector_report.v1"

WRITE_AUDIT_REPORT_SCHEMA = "cdb.evidence_harvester.write_audit_report.v1"
DEFAULT_STALE_THRESHOLD_SECONDS = 7200
DEFAULT_WARN_STALE_SECONDS = 5400
MIN_SANE_ARTIFACT_SIZE = 1
MAX_SANE_ARTIFACT_SIZE = 10 * 1024 * 1024


class WriteAuditError(ValueError):
    pass


def _parse_ts(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise WriteAuditError(f"{field_name} must not be blank")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise WriteAuditError(
                f"{field_name} must be an ISO-8601 UTC timestamp"
            ) from exc
    else:
        raise WriteAuditError(f"{field_name} must be an ISO-8601 UTC timestamp")
    if parsed.tzinfo is None:
        raise WriteAuditError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _now_utc() -> datetime:
    now = cdb_utcnow()
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WriteAuditError(f"{field_name} must be an object")
    return value


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise WriteAuditError(f"{field_name} must be a string")
    text = value.strip()
    if not text:
        raise WriteAuditError(f"{field_name} must not be blank")
    return text


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise WriteAuditError(f"Malformed JSON in {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise WriteAuditError(f"{path.name} JSON root must be an object")
    return payload


def _hash_collector_report(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_artifact_dir() -> Path:
    return _repo_root() / "artifacts" / "evidence_harvester" / "runner"


def _resolve_artifact_dir(path: Path | None) -> Path:
    return (path or _default_artifact_dir()).resolve()


@dataclass(frozen=True, slots=True)
class WriteAuditFinding:
    check_id: str
    check_name: str
    severity: str
    message: str
    artifact: str = ""
    field_name: str = ""


@dataclass(frozen=True, slots=True)
class WriteAuditVerdict:
    verdict: str
    total_checks: int
    pass_count: int
    warn_count: int
    fail_count: int


@dataclass(frozen=True, slots=True)
class WriteAuditReport:
    schema_version: str
    evaluated_at_utc: str
    artifact_dir: str
    required_artifacts_present: bool
    all_json_parse: bool
    schema_versions_match: bool
    hash_linkage_valid: bool
    safety_flags_correct: bool
    timestamps_coherent: bool
    source_modes_valid: bool
    sizes_sane: bool
    verdict: WriteAuditVerdict
    findings: tuple[WriteAuditFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _collect_artifact_paths(artifact_dir: Path) -> dict[str, list[Path]]:
    return {
        "collector_reports": sorted(artifact_dir.glob("collector_report_*.json")),
        "snapshots_json": sorted(artifact_dir.glob("snapshot_*.json")),
        "snapshots_md": sorted(artifact_dir.glob("snapshot_*.md")),
        "alerts_json": sorted(artifact_dir.glob("alert_*.json")),
        "alerts_md": sorted(artifact_dir.glob("alert_*.md")),
        "heartbeat": (
            [artifact_dir / "runner_heartbeat.json"]
            if (artifact_dir / "runner_heartbeat.json").exists()
            else []
        ),
        "state": (
            [artifact_dir / "runner_state.json"]
            if (artifact_dir / "runner_state.json").exists()
            else []
        ),
        "watchdog_json": sorted(artifact_dir.glob("watchdog_report.json")),
        "watchdog_md": sorted(artifact_dir.glob("watchdog_report.md")),
    }


REQUIRED_ARTIFACT_GLOBS: dict[str, str] = {
    "collector_reports": "collector_report_*.json",
    "snapshots_json": "snapshot_*.json",
    "snapshots_md": "snapshot_*.md",
    "alerts_json": "alert_*.json",
    "alerts_md": "alert_*.md",
    "heartbeat": "runner_heartbeat.json",
    "state": "runner_state.json",
    "watchdog_json": "watchdog_report.json",
}

OPTIONAL_ARTIFACT_GLOBS: dict[str, str] = {
    "watchdog_md": "watchdog_report.md",
}


def _check_required_artifacts(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    all_present = True
    for key, pattern in REQUIRED_ARTIFACT_GLOBS.items():
        paths = artifact_paths.get(key, [])
        if not paths:
            all_present = False
            findings.append(
                WriteAuditFinding(
                    check_id="A001",
                    check_name="Required artifact present",
                    severity="fail",
                    message=f"Missing required artifact matching {pattern}",
                    artifact=artifact_dir_label,
                )
            )
    for key, pattern in OPTIONAL_ARTIFACT_GLOBS.items():
        paths = artifact_paths.get(key, [])
        if not paths:
            findings.append(
                WriteAuditFinding(
                    check_id="A001",
                    check_name="Optional companion present",
                    severity="warn",
                    message=f"Missing optional companion {pattern}",
                    artifact=artifact_dir_label,
                )
            )
    if all_present:
        findings.append(
            WriteAuditFinding(
                check_id="A001",
                check_name="Required artifacts present",
                severity="pass",
                message="All required artifacts found",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _get_json_paths(
    artifact_paths: dict[str, list[Path]],
) -> dict[str, list[Path]]:
    return {
        k: v
        for k, v in artifact_paths.items()
        if k
        in {
            "collector_reports",
            "snapshots_json",
            "alerts_json",
            "heartbeat",
            "state",
            "watchdog_json",
        }
    }


def _check_json_integrity(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    json_paths = _get_json_paths(artifact_paths)
    all_parse = True
    for label, paths in json_paths.items():
        for path in paths:
            try:
                _load_json(path)
            except WriteAuditError as exc:
                all_parse = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A002",
                        check_name="JSON artifact parses",
                        severity="fail",
                        message=str(exc),
                        artifact=f"{artifact_dir_label}/{path.name}",
                    )
                )
    if all_parse:
        findings.append(
            WriteAuditFinding(
                check_id="A002",
                check_name="JSON artifacts parse",
                severity="pass",
                message="All found JSON artifacts parse successfully",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _check_schema_versions(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    expected: dict[str, dict[str, str | tuple[str, ...]]] = {
        "collector_reports": {
            "schema_version": COLLECTOR_REPORT_SCHEMA,
        },
        "snapshots_json": {
            "metadata.schema_version": SNAPSHOT_SCHEMA_VERSION,
        },
        "alerts_json": {
            "schema_version": ALERT_REPORT_SCHEMA_VERSION,
        },
        "heartbeat": {
            "schema_version": HEARTBEAT_SCHEMA,
        },
        "state": {
            "schema_version": STATE_SCHEMA,
        },
        "watchdog_json": {
            "schema_version": WATCHDOG_REPORT_SCHEMA,
        },
    }
    all_match = True
    for label, expected_map in expected.items():
        paths = artifact_paths.get(label, [])
        for path in paths:
            try:
                payload = _load_json(path)
            except WriteAuditError:
                continue
            for field, expected_ver in expected_map.items():
                if isinstance(expected_ver, tuple):
                    actual = _nested_get(payload, field)
                    if actual not in expected_ver:
                        all_match = False
                        findings.append(
                            WriteAuditFinding(
                                check_id="A003",
                                check_name="Schema version",
                                severity="fail",
                                message=(
                                    f"{path.name}[{field}] = {actual!r}, "
                                    f"expected one of {expected_ver}"
                                ),
                                artifact=f"{artifact_dir_label}/{path.name}",
                                field_name=field,
                            )
                        )
                else:
                    actual = _nested_get(payload, field)
                    if actual != expected_ver:
                        all_match = False
                        findings.append(
                            WriteAuditFinding(
                                check_id="A003",
                                check_name="Schema version",
                                severity="fail",
                                message=(
                                    f"{path.name}[{field}] = {actual!r}, "
                                    f"expected {expected_ver!r}"
                                ),
                                artifact=f"{artifact_dir_label}/{path.name}",
                                field_name=field,
                            )
                        )
    if all_match:
        findings.append(
            WriteAuditFinding(
                check_id="A003",
                check_name="Schema versions match",
                severity="pass",
                message="All schema versions match expected values",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _nested_get(payload: dict[str, Any], dotted: str) -> Any:
    parts = dotted.split(".")
    current: Any = payload
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _check_hash_linkage(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    collector_reports = artifact_paths.get("collector_reports", [])
    snapshots = artifact_paths.get("snapshots_json", [])
    if not collector_reports or not snapshots:
        findings.append(
            WriteAuditFinding(
                check_id="A004",
                check_name="Hash linkage",
                severity="fail",
                message="Cannot verify hash linkage: collector report or snapshot missing",
                artifact=artifact_dir_label,
            )
        )
        return findings

    all_valid = True
    for snapshot_path in snapshots:
        try:
            snapshot_payload = _load_json(snapshot_path)
        except WriteAuditError:
            all_valid = False
            continue
        expected_hash = snapshot_payload.get("metadata", {}).get(
            "collector_report_hash", ""
        )
        if not expected_hash:
            all_valid = False
            findings.append(
                WriteAuditFinding(
                    check_id="A004",
                    check_name="Hash linkage",
                    severity="fail",
                    message=(f"{snapshot_path.name} has no collector_report_hash"),
                    artifact=f"{artifact_dir_label}/{snapshot_path.name}",
                    field_name="metadata.collector_report_hash",
                )
            )
            continue
        expected_collector_id = snapshot_payload.get("metadata", {}).get(
            "collector_report_id", ""
        )
        matched = False
        for cr_path in collector_reports:
            try:
                cr_payload = _load_json(cr_path)
            except WriteAuditError:
                continue
            actual_hash = _hash_collector_report(cr_payload)
            if actual_hash == expected_hash:
                matched = True
                break
            cr_id = cr_payload.get("report_id", "")
            if cr_id and cr_id == expected_collector_id:
                matched = True
                break
        if matched:
            findings.append(
                WriteAuditFinding(
                    check_id="A004",
                    check_name="Hash linkage",
                    severity="pass",
                    message=(
                        f"{snapshot_path.name} collector_report_hash matches "
                        "a collector report"
                    ),
                    artifact=f"{artifact_dir_label}/{snapshot_path.name}",
                    field_name="metadata.collector_report_hash",
                )
            )
        else:
            all_valid = False
            findings.append(
                WriteAuditFinding(
                    check_id="A004",
                    check_name="Hash linkage",
                    severity="fail",
                    message=(
                        f"{snapshot_path.name} collector_report_hash="
                        f"{expected_hash} does not match any collector report"
                    ),
                    artifact=f"{artifact_dir_label}/{snapshot_path.name}",
                    field_name="metadata.collector_report_hash",
                )
            )
    if all_valid and len(snapshots) > 0:
        pass
    elif not all_valid:
        pass
    return findings


def _check_safety_flags(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    snapshots = artifact_paths.get("snapshots_json", [])
    all_correct = True
    for path in snapshots:
        try:
            payload = _load_json(path)
        except WriteAuditError:
            continue
        safety = payload.get("safety", {})
        for sf_key, expected in [
            ("lr_status", "NO-GO"),
            ("live_status", "NO-GO"),
            ("echtgeld_status", "NO-GO"),
        ]:
            actual = safety.get(sf_key)
            if actual != expected:
                all_correct = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A005",
                        check_name="Safety flag",
                        severity="fail",
                        message=(
                            f"{path.name}[safety.{sf_key}] = {actual!r}, "
                            f"expected {expected!r}"
                        ),
                        artifact=f"{artifact_dir_label}/{path.name}",
                        field_name=f"safety.{sf_key}",
                    )
                )
    alert_reports = artifact_paths.get("alerts_json", [])
    for path in alert_reports:
        try:
            payload = _load_json(path)
        except WriteAuditError:
            continue
        manual_only = payload.get("manual_escalation_only", True)
        if isinstance(manual_only, bool) and not manual_only:
            all_correct = False
            findings.append(
                WriteAuditFinding(
                    check_id="A005",
                    check_name="Safety flag",
                    severity="fail",
                    message=(f"{path.name}[manual_escalation_only] is false"),
                    artifact=f"{artifact_dir_label}/{path.name}",
                    field_name="manual_escalation_only",
                )
            )
    if all_correct:
        findings.append(
            WriteAuditFinding(
                check_id="A005",
                check_name="Safety flags correct",
                severity="pass",
                message="All safety flags are correctly set to NO-GO",
                artifact=artifact_dir_label,
            )
        )
    else:
        pass
    return findings


def _check_timestamp_coherence(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
    *,
    stale_threshold: int,
    warn_stale: int,
    now: datetime,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    all_coherent = True

    heartbeat_paths = artifact_paths.get("heartbeat", [])
    for hb_path in heartbeat_paths:
        try:
            hb = _load_json(hb_path)
        except WriteAuditError:
            continue
        current_run = hb.get("current_run_at_utc", "")
        if current_run:
            try:
                ts = _parse_ts(current_run, "current_run_at_utc")
                age = (now - ts).total_seconds()
                if age > stale_threshold:
                    all_coherent = False
                    findings.append(
                        WriteAuditFinding(
                            check_id="A006",
                            check_name="Timestamp coherence",
                            severity="fail",
                            message=(
                                f"heartbeat current_run_at_utc is {age:.0f}s old "
                                f"(threshold {stale_threshold}s)"
                            ),
                            artifact=f"{artifact_dir_label}/{hb_path.name}",
                            field_name="current_run_at_utc",
                        )
                    )
                elif age > warn_stale:
                    findings.append(
                        WriteAuditFinding(
                            check_id="A006",
                            check_name="Timestamp coherence",
                            severity="warn",
                            message=(
                                f"heartbeat current_run_at_utc is {age:.0f}s old "
                                f"(warn threshold {warn_stale}s)"
                            ),
                            artifact=f"{artifact_dir_label}/{hb_path.name}",
                            field_name="current_run_at_utc",
                        )
                    )
            except WriteAuditError:
                all_coherent = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A006",
                        check_name="Timestamp coherence",
                        severity="fail",
                        message=(
                            f"heartbeat has invalid current_run_at_utc={current_run!r}"
                        ),
                        artifact=f"{artifact_dir_label}/{hb_path.name}",
                        field_name="current_run_at_utc",
                    )
                )

    state_paths = artifact_paths.get("state", [])
    for state_path in state_paths:
        try:
            state_payload = _load_json(state_path)
        except WriteAuditError:
            continue
        last_cycle = state_payload.get("last_cycle_ended_at_utc", "")
        if last_cycle:
            try:
                ts = _parse_ts(last_cycle, "last_cycle_ended_at_utc")
                age = (now - ts).total_seconds()
                if age > stale_threshold:
                    all_coherent = False
                    findings.append(
                        WriteAuditFinding(
                            check_id="A006",
                            check_name="Timestamp coherence",
                            severity="fail",
                            message=(
                                f"runner_state last_cycle_ended_at_utc is {age:.0f}s old "
                                f"(threshold {stale_threshold}s)"
                            ),
                            artifact=f"{artifact_dir_label}/{state_path.name}",
                            field_name="last_cycle_ended_at_utc",
                        )
                    )
                elif age > warn_stale:
                    findings.append(
                        WriteAuditFinding(
                            check_id="A006",
                            check_name="Timestamp coherence",
                            severity="warn",
                            message=(
                                f"runner_state last_cycle_ended_at_utc is {age:.0f}s old "
                                f"(warn threshold {warn_stale}s)"
                            ),
                            artifact=f"{artifact_dir_label}/{state_path.name}",
                            field_name="last_cycle_ended_at_utc",
                        )
                    )
            except WriteAuditError:
                all_coherent = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A006",
                        check_name="Timestamp coherence",
                        severity="fail",
                        message=(
                            "runner_state has invalid "
                            f"last_cycle_ended_at_utc={last_cycle!r}"
                        ),
                        artifact=f"{artifact_dir_label}/{state_path.name}",
                        field_name="last_cycle_ended_at_utc",
                    )
                )

    collector_reports = artifact_paths.get("collector_reports", [])
    for cr_path in collector_reports:
        try:
            cr = _load_json(cr_path)
        except WriteAuditError:
            continue
        produced_at = cr.get("produced_at_utc", "")
        if produced_at:
            try:
                _parse_ts(produced_at, "produced_at_utc")
            except WriteAuditError:
                all_coherent = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A006",
                        check_name="Timestamp coherence",
                        severity="fail",
                        message=(
                            f"{cr_path.name} has invalid "
                            f"produced_at_utc={produced_at!r}"
                        ),
                        artifact=f"{artifact_dir_label}/{cr_path.name}",
                        field_name="produced_at_utc",
                    )
                )

    snapshots = artifact_paths.get("snapshots_json", [])
    latest_snapshot_path: Path | None = None
    latest_snapshot_ts: datetime | None = None
    for snap_path in snapshots:
        try:
            snap = _load_json(snap_path)
        except WriteAuditError:
            continue
        gen_at = snap.get("metadata", {}).get("generated_at_utc", "")
        if gen_at:
            try:
                ts = _parse_ts(gen_at, "generated_at_utc")
                if latest_snapshot_ts is None or ts > latest_snapshot_ts:
                    latest_snapshot_ts = ts
                    latest_snapshot_path = snap_path
            except WriteAuditError:
                all_coherent = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A006",
                        check_name="Timestamp coherence",
                        severity="fail",
                        message=(
                            f"{snap_path.name} has invalid "
                            f"generated_at_utc={gen_at!r}"
                        ),
                        artifact=f"{artifact_dir_label}/{snap_path.name}",
                        field_name="metadata.generated_at_utc",
                    )
                )

    if latest_snapshot_path is not None and latest_snapshot_ts is not None:
        age = (now - latest_snapshot_ts).total_seconds()
        if age > stale_threshold:
            all_coherent = False
            findings.append(
                WriteAuditFinding(
                    check_id="A006",
                    check_name="Timestamp coherence",
                    severity="fail",
                    message=(
                        f"latest snapshot {latest_snapshot_path.name} generated_at_utc is "
                        f"{age:.0f}s old (threshold {stale_threshold}s)"
                    ),
                    artifact=f"{artifact_dir_label}/{latest_snapshot_path.name}",
                    field_name="metadata.generated_at_utc",
                )
            )
        elif age > warn_stale:
            findings.append(
                WriteAuditFinding(
                    check_id="A006",
                    check_name="Timestamp coherence",
                    severity="warn",
                    message=(
                        f"latest snapshot {latest_snapshot_path.name} generated_at_utc is "
                        f"{age:.0f}s old (warn threshold {warn_stale}s)"
                    ),
                    artifact=f"{artifact_dir_label}/{latest_snapshot_path.name}",
                    field_name="metadata.generated_at_utc",
                )
            )
    if all_coherent:
        findings.append(
            WriteAuditFinding(
                check_id="A006",
                check_name="Timestamps coherent",
                severity="pass",
                message="All timestamps are valid and within threshold",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _check_source_modes(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    allowed_sources = {"fixture", "future_readonly"}
    all_valid = True

    collector_reports = artifact_paths.get("collector_reports", [])
    for cr_path in collector_reports:
        try:
            cr = _load_json(cr_path)
        except WriteAuditError:
            continue
        sm = cr.get("source_mode", "")
        if sm not in allowed_sources:
            all_valid = False
            findings.append(
                WriteAuditFinding(
                    check_id="A007",
                    check_name="Source mode",
                    severity="fail",
                    message=(
                        f"{cr_path.name} source_mode={sm!r}, "
                        f"expected one of {allowed_sources}"
                    ),
                    artifact=f"{artifact_dir_label}/{cr_path.name}",
                    field_name="source_mode",
                )
            )

    snapshots = artifact_paths.get("snapshots_json", [])
    for snap_path in snapshots:
        try:
            snap = _load_json(snap_path)
        except WriteAuditError:
            continue
        sm = snap.get("metadata", {}).get("source_mode", "")
        if sm not in allowed_sources:
            all_valid = False
            findings.append(
                WriteAuditFinding(
                    check_id="A007",
                    check_name="Source mode",
                    severity="fail",
                    message=(
                        f"{snap_path.name} metadata.source_mode={sm!r}, "
                        f"expected one of {allowed_sources}"
                    ),
                    artifact=f"{artifact_dir_label}/{snap_path.name}",
                    field_name="metadata.source_mode",
                )
            )

    if all_valid:
        findings.append(
            WriteAuditFinding(
                check_id="A007",
                check_name="Source modes valid",
                severity="pass",
                message="All source_mode values are valid",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _check_artifact_sizes(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    all_sane = True
    for label, paths in artifact_paths.items():
        for path in paths:
            if not path.exists():
                continue
            size = path.stat().st_size
            if size == 0:
                all_sane = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A008",
                        check_name="Artifact size",
                        severity="fail",
                        message=f"{path.name} is zero bytes",
                        artifact=f"{artifact_dir_label}/{path.name}",
                    )
                )
            elif size > MAX_SANE_ARTIFACT_SIZE:
                all_sane = False
                findings.append(
                    WriteAuditFinding(
                        check_id="A008",
                        check_name="Artifact size",
                        severity="fail",
                        message=(
                            f"{path.name} is {size} bytes "
                            f"(max sane {MAX_SANE_ARTIFACT_SIZE})"
                        ),
                        artifact=f"{artifact_dir_label}/{path.name}",
                    )
                )
    if all_sane:
        findings.append(
            WriteAuditFinding(
                check_id="A008",
                check_name="Artifact sizes sane",
                severity="pass",
                message="All artifact sizes are within bounds",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _check_markdown_companions(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    companion_pairs = [
        ("snapshots_json", "snapshots_md", "snapshot"),
        ("alerts_json", "alerts_md", "alert"),
        ("watchdog_json", "watchdog_md", "watchdog"),
    ]
    all_present = True
    for json_key, md_key, name in companion_pairs:
        json_paths = artifact_paths.get(json_key, [])
        md_paths = artifact_paths.get(md_key, [])
        has_companions = len(md_paths) >= len(json_paths)
        if json_paths and not has_companions:
            all_present = False
            findings.append(
                WriteAuditFinding(
                    check_id="A009",
                    check_name="Markdown companion",
                    severity="warn",
                    message=(
                        f"{name} JSON present but fewer Markdown companions: "
                        f"{len(json_paths)} JSON, {len(md_paths)} MD"
                    ),
                    artifact=artifact_dir_label,
                )
            )
    if all_present:
        findings.append(
            WriteAuditFinding(
                check_id="A009",
                check_name="Markdown companions present",
                severity="pass",
                message="All Markdown companions present where JSON exists",
                artifact=artifact_dir_label,
            )
        )
    return findings


def _check_metadata_fields(
    artifact_paths: dict[str, list[Path]],
    artifact_dir_label: str,
) -> list[WriteAuditFinding]:
    findings: list[WriteAuditFinding] = []
    all_ok = True

    json_checks: dict[str, list[tuple[str, str]]] = {
        "collector_reports": [
            ("schema_version", "schema_version"),
            ("source_mode", "source_mode"),
            ("report_id", "report_id"),
            ("produced_at_utc", "produced_at_utc"),
        ],
        "snapshots_json": [
            ("schema_version", "metadata.schema_version"),
            ("generated_at_utc", "metadata.generated_at_utc"),
            ("source_mode", "metadata.source_mode"),
            ("collector_report_hash", "metadata.collector_report_hash"),
            (
                "collector_report_schema_version",
                "metadata.collector_report_schema_version",
            ),
        ],
        "alerts_json": [
            ("schema_version", "schema_version"),
        ],
        "heartbeat": [
            ("schema_version", "schema_version"),
            ("current_run_at_utc", "current_run_at_utc"),
        ],
        "state": [
            ("schema_version", "schema_version"),
            ("last_cycle_verdict", "last_cycle_verdict"),
        ],
        "watchdog_json": [
            ("schema_version", "schema_version"),
            ("evaluated_at_utc", "evaluated_at_utc"),
            ("verdict", "verdict.verdict"),
        ],
    }

    for label, field_checks in json_checks.items():
        paths = artifact_paths.get(label, [])
        for path in paths:
            try:
                payload = _load_json(path)
            except WriteAuditError:
                continue
            for field_name, dotted_path in field_checks:
                val = _nested_get(payload, dotted_path)
                if not val or (isinstance(val, str) and not val.strip()):
                    all_ok = False
                    findings.append(
                        WriteAuditFinding(
                            check_id="A010",
                            check_name="Artifact metadata field",
                            severity="fail",
                            message=(f"{path.name} missing or empty {field_name}"),
                            artifact=f"{artifact_dir_label}/{path.name}",
                            field_name=dotted_path,
                        )
                    )
    if all_ok:
        findings.append(
            WriteAuditFinding(
                check_id="A010",
                check_name="Artifact metadata fields present",
                severity="pass",
                message="All expected metadata fields present and non-empty",
                artifact=artifact_dir_label,
            )
        )
    return findings


def run_write_audit(
    artifact_dir: Path,
    *,
    stale_threshold: int = DEFAULT_STALE_THRESHOLD_SECONDS,
    warn_stale: int = DEFAULT_WARN_STALE_SECONDS,
    now: datetime | None = None,
) -> WriteAuditReport:
    eval_now = now or _now_utc()
    artifact_dir_label = str(artifact_dir)
    artifact_paths = _collect_artifact_paths(artifact_dir)

    all_findings: list[WriteAuditFinding] = []

    required_findings = _check_required_artifacts(artifact_paths, artifact_dir_label)
    all_findings.extend(required_findings)

    integrity_findings = _check_json_integrity(artifact_paths, artifact_dir_label)
    all_findings.extend(integrity_findings)

    schema_findings = _check_schema_versions(artifact_paths, artifact_dir_label)
    all_findings.extend(schema_findings)

    hash_findings = _check_hash_linkage(artifact_paths, artifact_dir_label)
    all_findings.extend(hash_findings)

    safety_findings = _check_safety_flags(artifact_paths, artifact_dir_label)
    all_findings.extend(safety_findings)

    ts_findings = _check_timestamp_coherence(
        artifact_paths,
        artifact_dir_label,
        stale_threshold=stale_threshold,
        warn_stale=warn_stale,
        now=eval_now,
    )
    all_findings.extend(ts_findings)

    source_findings = _check_source_modes(artifact_paths, artifact_dir_label)
    all_findings.extend(source_findings)

    size_findings = _check_artifact_sizes(artifact_paths, artifact_dir_label)
    all_findings.extend(size_findings)

    md_findings = _check_markdown_companions(artifact_paths, artifact_dir_label)
    all_findings.extend(md_findings)

    meta_findings = _check_metadata_fields(artifact_paths, artifact_dir_label)
    all_findings.extend(meta_findings)

    fail_count = sum(1 for f in all_findings if f.severity == "fail")
    warn_count = sum(1 for f in all_findings if f.severity == "warn")
    pass_count = sum(1 for f in all_findings if f.severity == "pass")

    if fail_count:
        verdict = "FAIL"
    elif warn_count:
        verdict = "WARN"
    else:
        verdict = "PASS"

    required_artifacts_present = not any(
        f.check_id == "A001" and f.severity == "fail" for f in all_findings
    )
    all_json_parse = not any(
        f.check_id == "A002" and f.severity == "fail" for f in all_findings
    )
    schema_versions_match = not any(
        f.check_id == "A003" and f.severity == "fail" for f in all_findings
    )
    hash_linkage_valid = not any(
        f.check_id == "A004" and f.severity == "fail" for f in all_findings
    )
    safety_flags_correct = not any(
        f.check_id == "A005" and f.severity == "fail" for f in all_findings
    )
    timestamps_coherent = not any(
        f.check_id == "A006" and f.severity == "fail" for f in all_findings
    )
    source_modes_valid = not any(
        f.check_id == "A007" and f.severity == "fail" for f in all_findings
    )
    sizes_sane = not any(
        f.check_id == "A008" and f.severity == "fail" for f in all_findings
    )

    sorted_findings = tuple(
        sorted(
            all_findings,
            key=lambda f: (
                {"fail": 0, "warn": 1, "pass": 2}.get(f.severity, 9),
                f.check_id,
            ),
        )
    )

    return WriteAuditReport(
        schema_version=WRITE_AUDIT_REPORT_SCHEMA,
        evaluated_at_utc=_format_ts(eval_now),
        artifact_dir=str(artifact_dir),
        required_artifacts_present=required_artifacts_present,
        all_json_parse=all_json_parse,
        schema_versions_match=schema_versions_match,
        hash_linkage_valid=hash_linkage_valid,
        safety_flags_correct=safety_flags_correct,
        timestamps_coherent=timestamps_coherent,
        source_modes_valid=source_modes_valid,
        sizes_sane=sizes_sane,
        verdict=WriteAuditVerdict(
            verdict=verdict,
            total_checks=len(sorted_findings),
            pass_count=pass_count,
            warn_count=warn_count,
            fail_count=fail_count,
        ),
        findings=sorted_findings,
    )


def report_to_markdown(report: WriteAuditReport) -> str:
    payload = report.to_dict()
    lines = [
        "# Evidence Harvester Write-Audit Report",
        "",
        "## Metadata",
        f"- Schema version: `{payload['schema_version']}`",
        f"- Evaluated at (UTC): `{payload['evaluated_at_utc']}`",
        f"- Artifact directory: `{payload['artifact_dir']}`",
        "",
        "## Status Flags",
        f"- Required artifacts present: `{payload['required_artifacts_present']}`",
        f"- All JSON parse: `{payload['all_json_parse']}`",
        f"- Schema versions match: `{payload['schema_versions_match']}`",
        f"- Hash linkage valid: `{payload['hash_linkage_valid']}`",
        f"- Safety flags correct: `{payload['safety_flags_correct']}`",
        f"- Timestamps coherent: `{payload['timestamps_coherent']}`",
        f"- Source modes valid: `{payload['source_modes_valid']}`",
        f"- Sizes sane: `{payload['sizes_sane']}`",
        "",
        "## Summary",
        f"- Verdict: **{payload['verdict']['verdict']}**",
        f"- Total checks: {payload['verdict']['total_checks']}",
        f"- Pass: {payload['verdict']['pass_count']}",
        f"- Warn: {payload['verdict']['warn_count']}",
        f"- Fail: {payload['verdict']['fail_count']}",
        "",
        "## Findings",
    ]
    for item in payload["findings"]:
        icon = {"fail": "FAIL", "warn": "WARN", "pass": "PASS"}.get(
            item["severity"], "????"
        )
        artifact_part = f" [{item['artifact']}]" if item.get("artifact") else ""
        field_part = f" ({item['field_name']})" if item.get("field_name") else ""
        lines.append(
            f"  [{icon}] {item['check_name']}{artifact_part}{field_part}: {item['message']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "- No LR-Go / No Live-Go / No Echtgeld-Go.",
            "- No runtime / no DB execution / no Docker / no secrets.",
            "- Write-Audit is read-only and does not modify artifacts.",
            "- No automatic restart, GitHub write, or scheduler install.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evidence harvester write-audit — verify artifacts are actually written."
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="Runner artifact directory to audit.",
    )
    parser.add_argument(
        "--stale-threshold",
        type=int,
        default=DEFAULT_STALE_THRESHOLD_SECONDS,
        help="Max artifact age before FAIL (default: 7200).",
    )
    parser.add_argument(
        "--warn-stale",
        type=int,
        default=DEFAULT_WARN_STALE_SECONDS,
        help="Artifact age for WARN (default: 5400).",
    )
    parser.add_argument(
        "--evaluated-at-utc",
        help="Optional explicit evaluation timestamp for deterministic tests.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional path for write-audit report JSON.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional path for write-audit report Markdown.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact_dir = _resolve_artifact_dir(args.artifact_dir)
    now = _now_utc()
    if args.evaluated_at_utc:
        now = _parse_ts(args.evaluated_at_utc, "--evaluated-at-utc")
    report = run_write_audit(
        artifact_dir,
        stale_threshold=args.stale_threshold,
        warn_stale=args.warn_stale,
        now=now,
    )
    payload = report.to_dict()
    json_text = json.dumps(
        payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=True,
    )
    print(json_text)

    if args.json_output:
        args.json_output.write_text(
            json_text + ("" if json_text.endswith("\n") else "\n"),
            encoding="utf-8",
        )
    if args.markdown_output:
        args.markdown_output.write_text(report_to_markdown(report), encoding="utf-8")
    return 0 if report.verdict.verdict != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
