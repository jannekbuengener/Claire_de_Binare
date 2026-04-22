"""Unit tests for core/replay/scenario_harness.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.replay.scenario_harness import (
    ScenarioGroupManifest,
    ScenarioHarnessError,
    ScenarioRunResult,
    ScenarioSpec,
    build_scenario_group_id,
    run_scenario_group,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spec(
    scenario_id: str = "baseline",
    description: str = "Baseline scenario",
    config_overrides: dict[str, Any] | None = None,
) -> ScenarioSpec:
    return ScenarioSpec(
        scenario_id=scenario_id,
        description=description,
        config_overrides=config_overrides if config_overrides is not None else {},
    )


def _success_fn(spec: ScenarioSpec) -> ScenarioRunResult:
    return ScenarioRunResult(
        scenario_id=spec.scenario_id,
        exit_code=0,
        run_id="replay-aabbccdd1122-0001",
    )


def _failure_fn(spec: ScenarioSpec) -> ScenarioRunResult:
    return ScenarioRunResult(
        scenario_id=spec.scenario_id,
        exit_code=2,
        failure_reason="Simulated failure",
    )


# ---------------------------------------------------------------------------
# ScenarioSpec
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestScenarioSpec:
    def test_valid_construction(self) -> None:
        spec = _spec(config_overrides={"order_size": 2.0})
        assert spec.scenario_id == "baseline"
        assert spec.description == "Baseline scenario"
        assert spec.config_overrides == {"order_size": 2.0}

    def test_empty_scenario_id_fails(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="scenario_id"):
            _spec(scenario_id="")

    def test_whitespace_scenario_id_fails(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="scenario_id"):
            _spec(scenario_id="   ")

    def test_empty_description_fails(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="description"):
            _spec(description="")

    def test_invalid_config_overrides_fails(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="config_overrides"):
            ScenarioSpec(
                scenario_id="baseline",
                description="Baseline",
                config_overrides="not_a_dict",  # type: ignore[arg-type]
            )

    def test_config_overrides_is_defensively_copied(self) -> None:
        original: dict[str, Any] = {"order_size": 1.0}
        spec = _spec(config_overrides=original)
        original["injected"] = "evil"
        assert "injected" not in spec.config_overrides

    def test_to_dict_shape(self) -> None:
        spec = _spec(config_overrides={"order_size": 2.0})
        d = spec.to_dict()
        assert d["scenario_id"] == "baseline"
        assert d["description"] == "Baseline scenario"
        assert d["config_overrides"] == {"order_size": 2.0}


# ---------------------------------------------------------------------------
# ScenarioRunResult
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestScenarioRunResult:
    def test_success_result(self) -> None:
        result = ScenarioRunResult(
            scenario_id="baseline", exit_code=0, run_id="replay-aabb-0001"
        )
        assert result.succeeded is True

    def test_failure_result(self) -> None:
        result = ScenarioRunResult(
            scenario_id="pessimistic", exit_code=2, failure_reason="timeout"
        )
        assert result.succeeded is False

    def test_failure_requires_reason(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="failure_reason is required"):
            ScenarioRunResult(scenario_id="baseline", exit_code=2)

    def test_success_must_not_have_reason(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="failure_reason must be None"):
            ScenarioRunResult(
                scenario_id="baseline", exit_code=0, failure_reason="unexpected"
            )

    def test_exit_code_bool_rejected(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="not bool"):
            ScenarioRunResult(scenario_id="baseline", exit_code=True)  # type: ignore[arg-type]

    def test_to_dict_omits_none_fields(self) -> None:
        result = ScenarioRunResult(scenario_id="baseline", exit_code=0)
        d = result.to_dict()
        assert "run_id" not in d
        assert "failure_reason" not in d

    def test_to_dict_includes_optional_fields(self) -> None:
        result = ScenarioRunResult(
            scenario_id="pessimistic",
            exit_code=2,
            run_id="replay-aabb-0001",
            failure_reason="bridge error",
        )
        d = result.to_dict()
        assert d["run_id"] == "replay-aabb-0001"
        assert d["failure_reason"] == "bridge error"

    def test_empty_run_id_rejected(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="run_id"):
            ScenarioRunResult(scenario_id="baseline", exit_code=0, run_id="")

    def test_empty_failure_reason_rejected(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="failure_reason"):
            ScenarioRunResult(
                scenario_id="baseline", exit_code=2, failure_reason="   "
            )


# ---------------------------------------------------------------------------
# build_scenario_group_id
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildScenarioGroupId:
    def test_deterministic_for_same_inputs(self) -> None:
        gid1 = build_scenario_group_id(["baseline", "pessimistic"])
        gid2 = build_scenario_group_id(["baseline", "pessimistic"])
        assert gid1 == gid2

    def test_different_for_different_inputs(self) -> None:
        gid1 = build_scenario_group_id(["baseline"])
        gid2 = build_scenario_group_id(["pessimistic"])
        assert gid1 != gid2

    def test_order_sensitive(self) -> None:
        gid1 = build_scenario_group_id(["baseline", "pessimistic"])
        gid2 = build_scenario_group_id(["pessimistic", "baseline"])
        assert gid1 != gid2

    def test_empty_sequence_fails(self) -> None:
        with pytest.raises(ScenarioHarnessError, match="must not be empty"):
            build_scenario_group_id([])

    def test_group_id_format(self) -> None:
        gid = build_scenario_group_id(["baseline"])
        assert gid.startswith("sg-")
        assert len(gid) == len("sg-") + 12


# ---------------------------------------------------------------------------
# run_scenario_group
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRunScenarioGroup:
    def test_empty_specs_fail_closed(self, tmp_path: Path) -> None:
        with pytest.raises(ScenarioHarnessError, match="must not be empty"):
            run_scenario_group([], run_fn=_success_fn, output_dir=tmp_path)

    def test_duplicate_ids_fail_closed(self, tmp_path: Path) -> None:
        specs = [_spec("baseline"), _spec("baseline")]
        with pytest.raises(ScenarioHarnessError, match="Duplicate scenario_id"):
            run_scenario_group(specs, run_fn=_success_fn, output_dir=tmp_path)

    def test_invalid_custom_group_id_fails(self, tmp_path: Path) -> None:
        specs = [_spec("baseline")]
        with pytest.raises(ScenarioHarnessError, match="group_id"):
            run_scenario_group(
                specs, run_fn=_success_fn, output_dir=tmp_path, group_id="../evil"
            )

    def test_custom_group_id_accepted(self, tmp_path: Path) -> None:
        specs = [_spec("baseline")]
        manifest = run_scenario_group(
            specs, run_fn=_success_fn, output_dir=tmp_path, group_id="my-group-01"
        )
        assert manifest.group_id == "my-group-01"
        assert (tmp_path / "my-group-01" / "scenario_group_manifest.json").exists()

    def test_single_scenario_success(self, tmp_path: Path) -> None:
        specs = [_spec("baseline")]
        manifest = run_scenario_group(specs, run_fn=_success_fn, output_dir=tmp_path)
        assert manifest.total_scenarios == 1
        assert manifest.succeeded_count == 1
        assert manifest.failed_count == 0
        assert manifest.scenario_results[0].scenario_id == "baseline"
        assert manifest.scenario_results[0].exit_code == 0

    def test_multiple_scenarios_all_succeed(self, tmp_path: Path) -> None:
        specs = [_spec("baseline"), _spec("pessimistic"), _spec("delayed")]
        manifest = run_scenario_group(specs, run_fn=_success_fn, output_dir=tmp_path)
        assert manifest.total_scenarios == 3
        assert manifest.succeeded_count == 3
        assert manifest.failed_count == 0

    def test_failed_scenario_explicit_not_skipped(self, tmp_path: Path) -> None:
        specs = [_spec("baseline"), _spec("pessimistic")]

        def mixed_fn(spec: ScenarioSpec) -> ScenarioRunResult:
            if spec.scenario_id == "pessimistic":
                return ScenarioRunResult(
                    scenario_id=spec.scenario_id,
                    exit_code=2,
                    failure_reason="Simulated failure",
                )
            return ScenarioRunResult(scenario_id=spec.scenario_id, exit_code=0)

        manifest = run_scenario_group(specs, run_fn=mixed_fn, output_dir=tmp_path)
        assert manifest.total_scenarios == 2
        assert manifest.succeeded_count == 1
        assert manifest.failed_count == 1
        failed = [r for r in manifest.scenario_results if r.exit_code != 0]
        assert len(failed) == 1
        assert failed[0].scenario_id == "pessimistic"
        assert failed[0].failure_reason == "Simulated failure"

    def test_run_fn_exception_captured_not_propagated(self, tmp_path: Path) -> None:
        def exploding_fn(spec: ScenarioSpec) -> ScenarioRunResult:
            raise RuntimeError("unexpected crash")

        specs = [_spec("baseline")]
        manifest = run_scenario_group(specs, run_fn=exploding_fn, output_dir=tmp_path)
        assert manifest.failed_count == 1
        assert manifest.scenario_results[0].exit_code == 2
        assert "RuntimeError" in (manifest.scenario_results[0].failure_reason or "")

    def test_run_fn_wrong_return_type_raises(self, tmp_path: Path) -> None:
        def bad_fn(spec: ScenarioSpec) -> int:  # type: ignore[return-value]
            return 42

        specs = [_spec("baseline")]
        with pytest.raises(ScenarioHarnessError, match="must return ScenarioRunResult"):
            run_scenario_group(  # type: ignore[arg-type]
                specs,
                run_fn=bad_fn,
                output_dir=tmp_path,
            )

    def test_run_fn_wrong_scenario_id_raises(self, tmp_path: Path) -> None:
        def wrong_id_fn(spec: ScenarioSpec) -> ScenarioRunResult:
            return ScenarioRunResult(scenario_id="other-id", exit_code=0)

        specs = [_spec("baseline")]
        with pytest.raises(ScenarioHarnessError, match="wrong scenario"):
            run_scenario_group(specs, run_fn=wrong_id_fn, output_dir=tmp_path)

    def test_manifest_written_to_correct_path(self, tmp_path: Path) -> None:
        specs = [_spec("baseline")]
        manifest = run_scenario_group(specs, run_fn=_success_fn, output_dir=tmp_path)
        manifest_path = tmp_path / manifest.group_id / "scenario_group_manifest.json"
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert data["group_id"] == manifest.group_id
        assert len(data["scenario_results"]) == 1

    def test_group_fingerprint_stable_for_same_outcomes(self, tmp_path: Path) -> None:
        specs = [_spec("baseline"), _spec("pessimistic")]

        def deterministic_fn(spec: ScenarioSpec) -> ScenarioRunResult:
            return ScenarioRunResult(scenario_id=spec.scenario_id, exit_code=0)

        manifest1 = run_scenario_group(
            specs, run_fn=deterministic_fn, output_dir=tmp_path / "run1"
        )
        manifest2 = run_scenario_group(
            specs, run_fn=deterministic_fn, output_dir=tmp_path / "run2"
        )
        assert manifest1.group_fingerprint == manifest2.group_fingerprint

    def test_group_fingerprint_differs_for_different_outcomes(
        self, tmp_path: Path
    ) -> None:
        specs = [_spec("baseline")]

        manifest_ok = run_scenario_group(
            specs, run_fn=_success_fn, output_dir=tmp_path / "a"
        )
        manifest_fail = run_scenario_group(
            specs, run_fn=_failure_fn, output_dir=tmp_path / "b"
        )
        assert manifest_ok.group_fingerprint != manifest_fail.group_fingerprint

    def test_group_id_deterministic_across_runs(self, tmp_path: Path) -> None:
        specs = [_spec("baseline"), _spec("pessimistic")]
        manifest1 = run_scenario_group(
            specs, run_fn=_success_fn, output_dir=tmp_path / "a"
        )
        manifest2 = run_scenario_group(
            specs, run_fn=_success_fn, output_dir=tmp_path / "b"
        )
        assert manifest1.group_id == manifest2.group_id

    def test_execution_order_preserved(self, tmp_path: Path) -> None:
        call_order: list[str] = []

        def tracking_fn(spec: ScenarioSpec) -> ScenarioRunResult:
            call_order.append(spec.scenario_id)
            return ScenarioRunResult(scenario_id=spec.scenario_id, exit_code=0)

        specs = [_spec("z_last"), _spec("a_first"), _spec("m_middle")]
        run_scenario_group(specs, run_fn=tracking_fn, output_dir=tmp_path)
        assert call_order == ["z_last", "a_first", "m_middle"]

    def test_manifest_to_dict_round_trips(self, tmp_path: Path) -> None:
        specs = [_spec("baseline"), _spec("pessimistic")]
        manifest = run_scenario_group(specs, run_fn=_success_fn, output_dir=tmp_path)
        d = manifest.to_dict()
        assert d["total_scenarios"] == 2
        assert d["succeeded_count"] == 2
        assert d["failed_count"] == 0
        assert len(d["scenario_results"]) == 2
        ids = [r["scenario_id"] for r in d["scenario_results"]]
        assert ids == ["baseline", "pessimistic"]
