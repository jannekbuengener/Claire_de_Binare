"""ARVP built-in scenario pack library.

Scope (#1845): canonical scenario pack definitions and invocation wrapper.

Non-goals:
  - user-defined scenario DSLs
  - regime analytics or scorecards (#1846)
  - management-grade UX reports (#1847)
  - replay-vs-paper comparison
  - non-deterministic or random stress behaviour
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Sequence

from core.replay.canonical_json import canonical_json_dumps
from core.replay.scenario_harness import (
    ScenarioGroupManifest,
    ScenarioRunResult,
    ScenarioSpec,
    run_scenario_group,
)

# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class ScenarioPackError(ValueError):
    """Raised when a scenario pack cannot be resolved or invoked."""


# ---------------------------------------------------------------------------
# Pack definitions
# ---------------------------------------------------------------------------

#: Ordered canonical built-in scenario IDs (order is part of the public API).
BUILTIN_SCENARIO_IDS: tuple[str, ...] = (
    "baseline",
    "pessimistic_execution",
    "delayed_execution",
    "low_liquidity",
    "feed_gap",
)

_PACK_VERSION = "1"


def _make_spec(
    scenario_id: str, description: str, overrides: dict[str, Any]
) -> ScenarioSpec:
    """Build a ScenarioSpec with provenance keys injected into config_overrides."""
    provenance: dict[str, Any] = {
        "pack_id": scenario_id,
        "pack_version": _PACK_VERSION,
    }
    return ScenarioSpec(
        scenario_id=scenario_id,
        description=description,
        config_overrides={**provenance, **overrides},
    )


#: Internal pack registry.  Evaluated once at import time; immutable thereafter.
_PACKS: dict[str, ScenarioSpec] = {
    "baseline": _make_spec(
        scenario_id="baseline",
        description=(
            "Undegraded baseline replay: no execution perturbation, "
            "no data-quality degradation. Reference anchor for variant comparison."
        ),
        overrides={},
    ),
    "pessimistic_execution": _make_spec(
        scenario_id="pessimistic_execution",
        description=(
            "Pessimistic execution: elevated slippage, reduced fill rate, "
            "and pessimistic execution posture. Models adverse fill conditions."
        ),
        overrides={
            "execution_slippage_bps": 30,
            "fill_rate": 0.7,
            "execution_posture": "pessimistic",
        },
    ),
    "delayed_execution": _make_spec(
        scenario_id="delayed_execution",
        description=(
            "Delayed execution: deterministic bar-level execution delay. "
            "Signal at index i executes at index i+K where K = execution_delay_bars. "
            "Uses price from K bars later."
        ),
        overrides={
            "execution_delay_bars": 1,
            "execution_posture": "delayed",
        },
    ),
    "low_liquidity": _make_spec(
        scenario_id="low_liquidity",
        description=(
            "Low-liquidity: reduced available execution depth and degraded fill "
            "conditions. Models thin-book or illiquid market conditions."
        ),
        overrides={
            "fill_depth_factor": 0.3,
            "execution_posture": "low_liquidity",
        },
    ),
    "feed_gap": _make_spec(
        scenario_id="feed_gap",
        description=(
            "Feed-gap: deterministic bar-level stale-feed injection on the 1m "
            "replay canvas. Converts a contiguous midpoint window into stale, "
            "non-fresh replay bars instead of pretending sub-minute raw-data gaps."
        ),
        overrides={
            "feed_gap_bars": 2,
        },
    ),
}

# Validate internal consistency at import time (unconditional: not skipped under -O).
if set(_PACKS.keys()) != set(BUILTIN_SCENARIO_IDS):
    raise ScenarioPackError("Mismatch between _PACKS keys and BUILTIN_SCENARIO_IDS")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_builtin_scenario_ids() -> tuple[str, ...]:
    """Return the ordered tuple of canonical built-in scenario IDs."""
    return BUILTIN_SCENARIO_IDS


def get_scenario_pack(scenario_id: str) -> ScenarioSpec:
    """Resolve a built-in scenario pack by ID.

    Each call returns a fresh ScenarioSpec so callers cannot corrupt the
    internal registry by mutating the returned config_overrides dict.

    Args:
        scenario_id: One of the canonical built-in scenario IDs.

    Returns:
        A fresh ScenarioSpec with provenance in config_overrides.

    Raises:
        ScenarioPackError: If scenario_id is not a known built-in pack.
    """
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        raise ScenarioPackError(
            f"scenario_id must be a non-empty string, got {scenario_id!r}"
        )
    stored = _PACKS.get(scenario_id)
    if stored is None:
        known = ", ".join(repr(k) for k in BUILTIN_SCENARIO_IDS)
        raise ScenarioPackError(
            f"Unknown scenario pack {scenario_id!r}. Known built-in packs: {known}"
        )
    # Return a fresh copy; ScenarioSpec.__post_init__ deep-copies config_overrides.
    return ScenarioSpec(
        scenario_id=stored.scenario_id,
        description=stored.description,
        config_overrides=stored.config_overrides,
    )


def _write_specs_artifact(
    artifact_root: str, spec_dicts: Sequence[dict[str, Any]]
) -> None:
    """Write scenario_specs.json into the group artifact directory.

    Accepts pre-captured spec dicts (snapshots taken before run_fn executes)
    so that any mutation of config_overrides inside run_fn cannot corrupt
    the provenance artifact.
    """
    artifact_dir = Path(artifact_root)
    specs_path = artifact_dir / "scenario_specs.json"
    payload: dict[str, Any] = {
        "scenario_specs": list(spec_dicts),
    }
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        specs_path.write_text(canonical_json_dumps(payload), encoding="utf-8")
    except OSError as exc:
        raise ScenarioPackError(
            f"Failed to write scenario_specs.json to {artifact_dir}: {exc}"
        ) from exc


def run_builtin_scenario_group(
    scenario_ids: Sequence[str],
    *,
    run_fn: Callable[[ScenarioSpec], ScenarioRunResult],
    output_dir: Path | str,
    group_id: str | None = None,
) -> ScenarioGroupManifest:
    """Resolve built-in scenario packs and run them as a group.

    Convenience wrapper over :func:`run_scenario_group` that:
    1. Resolves each scenario_id to its canonical ScenarioSpec.
    2. Executes the group via the harness.
    3. Writes a ``scenario_specs.json`` provenance artifact into
       ``manifest.artifact_root`` alongside the group manifest.

    Args:
        scenario_ids: Ordered sequence of built-in scenario IDs to run.
            Must be non-empty and contain only known built-in IDs.
        run_fn: Callable accepted by :func:`run_scenario_group`.
        output_dir: Root directory for group output.
        group_id: Optional pre-computed group ID (forwarded to harness).

    Returns:
        ScenarioGroupManifest from the harness, after provenance artifact write.

    Raises:
        ScenarioPackError: If ``scenario_ids`` is a bare str/bytes, is empty,
            any scenario_id is unknown, or provenance write fails.
        ScenarioHarnessError: Propagated from :func:`run_scenario_group` on
            duplicate IDs, invalid group_id, or manifest write failure.
    """
    if isinstance(scenario_ids, (str, bytes)):
        raise ScenarioPackError(
            "scenario_ids must be a sequence of str, not a bare str or bytes; "
            "wrap in a list, e.g. [scenario_id]"
        )
    if not scenario_ids:
        raise ScenarioPackError("scenario_ids must not be empty")

    specs = [get_scenario_pack(sid) for sid in scenario_ids]
    # Snapshot spec dicts before run_fn executes so any in-flight mutation of
    # config_overrides cannot corrupt the provenance artifact.
    spec_snapshots = [spec.to_dict() for spec in specs]
    manifest = run_scenario_group(
        specs,
        run_fn=run_fn,
        output_dir=output_dir,
        group_id=group_id,
    )
    _write_specs_artifact(manifest.artifact_root, spec_snapshots)
    return manifest
