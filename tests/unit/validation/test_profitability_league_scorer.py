from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from services.validation.profitability_league_scorer import (
    DEFAULT_MODEL_ID,
    FORMULA_REF,
    ProfitabilityLeagueScorerError,
    _DIMENSION_ORDER,
    _WEIGHTS,
    _validate_report,
    build_league_table_report,
    hard_gate_failures,
    main,
    score_candidate,
    score_net_economics,
    score_safety_status,
)

# ===========================================================================
# Test-First Metadata
# ===========================================================================
#
# 1. Welche Regel wird geschützt?
#    Der Offline Strategy League Scorer v1 muss die Scoring Formula v1 (#3682)
#    exakt und fail-closed umsetzen: Hard-Gate-Fail => Sentinel (ranking_ready
#    false, alle Scores 0.0); PARK ist Research-Hold (keine Promotion); fehlende
#    Paper-Reference ist ein Blocker; Output ist schema-konform.
#
# 2. Welche Testart?
#    Bauteil-Tests (Dimensions-/Gate-Funktionen), Schutz-Tests (fail-closed),
#    Ketten-Tests (PEP -> Report -> Schema-Validierung, CLI).
#
# 3. Welche Entscheidung wird sicherer?
#    "Der Offline-Scorer liefert schema-konforme, fail-closed Bewertungen und
#     autorisiert nichts (keine Promotion, keine Capital Allocation)."
#
# Metadata:
#   test_id:      cdb-test-offline-league-scorer-3684
#   test_type:    mixed (Bauteil / Schutz / Ketten)
#   cdb_area:     validation
#   rule_ref:     PROFITABILITY_LEAGUE_SCORING_FORMULA_V1
#   issue_ref:    #3684 (follows #3682, #3383, #3040)
#   surrealdb_export: false
# ===========================================================================


def _ranking_ready_pep() -> dict[str, Any]:
    """A hypothetical, schema-valid, fully ranking-ready PEP."""

    return {
        "schema_version": "profitability_evidence_packet.v1",
        "evidence_packet_id": "pep-ranking-ready-v1",
        "candidate_id": "cand-ranking-ready-v1",
        "generated_at": "2026-07-02T12:00:00+00:00",
        "dataset_id": "btcusdt-mexc-multiwindow",
        "dataset_fingerprint": "sha256:" + "a" * 64,
        "source_run_refs": ["run-1", "run-2", "run-3", "run-4", "run-5"],
        "gross_return": 0.12,
        "net_return": 0.08,
        "fees": 1200.0,
        "spread_cost": 300.0,
        "slippage_cost": 150.0,
        "profit_factor": 1.6,
        "expectancy": 0.02,
        "win_rate": 0.55,
        "avg_win": 220.0,
        "avg_loss": 140.0,
        "max_drawdown": 0.08,
        "loss_streak": 2,
        "trade_count": 42,
        "regime_scorecard": {
            "status": "ok",
            "artifact_ref": "artifacts/regime.json",
            "summary": "ok",
        },
        "scenario_results": [
            {
                "scenario_id": "w1",
                "status": "PASS",
                "net_return": 0.05,
                "max_drawdown": 0.06,
                "notes": "",
            },
            {
                "scenario_id": "w2",
                "status": "PASS",
                "net_return": 0.03,
                "max_drawdown": 0.07,
                "notes": "",
            },
            {
                "scenario_id": "w3",
                "status": "WARNING",
                "net_return": 0.01,
                "max_drawdown": 0.09,
                "notes": "",
            },
        ],
        "replay_vs_paper_status": "aligned",
        "simulator_drift": "none",
        "risk_blocks": 0,
        "kill_switch_events": 0,
        "recommendation": "PROMOTE_TO_NEXT_RESEARCH_GATE",
        "limitations": ["research only"],
        "safety_boundaries": ["LR remains NO-GO."],
    }


def _sentinel_pep() -> dict[str, Any]:
    """Ranking-ready PEP mutated into the sentinel case (paper not run)."""

    pep = _ranking_ready_pep()
    pep["candidate_id"] = "cand-sentinel-v1"
    pep["evidence_packet_id"] = "pep-sentinel-v1"
    pep["replay_vs_paper_status"] = "not_run"
    pep["simulator_drift"] = "not_assessed"
    pep["recommendation"] = "PARK"
    return pep


# --------------------------------------------------------------------------- #
# Weights / configuration invariants
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_weights_sum_to_100_and_match_dimensions() -> None:
    assert sum(_WEIGHTS.values()) == pytest.approx(100.0)
    assert set(_WEIGHTS) == set(_DIMENSION_ORDER)
    assert len(_DIMENSION_ORDER) == 6


# --------------------------------------------------------------------------- #
# Sentinel case (mandatory): replay_vs_paper_status=not_run
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_sentinel_not_run_forces_ranking_false_and_zero_scores() -> None:
    result = score_candidate(_sentinel_pep())

    assert result.ranking_ready is False
    assert result.sentinel_mode is True
    assert result.total_score == 0.0
    assert all(dim.score == 0.0 for dim in result.dimension_scores)
    assert {dim.dimension for dim in result.dimension_scores} == set(_DIMENSION_ORDER)

    joined = " ".join(result.hard_gate_failures)
    assert "replay_vs_paper_status=not_run" in joined
    assert "simulator_drift=not_assessed" in joined
    assert any(FORMULA_REF in note for note in result.limitations_summary)


@pytest.mark.unit
def test_sentinel_single_candidate_report_is_partial() -> None:
    report = build_league_table_report([_sentinel_pep()])
    assert report["table_status"] == "PARTIAL"
    assert report["candidate_rankings"][0]["ranking_ready"] is False
    assert report["candidate_rankings"][0]["total_score"] == 0.0


# --------------------------------------------------------------------------- #
# Ranking-ready case (mandatory): all gates pass
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_ranking_ready_candidate_computes_real_scores() -> None:
    result = score_candidate(_ranking_ready_pep())

    assert result.ranking_ready is True
    assert result.sentinel_mode is False
    assert 0.0 < result.total_score <= 100.0

    dims = result.dimension_map()
    assert dims["NET_ECONOMICS"] == pytest.approx(66.0)
    assert dims["PAPER_REFERENCE_CONFIDENCE"] == pytest.approx(95.0)
    assert dims["SAFETY_STATUS"] == pytest.approx(70.0)
    assert dims["EVIDENCE_COMPLETENESS"] == pytest.approx(100.0)
    assert dims["EXECUTION_REALISM"] == pytest.approx(90.0)


@pytest.mark.unit
def test_ranking_ready_report_is_complete_and_schema_valid() -> None:
    report = build_league_table_report(
        [_ranking_ready_pep()], report_id="pltr-ranking-ready-test-3684"
    )
    assert report["table_status"] == "COMPLETE"
    assert report["model_id"] == DEFAULT_MODEL_ID
    assert report["candidate_rankings"][0]["rank"] == 1
    assert report["candidate_rankings"][0]["ranking_ready"] is True
    # Must not raise:
    _validate_report(report)


# --------------------------------------------------------------------------- #
# Dimension formula spot-checks
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_net_economics_negative_example_matches_formula() -> None:
    pep = _ranking_ready_pep()
    pep["net_return"] = -0.1221562421
    pep["max_drawdown"] = 0.05  # below penalty threshold
    assert score_net_economics(pep) == pytest.approx(19.46, abs=0.01)


@pytest.mark.unit
def test_net_economics_null_is_fail_closed_zero() -> None:
    pep = _ranking_ready_pep()
    pep["net_return"] = None
    assert score_net_economics(pep) == 0.0


@pytest.mark.unit
def test_safety_status_park_is_45() -> None:
    pep = _ranking_ready_pep()
    pep["recommendation"] = "PARK"
    assert score_safety_status(pep) == pytest.approx(45.0)


@pytest.mark.unit
def test_safety_status_kill_switch_caps_low() -> None:
    pep = _ranking_ready_pep()
    pep["kill_switch_events"] = 1
    assert score_safety_status(pep) <= 10.0


# --------------------------------------------------------------------------- #
# PARK as research hold (computed, not promotion)
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_park_negative_economics_is_computed_not_sentinel_not_ranking_ready() -> None:
    pep = _ranking_ready_pep()
    pep["recommendation"] = "PARK"
    pep["gross_return"] = -0.01
    pep["net_return"] = -0.02

    result = score_candidate(pep)

    assert result.sentinel_mode is False  # gates 1-9 pass
    assert result.ranking_ready is False  # economics gate fails for PARK
    assert result.dimension_map()["SAFETY_STATUS"] == pytest.approx(45.0)
    assert result.total_score > 0.0  # computed mode, not sentinel
    assert any("PARK is a research hold" in note for note in result.limitations_summary)


# --------------------------------------------------------------------------- #
# Hard gates / missing paper reference blocker
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_missing_reference_is_hard_gate() -> None:
    pep = _ranking_ready_pep()
    pep["replay_vs_paper_status"] = "missing_reference"
    failures = hard_gate_failures(pep)
    assert any("replay_vs_paper_status=missing_reference" in note for note in failures)


@pytest.mark.unit
def test_low_trade_count_is_hard_gate() -> None:
    pep = _ranking_ready_pep()
    pep["trade_count"] = 5
    failures = hard_gate_failures(pep)
    assert any("trade_count" in note for note in failures)


@pytest.mark.unit
def test_dataset_quality_blocked_is_hard_gate() -> None:
    pep = _ranking_ready_pep()
    failures = hard_gate_failures(pep, dataset_quality_verdict="BLOCKED")
    assert any("dataset quality verdict=BLOCKED" in note for note in failures)


# --------------------------------------------------------------------------- #
# Table status + ordering
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_ready_candidates_sort_before_not_ready() -> None:
    ready = _ranking_ready_pep()
    sentinel = _sentinel_pep()
    report = build_league_table_report([sentinel, ready])
    rankings = report["candidate_rankings"]
    assert rankings[0]["candidate_id"] == "cand-ranking-ready-v1"
    assert rankings[0]["rank"] == 1
    assert rankings[0]["ranking_ready"] is True
    assert rankings[1]["ranking_ready"] is False
    assert report["table_status"] == "PARTIAL"


@pytest.mark.unit
def test_all_unsafe_candidates_block_table() -> None:
    pep_a = _ranking_ready_pep()
    pep_a["candidate_id"] = "cand-unsafe-a"
    pep_a["recommendation"] = "UNSAFE"
    pep_b = _ranking_ready_pep()
    pep_b["candidate_id"] = "cand-unsafe-b"
    pep_b["recommendation"] = "REJECT"

    report = build_league_table_report([pep_a, pep_b])
    assert report["table_status"] == "BLOCKED"
    assert all(c["ranking_ready"] is False for c in report["candidate_rankings"])


# --------------------------------------------------------------------------- #
# Fail-closed guards
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_empty_peps_raises() -> None:
    with pytest.raises(ProfitabilityLeagueScorerError):
        build_league_table_report([])


@pytest.mark.unit
def test_missing_candidate_id_raises() -> None:
    with pytest.raises(ProfitabilityLeagueScorerError):
        score_candidate({"recommendation": "PARK"})


@pytest.mark.unit
def test_deterministic_scoring_is_stable() -> None:
    pep = _ranking_ready_pep()
    first = score_candidate(copy.deepcopy(pep))
    second = score_candidate(copy.deepcopy(pep))
    assert first.total_score == second.total_score
    assert first.dimension_map() == second.dimension_map()


# --------------------------------------------------------------------------- #
# Read-only CLI
# --------------------------------------------------------------------------- #


@pytest.mark.unit
def test_cli_emits_report_to_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pep_path = tmp_path / "pep.json"
    pep_path.write_text(json.dumps(_ranking_ready_pep()), encoding="utf-8")

    exit_code = main(["--pep", str(pep_path), "--report-id", "pltr-cli-stdout-3684"])
    assert exit_code == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "profitability_league_table_report.v1"
    assert payload["report_id"] == "pltr-cli-stdout-3684"
    assert payload["table_status"] == "COMPLETE"


@pytest.mark.unit
def test_cli_writes_out_json(tmp_path: Path) -> None:
    pep_path = tmp_path / "pep.json"
    pep_path.write_text(json.dumps(_sentinel_pep()), encoding="utf-8")
    out_path = tmp_path / "report.json"

    exit_code = main(
        [
            "--pep",
            str(pep_path),
            "--report-id",
            "pltr-cli-file-3684",
            "--out-json",
            str(out_path),
        ]
    )
    assert exit_code == 0
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert written["table_status"] == "PARTIAL"
    assert written["candidate_rankings"][0]["total_score"] == 0.0


@pytest.mark.unit
def test_cli_invalid_pep_file_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text('{"schema_version": "wrong"}', encoding="utf-8")

    exit_code = main(["--pep", str(bad_path)])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "ERROR:" in captured.err
