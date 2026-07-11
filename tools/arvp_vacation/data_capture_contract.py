from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from core.utils.clock import utcnow as cdb_utcnow

from .contract import VacationContractError, git_head_sha

DATA_CAPTURE_SCHEMA_VERSION = "1.0"
EVIDENCE_CLASS_CONTROLLED = "controlled_lab_evidence"
RUNTIME_RESOLVE = "RUNTIME_RESOLVE"

DEFAULT_ALLOWED_SERVICES: frozenset[str] = frozenset(
    {
        "cdb_postgres",
        "cdb_redis",
        "cdb_ws",
        "cdb_candles",
        "cdb_db_writer",
    }
)

DEFAULT_FORBIDDEN_SERVICES: frozenset[str] = frozenset(
    {
        "cdb_signal",
        "cdb_risk",
        "cdb_allocation",
        "cdb_execution",
        "cdb_paper_runner",
    }
)

DATA_CAPTURE_GO_PHRASE = (
    "DATA-CAPTURE-GO #3990 vacation 14d preflight and acceptance drill"
)


class DataCaptureContractError(ValueError):
    """Data-capture manifest or safety contract violation."""


@dataclass(frozen=True, slots=True)
class DataCaptureManifest:
    schema_version: str
    campaign_id: str
    source_sha: str
    symbol: str
    venue: str
    timeframe: str
    start_utc: str
    planned_end_utc: str
    max_duration_days: int
    allowed_services: tuple[str, ...]
    forbidden_services: tuple[str, ...]
    database_target: str
    heartbeat_interval_seconds: int
    stale_threshold_seconds: int
    min_free_disk_gb: float
    max_restart_budget: int
    evidence_dir: str
    allow_signal: bool
    allow_execution: bool
    allow_paper: bool
    allow_live_trading: bool
    compose_blue: str
    compose_red: str
    evidence_class: str = EVIDENCE_CLASS_CONTROLLED
    drill_duration_minutes: int = 15

    def validate_preflight(self) -> None:
        if self.schema_version != DATA_CAPTURE_SCHEMA_VERSION:
            raise DataCaptureContractError(
                f"unsupported schema_version {self.schema_version!r}"
            )
        if not self.campaign_id.strip():
            raise DataCaptureContractError("campaign_id is required")
        if self.evidence_class != EVIDENCE_CLASS_CONTROLLED:
            raise DataCaptureContractError(
                f"evidence_class must be {EVIDENCE_CLASS_CONTROLLED!r}"
            )
        if self.symbol != "BTCUSDT":
            raise DataCaptureContractError("symbol must be BTCUSDT for this campaign")
        if self.venue.upper() != "MEXC":
            raise DataCaptureContractError("venue must be MEXC")
        if self.timeframe != "1m":
            raise DataCaptureContractError("timeframe must be 1m")
        if self.database_target != "public.candles_1m":
            raise DataCaptureContractError("database_target must be public.candles_1m")
        if self.max_duration_days != 14:
            raise DataCaptureContractError("max_duration_days must be 14")
        if self.allow_signal or self.allow_execution or self.allow_paper:
            raise DataCaptureContractError(
                "allow_signal, allow_execution, allow_paper must be false"
            )
        if self.allow_live_trading:
            raise DataCaptureContractError("allow_live_trading must be false")
        if not self.allowed_services:
            raise DataCaptureContractError("allowed_services must be non-empty")
        if self.min_free_disk_gb <= 0:
            raise DataCaptureContractError("min_free_disk_gb must be > 0")
        if self.heartbeat_interval_seconds < 30:
            raise DataCaptureContractError("heartbeat_interval_seconds must be >= 30")
        if self.stale_threshold_seconds < 60:
            raise DataCaptureContractError("stale_threshold_seconds must be >= 60")
        if self.max_restart_budget < 0:
            raise DataCaptureContractError("max_restart_budget must be >= 0")
        overlap = set(self.allowed_services) & set(self.forbidden_services)
        if overlap:
            raise DataCaptureContractError(
                f"services cannot be both allowed and forbidden: {sorted(overlap)}"
            )
        for svc in self.forbidden_services:
            if svc not in DEFAULT_FORBIDDEN_SERVICES:
                raise DataCaptureContractError(
                    f"unexpected forbidden service {svc!r}; "
                    f"expected subset of {sorted(DEFAULT_FORBIDDEN_SERVICES)}"
                )
        for svc in self.allowed_services:
            if svc not in DEFAULT_ALLOWED_SERVICES:
                raise DataCaptureContractError(
                    f"unexpected allowed service {svc!r}; "
                    f"expected subset of {sorted(DEFAULT_ALLOWED_SERVICES)}"
                )

    def campaign_artifact_dir(self, repo_root: Path) -> Path:
        return repo_root / self.evidence_dir / self.campaign_id


def _parse_iso_utc(raw: str) -> datetime:
    text = raw.strip()
    if text.upper() in {RUNTIME_RESOLVE, "AUTO", ""}:
        raise DataCaptureContractError(
            "start_utc must be resolved before runtime start"
        )
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def resolve_planned_end_utc(start_utc: str, max_duration_days: int) -> str:
    start = _parse_iso_utc(start_utc)
    end = start + timedelta(days=max_duration_days)
    return end.isoformat().replace("+00:00", "Z")


def validate_end_matches_start(
    start_utc: str, planned_end_utc: str, max_duration_days: int
) -> None:
    start = _parse_iso_utc(start_utc)
    end = _parse_iso_utc(planned_end_utc)
    expected = start + timedelta(days=max_duration_days)
    if end != expected:
        raise DataCaptureContractError(
            f"planned_end_utc must be exactly {max_duration_days} days after start_utc "
            f"(expected {expected.isoformat().replace('+00:00', 'Z')}, "
            f"got {planned_end_utc!r})"
        )


def load_data_capture_manifest(path: Path) -> DataCaptureManifest:
    raw: Mapping[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    allowed = tuple(str(s) for s in raw.get("allowed_services") or ())
    forbidden = tuple(str(s) for s in raw.get("forbidden_services") or ())
    manifest = DataCaptureManifest(
        schema_version=str(raw.get("schema_version", "")),
        campaign_id=str(raw.get("campaign_id", "")),
        source_sha=str(raw.get("source_sha", RUNTIME_RESOLVE)),
        symbol=str(raw.get("symbol", "BTCUSDT")),
        venue=str(raw.get("venue", "MEXC")),
        timeframe=str(raw.get("timeframe", "1m")),
        start_utc=str(raw.get("start_utc", RUNTIME_RESOLVE)),
        planned_end_utc=str(raw.get("planned_end_utc", RUNTIME_RESOLVE)),
        max_duration_days=int(raw.get("max_duration_days", 14)),
        allowed_services=allowed or tuple(sorted(DEFAULT_ALLOWED_SERVICES)),
        forbidden_services=forbidden or tuple(sorted(DEFAULT_FORBIDDEN_SERVICES)),
        database_target=str(raw.get("database_target", "public.candles_1m")),
        heartbeat_interval_seconds=int(raw.get("heartbeat_interval_seconds", 300)),
        stale_threshold_seconds=int(raw.get("stale_threshold_seconds", 180)),
        min_free_disk_gb=float(raw.get("min_free_disk_gb", 5)),
        max_restart_budget=int(raw.get("max_restart_budget", 3)),
        evidence_dir=str(
            raw.get("evidence_dir", "artifacts/arvp_vacation/data_capture")
        ),
        allow_signal=bool(raw.get("allow_signal", False)),
        allow_execution=bool(raw.get("allow_execution", False)),
        allow_paper=bool(raw.get("allow_paper", False)),
        allow_live_trading=bool(raw.get("allow_live_trading", False)),
        compose_blue=str(
            raw.get("compose_blue", "infrastructure/compose/compose.blue.yml")
        ),
        compose_red=str(
            raw.get("compose_red", "infrastructure/compose/compose.red.yml")
        ),
        evidence_class=str(raw.get("evidence_class", EVIDENCE_CLASS_CONTROLLED)),
        drill_duration_minutes=int(raw.get("drill_duration_minutes", 15)),
    )
    manifest.validate_preflight()
    return manifest


def resolve_source_sha(manifest: DataCaptureManifest, repo_root: Path | None = None) -> str:
    raw = (manifest.source_sha or "").strip()
    if not raw or raw.upper() in {RUNTIME_RESOLVE, "AUTO"}:
        return git_head_sha(repo_root)
    return raw


def resolve_runtime_window(
    manifest: DataCaptureManifest, *, now: datetime | None = None
) -> tuple[str, str]:
    moment = now or cdb_utcnow()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    start = moment.astimezone(UTC).replace(microsecond=0)
    start_iso = start.isoformat().replace("+00:00", "Z")
    end_iso = resolve_planned_end_utc(start_iso, manifest.max_duration_days)
    return start_iso, end_iso


def classify_running_services(
    running: Sequence[str],
    *,
    allowed: Sequence[str],
    forbidden: Sequence[str],
) -> dict[str, list[str]]:
    allowed_set = set(allowed)
    forbidden_set = set(forbidden)
    cdb = [name for name in running if name.startswith("cdb_")]
    return {
        "running_allowed": sorted(n for n in cdb if n in allowed_set),
        "running_forbidden": sorted(n for n in cdb if n in forbidden_set),
        "running_unexpected": sorted(
            n for n in cdb if n not in allowed_set and n not in forbidden_set
        ),
    }
