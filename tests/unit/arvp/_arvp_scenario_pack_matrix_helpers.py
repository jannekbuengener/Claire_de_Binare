"""Shared helpers for ARVP scenario-pack matrix contract tests (#3826)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from core.replay.scenario_packs import ScenarioPackError, get_scenario_pack
from services.validation.strategy_replay_runner import (
    ARVPReplayConfig,
    ReplayRunnerError,
    _apply_scenario_overrides,
)

_MATRIX_FIXTURE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "arvp" / "scenario_pack_matrix_v1.json"
)

MatrixStatus = Literal["supported", "unsupported", "blocked"]


def load_scenario_pack_matrix_fixture() -> dict[str, Any]:
    return json.loads(_MATRIX_FIXTURE.read_text(encoding="utf-8"))


def classify_scenario_pack_cell(
    *,
    strategy_id: str,
    adapter_id: str,
    scenario_id: str,
    canonical_adapter_by_strategy: dict[str, str] | None = None,
) -> tuple[MatrixStatus, str]:
    """Classify strategy x adapter x scenario pack without running replay."""
    canonical = canonical_adapter_by_strategy or load_scenario_pack_matrix_fixture()[
        "canonical_adapter_by_strategy"
    ]

    try:
        get_scenario_pack(scenario_id)
    except ScenarioPackError:
        return "blocked", "unknown_scenario_pack"

    cfg = ARVPReplayConfig(
        input_candles_file="tests/fixtures/arvp/calibration/aligned_happy_path/replay_report.json",
        strategy_id=strategy_id,
        adapter_id=adapter_id,
        scenario_ids=(scenario_id,),
    )
    try:
        cfg.validate()
    except ValueError as exc:
        return "unsupported", str(exc)

    expected_adapter = canonical.get(strategy_id)
    if expected_adapter is not None and adapter_id != expected_adapter:
        return "unsupported", "adapter_strategy_mismatch"

    try:
        overrides = get_scenario_pack(scenario_id).config_overrides
        _apply_scenario_overrides(cfg, overrides)
    except ReplayRunnerError as exc:
        return "blocked", str(exc)

    return "supported", ""


def assert_matrix_fixture_covers_builtin_packs() -> None:
    fixture = load_scenario_pack_matrix_fixture()
    from core.replay.scenario_packs import BUILTIN_SCENARIO_IDS

    assert tuple(fixture["builtin_scenario_ids"]) == BUILTIN_SCENARIO_IDS
