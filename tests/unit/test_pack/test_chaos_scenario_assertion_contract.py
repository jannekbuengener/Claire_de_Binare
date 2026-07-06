"""Chaos scenario assertion contract tests (#3877).

Parent #3872. Deterministic fixtures and repo reads — no runtime mutation in CI.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.test_pack._test_pack_contract_helpers import (
    CANONICAL_REDIS_CONTAINER,
    CHAOS_GENERATE_SCENARIO,
    EVALUATE_ASSERTIONS_SCRIPT,
    FIXTURES_ROOT,
    LR041_RUNNER,
    LR042_RUNNER,
    TEST_PACK_ROOT,
    evaluate_chaos_assertions_from_snapshot,
    runtime_drill_operator_markers,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def _load_gen_regime():
    module = _load_module_from_path(
        "cdb_test_pack_generate_scenario", CHAOS_GENERATE_SCENARIO
    )
    return module.gen_regime


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_lr041_catalog():
    module = _load_module_from_path("cdb_lr041_runner_contract", LR041_RUNNER)
    return module._scenario_catalog()


def _load_lr042_catalog():
    module = _load_module_from_path("cdb_lr042_runner_contract", LR042_RUNNER)
    return module._scenario_catalog()


@pytest.mark.parametrize(
    ("mode", "step", "expected"),
    [
        ("flipflop", 0, "TREND"),
        ("flipflop", 1, "RANGE"),
        ("highvol_noise", 3, "NOISE"),
        ("whipsaw", 5, "TREND"),
        ("whipsaw", 15, "RANGE"),
    ],
)
def test_gen_regime_is_deterministic(mode: str, step: int, expected: str) -> None:
    gen_regime = _load_gen_regime()
    assert gen_regime(mode, step) == expected


def test_generate_scenario_output_is_byte_stable(tmp_path: Path) -> None:
    out_a = tmp_path / "a.jsonl"
    out_b = tmp_path / "b.jsonl"
    base_cmd = [
        sys.executable,
        str(CHAOS_GENERATE_SCENARIO),
        "--mode",
        "flipflop",
        "--minutes",
        "12",
        "--seed",
        "1337",
        "--start-utc",
        "2026-01-03T12:00:00Z",
    ]
    subprocess.run([*base_cmd, "--out", str(out_a)], check=True)
    subprocess.run([*base_cmd, "--out", str(out_b)], check=True)
    assert out_a.read_bytes() == out_b.read_bytes()
    lines = out_a.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 12
    first = json.loads(lines[0])
    assert {"ts", "price", "regime_hint", "seed", "step"} <= set(first.keys())


def test_chaos_assertions_pass_on_complete_snapshot_fixture() -> None:
    snapshot = json.loads(
        (FIXTURES_ROOT / "metrics_snapshot_pass.json").read_text(encoding="utf-8")
    )
    result = evaluate_chaos_assertions_from_snapshot(snapshot)
    assert result.overall_pass is True
    assert result.assertion_count == 3
    assert result.failed_ids == ()


def test_chaos_assertions_fail_on_no_data_snapshot_fixture() -> None:
    snapshot = json.loads(
        (FIXTURES_ROOT / "metrics_snapshot_no_data.json").read_text(encoding="utf-8")
    )
    result = evaluate_chaos_assertions_from_snapshot(snapshot)
    assert result.overall_pass is False
    assert "up_cdb" in result.failed_ids
    assert "circuit_breaker_metric" in result.failed_ids
    assert "orders_metrics_present" in result.failed_ids


def test_evaluate_assertions_script_is_stdlib_fixture_evaluator() -> None:
    text = EVALUATE_ASSERTIONS_SCRIPT.read_text(encoding="utf-8")
    assert "overall_pass" in text
    assert "snapshot_exists" in text
    assert "urlopen" not in text


def test_lr041_drill_contract_targets_cdb_redis_not_valkey() -> None:
    catalog = _load_lr041_catalog()
    assert "redis_restart" in catalog
    assert catalog["redis_restart"].target_container == CANONICAL_REDIS_CONTAINER
    markers = runtime_drill_operator_markers(LR041_RUNNER.read_text(encoding="utf-8"))
    assert markers["uses_docker_subprocess"]
    assert markers["mentions_container_restart"]
    assert markers["requires_cdb_redis"]


def test_lr042_drill_contract_is_operator_netem_path() -> None:
    catalog = _load_lr042_catalog()
    assert "latency_only" in catalog
    assert "packet_loss_only" in catalog
    markers = runtime_drill_operator_markers(LR042_RUNNER.read_text(encoding="utf-8"))
    assert markers["uses_docker_subprocess"]
    assert markers["mentions_netem"]
    assert markers["requires_cdb_redis"]


def test_chaos_template_declares_pass_fail_output_shape() -> None:
    template = (TEST_PACK_ROOT / "templates" / "assertions_chaos.md").read_text(
        encoding="utf-8"
    )
    assert "overall_pass" in template
    assert "assertions_result.json" in template
    assert "Pass/Fail" in template or "pass" in template.lower()


def test_contract_tests_use_unit_markers_not_runtime_chaos() -> None:
    markers = {mark.name for mark in pytestmark}
    assert markers == {"unit", "contract"}
    assert "chaos" not in markers
    assert "local_only" not in markers
