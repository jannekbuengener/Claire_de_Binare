from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict

import jsonschema
import pytest

from services.validation.profitability_evidence_packet_assembler import (
    ProfitabilityEvidencePacketAssemblerError,
    _deterministic_json_dumps,
    _read_json_payload,
    _sha256_hex,
    _sha256_ref,
    _validate_document,
    _validate_payload_against_schema,
    build_profitability_evidence_packet,
    build_profitability_evidence_packet_markdown,
    main,
    _normalize_path,
    _build_packet_id,
    _parse_generated_at_utc,
    _classify_replay_vs_paper,
    _build_regime_scorecard_block,
    _dedupe_preserve_order,
    _slugify_for_packet_id,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS_DIR = PROJECT_ROOT / "docs" / "contracts"

# ===========================================================================
# Test-First Metadata (Pilot: CDB-PILOT-001)
# ===========================================================================
#
# 1. Welche Regel wird geschützt?
#    Profitability Evidence Packet Assembly muss deterministisch,
#    schema-konform und fail-closed sein. Kein undichter Fehlerpfad
#    darf zum Absturz oder stillem Datenverlust führen.
#
# 2. Welche Testart passt?
#    Hauptsaechlich Bauteil-Tests (isolierte Funktionen/Klassen).
#    Einige Schutz-Tests (fail-closed bei fehlenden/kaputten Inputs).
#    Einige Ketten-Tests (Pipeline vom Input ueber Validierung zum Packet).
#    Klassifikation pro Gruppe unten.
#
# 3. Welche Entscheidung wird sicherer?
#    "Der ProfitabilityEvidencePacketAssembler produziert zuverlaessig
#     schema-konforme Packete, failt geschlossen bei fehlenden/kaputten
#     Inputs und ist deterministisch."
#
# 4. Welche Metadaten braucht der Test? (siehe Block unten)
#
# 5. Wie wird das Ergebnis weiterverarbeitet?
#    CI: pytest-sammlung + JUnit-Report. JSON-Export ist fuer
#    spaetere SurrealDB-Nutzung freigegeben
#    (surrealdb_export: true im Pilot). Kein DB-Write in diesem Slice.
#
# Metadata fields (TEST_FIRST_PROCESSING_CONTRACT.md §6):
#   test_id:              cdb-test-pilot-001
#   test_title:           Profitability Evidence Packet Assembler
#   test_type:            mixed (Bauteil / Schutz / Ketten; siehe Gruppe)
#   cdb_area:             validation
#   rule_ref:             PROFITABILITY_EVIDENCE_PACKET_SCHEMA_CONFORMANCE
#   decision_ref:         d-2026-04-08-evidence-packet-structure
#   issue_ref:            #1492
#   pr_ref:               (wird beim Pilot-PR gesetzt)
#   evidence_ref:         docs/contracts/profitability_evidence_packet.v1.schema.json
#   code_area:            ProfitabilityEvidencePacketAssembler
#   security_relevant:    false
#   live_relevant:        false
#   profitability_relevant: true
#   surrealdb_export:     true
#   ci_artifact:          test-report
#
# Gruppen-Klassifikation:
#   Happy-Path + CLI main  → Ketten-Test  (Pipeline-Durchstich)
#   Determinism + Serializer → Bauteil-Test (Determinismus-Garantie)
#   Missing/Invalid/Schema/Legacy → Schutz-Test (fail-closed)
#   Alle anderen           → Bauteil-Test  (isolierte Logik)
# ===========================================================================


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_candidate(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "profitability_candidate_contract.v1",
        "candidate_id": "cand-test-001",
        "strategy_family": "primary_breakout_v1",
        "symbol_universe": ["BTCUSDT"],
        "timeframe": "1h",
        "direction": "long_only",
        "regime_scope": {
            "allowed_regimes": ["trend"],
            "blocked_regimes": ["choppy"],
            "freshness_required": True,
        },
        "parameter_set": {},
        "hypothesis": "Test hypothesis for profitability evidence packet assembler unit tests.",
        "risk_assumptions": ["No risk"],
        "execution_assumptions": ["Standard execution"],
        "status": "ARVP_VALIDATED",
        "allowed_next_gate": "STRESS_TESTED",
        "reject_reason": None,
        "unsafe_zones": [],
        "limitations": ["Test limitation"],
    }
    base.update(overrides)
    return base


def _make_valid_dq(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "profitability_dataset_quality_report.v1",
        "report_id": "dq-test-001",
        "dataset_id": "ds-test-001",
        "dataset_fingerprint": "sha256:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "content_fingerprint": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "generated_at": "2026-06-22T12:00:00Z",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "requested_window": {"start_ts_ms": 1000, "end_ts_ms": 2000},
        "observed_window": {
            "start_ts_ms": 1000,
            "end_ts_ms": 2000,
            "candles_expected": 1000,
            "candles_observed": 998,
        },
        "coverage_summary": {
            "coverage_ratio": 0.998,
            "missing_candle_count": 2,
            "duplicate_timestamp_count": 0,
            "out_of_order_count": 0,
            "timeframe_mismatch_count": 0,
        },
        "checks": {
            "coverage_check": {"status": "PASS", "summary": "Coverage ok"},
            "missing_candle_check": {
                "status": "WARNING",
                "summary": "Missing 2 candles",
            },
            "duplicate_check": {"status": "PASS", "summary": "No duplicates"},
            "ordering_check": {"status": "PASS", "summary": "In order"},
            "timeframe_consistency_check": {"status": "PASS", "summary": "Consistent"},
            "symbol_window_metadata_check": {
                "status": "PASS",
                "summary": "Metadata ok",
            },
            "dataset_fingerprint_check": {
                "status": "PASS",
                "summary": "Fingerprint matches",
            },
        },
        "quality_verdict": "PASS",
        "blocking_reasons": [],
        "limitations": ["Some data gaps"],
    }
    base.update(overrides)
    return base


def _make_valid_replay(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "profitability_replay_report.v1",
        "candidate_id": "cand-test-001",
        "replay_run_id": "replay-abcdef123456-2026",
        "strategy_id": "pbv1-test",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "generated_at": "2026-06-22T12:00:00Z",
        "gross_return": 0.05,
        "profit_factor": 1.5,
        "expectancy": 0.02,
        "win_rate": 0.55,
        "avg_win": 0.04,
        "avg_loss": 0.02,
        "max_drawdown": 0.08,
        "loss_streak": 3,
        "trade_count": 100,
        "data_integrity_ok": True,
        "deterministic_replay_ok": True,
        "notes": ["Replay completed"],
    }
    base.update(overrides)
    return base


def _make_valid_scenario(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "profitability_scenario_stress_summary.v1",
        "stress_summary_id": "pss-test-001",
        "candidate_id": "cand-test-001",
        "catalog_id": "psc-test-001",
        "generated_at": "2026-06-22T12:00:00Z",
        "overall_stress_outcome": "PASS",
        "scenario_results": [
            {
                "scenario_id": "slippage_high",
                "domain": "SLIPPAGE",
                "severity": "HIGH",
                "status": "PASS",
                "net_return_delta": None,
                "max_drawdown_delta": 0.02,
                "impact_summary": "Slippage impact within bounds",
            }
        ],
        "recommendation_impact": {
            "promote_allowed": True,
            "park_required": False,
            "reject_required": False,
            "notes": "No impact",
        },
        "limitations": ["Scenario set limited"],
    }
    base.update(overrides)
    return base


def _make_valid_economics(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "profitability_execution_economics_assessment.v1",
        "assessment_id": "peea-test-001",
        "candidate_id": "cand-test-001",
        "model_id": "peem-test-001",
        "generated_at": "2026-06-22T12:00:00Z",
        "gross_return": 0.05,
        "net_return": 0.02,
        "cost_breakdown": {
            "fees": 0.01,
            "spread_cost": 0.01,
            "slippage_cost": 0.01,
            "other_friction_cost": 0.0,
            "total_cost": 0.03,
        },
        "assessment_status": "PASS",
        "ranking_ready": True,
        "assumption_findings": [
            {
                "category": "FEE",
                "severity": "INFO",
                "summary": "Fees within expected range",
            }
        ],
        "limitations": ["Cost model assumes standard tier"],
    }
    base.update(overrides)
    return base


def _make_valid_harvester(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "profitability_harvester_ref.v1",
        "candidate_id": "cand-test-001",
        "source_run_refs": ["run-harvester-001"],
        "risk_blocks": 0,
        "kill_switch_events": 0,
        "limitations": ["Harvester run had partial coverage"],
        "safety_boundaries": ["No live execution without human gate"],
    }
    base.update(overrides)
    return base


def _make_valid_compare(**overrides: Any) -> dict[str, Any]:
    base = {
        "comparison_fingerprint": "ab" * 32,
        "status": "aligned",
        "paper_provenance_id": "paper-001",
        "replay_run_id": "replay-abcdef123456-2026",
        "symbol": "BTCUSDT",
        "strategy_id": "pbv1-test",
        "signal_count_delta": 0,
        "order_count_delta": 0,
        "fill_count_delta": 0,
        "inferred_unfilled_count_delta": 0,
        "signal_context_delta": 0,
        "signal_count_false_neutral_detected": False,
        "window_start_utc_replay": "2026-06-01T00:00:00Z",
        "window_end_utc_replay": "2026-06-22T00:00:00Z",
        "window_start_utc_paper": "2026-06-01T00:00:00Z",
        "window_end_utc_paper": "2026-06-22T00:00:00Z",
    }
    base.update(overrides)
    return base


def _make_valid_scorecard(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "arvp_regime_scorecard.v1",
        "status": "ok",
        "run_id": "replay-abcdef123456-2026",
        "source": "replay_trace",
        "scorecard_fingerprint": "cd" * 32,
        "segments": [
            {
                "regime_id": "trend",
                "observation_count": 100,
                "signal_count": 10,
                "trade_close_count": 5,
            }
        ],
        "notes": ["Scorecard completed"],
    }
    base.update(overrides)
    return base


def _write_json(
    tmp_path: Path, subdir: str, filename: str, payload: dict[str, Any]
) -> Path:
    dirpath = tmp_path / subdir
    dirpath.mkdir(parents=True, exist_ok=True)
    filepath = dirpath / filename
    filepath.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return filepath


def _write_required_inputs(
    tmp_path: Path,
    *,
    candidate: dict[str, Any] | None = None,
    dq: dict[str, Any] | None = None,
    replay: dict[str, Any] | None = None,
    scenario: dict[str, Any] | None = None,
    economics: dict[str, Any] | None = None,
    harvester: dict[str, Any] | None = None,
) -> dict[str, Path]:
    return {
        "candidate": _write_json(
            tmp_path, "inputs", "candidate.json", candidate or _make_valid_candidate()
        ),
        "dq": _write_json(tmp_path, "inputs", "dq.json", dq or _make_valid_dq()),
        "replay": _write_json(
            tmp_path, "inputs", "replay.json", replay or _make_valid_replay()
        ),
        "scenario": _write_json(
            tmp_path, "inputs", "scenario.json", scenario or _make_valid_scenario()
        ),
        "economics": _write_json(
            tmp_path, "inputs", "economics.json", economics or _make_valid_economics()
        ),
        "harvester": _write_json(
            tmp_path, "inputs", "harvester.json", harvester or _make_valid_harvester()
        ),
    }


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def _build_result(
    tmp_path: Path, generated_at: str = "2026-06-22T12:00:00Z", **overrides: Any
):
    paths = _write_required_inputs(tmp_path)
    candidate = _validate_document(
        "candidate_contract",
        paths["candidate"],
        CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json",
    )
    dq = _validate_document(
        "data_quality_report",
        paths["dq"],
        CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json",
    )
    replay = _validate_document(
        "replay_report",
        paths["replay"],
        CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
    )
    scenario = _validate_document(
        "scenario_stress_summary",
        paths["scenario"],
        CONTRACTS_DIR / "profitability_scenario_stress_summary.v1.schema.json",
    )
    economics = _validate_document(
        "execution_economics_assessment",
        paths["economics"],
        CONTRACTS_DIR / "profitability_execution_economics_assessment.v1.schema.json",
    )
    harvester = _validate_document(
        "harvester_ref",
        paths["harvester"],
        CONTRACTS_DIR / "profitability_harvester_ref.v1.schema.json",
    )

    optional_compare = None
    optional_scorecard = None
    if "compare" in overrides:
        path = _write_json(tmp_path, "inputs", "compare.json", overrides["compare"])
        optional_compare = _validate_document(
            "replay_vs_paper_compare",
            path,
            CONTRACTS_DIR / "shadow_comparison.v1.schema.json",
        )
    if "scorecard" in overrides:
        path = _write_json(tmp_path, "inputs", "scorecard.json", overrides["scorecard"])
        optional_scorecard = _validate_document(
            "regime_scorecard",
            path,
            CONTRACTS_DIR / "arvp_regime_scorecard.v1.schema.json",
        )

    result = build_profitability_evidence_packet(
        candidate_contract=candidate,
        data_quality_report=dq,
        replay_report=replay,
        scenario_stress_summary=scenario,
        economics_assessment=economics,
        harvester_ref=harvester,
        generated_at_utc=generated_at,
        replay_vs_paper_compare=optional_compare,
        regime_scorecard=optional_scorecard,
    )
    return result, paths


@pytest.mark.unit
def test_happy_path_creates_valid_json_and_markdown(tmp_path: Path) -> None:
    result, _ = _build_result(tmp_path)

    packet = result.packet
    assert packet["schema_version"] == "profitability_evidence_packet.v1"
    assert packet["candidate_id"] == "cand-test-001"
    assert packet["evidence_packet_id"].startswith("pep-test-001-")
    assert packet["generated_at"] == "2026-06-22T12:00:00Z"
    assert packet["gross_return"] == 0.05
    assert packet["recommendation"] == "NO_RECOMMENDATION"
    assert packet["replay_vs_paper_status"] == "not_run"
    assert packet["simulator_drift"] == "not_assessed"

    schema_path = CONTRACTS_DIR / "profitability_evidence_packet.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = list(validator.iter_errors(packet))
    assert not errors, f"Schema validation errors: {errors}"

    md = result.markdown
    assert md.startswith("# Profitability Evidence Packet Summary")
    assert "cand-test-001" in md
    assert "NO_RECOMMENDATION" in md
    assert packet["evidence_packet_id"] in md
    assert "not_run" in md
    assert "not_assessed" in md


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_determinism_identical_inputs_produce_identical_json(tmp_path: Path) -> None:
    generated_at = "2026-06-22T12:00:00Z"
    result1, _ = _build_result(tmp_path, generated_at=generated_at)
    result2, _ = _build_result(tmp_path, generated_at=generated_at)

    json1 = _deterministic_json_dumps(result1.packet)
    json2 = _deterministic_json_dumps(result2.packet)
    assert json1 == json2
    assert (
        hashlib.sha256(json1.encode("utf-8")).hexdigest()
        == hashlib.sha256(json2.encode("utf-8")).hexdigest()
    )


@pytest.mark.unit
def test_determinism_different_utc_produces_different_id(tmp_path: Path) -> None:
    result1, _ = _build_result(tmp_path, generated_at="2026-06-22T12:00:00Z")
    result2, _ = _build_result(tmp_path, generated_at="2026-06-23T12:00:00Z")

    assert result1.packet["evidence_packet_id"] != result2.packet["evidence_packet_id"]


# ---------------------------------------------------------------------------
# Missing required inputs (fails closed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_missing_economics_fails_closed(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    candidate = _validate_document(
        "candidate_contract",
        paths["candidate"],
        CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json",
    )
    dq = _validate_document(
        "data_quality_report",
        paths["dq"],
        CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json",
    )
    replay = _validate_document(
        "replay_report",
        paths["replay"],
        CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
    )
    scenario = _validate_document(
        "scenario_stress_summary",
        paths["scenario"],
        CONTRACTS_DIR / "profitability_scenario_stress_summary.v1.schema.json",
    )
    harvester = _validate_document(
        "harvester_ref",
        paths["harvester"],
        CONTRACTS_DIR / "profitability_harvester_ref.v1.schema.json",
    )

    with pytest.raises(TypeError):
        build_profitability_evidence_packet(
            candidate_contract=candidate,
            data_quality_report=dq,
            replay_report=replay,
            scenario_stress_summary=scenario,
            harvester_ref=harvester,
            generated_at_utc="2026-06-22T12:00:00Z",
        )


@pytest.mark.unit
def test_missing_replay_report_path_fails_closed(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_such_file.json"
    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError, match="Failed to read"
    ):
        _validate_document(
            "replay_report",
            nonexistent,
            CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
        )


@pytest.mark.unit
def test_missing_data_quality_path_fails_closed(tmp_path: Path) -> None:
    nonexistent = tmp_path / "no_such_dq.json"
    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError, match="Failed to read"
    ):
        _validate_document(
            "data_quality_report",
            nonexistent,
            CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json",
        )


# ---------------------------------------------------------------------------
# Invalid JSON
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invalid_json_fails_closed(tmp_path: Path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json", encoding="utf-8")
    with pytest.raises(ProfitabilityEvidencePacketAssemblerError, match="Invalid JSON"):
        _validate_document(
            "replay_report",
            bad_file,
            CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
        )


@pytest.mark.unit
def test_non_dict_json_fails_closed(tmp_path: Path) -> None:
    bad_file = tmp_path / "array.json"
    bad_file.write_text("[1,2,3]", encoding="utf-8")
    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError, match="must be an object"
    ):
        _validate_document(
            "replay_report",
            bad_file,
            CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
        )


# ---------------------------------------------------------------------------
# Schema mismatch
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_schema_mismatch_fails_closed(tmp_path: Path) -> None:
    invalid_payload = {"invalid": "data", "schema_version": "wrong"}
    bad_file = _write_json(tmp_path, "inputs", "bad_replay.json", invalid_payload)
    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError, match="Schema mismatch"
    ):
        _validate_document(
            "replay_report",
            bad_file,
            CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
        )


@pytest.mark.unit
def test_bad_candidate_id_mismatch_fails_closed(tmp_path: Path) -> None:
    paths = _write_required_inputs(
        tmp_path, candidate=_make_valid_candidate(candidate_id="cand-other-001")
    )
    candidate = _validate_document(
        "candidate_contract",
        paths["candidate"],
        CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json",
    )
    dq = _validate_document(
        "data_quality_report",
        paths["dq"],
        CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json",
    )
    replay = _validate_document(
        "replay_report",
        paths["replay"],
        CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
    )
    scenario = _validate_document(
        "scenario_stress_summary",
        paths["scenario"],
        CONTRACTS_DIR / "profitability_scenario_stress_summary.v1.schema.json",
    )
    economics = _validate_document(
        "execution_economics_assessment",
        paths["economics"],
        CONTRACTS_DIR / "profitability_execution_economics_assessment.v1.schema.json",
    )
    harvester = _validate_document(
        "harvester_ref",
        paths["harvester"],
        CONTRACTS_DIR / "profitability_harvester_ref.v1.schema.json",
    )

    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError,
        match="replay_report.candidate_id must match",
    ):
        build_profitability_evidence_packet(
            candidate_contract=candidate,
            data_quality_report=dq,
            replay_report=replay,
            scenario_stress_summary=scenario,
            economics_assessment=economics,
            harvester_ref=harvester,
            generated_at_utc="2026-06-22T12:00:00Z",
        )


# ---------------------------------------------------------------------------
# Optional inputs classification
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_optional_compare_not_provided_classified_correctly(tmp_path: Path) -> None:
    result, _ = _build_result(tmp_path)
    assert result.packet["replay_vs_paper_status"] == "not_run"
    assert result.packet["simulator_drift"] == "not_assessed"
    roles = [e["artifact_role"] for e in result.packet.get("missing_evidence", [])]
    assert "replay_vs_paper_compare" in roles


@pytest.mark.unit
def test_optional_scorecard_not_provided_classified_correctly(tmp_path: Path) -> None:
    result, _ = _build_result(tmp_path)
    assert result.packet["regime_scorecard"]["status"] == "unavailable"
    roles = [e["artifact_role"] for e in result.packet.get("missing_evidence", [])]
    assert "regime_scorecard" in roles


@pytest.mark.unit
def test_optional_compare_provided_aligned(tmp_path: Path) -> None:
    result, _ = _build_result(tmp_path, compare=_make_valid_compare())
    assert result.packet["replay_vs_paper_status"] == "aligned"
    assert result.packet["simulator_drift"] == "none"


@pytest.mark.unit
def test_optional_scorecard_provided(tmp_path: Path) -> None:
    result, _ = _build_result(tmp_path, scorecard=_make_valid_scorecard())
    assert result.packet["regime_scorecard"]["status"] == "ok"
    assert result.packet["regime_scorecard"]["artifact_ref"] is not None


# ---------------------------------------------------------------------------
# Harvester refs propagate
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_harvester_refs_propagate_into_source_run_refs(tmp_path: Path) -> None:
    harvester = _make_valid_harvester(source_run_refs=["run-alpha", "run-beta"])
    paths = _write_required_inputs(tmp_path, harvester=harvester)
    candidate = _validate_document(
        "candidate_contract",
        paths["candidate"],
        CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json",
    )
    dq = _validate_document(
        "data_quality_report",
        paths["dq"],
        CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json",
    )
    replay = _validate_document(
        "replay_report",
        paths["replay"],
        CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
    )
    scenario = _validate_document(
        "scenario_stress_summary",
        paths["scenario"],
        CONTRACTS_DIR / "profitability_scenario_stress_summary.v1.schema.json",
    )
    economics = _validate_document(
        "execution_economics_assessment",
        paths["economics"],
        CONTRACTS_DIR / "profitability_execution_economics_assessment.v1.schema.json",
    )
    harvester_doc = _validate_document(
        "harvester_ref",
        paths["harvester"],
        CONTRACTS_DIR / "profitability_harvester_ref.v1.schema.json",
    )

    result = build_profitability_evidence_packet(
        candidate_contract=candidate,
        data_quality_report=dq,
        replay_report=replay,
        scenario_stress_summary=scenario,
        economics_assessment=economics,
        harvester_ref=harvester_doc,
        generated_at_utc="2026-06-22T12:00:00Z",
    )

    refs = result.packet["source_run_refs"]
    assert "run-alpha" in refs
    assert "run-beta" in refs
    assert result.packet["risk_blocks"] == 0
    assert result.packet["kill_switch_events"] == 0


@pytest.mark.unit
def test_harvester_safety_boundaries_propagate(tmp_path: Path) -> None:
    harvester = _make_valid_harvester(safety_boundaries=["Custom safety boundary"])
    paths = _write_required_inputs(tmp_path, harvester=harvester)
    candidate = _validate_document(
        "candidate_contract",
        paths["candidate"],
        CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json",
    )
    dq = _validate_document(
        "data_quality_report",
        paths["dq"],
        CONTRACTS_DIR / "profitability_dataset_quality_report.v1.schema.json",
    )
    replay = _validate_document(
        "replay_report",
        paths["replay"],
        CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
    )
    scenario = _validate_document(
        "scenario_stress_summary",
        paths["scenario"],
        CONTRACTS_DIR / "profitability_scenario_stress_summary.v1.schema.json",
    )
    economics = _validate_document(
        "execution_economics_assessment",
        paths["economics"],
        CONTRACTS_DIR / "profitability_execution_economics_assessment.v1.schema.json",
    )
    harvester_doc = _validate_document(
        "harvester_ref",
        paths["harvester"],
        CONTRACTS_DIR / "profitability_harvester_ref.v1.schema.json",
    )

    result = build_profitability_evidence_packet(
        candidate_contract=candidate,
        data_quality_report=dq,
        replay_report=replay,
        scenario_stress_summary=scenario,
        economics_assessment=economics,
        harvester_ref=harvester_doc,
        generated_at_utc="2026-06-22T12:00:00Z",
    )

    boundaries = result.packet["safety_boundaries"]
    assert "Custom safety boundary" in boundaries


# ---------------------------------------------------------------------------
# Legacy / non-canonical economics payload rejected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_legacy_economics_payload_rejected(tmp_path: Path) -> None:
    legacy = {"schema_version": "v0_legacy", "candidate_id": "cand-test-001"}
    bad_file = _write_json(tmp_path, "inputs", "legacy_economics.json", legacy)
    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError, match="Schema mismatch"
    ):
        _validate_document(
            "execution_economics_assessment",
            bad_file,
            CONTRACTS_DIR
            / "profitability_execution_economics_assessment.v1.schema.json",
        )


# ---------------------------------------------------------------------------
# Serializer preserves null and sorts stably
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deterministic_json_dumps_preserves_null() -> None:
    payload = {"a": None, "b": 1, "c": "hello"}
    dumped = _deterministic_json_dumps(payload)
    assert '"a":null' in dumped
    assert dumped == '{"a":null,"b":1,"c":"hello"}'


@pytest.mark.unit
def test_deterministic_json_dumps_sorted_keys() -> None:
    payload = {"z": 1, "a": 2, "m": 3}
    dumped = _deterministic_json_dumps(payload)
    assert dumped == '{"a":2,"m":3,"z":1}'


@pytest.mark.unit
def test_deterministic_json_dumps_pretty() -> None:
    payload = {"a": 1, "b": 2}
    dumped = _deterministic_json_dumps(payload, pretty=True)
    assert "  " in dumped
    assert "\n" in dumped


# ---------------------------------------------------------------------------
# _build_packet_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_packet_id_format() -> None:
    artifacts = [
        {
            "artifact_role": "candidate_contract",
            "path": "test.json",
            "schema_ref": "schema.json",
            "sha256": "sha256:ab" * 32,
        }
    ]
    pid = _build_packet_id("cand-test-001", "2026-06-22T12:00:00Z", artifacts)
    assert pid.startswith("pep-test-001-")
    assert len(pid) > 20


# ---------------------------------------------------------------------------
# _parse_generated_at_utc
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_generated_at_utc_valid() -> None:
    result = _parse_generated_at_utc("2026-06-22T12:00:00Z")
    assert result.endswith("Z")
    assert "2026-06-22" in result


@pytest.mark.unit
def test_parse_generated_at_utc_no_tz_fails() -> None:
    with pytest.raises(ProfitabilityEvidencePacketAssemblerError, match="UTC offset"):
        _parse_generated_at_utc("2026-06-22T12:00:00")


@pytest.mark.unit
def test_parse_generated_at_utc_empty_fails() -> None:
    with pytest.raises(ProfitabilityEvidencePacketAssemblerError, match="non-empty"):
        _parse_generated_at_utc("")


# ---------------------------------------------------------------------------
# _classify_replay_vs_paper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_classify_replay_vs_paper_missing() -> None:
    missing: list[dict[str, Any]] = []
    status, drift = _classify_replay_vs_paper(None, missing)
    assert status == "not_run"
    assert drift == "not_assessed"
    assert len(missing) == 1
    assert missing[0]["classification"] == "OPTIONAL_NOT_PROVIDED"


@pytest.mark.unit
def test_classify_replay_vs_paper_aligned() -> None:
    payload = _make_valid_compare(status="aligned")
    missing: list[dict[str, Any]] = []
    from services.validation.profitability_evidence_packet_assembler import (
        ValidatedJsonDocument,
    )

    doc = ValidatedJsonDocument(
        artifact_role="replay_vs_paper_compare",
        path=Path("/fake"),
        display_path="fake.json",
        sha256="sha256:aa",
        schema_ref="shadow_comparison.v1.schema.json",
        payload=payload,
    )
    status, drift = _classify_replay_vs_paper(doc, missing)
    assert status == "aligned"
    assert drift == "none"
    assert len(missing) == 0


# ---------------------------------------------------------------------------
# _build_regime_scorecard_block
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_regime_scorecard_block_missing() -> None:
    missing: list[dict[str, Any]] = []
    block = _build_regime_scorecard_block(None, missing)
    assert block["status"] == "unavailable"
    assert block["artifact_ref"] is None


@pytest.mark.unit
def test_build_regime_scorecard_block_ok() -> None:
    missing: list[dict[str, Any]] = []
    from services.validation.profitability_evidence_packet_assembler import (
        ValidatedJsonDocument,
    )

    doc = ValidatedJsonDocument(
        artifact_role="regime_scorecard",
        path=Path("/fake"),
        display_path="scorecard.json",
        sha256="sha256:bb",
        schema_ref="arvp_regime_scorecard.v1.schema.json",
        payload=_make_valid_scorecard(),
    )
    block = _build_regime_scorecard_block(doc, missing)
    assert block["status"] == "ok"
    assert block["artifact_ref"] == "scorecard.json"


# ---------------------------------------------------------------------------
# CLI main integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_main_happy_path(tmp_path: Path) -> None:
    paths = _write_required_inputs(tmp_path)
    out_json = tmp_path / "out" / "packet.json"
    out_md = tmp_path / "out" / "packet.md"

    exit_code = main(
        [
            "--candidate-contract",
            str(paths["candidate"]),
            "--data-quality-report",
            str(paths["dq"]),
            "--replay-report",
            str(paths["replay"]),
            "--scenario-stress-summary",
            str(paths["scenario"]),
            "--execution-economics-assessment",
            str(paths["economics"]),
            "--harvester-ref",
            str(paths["harvester"]),
            "--generated-at-utc",
            "2026-06-22T12:00:00Z",
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ]
    )
    assert exit_code == 0
    assert out_json.exists()
    assert out_md.exists()

    packet = json.loads(out_json.read_text(encoding="utf-8"))
    assert packet["schema_version"] == "profitability_evidence_packet.v1"


@pytest.mark.unit
def test_main_missing_required_arg_fails() -> None:
    exit_code = main(["--generated-at-utc", "2026-06-22T12:00:00Z"])
    assert exit_code == 1


@pytest.mark.unit
def test_main_bad_input_path_fails(tmp_path: Path) -> None:
    exit_code = main(
        [
            "--candidate-contract",
            str(tmp_path / "nonexistent.json"),
            "--data-quality-report",
            str(tmp_path / "nonexistent.json"),
            "--replay-report",
            str(tmp_path / "nonexistent.json"),
            "--scenario-stress-summary",
            str(tmp_path / "nonexistent.json"),
            "--execution-economics-assessment",
            str(tmp_path / "nonexistent.json"),
            "--harvester-ref",
            str(tmp_path / "nonexistent.json"),
            "--generated-at-utc",
            "2026-06-22T12:00:00Z",
            "--out-json",
            str(tmp_path / "out.json"),
            "--out-md",
            str(tmp_path / "out.md"),
        ]
    )
    assert exit_code == 2


# ---------------------------------------------------------------------------
# Dedupe preserve order
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dedupe_preserve_order() -> None:
    result = _dedupe_preserve_order(["b", "a", "b", "c", "a"])
    assert result == ["b", "a", "c"]


@pytest.mark.unit
def test_dedupe_preserve_order_skips_empty() -> None:
    result = _dedupe_preserve_order(["", "a", " ", "b"])
    assert result == ["a", "b"]


# ---------------------------------------------------------------------------
# Slugify for packet ID
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_slugify_simple() -> None:
    assert _slugify_for_packet_id("cand-test-001") == "cand-test-001"


@pytest.mark.unit
def test_slugify_special_chars() -> None:
    result = _slugify_for_packet_id("hello world/foo.bar")
    assert "--" not in result
    assert result == "hello-world-foo-bar"


@pytest.mark.unit
def test_slugify_empty_fallback() -> None:
    assert _slugify_for_packet_id("!!!") == "packet"


# ---------------------------------------------------------------------------
# Schema validation helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_payload_against_schema_passes() -> None:
    payload = _make_valid_replay()
    _validate_payload_against_schema(
        payload,
        schema_path=CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
        artifact_role="replay_report",
    )


@pytest.mark.unit
def test_validate_payload_against_schema_candidate_passes() -> None:
    payload = _make_valid_candidate()
    _validate_payload_against_schema(
        payload,
        schema_path=CONTRACTS_DIR / "profitability_candidate_contract.v1.schema.json",
        artifact_role="candidate_contract",
    )


@pytest.mark.unit
def test_validate_payload_against_schema_fails() -> None:
    with pytest.raises(
        ProfitabilityEvidencePacketAssemblerError, match="Schema mismatch"
    ):
        _validate_payload_against_schema(
            {"wrong": "data"},
            schema_path=CONTRACTS_DIR / "profitability_replay_report.v1.schema.json",
            artifact_role="replay_report",
        )
