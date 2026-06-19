from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from core.utils.evidence_class import is_valid_evidence_class

from .models import (
    CandleCoverageInput,
    CollectorInput,
    CollectorReport,
    CollectorSummary,
    CollectorValidationError,
    CoverageFinding,
    GapFinding,
    PaperChainFinding,
    ProvenanceSourceFinding,
    ProvenanceSummary,
    RawEvidenceSummary,
    RegimeCoverageFinding,
    RegimeDistributionItem,
    _format_ts,
    _parse_ts,
)


def _severity_rank(value: str) -> int:
    return {"blocking": 0, "warning": 1, "info": 2}.get(value, 99)


def _status_for_missing(observed_count: int, expected_count: int, stale_minutes: int | None = None) -> str:
    if stale_minutes is not None and stale_minutes >= 0:
        return "blocking" if stale_minutes > 0 else "warning"
    if observed_count == 0:
        return "blocking"
    if observed_count < expected_count:
        return "warning"
    return "info"


def _format_gap_type(symbol: str, venue: str, timeframe: str) -> str:
    return f"{symbol}:{venue}:{timeframe}"


def _hash_payload(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_collector_input(path: str | Path) -> CollectorInput:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CollectorValidationError("Collector input JSON root must be an object")
    return CollectorInput.from_mapping(payload)


class EvidenceHarvesterCollector:
    def __init__(self, stale_after_minutes: int = 120) -> None:
        if stale_after_minutes <= 0:
            raise CollectorValidationError("stale_after_minutes must be > 0")
        self.stale_after_minutes = stale_after_minutes

    def collect(self, collector_input: CollectorInput) -> CollectorReport:
        if not is_valid_evidence_class(collector_input.evidence_class):
            raise CollectorValidationError(
                f"unknown evidence_class={collector_input.evidence_class!r}"
            )

        canonical_payload = collector_input.canonical_payload()
        report_id = f"harv-{_hash_payload(canonical_payload)[:12]}"
        produced_at_utc = _format_ts(collector_input.produced_at_utc)

        candle_coverages = tuple(
            sorted(
                (self._build_candle_coverage(item, collector_input.produced_at_utc) for item in collector_input.candle_coverages),
                key=lambda item: (item.symbol, item.venue, item.timeframe, item.first_ts_utc),
            )
        )
        regime_coverages = tuple(
            sorted(
                (self._build_regime_coverage(item, collector_input.produced_at_utc) for item in collector_input.regime_coverages),
                key=lambda item: (item.symbol, item.venue, item.timeframe, item.first_ts_utc),
            )
        )
        paper_chain_coverages = tuple(
            sorted(
                (self._build_paper_chain_finding(item) for item in collector_input.paper_chain_coverages),
                key=lambda item: (item.symbol, item.venue, item.timeframe),
            )
        )
        provenance = self._build_provenance_summary(
            collector_input.allowed_provenance_sources,
            collector_input.provenance_observations,
        )
        gap_findings = self._build_gap_findings(
            candle_coverages,
            regime_coverages,
            paper_chain_coverages,
            provenance,
        )
        summary = self._build_summary(gap_findings)

        return CollectorReport(
            schema_version="evidence_harvester.collector_report.v1",
            report_id=report_id,
            evidence_class=collector_input.evidence_class,
            evidence_class_version=collector_input.evidence_class_version,
            produced_by=collector_input.produced_by,
            produced_at_utc=produced_at_utc,
            source_mode=collector_input.source_mode,
            raw_evidence=RawEvidenceSummary(
                candle_input_count=len(collector_input.candle_coverages),
                regime_input_count=len(collector_input.regime_coverages),
                paper_chain_input_count=len(collector_input.paper_chain_coverages),
                provenance_input_count=len(collector_input.provenance_observations),
                observed_input_count=len(collector_input.candle_coverages)
                + len(collector_input.regime_coverages)
                + len(collector_input.paper_chain_coverages)
                + len(collector_input.provenance_observations),
            ),
            candle_coverages=candle_coverages,
            regime_coverages=regime_coverages,
            paper_chain_coverages=paper_chain_coverages,
            provenance=provenance,
            gap_findings=gap_findings,
            summary=summary,
        )

    def _build_candle_coverage(self, item: CandleCoverageInput, captured_at_utc: datetime) -> CoverageFinding:
        missing = item.expected_count - item.observed_count
        coverage = round(item.observed_count / item.expected_count, 6)
        stale_minutes = int((captured_at_utc - item.last_ts_utc).total_seconds() // 60)
        if stale_minutes < 0:
            raise CollectorValidationError("last_ts_utc cannot be in the future relative to produced_at_utc")
        status = "info"
        if stale_minutes > self.stale_after_minutes:
            status = "blocking"
        elif missing > 0:
            status = "warning"
        return CoverageFinding(
            symbol=item.symbol,
            venue=item.venue,
            timeframe=item.timeframe,
            status=status,
            first_ts_utc=_format_ts(item.first_ts_utc),
            last_ts_utc=_format_ts(item.last_ts_utc),
            observed_count=item.observed_count,
            expected_count=item.expected_count,
            missing_count=missing,
            coverage_pct=coverage,
            stale_minutes=stale_minutes,
        )

    def _build_regime_coverage(
        self, item: Any, captured_at_utc: datetime
    ) -> RegimeCoverageFinding:
        missing = item.expected_count - item.observed_count
        coverage = round(item.observed_count / item.expected_count, 6)
        stale_minutes = int((captured_at_utc - item.last_ts_utc).total_seconds() // 60)
        if stale_minutes < 0:
            raise CollectorValidationError("last_ts_utc cannot be in the future relative to produced_at_utc")
        status = "info"
        if item.observed_count == 0:
            status = "blocking"
        elif stale_minutes > self.stale_after_minutes:
            status = "blocking"
        elif missing > 0:
            status = "warning"
        total = sum(count for _, count in item.regime_distribution) or 1
        distribution = tuple(
            RegimeDistributionItem(
                regime=regime,
                count=count,
                share=round(count / total, 6),
            )
            for regime, count in item.regime_distribution
        )
        return RegimeCoverageFinding(
            symbol=item.symbol,
            venue=item.venue,
            timeframe=item.timeframe,
            status=status,
            first_ts_utc=_format_ts(item.first_ts_utc),
            last_ts_utc=_format_ts(item.last_ts_utc),
            observed_count=item.observed_count,
            expected_count=item.expected_count,
            missing_count=missing,
            coverage_pct=coverage,
            stale_minutes=stale_minutes,
            regime_distribution=distribution,
        )

    def _build_paper_chain_finding(self, item: Any) -> PaperChainFinding:
        signal_density = round(item.signal_count / item.observation_window_hours, 6)
        status = "info"
        if item.complete_chain_count == 0:
            status = "blocking"
        elif item.partial_chain_count > 0:
            status = "warning"
        elif item.signal_count == 0:
            status = "blocking"
        return PaperChainFinding(
            symbol=item.symbol,
            venue=item.venue,
            timeframe=item.timeframe,
            status=status,
            observation_window_hours=item.observation_window_hours,
            signal_count=item.signal_count,
            decision_count=item.decision_count,
            order_count=item.order_count,
            fill_count=item.fill_count,
            complete_chain_count=item.complete_chain_count,
            partial_chain_count=item.partial_chain_count,
            signal_density_per_hour=signal_density,
        )

    def _build_provenance_summary(
        self,
        allowed_sources: tuple[str, ...],
        observations: tuple[Any, ...],
    ) -> ProvenanceSummary:
        allowed = set(allowed_sources)
        source_findings: list[ProvenanceSourceFinding] = []
        unknown_count = 0
        contaminated_count = 0

        for item in sorted(observations, key=lambda row: row.source):
            if item.source in allowed:
                status = "allowed"
            else:
                status = "unknown"
                unknown_count += item.observed_count
            if item.contaminated:
                status = "contaminated"
                contaminated_count += item.observed_count
            source_findings.append(
                ProvenanceSourceFinding(
                    source=item.source,
                    observed_count=item.observed_count,
                    status=status,
                )
            )

        return ProvenanceSummary(
            allowed_sources=allowed_sources,
            source_findings=tuple(source_findings),
            unknown_source_count=unknown_count,
            contaminated_source_count=contaminated_count,
        )

    def _build_gap_findings(
        self,
        candle_coverages: tuple[CoverageFinding, ...],
        regime_coverages: tuple[RegimeCoverageFinding, ...],
        paper_chain_coverages: tuple[PaperChainFinding, ...],
        provenance: ProvenanceSummary,
    ) -> tuple[GapFinding, ...]:
        findings: list[GapFinding] = []
        gap_index = 1

        for item in candle_coverages:
            if item.stale_minutes is not None and item.stale_minutes > self.stale_after_minutes:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="stale_feed",
                        severity="blocking",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} is stale by {item.stale_minutes} minutes"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1
            if item.missing_count > 0:
                severity = "blocking" if item.coverage_pct == 0.0 else "warning"
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="missing_candles",
                        severity=severity,
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} missing {item.missing_count} candles"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1

        for item in regime_coverages:
            if item.stale_minutes is not None and item.stale_minutes > self.stale_after_minutes:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="stale_regime",
                        severity="blocking",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} regime data is stale by {item.stale_minutes} minutes"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1
            if item.observed_count == 0:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="missing_regime",
                        severity="blocking",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} has no regime coverage"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1
            elif item.missing_count > 0:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="missing_regime",
                        severity="warning",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} missing {item.missing_count} regime rows"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1

        for item in paper_chain_coverages:
            if item.complete_chain_count == 0:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="zero_paper_chains",
                        severity="blocking",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} has zero complete paper chains"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1
            if item.signal_count == 0:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="missing_signal_density",
                        severity="blocking",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} has zero signal density"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1
            elif item.partial_chain_count > 0:
                findings.append(
                    GapFinding(
                        gap_id=f"gap-{gap_index:03d}",
                        gap_type="partial_paper_chains",
                        severity="warning",
                        message=(
                            f"{item.symbol}/{item.venue}/{item.timeframe} has {item.partial_chain_count} partial chains"
                        ),
                        scope=_format_gap_type(item.symbol, item.venue, item.timeframe),
                        source_refs=(item.venue,),
                    )
                )
                gap_index += 1

        if provenance.unknown_source_count > 0:
            findings.append(
                GapFinding(
                    gap_id=f"gap-{gap_index:03d}",
                    gap_type="provenance_contamination",
                    severity="blocking",
                    message=f"{provenance.unknown_source_count} observations came from unknown sources",
                    scope="provenance",
                    source_refs=tuple(source.source for source in provenance.source_findings if source.status == "unknown"),
                )
            )
            gap_index += 1

        if provenance.contaminated_source_count > 0:
            findings.append(
                GapFinding(
                    gap_id=f"gap-{gap_index:03d}",
                    gap_type="provenance_contamination",
                    severity="blocking",
                    message=f"{provenance.contaminated_source_count} observations were marked contaminated",
                    scope="provenance",
                    source_refs=tuple(source.source for source in provenance.source_findings if source.status == "contaminated"),
                )
            )
            gap_index += 1

        return tuple(sorted(findings, key=lambda item: (_severity_rank(item.severity), item.gap_type, item.scope)))

    def _build_summary(self, gap_findings: tuple[GapFinding, ...]) -> CollectorSummary:
        blocking = sum(1 for gap in gap_findings if gap.severity == "blocking")
        warning = sum(1 for gap in gap_findings if gap.severity == "warning")
        info = sum(1 for gap in gap_findings if gap.severity == "info")
        if blocking:
            status = "blocked"
        elif warning:
            status = "warning"
        else:
            status = "ok"
        has_zero_paper_chains = any(gap.gap_type == "zero_paper_chains" for gap in gap_findings)
        return CollectorSummary(
            overall_status=status,
            blocking_count=blocking,
            warning_count=warning,
            info_count=info,
            has_zero_paper_chains=has_zero_paper_chains,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Passive evidence harvester collector (fixture / dry-run mode)."
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Path to a JSON fixture describing collector input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the normalized collector report JSON.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output instead of compact JSON.",
    )
    parser.add_argument(
        "--stale-after-minutes",
        type=int,
        default=120,
        help="Default staleness threshold used when the fixture does not override it.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw_input = json.loads(args.fixture.read_text(encoding="utf-8"))
    if not isinstance(raw_input, dict):
        raise CollectorValidationError("Fixture JSON root must be an object")

    raw_input.setdefault("stale_after_minutes", args.stale_after_minutes)
    collector_input = CollectorInput.from_mapping(raw_input)
    report = EvidenceHarvesterCollector(
        stale_after_minutes=collector_input.stale_after_minutes,
    ).collect(collector_input)

    payload = report.to_dict()
    json_text = json.dumps(
        payload,
        indent=2 if args.pretty else None,
        sort_keys=True,
        ensure_ascii=False,
    )

    if args.output:
        args.output.write_text(json_text + ("\n" if not json_text.endswith("\n") else ""), encoding="utf-8")
    else:
        print(json_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
