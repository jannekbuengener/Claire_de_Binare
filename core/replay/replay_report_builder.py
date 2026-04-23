"""ARVP operator-facing report builder: management-grade replay reports.

Scope (#1847): translate machine-readable replay artifacts into operator-
consumable markdown surfaces.

Design rules:
  - All outputs are grounded in existing machine-readable domain objects.
  - No invented narrative: every sentence maps to a field in the input model.
  - Pure functions (build_*) perform no I/O; write_* functions are the sole
    I/O entry points and are fail-closed.
  - Deterministic: same inputs produce identical report text.

Non-goals:
  - Auto-wiring into existing runner/reporter files
  - Dashboard or web UI
  - Replay-vs-paper comparison
  - New business logic or strategy evaluation
  - Subjective commentary unsupported by input metrics

relations:
  domain: validation
  upstream:
    - core.replay.run_registry     (ReplayRunRecord)
    - core.replay.scenario_harness (ScenarioGroupManifest)
    - core.replay.regime_analytics (RegimeScorecard)
    - core.replay.resampling       (ResamplingStabilityArtifact)
    - core.replay.canonical_json   (canonical_json_dumps)
"""

from __future__ import annotations

import pathlib
from typing import Sequence

from core.replay.canonical_json import canonical_json_dumps
from core.replay.regime_analytics import RegimeScorecard
from core.replay.resampling import ResamplingStabilityArtifact
from core.replay.run_registry import ReplayRunRecord
from core.replay.scenario_harness import ScenarioGroupManifest

_MANAGEMENT_REPORT_FILENAME = "management_report.md"
_RUN_INDEX_FILENAME = "run_index.json"


class ReplayReportBuilderError(ValueError):
    """Raised when report building or artifact writing fails."""


# ---------------------------------------------------------------------------
# Internal helpers (no I/O)
# ---------------------------------------------------------------------------


def _status_icon(status: str) -> str:
    return "✓" if status == "completed" else "✗"


def _trunc(value: str, n: int = 12) -> str:
    return value[:n] if len(value) > n else value


def _fmt_bool(value: bool) -> str:
    return "yes" if value else "no"


# ---------------------------------------------------------------------------
# Public pure functions (no I/O)
# ---------------------------------------------------------------------------


def build_run_summary_text(record: ReplayRunRecord) -> str:
    """Build a concise markdown operator summary for a single replay run.

    All content is grounded in ReplayRunRecord fields.  No I/O is performed.
    Failure cases produce an explicit '## Failure' section.
    """
    if not isinstance(record, ReplayRunRecord):
        raise ReplayReportBuilderError(
            f"Expected ReplayRunRecord, got {type(record).__name__}"
        )

    icon = _status_icon(record.status)
    lines: list[str] = [
        f"# Replay Run: {record.run_id}  {icon}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Status | {record.status} |",
        f"| Strategy | {record.strategy_id} |",
        f"| Symbol | {record.symbol} |",
        f"| Mode | {record.mode} |",
        f"| Scheduler profile | {record.scheduler_profile} |",
        f"| Deterministic | {_fmt_bool(record.deterministic_replay_ok)} |",
        f"| Gate status | {record.gate_status or '—'} |",
        f"| Dataset fingerprint | {_trunc(record.dataset_fingerprint)}… |",
        f"| Execution provenance | {record.execution_provenance_id} |",
        f"| Started | {record.started_at_utc} |",
        f"| Finished | {record.finished_at_utc or '—'} |",
        f"| Artifact root | {record.artifact_root} |",
    ]

    if record.failure_reason is not None:
        lines.append("")
        lines.append("## Failure")
        lines.append("")
        lines.append(f"> {record.failure_reason}")

    return "\n".join(lines)


def build_scenario_comparison_summary(manifest: ScenarioGroupManifest) -> str:
    """Build a comparison-oriented markdown summary for a scenario group.

    Surfaces baseline-vs-variant outcomes in a table, grounded in the
    ScenarioGroupManifest.  No I/O is performed.
    """
    if not isinstance(manifest, ScenarioGroupManifest):
        raise ReplayReportBuilderError(
            f"Expected ScenarioGroupManifest, got {type(manifest).__name__}"
        )

    lines: list[str] = [
        f"# Scenario Group: {manifest.group_id}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Group ID | {manifest.group_id} |",
        f"| Total scenarios | {manifest.total_scenarios} |",
        f"| Succeeded | {manifest.succeeded_count} |",
        f"| Failed | {manifest.failed_count} |",
        f"| Started | {manifest.started_at_utc} |",
        f"| Finished | {manifest.finished_at_utc} |",
        f"| Group fingerprint | {_trunc(manifest.group_fingerprint)}… |",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Result | Run ID | Failure |",
        "|----------|--------|--------|---------|",
    ]

    for result in manifest.scenario_results:
        outcome = "✓ ok" if result.succeeded else "✗ failed"
        run_id_col = result.run_id if result.run_id is not None else "—"
        failure_col = result.failure_reason if result.failure_reason is not None else "—"
        lines.append(
            f"| {result.scenario_id} | {outcome} | {run_id_col} | {failure_col} |"
        )

    return "\n".join(lines)


def build_regime_scorecard_summary(scorecard: RegimeScorecard) -> str:
    """Build a markdown operator summary for a regime scorecard.

    Renders per-regime KPI segments in a table, grounded in RegimeScorecard.
    No I/O is performed.
    """
    if not isinstance(scorecard, RegimeScorecard):
        raise ReplayReportBuilderError(
            f"Expected RegimeScorecard, got {type(scorecard).__name__}"
        )

    if scorecard.total_records > 0:
        known = scorecard.total_records - scorecard.unknown_regime_count
        known_pct = f"{known / scorecard.total_records * 100:.1f}%"
    else:
        known_pct = "n/a"

    lines: list[str] = [
        f"# Regime Scorecard: {scorecard.run_id}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Total records | {scorecard.total_records} |",
        f"| Unknown regime | {scorecard.unknown_regime_count} |",
        f"| Known regime coverage | {known_pct} |",
        f"| Input fingerprint | {_trunc(scorecard.input_fingerprint)}… |",
        "",
        "## Per-Regime KPIs",
        "",
        "| Regime | Records | Signals | Fills | Rejects | Fill Rate | PnL Sum |",
        "|--------|---------|---------|-------|---------|-----------|---------|",
    ]

    if scorecard.segments:
        for seg in scorecard.segments:
            lines.append(
                f"| {seg.regime_id}"
                f" | {seg.record_count}"
                f" | {seg.signal_count}"
                f" | {seg.fill_count}"
                f" | {seg.reject_count}"
                f" | {seg.fill_rate}"
                f" | {seg.pnl_sum} |"
            )
    else:
        lines.append("| — | — | — | — | — | — | — |")

    return "\n".join(lines)


def build_resampling_stability_summary(stability: ResamplingStabilityArtifact) -> str:
    """Build a markdown operator summary for a resampling stability artifact."""
    if not isinstance(stability, ResamplingStabilityArtifact):
        raise ReplayReportBuilderError(
            f"Expected ResamplingStabilityArtifact, got {type(stability).__name__}"
        )

    provenance = stability.source_provenance
    lines: list[str] = [
        f"# Resampling Stability: {provenance.source_run_id}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Method | {stability.resampling_method} |",
        f"| Sample count | {stability.sample_count} |",
        f"| Blocks per sample | {stability.sample_block_count} |",
        f"| Source blocks | {provenance.block_count} |",
        f"| Dataset fingerprint | {_trunc(provenance.dataset_fingerprint)}… |",
        f"| Execution provenance | {provenance.execution_provenance_id} |",
        f"| Config fingerprint | {_trunc(stability.config_fingerprint)}… |",
        "",
        "## Empirical KPI Bands",
        "",
        "| KPI | Baseline | Min | P05 | P50 | P95 | Max | Span |",
        "|-----|----------|-----|-----|-----|-----|-----|------|",
    ]

    for summary in stability.kpi_summaries:
        lines.append(
            f"| {summary.kpi}"
            f" | {summary.baseline}"
            f" | {summary.minimum}"
            f" | {summary.p05}"
            f" | {summary.p50}"
            f" | {summary.p95}"
            f" | {summary.maximum}"
            f" | {summary.empirical_span} |"
        )

    lines.extend(["", "## Operator Summary", ""])
    for line in stability.operator_summary:
        lines.append(f"- {line}")

    return "\n".join(lines)


def build_management_report(
    *,
    record: ReplayRunRecord,
    manifest: ScenarioGroupManifest | None = None,
    scorecard: RegimeScorecard | None = None,
    stability: ResamplingStabilityArtifact | None = None,
) -> str:
    """Build a management-grade markdown report for a replay run.

    Combines a per-run operator summary with optional scenario comparison and
    regime scorecard / resampling stability sections.  All content is grounded
    in the supplied domain objects; no narrative is invented.  No I/O is
    performed.
    """
    if not isinstance(record, ReplayRunRecord):
        raise ReplayReportBuilderError(
            f"Expected ReplayRunRecord, got {type(record).__name__}"
        )
    if manifest is not None and not isinstance(manifest, ScenarioGroupManifest):
        raise ReplayReportBuilderError(
            f"manifest must be ScenarioGroupManifest or None, "
            f"got {type(manifest).__name__}"
        )
    if scorecard is not None and not isinstance(scorecard, RegimeScorecard):
        raise ReplayReportBuilderError(
            f"scorecard must be RegimeScorecard or None, "
            f"got {type(scorecard).__name__}"
        )
    if stability is not None and not isinstance(stability, ResamplingStabilityArtifact):
        raise ReplayReportBuilderError(
            f"stability must be ResamplingStabilityArtifact or None, "
            f"got {type(stability).__name__}"
        )

    sections: list[str] = [build_run_summary_text(record)]

    if manifest is not None:
        sections.extend(["", "---", "", build_scenario_comparison_summary(manifest)])

    if scorecard is not None:
        sections.extend(["", "---", "", build_regime_scorecard_summary(scorecard)])

    if stability is not None:
        sections.extend(["", "---", "", build_resampling_stability_summary(stability)])

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# I/O entry points (fail-closed)
# ---------------------------------------------------------------------------


def write_management_report(
    report_str: str,
    artifact_root: str | pathlib.Path,
) -> None:
    """Write management_report.md into artifact_root.

    Fail-closed: raises ReplayReportBuilderError on any I/O failure.
    The report_str must be a non-empty string (output of build_management_report
    or a compatible builder).
    """
    if not isinstance(report_str, str) or not report_str.strip():
        raise ReplayReportBuilderError("report_str must be a non-empty string")

    root = pathlib.Path(artifact_root)
    out_path = root / _MANAGEMENT_REPORT_FILENAME
    try:
        root.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_str, encoding="utf-8")
    except OSError as exc:
        raise ReplayReportBuilderError(
            f"Failed to write management report to {out_path}: {exc}"
        ) from exc


def write_run_index_artifact(
    records: Sequence[ReplayRunRecord],
    artifact_root: str | pathlib.Path,
) -> None:
    """Write a deterministic run_index.json snapshot into artifact_root.

    The index is a machine-readable JSON object containing all supplied run
    records, ordered as provided.  Callers should supply records from
    ReplayRunRegistry.load_all() for a consistent history snapshot.

    Fail-closed: raises ReplayReportBuilderError on any validation or I/O failure.
    """
    # Materialize once: safe for any iterable, enables len() without re-iteration.
    records_list = list(records)
    for i, rec in enumerate(records_list):
        if not isinstance(rec, ReplayRunRecord):
            raise ReplayReportBuilderError(
                f"records[{i}] must be ReplayRunRecord, got {type(rec).__name__}"
            )

    root = pathlib.Path(artifact_root)
    out_path = root / _RUN_INDEX_FILENAME
    payload = {
        "run_count": len(records_list),
        "runs": [r.to_dict() for r in records_list],
    }
    try:
        root.mkdir(parents=True, exist_ok=True)
        out_path.write_text(canonical_json_dumps(payload), encoding="utf-8")
    except OSError as exc:
        raise ReplayReportBuilderError(
            f"Failed to write run index to {out_path}: {exc}"
        ) from exc
