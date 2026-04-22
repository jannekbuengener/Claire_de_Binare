"""ARVP scenario harness: multi-variant replay run orchestration.

Scope (#1844): scenario abstraction, group orchestration, and manifest.

Non-goals:
  - built-in scenario packs (defined in #1845)
  - regime analytics or scorecards (#1846)
  - management-grade UX reports (#1847)
  - database-backed manifests or multi-process locking
  - strategy or execution business logic
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.utils.clock import utcnow

_GROUP_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class ScenarioHarnessError(ValueError):
    """Raised when scenario harness validation or orchestration fails."""


def _utc_now_iso() -> str:
    return utcnow().replace(tzinfo=timezone.utc).isoformat()


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioHarnessError(f"{field_name} must be a non-empty string")


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    """Specification for a single scenario variant in a group.

    config_overrides is an opaque dict of parameter overrides applied on top of
    the base config at the runner layer.  The harness does not validate specific
    override keys; that is the caller's responsibility.
    """

    scenario_id: str
    description: str
    config_overrides: dict[str, Any]

    def __post_init__(self) -> None:
        _require_non_empty_string(self.scenario_id, "scenario_id")
        _require_non_empty_string(self.description, "description")
        if not isinstance(self.config_overrides, dict):
            raise ScenarioHarnessError("config_overrides must be a dict")
        # Defensive copy: prevents external mutation from affecting harness
        # determinism after construction.
        object.__setattr__(self, "config_overrides", dict(self.config_overrides))

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "description": self.description,
            "config_overrides": dict(self.config_overrides),
        }


@dataclass(frozen=True, slots=True)
class ScenarioRunResult:
    """Result of executing a single scenario variant.

    Invariants:
    - failure_reason is required when exit_code != 0
    - failure_reason must be None when exit_code == 0
    - run_id, when set, must be a non-empty string
    """

    scenario_id: str
    exit_code: int
    run_id: str | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.scenario_id, "scenario_id")
        if isinstance(self.exit_code, bool) or not isinstance(self.exit_code, int):
            raise ScenarioHarnessError("exit_code must be an int (not bool)")
        if self.exit_code != 0 and self.failure_reason is None:
            raise ScenarioHarnessError(
                "failure_reason is required when exit_code != 0"
            )
        if self.exit_code == 0 and self.failure_reason is not None:
            raise ScenarioHarnessError(
                "failure_reason must be None when exit_code == 0"
            )
        if self.failure_reason is not None:
            _require_non_empty_string(self.failure_reason, "failure_reason")
        if self.run_id is not None:
            _require_non_empty_string(self.run_id, "run_id")

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "scenario_id": self.scenario_id,
            "exit_code": self.exit_code,
        }
        if self.run_id is not None:
            result["run_id"] = self.run_id
        if self.failure_reason is not None:
            result["failure_reason"] = self.failure_reason
        return result


@dataclass(frozen=True, slots=True)
class ScenarioGroupManifest:
    """Manifest for a completed scenario group execution."""

    group_id: str
    scenario_results: tuple[ScenarioRunResult, ...]
    artifact_root: str
    group_fingerprint: str
    started_at_utc: str
    finished_at_utc: str
    total_scenarios: int
    succeeded_count: int
    failed_count: int

    def __post_init__(self) -> None:
        _require_non_empty_string(self.group_id, "group_id")
        _require_non_empty_string(self.artifact_root, "artifact_root")
        if not isinstance(self.scenario_results, tuple):
            raise ScenarioHarnessError("scenario_results must be a tuple")
        if self.total_scenarios != len(self.scenario_results):
            raise ScenarioHarnessError(
                "total_scenarios must equal len(scenario_results)"
            )
        if self.succeeded_count + self.failed_count != self.total_scenarios:
            raise ScenarioHarnessError(
                "succeeded_count + failed_count must equal total_scenarios"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "group_fingerprint": self.group_fingerprint,
            "artifact_root": self.artifact_root,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "total_scenarios": self.total_scenarios,
            "succeeded_count": self.succeeded_count,
            "failed_count": self.failed_count,
            "scenario_results": [r.to_dict() for r in self.scenario_results],
        }


def build_scenario_group_id(scenario_ids: Sequence[str]) -> str:
    """Build a deterministic group ID from an ordered sequence of scenario IDs."""
    if not scenario_ids:
        raise ScenarioHarnessError("scenario_ids must not be empty")
    for sid in scenario_ids:
        if not isinstance(sid, str) or not sid.strip():
            raise ScenarioHarnessError(
                "each scenario_id in scenario_ids must be a non-empty string"
            )
    payload: dict[str, Any] = {"scenario_ids": list(scenario_ids)}
    fingerprint = canonical_hash(payload)
    return f"sg-{fingerprint[:12]}"


def _build_group_fingerprint(
    group_id: str,
    results: Sequence[ScenarioRunResult],
) -> str:
    """Build a deterministic fingerprint from group_id and scenario outcomes.

    Excludes wall-clock timestamps, filesystem paths, and attempt-based run_ids
    so that the fingerprint is stable across reruns that produce identical outcomes.
    """
    payload: dict[str, Any] = {
        "group_id": group_id,
        "scenario_outcomes": [
            {"scenario_id": r.scenario_id, "exit_code": r.exit_code}
            for r in results
        ],
    }
    return canonical_hash(payload)


def _write_group_manifest(output_dir: Path, manifest: ScenarioGroupManifest) -> None:
    group_dir = output_dir / manifest.group_id
    try:
        group_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = group_dir / "scenario_group_manifest.json"
        manifest_path.write_text(
            canonical_json_dumps(manifest.to_dict()),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ScenarioHarnessError(
            f"Failed to write scenario group manifest to {group_dir}: {exc}"
        ) from exc


def run_scenario_group(
    scenario_specs: Sequence[ScenarioSpec],
    *,
    run_fn: Callable[[ScenarioSpec], ScenarioRunResult],
    output_dir: Path | str,
    group_id: str | None = None,
) -> ScenarioGroupManifest:
    """Orchestrate a group of scenario runs deterministically.

    Executes each scenario in the order provided.  Scenario failures are captured
    explicitly as ScenarioRunResult entries — no scenario is silently skipped.
    Unexpected exceptions from run_fn are also caught and recorded as failures.

    Args:
        scenario_specs: Non-empty sequence of ScenarioSpec with unique scenario_ids.
        run_fn: Callable that executes a single scenario and returns a
            ScenarioRunResult whose scenario_id matches the input ScenarioSpec.
            Must not return a different type; that is treated as a harness error.
            Exceptions other than that contract violation are caught and recorded
            as failed results.
        output_dir: Root directory for group output.  The manifest is written
            to output_dir / group_id / scenario_group_manifest.json.
        group_id: Optional pre-computed group ID.  If None, derived
            deterministically from the ordered scenario_ids.  When supplied,
            must match ^[a-zA-Z0-9_-]{1,64}$.

    Returns:
        ScenarioGroupManifest with all results and a written manifest.

    Raises:
        ScenarioHarnessError: empty specs, duplicate scenario_ids, invalid
            group_id, run_fn returning wrong type or wrong scenario_id, or
            manifest write failure.
    """
    if not scenario_specs:
        raise ScenarioHarnessError("scenario_specs must not be empty")

    seen_ids: set[str] = set()
    for spec in scenario_specs:
        if not isinstance(spec, ScenarioSpec):
            raise ScenarioHarnessError(
                f"Expected ScenarioSpec, got {type(spec).__name__}"
            )
        if spec.scenario_id in seen_ids:
            raise ScenarioHarnessError(
                f"Duplicate scenario_id: {spec.scenario_id!r}"
            )
        seen_ids.add(spec.scenario_id)

    if group_id is not None:
        if not _GROUP_ID_RE.match(group_id):
            raise ScenarioHarnessError(
                "group_id must be a 1-64 character string of [a-zA-Z0-9_-]"
            )

    scenario_ids = [spec.scenario_id for spec in scenario_specs]
    resolved_group_id = group_id if group_id is not None else build_scenario_group_id(scenario_ids)
    output_path = Path(output_dir)
    artifact_root = str(output_path / resolved_group_id)
    started_at_utc = _utc_now_iso()

    results: list[ScenarioRunResult] = []
    for spec in scenario_specs:
        try:
            result = run_fn(spec)
        except Exception as exc:
            exc_msg = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
            result = ScenarioRunResult(
                scenario_id=spec.scenario_id,
                exit_code=2,
                failure_reason=f"Scenario run raised unexpected exception: {exc_msg}",
            )
        else:
            if not isinstance(result, ScenarioRunResult):
                raise ScenarioHarnessError(
                    f"run_fn must return ScenarioRunResult for scenario "
                    f"{spec.scenario_id!r}, got {type(result).__name__}"
                )
            if result.scenario_id != spec.scenario_id:
                raise ScenarioHarnessError(
                    f"run_fn returned result for wrong scenario: "
                    f"expected {spec.scenario_id!r}, got {result.scenario_id!r}"
                )
        results.append(result)

    finished_at_utc = _utc_now_iso()
    succeeded_count = sum(1 for r in results if r.exit_code == 0)
    failed_count = len(results) - succeeded_count
    group_fingerprint = _build_group_fingerprint(resolved_group_id, results)

    manifest = ScenarioGroupManifest(
        group_id=resolved_group_id,
        scenario_results=tuple(results),
        artifact_root=artifact_root,
        group_fingerprint=group_fingerprint,
        started_at_utc=started_at_utc,
        finished_at_utc=finished_at_utc,
        total_scenarios=len(results),
        succeeded_count=succeeded_count,
        failed_count=failed_count,
    )

    _write_group_manifest(output_path, manifest)
    return manifest
