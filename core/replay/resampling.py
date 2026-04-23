"""Deterministic replay resampling for KPI stability analysis.

Scope (#1852): a minimal, explicit bootstrap layer over caller-supplied replay
KPI blocks. This slice intentionally does not infer blocks from runner outputs
or add new replay execution modes.

Design rules:
  - Only explicit caller-supplied blocks are accepted; no hidden grouping
    inference or silent fallback behavior.
  - Deterministic: same blocks + same config => identical artifact payload.
  - Fail-closed: unsupported modes, mixed provenance, and invalid KPI requests
    raise ResamplingError immediately.
  - No-float rule for canonical artifacts: Decimal values serialize as strings.
  - Machine-readable outputs prefer empirical quantile summaries over broader
    statistical claims.

Non-goals:
  - predictive simulation or synthetic market generation
  - replay runner auto-wiring
  - regime-weighted sampling in this first slice
  - schema changes to replay_report.v1
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.utils.seed import SeedManager

_PNL_Q = Decimal("0.00000001")
_RATE_Q = Decimal("0.00000001")
_RUN_ID_RE = re.compile(r"^replay-[a-f0-9]{12}-\d{4}$")
_HEX_64_RE = re.compile(r"^[a-f0-9]{64}$")
_EXECUTION_PROVENANCE_ID_RE = re.compile(r"^bt-[a-f0-9]{16}$")
_SUPPORTED_METHODS: frozenset[str] = frozenset({"block_bootstrap"})
_INT_KPIS: frozenset[str] = frozenset({"signal_count", "fill_count", "reject_count"})
_DECIMAL_KPIS: frozenset[str] = frozenset({"pnl_sum", "fill_rate"})
_SUPPORTED_KPIS: frozenset[str] = _INT_KPIS | _DECIMAL_KPIS
_STABILITY_ARTIFACT_FILENAME = "resampling_stability.json"


class ResamplingError(ValueError):
    """Raised when resampling validation or artifact writing fails."""


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ResamplingError(f"{field_name} must be a non-empty string")


def _require_non_negative_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ResamplingError(f"{field_name} must be a non-negative int")


def _require_positive_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ResamplingError(f"{field_name} must be a positive int")


def _quantize_decimal(value: Decimal, quantum: Decimal) -> Decimal:
    return value.quantize(quantum)


def _fill_rate(fill_count: int, reject_count: int) -> Decimal:
    total = fill_count + reject_count
    if total == 0:
        return Decimal("0").quantize(_RATE_Q)
    return (Decimal(fill_count) / Decimal(total)).quantize(_RATE_Q)


def _serialize_metric(metric_name: str, value: int | Decimal) -> str:
    if metric_name in _INT_KPIS:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ResamplingError(f"{metric_name} must serialize from int")
        return str(value)
    if metric_name == "pnl_sum":
        if not isinstance(value, Decimal):
            raise ResamplingError("pnl_sum must serialize from Decimal")
        return str(_quantize_decimal(value, _PNL_Q))
    if metric_name == "fill_rate":
        if not isinstance(value, Decimal):
            raise ResamplingError("fill_rate must serialize from Decimal")
        return str(_quantize_decimal(value, _RATE_Q))
    raise ResamplingError(f"Unsupported KPI for serialization: {metric_name}")


def _subtract_metric(metric_name: str, maximum: int | Decimal, minimum: int | Decimal) -> int | Decimal:
    if metric_name in _INT_KPIS:
        if not isinstance(maximum, int) or not isinstance(minimum, int):
            raise ResamplingError(f"{metric_name} span requires int values")
        return maximum - minimum
    if metric_name == "pnl_sum":
        if not isinstance(maximum, Decimal) or not isinstance(minimum, Decimal):
            raise ResamplingError("pnl_sum span requires Decimal values")
        return (maximum - minimum).quantize(_PNL_Q)
    if metric_name == "fill_rate":
        if not isinstance(maximum, Decimal) or not isinstance(minimum, Decimal):
            raise ResamplingError("fill_rate span requires Decimal values")
        return (maximum - minimum).quantize(_RATE_Q)
    raise ResamplingError(f"Unsupported KPI for span calculation: {metric_name}")


def _quantile(values: Sequence[int | Decimal], *, numerator: int, denominator: int) -> int | Decimal:
    if not values:
        raise ResamplingError("quantile values must not be empty")
    index = ((len(values) - 1) * numerator) // denominator
    return values[index]


def _aggregate_blocks(blocks: Sequence["ReplayKPIBlock"]) -> dict[str, int | Decimal]:
    signal_count = sum(block.signal_count for block in blocks)
    fill_count = sum(block.fill_count for block in blocks)
    reject_count = sum(block.reject_count for block in blocks)
    pnl_sum = sum((block.pnl_sum for block in blocks), Decimal("0")).quantize(_PNL_Q)
    return {
        "signal_count": signal_count,
        "fill_count": fill_count,
        "reject_count": reject_count,
        "pnl_sum": pnl_sum,
        "fill_rate": _fill_rate(fill_count, reject_count),
    }


def _input_fingerprint(blocks: Sequence["ReplayKPIBlock"]) -> str:
    return canonical_hash([block.to_dict() for block in blocks])


def _validate_uniform_provenance(blocks: Sequence["ReplayKPIBlock"]) -> None:
    run_ids = {block.source_run_id for block in blocks}
    dataset_fingerprints = {block.dataset_fingerprint for block in blocks}
    execution_ids = {block.execution_provenance_id for block in blocks}
    if len(run_ids) != 1:
        raise ResamplingError("All blocks must share the same source_run_id")
    if len(dataset_fingerprints) != 1:
        raise ResamplingError("All blocks must share the same dataset_fingerprint")
    if len(execution_ids) != 1:
        raise ResamplingError("All blocks must share the same execution_provenance_id")


def _build_operator_summary(
    *,
    config: "ResamplingConfig",
    summaries: Sequence["ResamplingKPISummary"],
) -> tuple[str, ...]:
    lines = [
        (
            f"method={config.method}; samples={config.sample_count}; "
            f"blocks_per_sample={config.sample_block_count}; seed={config.seed}"
        )
    ]
    for summary in summaries:
        lines.append(
            f"{summary.kpi}: baseline={summary.baseline}; "
            f"empirical_band_p05_p95={summary.p05}..{summary.p95}; "
            f"span={summary.empirical_span}"
        )
    return tuple(lines)


@dataclass(frozen=True, slots=True)
class ResamplingConfig:
    """Explicit bootstrap configuration for replay KPI stability analysis."""

    method: str
    sample_count: int
    sample_block_count: int
    seed: int
    selected_kpis: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.method not in _SUPPORTED_METHODS:
            raise ResamplingError(
                f"Unsupported resampling method {self.method!r}. "
                f"Valid: {sorted(_SUPPORTED_METHODS)}"
            )
        _require_positive_int(self.sample_count, "sample_count")
        _require_positive_int(self.sample_block_count, "sample_block_count")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool) or self.seed < 0:
            raise ResamplingError("seed must be a non-negative int")
        if not isinstance(self.selected_kpis, tuple) or not self.selected_kpis:
            raise ResamplingError("selected_kpis must be a non-empty tuple")
        seen: set[str] = set()
        for kpi in self.selected_kpis:
            if not isinstance(kpi, str):
                raise ResamplingError("selected_kpis entries must be strings")
            if kpi not in _SUPPORTED_KPIS:
                raise ResamplingError(
                    f"Unsupported KPI {kpi!r}. Valid: {sorted(_SUPPORTED_KPIS)}"
                )
            if kpi in seen:
                raise ResamplingError(f"Duplicate KPI in selected_kpis: {kpi!r}")
            seen.add(kpi)

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "sample_count": self.sample_count,
            "sample_block_count": self.sample_block_count,
            "seed": self.seed,
            "selected_kpis": list(self.selected_kpis),
        }


@dataclass(frozen=True, slots=True)
class ReplayKPIBlock:
    """A single replay-backed KPI block for deterministic resampling."""

    block_id: str
    source_run_id: str
    dataset_fingerprint: str
    execution_provenance_id: str
    signal_count: int
    fill_count: int
    reject_count: int
    pnl_sum: Decimal

    def __post_init__(self) -> None:
        _require_non_empty_string(self.block_id, "block_id")
        if not _RUN_ID_RE.match(self.source_run_id):
            raise ResamplingError(
                "source_run_id must match 'replay-<12 hex>-<4 digit attempt>'"
            )
        if not _HEX_64_RE.match(self.dataset_fingerprint):
            raise ResamplingError("dataset_fingerprint must be a 64-char lowercase hex hash")
        if not _EXECUTION_PROVENANCE_ID_RE.match(self.execution_provenance_id):
            raise ResamplingError(
                "execution_provenance_id must match 'bt-<16 hex>'"
            )
        _require_non_negative_int(self.signal_count, "signal_count")
        _require_non_negative_int(self.fill_count, "fill_count")
        _require_non_negative_int(self.reject_count, "reject_count")
        if not isinstance(self.pnl_sum, Decimal):
            raise ResamplingError("pnl_sum must be a Decimal")

    def to_dict(self) -> dict[str, object]:
        return {
            "block_id": self.block_id,
            "source_run_id": self.source_run_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "execution_provenance_id": self.execution_provenance_id,
            "signal_count": self.signal_count,
            "fill_count": self.fill_count,
            "reject_count": self.reject_count,
            "pnl_sum": str(self.pnl_sum),
        }


@dataclass(frozen=True, slots=True)
class ResamplingSourceProvenance:
    """Pinned provenance for a stability artifact."""

    source_run_id: str
    run_count: int
    block_count: int
    dataset_fingerprint: str
    execution_provenance_id: str
    input_fingerprint: str

    def __post_init__(self) -> None:
        if not _RUN_ID_RE.match(self.source_run_id):
            raise ResamplingError(
                "source_run_id must match 'replay-<12 hex>-<4 digit attempt>'"
            )
        _require_positive_int(self.run_count, "run_count")
        _require_positive_int(self.block_count, "block_count")
        if not _HEX_64_RE.match(self.dataset_fingerprint):
            raise ResamplingError("dataset_fingerprint must be a 64-char lowercase hex hash")
        if not _EXECUTION_PROVENANCE_ID_RE.match(self.execution_provenance_id):
            raise ResamplingError(
                "execution_provenance_id must match 'bt-<16 hex>'"
            )
        if not _HEX_64_RE.match(self.input_fingerprint):
            raise ResamplingError("input_fingerprint must be a 64-char lowercase hex hash")

    def to_dict(self) -> dict[str, object]:
        return {
            "source_run_id": self.source_run_id,
            "run_count": self.run_count,
            "block_count": self.block_count,
            "dataset_fingerprint": self.dataset_fingerprint,
            "execution_provenance_id": self.execution_provenance_id,
            "input_fingerprint": self.input_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ResamplingKPISummary:
    """Empirical quantile summary for one selected KPI."""

    kpi: str
    sample_count: int
    baseline: str
    minimum: str
    p05: str
    p50: str
    p95: str
    maximum: str
    empirical_span: str

    def __post_init__(self) -> None:
        if self.kpi not in _SUPPORTED_KPIS:
            raise ResamplingError(
                f"Unsupported KPI summary {self.kpi!r}. Valid: {sorted(_SUPPORTED_KPIS)}"
            )
        _require_positive_int(self.sample_count, "sample_count")
        for field_name in ("baseline", "minimum", "p05", "p50", "p95", "maximum", "empirical_span"):
            _require_non_empty_string(getattr(self, field_name), field_name)

    def to_dict(self) -> dict[str, object]:
        return {
            "kpi": self.kpi,
            "sample_count": self.sample_count,
            "baseline": self.baseline,
            "minimum": self.minimum,
            "p05": self.p05,
            "p50": self.p50,
            "p95": self.p95,
            "maximum": self.maximum,
            "empirical_span": self.empirical_span,
        }


@dataclass(frozen=True, slots=True)
class ResamplingStabilityArtifact:
    """Deterministic machine-readable replay stability artifact."""

    schema_version: str
    resampling_method: str
    sample_count: int
    sample_block_count: int
    config: ResamplingConfig
    config_fingerprint: str
    source_provenance: ResamplingSourceProvenance
    baseline_metrics: dict[str, str]
    kpi_summaries: tuple[ResamplingKPISummary, ...]
    operator_summary: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "replay_resampling_stability.v1":
            raise ResamplingError("schema_version must be 'replay_resampling_stability.v1'")
        if self.resampling_method not in _SUPPORTED_METHODS:
            raise ResamplingError(
                f"Unsupported resampling_method {self.resampling_method!r}. "
                f"Valid: {sorted(_SUPPORTED_METHODS)}"
            )
        _require_positive_int(self.sample_count, "sample_count")
        _require_positive_int(self.sample_block_count, "sample_block_count")
        if self.resampling_method != self.config.method:
            raise ResamplingError("resampling_method must match config.method")
        if self.sample_count != self.config.sample_count:
            raise ResamplingError("sample_count must match config.sample_count")
        if self.sample_block_count != self.config.sample_block_count:
            raise ResamplingError("sample_block_count must match config.sample_block_count")
        if not _HEX_64_RE.match(self.config_fingerprint):
            raise ResamplingError("config_fingerprint must be a 64-char lowercase hex hash")
        if not isinstance(self.baseline_metrics, dict):
            raise ResamplingError("baseline_metrics must be a dict")
        if tuple(self.baseline_metrics.keys()) != self.config.selected_kpis:
            raise ResamplingError("baseline_metrics keys must match config.selected_kpis order")
        if len(self.kpi_summaries) != len(self.config.selected_kpis):
            raise ResamplingError("kpi_summaries must align with config.selected_kpis")
        summary_keys = tuple(summary.kpi for summary in self.kpi_summaries)
        if summary_keys != self.config.selected_kpis:
            raise ResamplingError("kpi_summaries must follow config.selected_kpis order")
        if not isinstance(self.operator_summary, tuple) or not self.operator_summary:
            raise ResamplingError("operator_summary must be a non-empty tuple")
        for line in self.operator_summary:
            _require_non_empty_string(line, "operator_summary entry")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "resampling_method": self.resampling_method,
            "sample_count": self.sample_count,
            "sample_block_count": self.sample_block_count,
            "config": self.config.to_dict(),
            "config_fingerprint": self.config_fingerprint,
            "source_provenance": self.source_provenance.to_dict(),
            "baseline_metrics": self.baseline_metrics,
            "kpi_summaries": [summary.to_dict() for summary in self.kpi_summaries],
            "operator_summary": list(self.operator_summary),
        }


def compute_resampling_stability(
    blocks: Sequence[ReplayKPIBlock],
    *,
    config: ResamplingConfig,
) -> ResamplingStabilityArtifact:
    """Compute deterministic block-bootstrap stability summaries.

    The minimal slice intentionally supports only a single explicit method:
    ``block_bootstrap`` over caller-supplied ReplayKPIBlock records.
    """
    if not isinstance(config, ResamplingConfig):
        raise ResamplingError(
            f"config must be ResamplingConfig, got {type(config).__name__}"
        )

    blocks_list = list(blocks)
    if not blocks_list:
        raise ResamplingError("blocks must not be empty")
    for index, block in enumerate(blocks_list):
        if not isinstance(block, ReplayKPIBlock):
            raise ResamplingError(
                f"blocks[{index}] must be ReplayKPIBlock, got {type(block).__name__}"
            )

    _validate_uniform_provenance(blocks_list)
    if config.sample_block_count != len(blocks_list):
        raise ResamplingError(
            "sample_block_count must equal len(blocks) for block_bootstrap in this slice"
        )
    baseline_metrics = _aggregate_blocks(blocks_list)
    config_fingerprint = canonical_hash(config.to_dict())
    input_fingerprint = _input_fingerprint(blocks_list)

    source_provenance = ResamplingSourceProvenance(
        source_run_id=blocks_list[0].source_run_id,
        run_count=1,
        block_count=len(blocks_list),
        dataset_fingerprint=blocks_list[0].dataset_fingerprint,
        execution_provenance_id=blocks_list[0].execution_provenance_id,
        input_fingerprint=input_fingerprint,
    )

    rng = SeedManager(config.seed)
    sample_values: dict[str, list[int | Decimal]] = {
        kpi: [] for kpi in config.selected_kpis
    }
    for _ in range(config.sample_count):
        sampled_blocks = [
            blocks_list[rng.random_int(0, len(blocks_list) - 1)]
            for _ in range(config.sample_block_count)
        ]
        aggregate = _aggregate_blocks(sampled_blocks)
        for kpi in config.selected_kpis:
            sample_values[kpi].append(aggregate[kpi])

    summaries: list[ResamplingKPISummary] = []
    serialized_baseline: dict[str, str] = {}
    for kpi in config.selected_kpis:
        values = sorted(sample_values[kpi])
        baseline = baseline_metrics[kpi]
        minimum = values[0]
        maximum = values[-1]
        p05 = _quantile(values, numerator=5, denominator=100)
        p50 = _quantile(values, numerator=50, denominator=100)
        p95 = _quantile(values, numerator=95, denominator=100)
        span = _subtract_metric(kpi, maximum, minimum)

        serialized_baseline[kpi] = _serialize_metric(kpi, baseline)
        summaries.append(
            ResamplingKPISummary(
                kpi=kpi,
                sample_count=config.sample_count,
                baseline=_serialize_metric(kpi, baseline),
                minimum=_serialize_metric(kpi, minimum),
                p05=_serialize_metric(kpi, p05),
                p50=_serialize_metric(kpi, p50),
                p95=_serialize_metric(kpi, p95),
                maximum=_serialize_metric(kpi, maximum),
                empirical_span=_serialize_metric(kpi, span),
            )
        )

    return ResamplingStabilityArtifact(
        schema_version="replay_resampling_stability.v1",
        resampling_method=config.method,
        sample_count=config.sample_count,
        sample_block_count=config.sample_block_count,
        config=config,
        config_fingerprint=config_fingerprint,
        source_provenance=source_provenance,
        baseline_metrics=serialized_baseline,
        kpi_summaries=tuple(summaries),
        operator_summary=_build_operator_summary(config=config, summaries=summaries),
    )


def write_resampling_stability_artifact(
    artifact: ResamplingStabilityArtifact,
    artifact_root: str | pathlib.Path,
) -> None:
    """Write ``resampling_stability.json`` into artifact_root."""
    if not isinstance(artifact, ResamplingStabilityArtifact):
        raise ResamplingError(
            f"artifact must be ResamplingStabilityArtifact, got {type(artifact).__name__}"
        )

    out_dir = pathlib.Path(artifact_root)
    artifact_path = out_dir / _STABILITY_ARTIFACT_FILENAME
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            canonical_json_dumps(artifact.to_dict()),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ResamplingError(
            f"Failed to write {_STABILITY_ARTIFACT_FILENAME} to {artifact_path}: {exc}"
        ) from exc
