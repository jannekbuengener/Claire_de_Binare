from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import yaml

from core.replay.canonical_json import canonical_hash

MANIFEST_SCHEMA_VERSION = "1.0"
QUEUE_STATE_SCHEMA_VERSION = "1.0"
EVIDENCE_CLASS_CONTROLLED = "controlled_lab_evidence"

JOB_PENDING = "PENDING"
JOB_RUNNING = "RUNNING"
JOB_PASS = "PASS"
JOB_FAIL = "FAIL"
JOB_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
JOB_INTERRUPTED = "INTERRUPTED"
JOB_SKIPPED_DUPLICATE = "SKIPPED_DUPLICATE"
JOB_FATAL_STOP = "FATAL_STOP"

TERMINAL_JOB_STATUSES = frozenset(
    {
        JOB_PASS,
        JOB_FAIL,
        JOB_INSUFFICIENT_DATA,
        JOB_SKIPPED_DUPLICATE,
        JOB_FATAL_STOP,
    }
)

STRATEGY_ACTIVE = "active"
STRATEGY_PARKED = "parked_reference"

ALLOWED_STRATEGIES: frozenset[str] = frozenset(
    {
        "donchian_breakout_v1",
        "breakout_trend_filter_v1",
        "primary_breakout_v1",
    }
)

STRATEGY_ADAPTERS: dict[str, str] = {
    "donchian_breakout_v1": "donchian_breakout_runner_v1",
    "breakout_trend_filter_v1": "breakout_trend_filter_runner_v1",
    "primary_breakout_v1": "primary_breakout_runner_v1",
}

ALLOWED_SCENARIOS: frozenset[str] = frozenset(
    {"baseline", "pessimistic_execution", "feed_gap"}
)

_HEX64_RE = re.compile(r"^[a-f0-9]{64}$")


class VacationContractError(ValueError):
    """Manifest or dataset contract violation."""


@dataclass(frozen=True, slots=True)
class StrategySpec:
    strategy_id: str
    role: str = STRATEGY_ACTIVE


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    dataset_id: str
    dataset_dir: str
    spec_path: str
    input_candles: str
    dataset_fingerprint: str
    symbol: str
    start_ts_ms: int | None
    end_ts_ms: int | None
    evidence_class: str | None


@dataclass(frozen=True, slots=True)
class VacationManifest:
    schema_version: str
    campaign_id: str
    source_sha: str
    evidence_class: str
    artifact_root: str
    dataset_roots: tuple[str, ...]
    strategies: tuple[StrategySpec, ...]
    scenarios: tuple[str, ...]
    max_job_runtime_seconds: int
    max_attempts_per_job: int
    min_free_disk_gb: float
    allow_paper_jobs: bool
    speedup_profile: str = "instant"
    symbol: str = "BTCUSDT"

    def validate_preflight(self) -> None:
        if self.schema_version != MANIFEST_SCHEMA_VERSION:
            raise VacationContractError(
                f"unsupported schema_version {self.schema_version!r}"
            )
        if not self.campaign_id.strip():
            raise VacationContractError("campaign_id is required")
        if self.evidence_class != EVIDENCE_CLASS_CONTROLLED:
            raise VacationContractError(
                f"evidence_class must be {EVIDENCE_CLASS_CONTROLLED!r}"
            )
        if self.allow_paper_jobs:
            raise VacationContractError(
                "allow_paper_jobs=true is forbidden in vacation MVP"
            )
        if not self.dataset_roots:
            raise VacationContractError("dataset_roots must be non-empty")
        if not self.strategies:
            raise VacationContractError("strategies must be non-empty")
        if not self.scenarios:
            raise VacationContractError("scenarios must be non-empty")
        unknown = set(self.scenarios) - ALLOWED_SCENARIOS
        if unknown:
            raise VacationContractError(f"unsupported scenarios: {sorted(unknown)}")
        for spec in self.strategies:
            if spec.strategy_id not in ALLOWED_STRATEGIES:
                raise VacationContractError(
                    f"unsupported strategy_id {spec.strategy_id!r}"
                )
            if spec.role not in {STRATEGY_ACTIVE, STRATEGY_PARKED}:
                raise VacationContractError(f"unsupported strategy role {spec.role!r}")
        if self.max_attempts_per_job < 1:
            raise VacationContractError("max_attempts_per_job must be >= 1")
        if self.max_job_runtime_seconds < 1:
            raise VacationContractError("max_job_runtime_seconds must be >= 1")
        if self.min_free_disk_gb <= 0:
            raise VacationContractError("min_free_disk_gb must be > 0")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_manifest(path: Path | str) -> VacationManifest:
    manifest_path = Path(path)
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise VacationContractError("manifest root must be a mapping")
    strategies_raw = raw.get("strategies") or []
    strategies: list[StrategySpec] = []
    for entry in strategies_raw:
        if isinstance(entry, str):
            strategies.append(StrategySpec(strategy_id=entry))
        elif isinstance(entry, dict):
            strategies.append(
                StrategySpec(
                    strategy_id=str(entry["strategy_id"]),
                    role=str(entry.get("role", STRATEGY_ACTIVE)),
                )
            )
        else:
            raise VacationContractError("strategy entry must be string or mapping")
    return VacationManifest(
        schema_version=str(raw.get("schema_version", "")),
        campaign_id=str(raw.get("campaign_id", "")),
        source_sha=str(raw.get("source_sha", "")),
        evidence_class=str(raw.get("evidence_class", "")),
        artifact_root=str(raw.get("artifact_root", "artifacts/arvp_vacation")),
        dataset_roots=tuple(str(p) for p in raw.get("dataset_roots") or []),
        strategies=tuple(strategies),
        scenarios=tuple(str(s) for s in raw.get("scenarios") or []),
        max_job_runtime_seconds=int(raw.get("max_job_runtime_seconds", 3600)),
        max_attempts_per_job=int(raw.get("max_attempts_per_job", 2)),
        min_free_disk_gb=float(raw.get("min_free_disk_gb", 10)),
        allow_paper_jobs=bool(raw.get("allow_paper_jobs", False)),
        speedup_profile=str(raw.get("speedup_profile", "instant")),
        symbol=str(raw.get("symbol", "BTCUSDT")),
    )


def _dataset_id_from_spec(spec: Mapping[str, Any], spec_path: Path) -> str:
    for key in ("dataset_id", "window_id"):
        value = spec.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return spec_path.parent.name


def _dataset_fingerprint_from_spec(spec: Mapping[str, Any]) -> str:
    for key in ("fingerprint", "candles_sha256"):
        value = spec.get(key)
        if isinstance(value, str) and _HEX64_RE.match(value.strip()):
            return value.strip().lower()
    raise VacationContractError("dataset spec missing fingerprint/candles_sha256")


def _resolve_candles_path(
    repo_root: Path, spec: Mapping[str, Any], spec_path: Path
) -> Path:
    file_path = spec.get("file_path")
    if not isinstance(file_path, str) or not file_path.strip():
        raise VacationContractError(f"{spec_path}: missing file_path")
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    if not candidate.exists():
        raise VacationContractError(f"candle file missing: {candidate}")
    return candidate


def parse_dataset_spec(
    spec_path: Path, repo_root: Path | None = None
) -> DatasetRecord:
    root = repo_root or _repo_root()
    if not spec_path.exists():
        raise VacationContractError(f"dataset spec missing: {spec_path}")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VacationContractError(f"invalid dataset spec JSON: {spec_path}") from exc
    if not isinstance(spec, dict):
        raise VacationContractError(f"dataset spec root must be object: {spec_path}")
    evidence_class = spec.get("evidence_class")
    if evidence_class is not None and evidence_class != EVIDENCE_CLASS_CONTROLLED:
        raise VacationContractError(
            f"dataset evidence_class must be {EVIDENCE_CLASS_CONTROLLED!r}, "
            f"got {evidence_class!r}"
        )
    if spec.get("natural_paper_evidence") is True:
        raise VacationContractError("natural_paper_evidence datasets are forbidden")
    candles_path = _resolve_candles_path(root, spec, spec_path)
    fingerprint = _dataset_fingerprint_from_spec(spec)
    start_ts = spec.get("start_ts_ms")
    end_ts = spec.get("end_ts_ms")
    symbol = str(spec.get("symbol", "BTCUSDT"))
    return DatasetRecord(
        dataset_id=_dataset_id_from_spec(spec, spec_path),
        dataset_dir=str(spec_path.parent.relative_to(root)).replace("\\", "/"),
        spec_path=str(spec_path.relative_to(root)).replace("\\", "/"),
        input_candles=str(candles_path.relative_to(root)).replace("\\", "/"),
        dataset_fingerprint=fingerprint,
        symbol=symbol,
        start_ts_ms=int(start_ts) if start_ts is not None else None,
        end_ts_ms=int(end_ts) if end_ts is not None else None,
        evidence_class=str(evidence_class) if evidence_class else None,
    )


def _time_window_key(record: DatasetRecord) -> tuple[int, int] | None:
    if record.start_ts_ms is None or record.end_ts_ms is None:
        return None
    return (record.start_ts_ms, record.end_ts_ms)


def discover_datasets(
    manifest: VacationManifest,
    repo_root: Path | None = None,
    *,
    exclude_fingerprints: Iterable[str] = (),
    exclude_time_windows: Iterable[tuple[int, int]] = (),
) -> list[DatasetRecord]:
    root = repo_root or _repo_root()
    seen_fingerprints: set[str] = {f.lower() for f in exclude_fingerprints}
    seen_windows: set[tuple[int, int]] = set(exclude_time_windows)
    discovered: list[DatasetRecord] = []

    for dataset_root in manifest.dataset_roots:
        base = root / dataset_root
        candidates: list[Path] = []
        direct_spec = base / "dataset_spec.json"
        if direct_spec.exists():
            candidates.append(direct_spec)
        elif base.is_dir():
            for child in sorted(base.iterdir()):
                if child.is_dir():
                    child_spec = child / "dataset_spec.json"
                    if child_spec.exists():
                        candidates.append(child_spec)
        else:
            continue

        for spec_path in candidates:
            try:
                record = parse_dataset_spec(spec_path, root)
            except VacationContractError:
                continue
            if record.dataset_fingerprint in seen_fingerprints:
                continue
            window_key = _time_window_key(record)
            if window_key is not None and window_key in seen_windows:
                continue
            seen_fingerprints.add(record.dataset_fingerprint)
            if window_key is not None:
                seen_windows.add(window_key)
            discovered.append(record)

    return discovered


def build_job_fingerprint(
    *,
    source_sha: str,
    strategy_id: str,
    dataset_fingerprint: str,
    scenarios: Sequence[str],
    speedup_profile: str,
    execution_params: Mapping[str, Any] | None = None,
) -> str:
    payload = {
        "source_sha": source_sha.strip().lower(),
        "strategy_id": strategy_id,
        "dataset_fingerprint": dataset_fingerprint.lower(),
        "scenarios": sorted(scenarios),
        "speedup_profile": speedup_profile,
        "execution_params": dict(execution_params or {}),
    }
    return canonical_hash(payload)


def build_job_id(strategy_id: str, dataset_id: str) -> str:
    safe_strategy = strategy_id.replace("_", "-")
    safe_dataset = re.sub(r"[^a-zA-Z0-9._-]+", "-", dataset_id)
    return f"vac-{safe_strategy}-{safe_dataset}-scenarios"


def campaign_artifact_dir(manifest: VacationManifest, repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root / manifest.artifact_root / manifest.campaign_id


def git_head_sha(repo_root: Path | None = None) -> str:
    root = repo_root or _repo_root()
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "0000000"
    return result.stdout.strip()


def resolve_source_sha(manifest: VacationManifest, repo_root: Path | None = None) -> str:
    raw = (manifest.source_sha or "").strip()
    if not raw or raw.upper() in {"RUNTIME_RESOLVE", "AUTO"}:
        return git_head_sha(repo_root)
    return raw


DiskSpaceProbe = Callable[[Path], float]
