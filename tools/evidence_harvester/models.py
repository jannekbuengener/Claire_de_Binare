from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timezone
from typing import Any, Mapping, Sequence

from core.utils.evidence_class import is_valid_evidence_class


class CollectorValidationError(ValueError):
    pass


def _coalesce(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _parse_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or value is None:
        raise CollectorValidationError(f"{field_name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise CollectorValidationError(f"{field_name} must be an integer") from exc
    if parsed < 0:
        raise CollectorValidationError(f"{field_name} must be non-negative")
    return parsed


def _parse_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or value is None:
        raise CollectorValidationError(f"{field_name} must be a number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise CollectorValidationError(f"{field_name} must be a number") from exc
    if parsed < 0:
        raise CollectorValidationError(f"{field_name} must be non-negative")
    return parsed


def _parse_ts(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        parsed = datetime.fromtimestamp(float(value) / 1000.0, tz=UTC)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise CollectorValidationError(f"{field_name} must not be blank")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise CollectorValidationError(
                f"{field_name} must be an ISO-8601 UTC timestamp"
            ) from exc
    else:
        raise CollectorValidationError(
            f"{field_name} must be an ISO-8601 UTC timestamp"
        )

    if parsed.tzinfo is None:
        raise CollectorValidationError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(UTC)


def _format_ts(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sorted_source_tuple(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({value.strip() for value in values if value and value.strip()}))


@dataclass(frozen=True, slots=True)
class CandleCoverageInput:
    symbol: str
    venue: str
    timeframe: str
    first_ts_utc: datetime
    last_ts_utc: datetime
    observed_count: int
    expected_count: int

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CandleCoverageInput":
        symbol = str(_coalesce(mapping, "symbol", "instrument")).strip()
        venue = str(_coalesce(mapping, "venue", "source", "source_ref")).strip()
        timeframe = str(_coalesce(mapping, "timeframe", "interval")).strip()
        if not symbol:
            raise CollectorValidationError("candle symbol must not be blank")
        if not venue:
            raise CollectorValidationError("candle venue/source must not be blank")
        if not timeframe:
            raise CollectorValidationError("candle timeframe must not be blank")

        first_ts_utc = _parse_ts(
            _coalesce(mapping, "first_ts_utc", "first_ts", "start_ts_utc", "start_ts"),
            "first_ts_utc",
        )
        last_ts_utc = _parse_ts(
            _coalesce(mapping, "last_ts_utc", "last_ts", "end_ts_utc", "end_ts"),
            "last_ts_utc",
        )
        if last_ts_utc < first_ts_utc:
            raise CollectorValidationError("candle last_ts_utc must be >= first_ts_utc")

        observed_count = _parse_int(
            _coalesce(mapping, "observed_count", "count"), "observed_count"
        )
        expected_count = _parse_int(
            _coalesce(mapping, "expected_count", "expected"), "expected_count"
        )
        if expected_count == 0:
            raise CollectorValidationError("expected_count must be > 0")
        if observed_count > expected_count:
            raise CollectorValidationError(
                "observed_count cannot exceed expected_count"
            )

        return cls(
            symbol=symbol,
            venue=venue,
            timeframe=timeframe,
            first_ts_utc=first_ts_utc,
            last_ts_utc=last_ts_utc,
            observed_count=observed_count,
            expected_count=expected_count,
        )


@dataclass(frozen=True, slots=True)
class RegimeCoverageInput:
    symbol: str
    venue: str
    timeframe: str
    first_ts_utc: datetime
    last_ts_utc: datetime
    observed_count: int
    expected_count: int
    regime_distribution: tuple[tuple[str, int], ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "RegimeCoverageInput":
        symbol = str(_coalesce(mapping, "symbol", "instrument")).strip()
        venue = str(_coalesce(mapping, "venue", "source", "source_ref")).strip()
        timeframe = str(_coalesce(mapping, "timeframe", "interval")).strip()
        if not symbol:
            raise CollectorValidationError("regime symbol must not be blank")
        if not venue:
            raise CollectorValidationError("regime venue/source must not be blank")
        if not timeframe:
            raise CollectorValidationError("regime timeframe must not be blank")

        first_ts_utc = _parse_ts(
            _coalesce(mapping, "first_ts_utc", "first_ts", "start_ts_utc", "start_ts"),
            "first_ts_utc",
        )
        last_ts_utc = _parse_ts(
            _coalesce(mapping, "last_ts_utc", "last_ts", "end_ts_utc", "end_ts"),
            "last_ts_utc",
        )
        if last_ts_utc < first_ts_utc:
            raise CollectorValidationError("regime last_ts_utc must be >= first_ts_utc")

        observed_count = _parse_int(
            _coalesce(mapping, "observed_count", "count"), "observed_count"
        )
        expected_count = _parse_int(
            _coalesce(mapping, "expected_count", "expected"), "expected_count"
        )
        if expected_count == 0:
            raise CollectorValidationError("expected_count must be > 0")
        if observed_count > expected_count:
            raise CollectorValidationError(
                "observed_count cannot exceed expected_count"
            )

        dist_raw = (
            _coalesce(mapping, "regime_distribution", "distribution", "regimes") or {}
        )
        if not isinstance(dist_raw, Mapping):
            raise CollectorValidationError("regime_distribution must be a mapping")
        distribution: list[tuple[str, int]] = []
        for regime, count in sorted(dist_raw.items(), key=lambda item: str(item[0])):
            regime_name = str(regime).strip()
            if not regime_name:
                raise CollectorValidationError("regime names must not be blank")
            regime_count = _parse_int(count, f"regime_distribution[{regime_name}]")
            distribution.append((regime_name, regime_count))

        if sum(count for _, count in distribution) != observed_count:
            raise CollectorValidationError(
                "regime_distribution counts must sum to observed_count"
            )

        return cls(
            symbol=symbol,
            venue=venue,
            timeframe=timeframe,
            first_ts_utc=first_ts_utc,
            last_ts_utc=last_ts_utc,
            observed_count=observed_count,
            expected_count=expected_count,
            regime_distribution=tuple(distribution),
        )


@dataclass(frozen=True, slots=True)
class PaperChainCoverageInput:
    symbol: str
    venue: str
    timeframe: str
    observation_window_hours: float
    signal_count: int
    decision_count: int
    order_count: int
    fill_count: int
    complete_chain_count: int
    partial_chain_count: int

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "PaperChainCoverageInput":
        symbol = str(_coalesce(mapping, "symbol", "instrument")).strip()
        venue = str(_coalesce(mapping, "venue", "source", "source_ref")).strip()
        timeframe = str(_coalesce(mapping, "timeframe", "interval")).strip()
        if not symbol:
            raise CollectorValidationError("paper chain symbol must not be blank")
        if not venue:
            raise CollectorValidationError("paper chain venue/source must not be blank")
        if not timeframe:
            raise CollectorValidationError("paper chain timeframe must not be blank")

        observation_window_hours = _parse_float(
            _coalesce(mapping, "observation_window_hours", "window_hours", "hours"),
            "observation_window_hours",
        )
        if observation_window_hours <= 0:
            raise CollectorValidationError("observation_window_hours must be > 0")

        signal_count = _parse_int(
            _coalesce(mapping, "signal_count", "signals"), "signal_count"
        )
        decision_count = _parse_int(
            _coalesce(mapping, "decision_count", "decisions"), "decision_count"
        )
        order_count = _parse_int(
            _coalesce(mapping, "order_count", "orders"), "order_count"
        )
        fill_count = _parse_int(_coalesce(mapping, "fill_count", "fills"), "fill_count")
        complete_chain_count = _parse_int(
            _coalesce(mapping, "complete_chain_count", "complete_chains"),
            "complete_chain_count",
        )
        partial_chain_count = _parse_int(
            _coalesce(mapping, "partial_chain_count", "partial_chains"),
            "partial_chain_count",
        )

        return cls(
            symbol=symbol,
            venue=venue,
            timeframe=timeframe,
            observation_window_hours=observation_window_hours,
            signal_count=signal_count,
            decision_count=decision_count,
            order_count=order_count,
            fill_count=fill_count,
            complete_chain_count=complete_chain_count,
            partial_chain_count=partial_chain_count,
        )


@dataclass(frozen=True, slots=True)
class ProvenanceObservationInput:
    source: str
    observed_count: int
    contaminated: bool = False

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ProvenanceObservationInput":
        source = str(_coalesce(mapping, "source", "source_ref", "venue")).strip()
        if not source:
            raise CollectorValidationError("provenance source must not be blank")
        observed_count = _parse_int(
            _coalesce(mapping, "observed_count", "count"), "observed_count"
        )
        contaminated = bool(
            _coalesce(mapping, "contaminated", "is_contaminated") or False
        )
        return cls(
            source=source, observed_count=observed_count, contaminated=contaminated
        )


@dataclass(frozen=True, slots=True)
class CollectorInput:
    produced_by: str
    produced_at_utc: datetime
    evidence_class: str = "pipeline_test_evidence"
    evidence_class_version: str = "1.0"
    source_mode: str = "fixture"
    allowed_provenance_sources: tuple[str, ...] = field(default_factory=tuple)
    stale_after_minutes: int = 120
    candle_coverages: tuple[CandleCoverageInput, ...] = field(default_factory=tuple)
    regime_coverages: tuple[RegimeCoverageInput, ...] = field(default_factory=tuple)
    paper_chain_coverages: tuple[PaperChainCoverageInput, ...] = field(
        default_factory=tuple
    )
    provenance_observations: tuple[ProvenanceObservationInput, ...] = field(
        default_factory=tuple
    )

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CollectorInput":
        artifact = dict(mapping)
        evidence_class = str(artifact.get("evidence_class") or "").strip()
        if not evidence_class:
            raise CollectorValidationError("missing evidence_class")
        if not is_valid_evidence_class(evidence_class):
            raise CollectorValidationError(f"unknown evidence_class={evidence_class!r}")

        produced_by = str(
            _coalesce(mapping, "produced_by", "runner", "collector_id")
        ).strip()
        if not produced_by:
            raise CollectorValidationError("produced_by must not be blank")
        produced_at_utc = _parse_ts(
            _coalesce(mapping, "produced_at_utc", "captured_at_utc", "generated_at"),
            "produced_at_utc",
        )
        source_mode = str(
            _coalesce(mapping, "source_mode", "mode") or "fixture"
        ).strip()
        allowed_sources_raw = (
            _coalesce(mapping, "allowed_provenance_sources", "allowed_sources") or []
        )
        if not isinstance(allowed_sources_raw, Sequence) or isinstance(
            allowed_sources_raw, (str, bytes)
        ):
            raise CollectorValidationError(
                "allowed_provenance_sources must be a sequence"
            )
        allowed_provenance_sources = _sorted_source_tuple(
            [str(item) for item in allowed_sources_raw]
        )

        stale_after_minutes = _parse_int(
            _coalesce(mapping, "stale_after_minutes", "max_age_minutes") or 120,
            "stale_after_minutes",
        )
        if stale_after_minutes <= 0:
            raise CollectorValidationError("stale_after_minutes must be > 0")

        def _load_rows(key: str, row_type: type[Any]) -> tuple[Any, ...]:
            raw_rows = _coalesce(mapping, key) or []
            if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
                raise CollectorValidationError(f"{key} must be a sequence")
            return tuple(row_type.from_mapping(row) for row in raw_rows)

        return cls(
            produced_by=produced_by,
            produced_at_utc=produced_at_utc,
            evidence_class=evidence_class,
            evidence_class_version=str(
                _coalesce(mapping, "evidence_class_version") or "1.0"
            ),
            source_mode=source_mode,
            allowed_provenance_sources=allowed_provenance_sources,
            stale_after_minutes=stale_after_minutes,
            candle_coverages=_load_rows("candle_coverages", CandleCoverageInput),
            regime_coverages=_load_rows("regime_coverages", RegimeCoverageInput),
            paper_chain_coverages=_load_rows(
                "paper_chain_coverages", PaperChainCoverageInput
            ),
            provenance_observations=_load_rows(
                "provenance_observations", ProvenanceObservationInput
            ),
        )

    def canonical_payload(self) -> dict[str, Any]:
        candle_coverages = []
        for item in self.candle_coverages:
            candle_coverages.append(
                {
                    "symbol": item.symbol,
                    "venue": item.venue,
                    "timeframe": item.timeframe,
                    "first_ts_utc": _format_ts(item.first_ts_utc),
                    "last_ts_utc": _format_ts(item.last_ts_utc),
                    "observed_count": item.observed_count,
                    "expected_count": item.expected_count,
                }
            )

        regime_coverages = []
        for item in self.regime_coverages:
            regime_coverages.append(
                {
                    "symbol": item.symbol,
                    "venue": item.venue,
                    "timeframe": item.timeframe,
                    "first_ts_utc": _format_ts(item.first_ts_utc),
                    "last_ts_utc": _format_ts(item.last_ts_utc),
                    "observed_count": item.observed_count,
                    "expected_count": item.expected_count,
                    "regime_distribution": {
                        regime: count for regime, count in item.regime_distribution
                    },
                }
            )

        paper_chain_coverages = []
        for item in self.paper_chain_coverages:
            paper_chain_coverages.append(
                {
                    "symbol": item.symbol,
                    "venue": item.venue,
                    "timeframe": item.timeframe,
                    "observation_window_hours": item.observation_window_hours,
                    "signal_count": item.signal_count,
                    "decision_count": item.decision_count,
                    "order_count": item.order_count,
                    "fill_count": item.fill_count,
                    "complete_chain_count": item.complete_chain_count,
                    "partial_chain_count": item.partial_chain_count,
                }
            )

        provenance_observations = []
        for item in self.provenance_observations:
            provenance_observations.append(
                {
                    "source": item.source,
                    "observed_count": item.observed_count,
                    "contaminated": item.contaminated,
                }
            )

        return {
            "allowed_provenance_sources": list(self.allowed_provenance_sources),
            "candle_coverages": candle_coverages,
            "evidence_class": self.evidence_class,
            "evidence_class_version": self.evidence_class_version,
            "paper_chain_coverages": paper_chain_coverages,
            "produced_at_utc": _format_ts(self.produced_at_utc),
            "produced_by": self.produced_by,
            "provenance_observations": provenance_observations,
            "regime_coverages": regime_coverages,
            "source_mode": self.source_mode,
            "stale_after_minutes": self.stale_after_minutes,
        }


@dataclass(frozen=True, slots=True)
class CoverageFinding:
    symbol: str
    venue: str
    timeframe: str
    status: str
    first_ts_utc: str
    last_ts_utc: str
    observed_count: int
    expected_count: int
    missing_count: int
    coverage_pct: float
    stale_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class RegimeDistributionItem:
    regime: str
    count: int
    share: float


@dataclass(frozen=True, slots=True)
class RegimeCoverageFinding:
    symbol: str
    venue: str
    timeframe: str
    status: str
    first_ts_utc: str
    last_ts_utc: str
    observed_count: int
    expected_count: int
    missing_count: int
    coverage_pct: float
    stale_minutes: int | None
    regime_distribution: tuple[RegimeDistributionItem, ...]


@dataclass(frozen=True, slots=True)
class PaperChainFinding:
    symbol: str
    venue: str
    timeframe: str
    status: str
    observation_window_hours: float
    signal_count: int
    decision_count: int
    order_count: int
    fill_count: int
    complete_chain_count: int
    partial_chain_count: int
    signal_density_per_hour: float


@dataclass(frozen=True, slots=True)
class ProvenanceSourceFinding:
    source: str
    observed_count: int
    status: str


@dataclass(frozen=True, slots=True)
class ProvenanceSummary:
    allowed_sources: tuple[str, ...]
    source_findings: tuple[ProvenanceSourceFinding, ...]
    unknown_source_count: int
    contaminated_source_count: int


@dataclass(frozen=True, slots=True)
class GapFinding:
    gap_id: str
    gap_type: str
    severity: str
    message: str
    scope: str
    source_refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RawEvidenceSummary:
    candle_input_count: int
    regime_input_count: int
    paper_chain_input_count: int
    provenance_input_count: int
    observed_input_count: int


@dataclass(frozen=True, slots=True)
class CollectorSummary:
    overall_status: str
    blocking_count: int
    warning_count: int
    info_count: int
    has_zero_paper_chains: bool


@dataclass(frozen=True, slots=True)
class CollectorReport:
    schema_version: str
    report_id: str
    evidence_class: str
    evidence_class_version: str
    produced_by: str
    produced_at_utc: str
    source_mode: str
    raw_evidence: RawEvidenceSummary
    candle_coverages: tuple[CoverageFinding, ...]
    regime_coverages: tuple[RegimeCoverageFinding, ...]
    paper_chain_coverages: tuple[PaperChainFinding, ...]
    provenance: ProvenanceSummary
    gap_findings: tuple[GapFinding, ...]
    summary: CollectorSummary

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
