"""Shared helpers for Harvester→ARVP→Profitability mapping contract tests (#3828)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.validation.profitability_evidence_packet_assembler import (
    _build_coverage_readiness,
    _build_recommendation,
)

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "arvp"
    / "evidence_mapping"
    / "cases_v1.json"
)


def load_evidence_mapping_cases() -> list[dict[str, Any]]:
    payload = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError("evidence mapping fixture must contain cases list")
    return cases


def _base_inputs(case: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    harvester = {
        "schema_version": "profitability_harvester_ref.v1",
        "candidate_id": "cand-test-001",
        "risk_blocks": 1,
        "kill_switch_events": 0,
        **case["harvester"],
    }
    inputs = {
        "data_quality_report": {
            "quality_verdict": case["data_quality_verdict"],
            "limitations": [],
        },
        "replay_metrics": {
            "data_integrity_ok": True,
            "deterministic_replay_ok": True,
            "profit_factor": 1.1,
            "expectancy": 0.01,
            "win_rate": 0.5,
            "avg_win": 0.02,
            "avg_loss": -0.01,
            "max_drawdown": 0.05,
            "loss_streak": 1,
            "trade_count": 10,
        },
        "scenario_stress_summary": {
            "overall_stress_outcome": "PASS",
            "limitations": [],
        },
        "economics_assessment": {
            "assessment_status": "PASS",
            "ranking_ready": False,
            "limitations": [],
        },
        "regime_scorecard_block": {
            "status": case["regime_status"],
            "segments": [],
            "notes": ["regime unavailable"] if case["regime_status"] != "ok" else [],
        },
        "replay_vs_paper_status": case["replay_vs_paper_status"],
        "harvester_ref": harvester,
    }
    candidate_contract = {
        "status": "ACTIVE",
        "limitations": [],
        "execution_assumptions": ["paper only"],
    }
    return inputs, candidate_contract


def evaluate_evidence_mapping_case(case: dict[str, Any]) -> dict[str, Any]:
    inputs, candidate_contract = _base_inputs(case)
    coverage = _build_coverage_readiness(
        data_quality_report=inputs["data_quality_report"],
        replay_metrics=inputs["replay_metrics"],
        scenario_stress_summary=inputs["scenario_stress_summary"],
        economics_assessment=inputs["economics_assessment"],
        regime_scorecard_block=inputs["regime_scorecard_block"],
        replay_vs_paper_status=inputs["replay_vs_paper_status"],
        harvester_ref=inputs["harvester_ref"],
    )
    recommendation = _build_recommendation(
        candidate_contract=candidate_contract,
        economics_assessment=inputs["economics_assessment"],
        coverage_readiness=coverage,
    )
    limitations = list(inputs["harvester_ref"].get("limitations", []))
    safety = list(inputs["harvester_ref"].get("safety_boundaries", []))
    return {
        "coverage": coverage,
        "recommendation": recommendation,
        "limitations": limitations,
        "safety_boundaries": safety,
    }
