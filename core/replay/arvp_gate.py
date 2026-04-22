"""ARVP gate/evidence integration: machine-readable verdict surface.

Scope (#1849): aggregate ARVP artifacts from #1843–#1848 into a single
machine-readable gate verdict (pass/fail/blocked) with explicit blocking
vs informational finding classification.

Design rules:
  - ARVPEvidenceBundle is caller-supplied; no I/O, no live data access.
  - build_arvp_gate_verdict() is a pure function; performs no I/O.
  - write_gate_verdict_artifact() is the sole I/O entry point; fail-closed.
  - Deterministic: same inputs produce identical verdict_fingerprint.
  - All blocking/informational rules are explicit and repo-backed.

Gate rules:
  Required artifact:
    - record (ReplayRunRecord) — must be provided and non-None.
  Blocked (verdict = "blocked"):
    - record.status == "running" — run not yet complete; no verdict possible.
  Blocking findings (verdict = "fail"):
    - record.status == "failed"
    - record.deterministic_replay_ok == False
    - ShadowComparisonResult.alignment_issue is not None (if provided)
  Informational (advisory, never blocking):
    - ScenarioGroupManifest: scenario group outcome summary
    - RegimeScorecard: unknown_regime_count > 0 advisory, or general stats
    - ShadowComparisonResult: fill_rate_delta advisory (when aligned)

Non-goals:
  - Redefining global governance rules
  - Wiring into existing runner/reporter surfaces
  - Dashboard or UI
  - CI/workflow integration beyond the verdict artifact
  - Business logic changes

relations:
  domain: validation
  upstream:
    - core.replay.run_registry      (ReplayRunRecord)
    - core.replay.scenario_harness  (ScenarioGroupManifest)
    - core.replay.regime_analytics  (RegimeScorecard)
    - core.replay.shadow_compare    (ShadowComparisonResult)
    - core.replay.canonical_json    (canonical_hash, canonical_json_dumps)
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.replay.regime_analytics import RegimeScorecard
from core.replay.run_registry import ReplayRunRecord
from core.replay.scenario_harness import ScenarioGroupManifest
from core.replay.shadow_compare import ShadowComparisonResult

_GATE_VERDICT_FILENAME = "arvp_gate_verdict.json"
_VALID_VERDICTS: frozenset[str] = frozenset({"pass", "fail", "blocked"})


class ARVPGateError(ValueError):
    """Raised when ARVP gate validation or I/O fails."""


@dataclass(frozen=True, slots=True)
class ARVPEvidenceBundle:
    """Caller-supplied collection of ARVP artifacts for gate assessment.

    record is the only required artifact; all others are optional.
    Providing more artifacts enables richer gate output without changing
    the blocking rules applied to the required artifact.
    """

    record: ReplayRunRecord
    manifest: ScenarioGroupManifest | None = None
    scorecard: RegimeScorecard | None = None
    shadow: ShadowComparisonResult | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.record, ReplayRunRecord):
            raise ARVPGateError(
                f"record must be a ReplayRunRecord, got {type(self.record).__name__}"
            )
        if self.manifest is not None and not isinstance(
            self.manifest, ScenarioGroupManifest
        ):
            raise ARVPGateError(
                f"manifest must be ScenarioGroupManifest or None, "
                f"got {type(self.manifest).__name__}"
            )
        if self.scorecard is not None and not isinstance(
            self.scorecard, RegimeScorecard
        ):
            raise ARVPGateError(
                f"scorecard must be RegimeScorecard or None, "
                f"got {type(self.scorecard).__name__}"
            )
        if self.shadow is not None and not isinstance(
            self.shadow, ShadowComparisonResult
        ):
            raise ARVPGateError(
                f"shadow must be ShadowComparisonResult or None, "
                f"got {type(self.shadow).__name__}"
            )


@dataclass(frozen=True, slots=True)
class ARVPGateVerdict:
    """Machine-readable ARVP gate verdict.

    verdict:
      "pass"    — no blocking findings; run complete and determinism ok.
      "fail"    — one or more blocking findings detected.
      "blocked" — run still in progress; no verdict possible yet.

    blocking_findings: tuple of strings describing each blocking finding.
    informational_findings: tuple of advisory strings (never blocking).
    required_artifacts_present: always True (record was supplied and required).
    verdict_fingerprint: deterministic SHA-256 of the verdict payload.
    """

    verdict: str
    run_id: str
    required_artifacts_present: bool
    blocking_findings: tuple[str, ...]
    informational_findings: tuple[str, ...]
    verdict_fingerprint: str

    def __post_init__(self) -> None:
        if self.verdict not in _VALID_VERDICTS:
            raise ARVPGateError(
                f"verdict must be one of {sorted(_VALID_VERDICTS)}, "
                f"got {self.verdict!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "run_id": self.run_id,
            "required_artifacts_present": self.required_artifacts_present,
            "blocking_findings": list(self.blocking_findings),
            "informational_findings": list(self.informational_findings),
            "verdict_fingerprint": self.verdict_fingerprint,
        }


def _compute_verdict_fingerprint(
    run_id: str,
    verdict: str,
    blocking_findings: tuple[str, ...],
    informational_findings: tuple[str, ...],
) -> str:
    payload: dict[str, Any] = {
        "blocking_findings": sorted(blocking_findings),
        "informational_findings": sorted(informational_findings),
        "run_id": run_id,
        "verdict": verdict,
    }
    return canonical_hash(payload)


def build_arvp_gate_verdict(bundle: ARVPEvidenceBundle) -> ARVPGateVerdict:
    """Build a machine-readable ARVP gate verdict from an evidence bundle.

    Pure function; performs no I/O.

    Raises:
        ARVPGateError: if bundle is not an ARVPEvidenceBundle instance.
    """
    if not isinstance(bundle, ARVPEvidenceBundle):
        raise ARVPGateError(
            f"bundle must be ARVPEvidenceBundle, got {type(bundle).__name__}"
        )

    record = bundle.record

    # Blocked immediately — run not yet complete, no verdict possible.
    if record.status == "running":
        fingerprint = _compute_verdict_fingerprint(record.run_id, "blocked", (), ())
        return ARVPGateVerdict(
            verdict="blocked",
            run_id=record.run_id,
            required_artifacts_present=True,
            blocking_findings=(),
            informational_findings=(),
            verdict_fingerprint=fingerprint,
        )

    blocking: list[str] = []
    informational: list[str] = []

    # --- Blocking rules ---

    if record.status == "failed":
        reason = record.failure_reason or "unknown"
        blocking.append(f"run_failed: {reason}")

    if not record.deterministic_replay_ok:
        blocking.append(
            "determinism_check_failed: deterministic_replay_ok is False"
        )

    if bundle.shadow is not None and bundle.shadow.alignment_issue is not None:
        blocking.append(f"shadow_alignment_issue: {bundle.shadow.alignment_issue}")

    # --- Informational rules ---

    if bundle.manifest is not None:
        m = bundle.manifest
        informational.append(
            f"scenario_group: group_id={m.group_id} "
            f"total={m.total_scenarios} "
            f"succeeded={m.succeeded_count} "
            f"failed={m.failed_count}"
        )

    if bundle.scorecard is not None:
        sc = bundle.scorecard
        if sc.unknown_regime_count > 0:
            informational.append(
                f"regime_scorecard: unknown_regime_count={sc.unknown_regime_count} "
                f"(review regime coverage)"
            )
        else:
            informational.append(
                f"regime_scorecard: total_records={sc.total_records} "
                f"segments={len(sc.segments)}"
            )

    if bundle.shadow is not None and bundle.shadow.alignment_issue is None:
        s = bundle.shadow
        informational.append(
            f"shadow_comparison: fill_rate_delta={s.fill_rate_delta} "
            f"signal_count_delta={s.signal_count_delta} "
            f"fill_count_delta={s.fill_count_delta}"
        )

    blocking_tuple = tuple(sorted(blocking))
    informational_tuple = tuple(sorted(informational))
    verdict = "fail" if blocking_tuple else "pass"
    fingerprint = _compute_verdict_fingerprint(
        record.run_id, verdict, blocking_tuple, informational_tuple
    )

    return ARVPGateVerdict(
        verdict=verdict,
        run_id=record.run_id,
        required_artifacts_present=True,
        blocking_findings=blocking_tuple,
        informational_findings=informational_tuple,
        verdict_fingerprint=fingerprint,
    )


def write_gate_verdict_artifact(
    verdict: ARVPGateVerdict,
    artifact_root: str | pathlib.Path,
) -> None:
    """Write the gate verdict as arvp_gate_verdict.json into artifact_root.

    Fail-closed: raises ARVPGateError on any I/O failure.
    """
    if not isinstance(verdict, ARVPGateVerdict):
        raise ARVPGateError(
            f"verdict must be ARVPGateVerdict, got {type(verdict).__name__}"
        )
    root = pathlib.Path(artifact_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        output_path = root / _GATE_VERDICT_FILENAME
        output_path.write_text(
            canonical_json_dumps(verdict.to_dict()), encoding="utf-8"
        )
    except OSError as exc:
        raise ARVPGateError(
            f"Failed to write gate verdict artifact: {exc}"
        ) from exc
