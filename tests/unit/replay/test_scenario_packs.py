"""Unit tests for core/replay/scenario_packs.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.replay.scenario_harness import ScenarioHarnessError, ScenarioRunResult, ScenarioSpec
from core.replay.scenario_packs import (
    BUILTIN_SCENARIO_IDS,
    ScenarioPackError,
    get_scenario_pack,
    list_builtin_scenario_ids,
    run_builtin_scenario_group,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _success_fn(spec: ScenarioSpec) -> ScenarioRunResult:
    return ScenarioRunResult(scenario_id=spec.scenario_id, exit_code=0)


# ---------------------------------------------------------------------------
# BUILTIN_SCENARIO_IDS / list_builtin_scenario_ids
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuiltinScenarioIds:
    def test_contains_all_five_packs(self) -> None:
        expected = {
            "baseline",
            "pessimistic_execution",
            "delayed_execution",
            "low_liquidity",
            "feed_gap",
        }
        assert set(BUILTIN_SCENARIO_IDS) == expected

    def test_order_is_stable(self) -> None:
        assert list_builtin_scenario_ids() == BUILTIN_SCENARIO_IDS

    def test_list_builtin_is_deterministic(self) -> None:
        assert list_builtin_scenario_ids() == list_builtin_scenario_ids()

    def test_baseline_is_first(self) -> None:
        assert BUILTIN_SCENARIO_IDS[0] == "baseline"


# ---------------------------------------------------------------------------
# get_scenario_pack
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetScenarioPack:
    def test_all_builtin_ids_resolve(self) -> None:
        for sid in BUILTIN_SCENARIO_IDS:
            spec = get_scenario_pack(sid)
            assert isinstance(spec, ScenarioSpec)
            assert spec.scenario_id == sid

    def test_unknown_id_fails_closed(self) -> None:
        with pytest.raises(ScenarioPackError, match="Unknown scenario pack"):
            get_scenario_pack("not_a_real_pack")

    def test_empty_string_fails_closed(self) -> None:
        with pytest.raises(ScenarioPackError):
            get_scenario_pack("")

    def test_whitespace_only_fails_closed(self) -> None:
        with pytest.raises(ScenarioPackError):
            get_scenario_pack("   ")

    def test_returns_consistent_spec_on_repeated_calls(self) -> None:
        s1 = get_scenario_pack("baseline")
        s2 = get_scenario_pack("baseline")
        assert s1.scenario_id == s2.scenario_id
        assert s1.config_overrides == s2.config_overrides

    # --- baseline ---

    def test_baseline_has_no_perturbation_keys(self) -> None:
        spec = get_scenario_pack("baseline")
        overrides = spec.config_overrides
        perturbation_keys = {
            "execution_slippage_bps",
            "fill_rate",
            "execution_posture",
            "execution_delay_ms",
            "fill_depth_factor",
            "feed_gap_seconds",
            "drop_ticks_on_gap",
        }
        assert not perturbation_keys.intersection(overrides.keys())

    def test_baseline_carries_provenance(self) -> None:
        spec = get_scenario_pack("baseline")
        assert spec.config_overrides["pack_id"] == "baseline"
        assert spec.config_overrides["pack_version"] == "1"

    # --- pessimistic_execution ---

    def test_pessimistic_execution_overrides(self) -> None:
        spec = get_scenario_pack("pessimistic_execution")
        o = spec.config_overrides
        assert o["execution_slippage_bps"] == 30
        assert o["fill_rate"] == 0.7
        assert o["execution_posture"] == "pessimistic"
        assert o["pack_id"] == "pessimistic_execution"
        assert o["pack_version"] == "1"

    # --- delayed_execution ---

    def test_delayed_execution_overrides(self) -> None:
        spec = get_scenario_pack("delayed_execution")
        o = spec.config_overrides
        assert o["execution_delay_ms"] == 500
        assert o["execution_posture"] == "delayed"
        assert o["pack_id"] == "delayed_execution"

    # --- low_liquidity ---

    def test_low_liquidity_overrides(self) -> None:
        spec = get_scenario_pack("low_liquidity")
        o = spec.config_overrides
        assert o["fill_depth_factor"] == 0.3
        assert o["execution_posture"] == "low_liquidity"
        assert o["pack_id"] == "low_liquidity"

    # --- feed_gap ---

    def test_feed_gap_overrides(self) -> None:
        spec = get_scenario_pack("feed_gap")
        o = spec.config_overrides
        assert o["feed_gap_seconds"] == 30
        assert o["drop_ticks_on_gap"] is True
        assert o["pack_id"] == "feed_gap"

    # --- determinism ---

    def test_overrides_are_stable_across_calls(self) -> None:
        for sid in BUILTIN_SCENARIO_IDS:
            s1 = get_scenario_pack(sid)
            s2 = get_scenario_pack(sid)
            assert s1.config_overrides == s2.config_overrides

    def test_config_overrides_are_isolated(self) -> None:
        spec = get_scenario_pack("pessimistic_execution")
        # Mutating the returned dict must not affect the registry.
        spec.config_overrides["injected"] = "evil"
        fresh = get_scenario_pack("pessimistic_execution")
        assert "injected" not in fresh.config_overrides


# ---------------------------------------------------------------------------
# run_builtin_scenario_group
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunBuiltinScenarioGroup:
    def test_empty_scenario_ids_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ScenarioPackError, match="must not be empty"):
            run_builtin_scenario_group([], run_fn=_success_fn, output_dir=tmp_path)

    def test_unknown_id_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ScenarioPackError, match="Unknown scenario pack"):
            run_builtin_scenario_group(
                ["baseline", "not_real"], run_fn=_success_fn, output_dir=tmp_path
            )

    def test_single_pack_succeeds(self, tmp_path: Path) -> None:
        manifest = run_builtin_scenario_group(
            ["baseline"], run_fn=_success_fn, output_dir=tmp_path
        )
        assert manifest.total_scenarios == 1
        assert manifest.succeeded_count == 1

    def test_all_five_packs_succeed(self, tmp_path: Path) -> None:
        manifest = run_builtin_scenario_group(
            list(BUILTIN_SCENARIO_IDS), run_fn=_success_fn, output_dir=tmp_path
        )
        assert manifest.total_scenarios == 5
        assert manifest.succeeded_count == 5
        assert manifest.failed_count == 0

    def test_scenario_specs_json_written(self, tmp_path: Path) -> None:
        manifest = run_builtin_scenario_group(
            ["baseline", "pessimistic_execution"],
            run_fn=_success_fn,
            output_dir=tmp_path,
        )
        specs_path = Path(manifest.artifact_root) / "scenario_specs.json"
        assert specs_path.exists()

    def test_scenario_specs_json_content(self, tmp_path: Path) -> None:
        ids = ["baseline", "pessimistic_execution", "delayed_execution"]
        manifest = run_builtin_scenario_group(
            ids, run_fn=_success_fn, output_dir=tmp_path
        )
        specs_path = Path(manifest.artifact_root) / "scenario_specs.json"
        data = json.loads(specs_path.read_text(encoding="utf-8"))
        assert "scenario_specs" in data
        written_ids = [s["scenario_id"] for s in data["scenario_specs"]]
        assert written_ids == ids

    def test_scenario_specs_json_contains_overrides(self, tmp_path: Path) -> None:
        manifest = run_builtin_scenario_group(
            ["pessimistic_execution"], run_fn=_success_fn, output_dir=tmp_path
        )
        specs_path = Path(manifest.artifact_root) / "scenario_specs.json"
        data = json.loads(specs_path.read_text(encoding="utf-8"))
        spec_dict = data["scenario_specs"][0]
        assert spec_dict["config_overrides"]["pack_id"] == "pessimistic_execution"
        assert spec_dict["config_overrides"]["pack_version"] == "1"
        assert spec_dict["config_overrides"]["execution_slippage_bps"] == 30

    def test_scenario_specs_json_stable_across_runs(self, tmp_path: Path) -> None:
        ids = ["baseline", "feed_gap"]

        manifest1 = run_builtin_scenario_group(
            ids, run_fn=_success_fn, output_dir=tmp_path / "run1"
        )
        manifest2 = run_builtin_scenario_group(
            ids, run_fn=_success_fn, output_dir=tmp_path / "run2"
        )
        specs1 = json.loads(
            (Path(manifest1.artifact_root) / "scenario_specs.json").read_text(encoding="utf-8")
        )
        specs2 = json.loads(
            (Path(manifest2.artifact_root) / "scenario_specs.json").read_text(encoding="utf-8")
        )
        assert specs1 == specs2

    def test_custom_group_id_forwarded(self, tmp_path: Path) -> None:
        manifest = run_builtin_scenario_group(
            ["baseline"],
            run_fn=_success_fn,
            output_dir=tmp_path,
            group_id="my-pack-run",
        )
        assert manifest.group_id == "my-pack-run"
        assert (tmp_path / "my-pack-run" / "scenario_specs.json").exists()

    def test_harness_duplicate_ids_still_fail_closed(self, tmp_path: Path) -> None:
        # Duplicate resolution goes through harness; verify it surfaces correctly.
        specs_direct = [
            get_scenario_pack("baseline"),
            get_scenario_pack("baseline"),
        ]
        with pytest.raises(ScenarioHarnessError, match="Duplicate scenario_id"):
            from core.replay.scenario_harness import run_scenario_group

            run_scenario_group(specs_direct, run_fn=_success_fn, output_dir=tmp_path)

    def test_execution_order_matches_input(self, tmp_path: Path) -> None:
        order: list[str] = []

        def tracking_fn(spec: ScenarioSpec) -> ScenarioRunResult:
            order.append(spec.scenario_id)
            return ScenarioRunResult(scenario_id=spec.scenario_id, exit_code=0)

        ids = ["feed_gap", "baseline", "low_liquidity"]
        run_builtin_scenario_group(ids, run_fn=tracking_fn, output_dir=tmp_path)
        assert order == ids
