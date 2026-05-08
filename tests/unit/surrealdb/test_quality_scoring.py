"""Unit tests for quality_scoring.py — Knowledge Quality Scoring Service v1.

Issues:
    #2176 — [SURREALDB][CONTEXT][QUALITY-TESTS] Tests for Wave-18 quality scoring
    Parent: #2170 (Wave-18 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/quality_scoring.py.
    All fixtures are inline — no file loading.
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No real datetime.now() — as_of is passed explicitly for determinism.

Coverage:
    - All 8 scoring dimensions produce scores with triggering input.
    - Grade thresholds: blocking < 0.30, watch 0.30–0.50, weak 0.50–0.70, good >= 0.70.
    - Weighted aggregation.
    - Blocking downgrade: any blocking dimension → overall grade capped at watch.
    - Empty bundle (no sources) returns blocking coverage_score.
    - Clean bundle returns good overall grade.
    - Invalid bundle raises QualityScoringError.
    - to_dict() structure.
    - Guardrails in result.
"""

from __future__ import annotations

from typing import Any

import pytest

from tools.surrealdb.quality_scoring import (
    GRADE_BLOCKING,
    GRADE_GOOD,
    GRADE_WATCH,
    GRADE_WEAK,
    GRADES,
    GUARDRAILS,
    SCHEMA_VERSION,
    SCORE_DIMENSIONS,
    QualityScoreResult,
    QualityScoringError,
    _grade,
    score_knowledge_quality_v1,
)

_AS_OF = "2026-05-06T12:00:00+00:00"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _minimal_bundle(scope_id: str = "test-scope") -> dict[str, Any]:
    """Minimal valid bundle with no findings."""
    return {"meta": {"scope_id": scope_id, "level": "system"}}


def _clean_bundle() -> dict[str, Any]:
    """A clean bundle with good scores in all dimensions."""
    return {
        "meta": {"scope_id": "clean-001", "level": "system"},
        "sources": [
            {
                "source_path": "core/domain/models.py",
                "has_documentation": True,
                "has_tests": True,
                "status": "current",
                "file_type": "python",
            },
            {
                "source_path": "core/risk/service.py",
                "has_documentation": True,
                "has_tests": True,
                "status": "current",
                "file_type": "python",
            },
        ],
        "decisions": [
            {
                "decision_id": "dec-001",
                "status": "current",
                "evidence_refs": ["ev-001"],
            },
        ],
        "evidence_items": [
            {
                "evidence_id": "ev-001",
                "strength": "strong",
                "expired": False,
            }
        ],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [
            {"edge_id": "edge-001", "confidence": "high"},
            {"edge_id": "edge-002", "confidence": "high"},
        ],
        "memory_items": [
            {"memory_id": "mem-001", "trust_level": "strong"},
        ],
        "scope_drift_findings": [],
    }


def _blocking_bundle() -> dict[str, Any]:
    """Bundle designed to trigger blocking grade."""
    return {
        "meta": {"scope_id": "blocking-001", "level": "system"},
        "sources": [],
        "decisions": [],
        "evidence_items": [],
        "contradiction_findings": [
            {"contradiction_id": "c-001", "severity": "blocking", "status": "open"},
            {"contradiction_id": "c-002", "severity": "blocking", "status": "open"},
        ],
        "stale_findings": [
            {"stale_id": "s-001", "status": "stale"},
            {"stale_id": "s-002", "status": "stale"},
        ],
        "dependency_edges": [
            {"edge_id": "edge-bad-001", "confidence": "low"},
            {"edge_id": "edge-bad-002", "confidence": "low"},
        ],
        "memory_items": [
            {"memory_id": "mem-blocked", "trust_level": "blocked"},
        ],
        "scope_drift_findings": [
            {"drift_id": "drift-001", "severity": "blocking", "status": "open"},
        ],
    }


def _score(bundle: dict[str, Any], as_of: str = _AS_OF) -> QualityScoreResult:
    return score_knowledge_quality_v1(bundle, as_of=as_of)


# ── Grade threshold tests ─────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.parametrize(
    "score_val,expected_grade",
    [
        (0.0, GRADE_BLOCKING),
        (0.10, GRADE_BLOCKING),
        (0.29, GRADE_BLOCKING),
        (0.30, GRADE_WATCH),
        (0.40, GRADE_WATCH),
        (0.49, GRADE_WATCH),
        (0.50, GRADE_WEAK),
        (0.60, GRADE_WEAK),
        (0.69, GRADE_WEAK),
        (0.70, GRADE_GOOD),
        (0.90, GRADE_GOOD),
        (1.00, GRADE_GOOD),
    ],
)
def test_grade_thresholds(score_val: float, expected_grade: str) -> None:
    """_grade() produces correct grade at each threshold."""
    assert _grade(score_val) == expected_grade


# ── Constants ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_score_dimensions_count() -> None:
    """SCORE_DIMENSIONS has exactly 8 entries."""
    assert len(SCORE_DIMENSIONS) == 8


@pytest.mark.unit
def test_grades_tuple() -> None:
    """GRADES contains the 4 expected grade strings."""
    assert set(GRADES) == {"blocking", "watch", "weak", "good"}


@pytest.mark.unit
def test_guardrails_present() -> None:
    """GUARDRAILS has at least 5 strings."""
    assert len(GUARDRAILS) >= 5
    for g in GUARDRAILS:
        assert isinstance(g, str) and len(g) > 0


# ── Minimal bundle (no sources → blocking coverage) ───────────────────────────


@pytest.mark.unit
def test_minimal_bundle_returns_result() -> None:
    """Minimal bundle with meta only returns a valid QualityScoreResult."""
    result = _score(_minimal_bundle())
    assert isinstance(result, QualityScoreResult)
    assert result.scope_id == "test-scope"
    assert result.overall_grade in GRADES


@pytest.mark.unit
def test_empty_sources_blocking_coverage() -> None:
    """Empty sources list → coverage_score is blocking."""
    bundle = {
        "meta": {"scope_id": "empty-src", "level": "artifact"},
        "sources": [],
    }
    result = _score(bundle)
    coverage_dims = [d for d in result.dimensions if d.dimension == "coverage_score"]
    assert len(coverage_dims) == 1
    assert coverage_dims[0].grade == GRADE_BLOCKING


@pytest.mark.unit
def test_no_evidence_blocking_evidence_score() -> None:
    """No evidence items → evidence_score is blocking."""
    bundle = {
        "meta": {"scope_id": "no-ev", "level": "artifact"},
        "evidence_items": [],
    }
    result = _score(bundle)
    ev_dims = [d for d in result.dimensions if d.dimension == "evidence_score"]
    assert len(ev_dims) == 1
    assert ev_dims[0].grade == GRADE_BLOCKING


# ── Clean bundle → good overall ───────────────────────────────────────────────


@pytest.mark.unit
def test_clean_bundle_good_grade() -> None:
    """Clean bundle returns overall_grade of 'good'."""
    result = _score(_clean_bundle())
    assert result.overall_grade == GRADE_GOOD


@pytest.mark.unit
def test_clean_bundle_no_blocking_dims() -> None:
    """Clean bundle has no blocking dimensions."""
    result = _score(_clean_bundle())
    assert result.blocking_dimensions == ()


# ── Blocking downgrade rule ────────────────────────────────────────────────────


@pytest.mark.unit
def test_blocking_dimension_caps_overall() -> None:
    """If any dimension is blocking, overall_grade must be at most 'watch'."""
    result = _score(_blocking_bundle())
    assert result.overall_grade in (GRADE_BLOCKING, GRADE_WATCH)


@pytest.mark.unit
def test_blocking_bundle_has_blocking_dims() -> None:
    """Blocking bundle produces at least one blocking dimension."""
    result = _score(_blocking_bundle())
    assert len(result.blocking_dimensions) > 0


# ── Contradiction score ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_open_blocking_contradictions_lower_score() -> None:
    """Open blocking contradictions reduce contradiction_score."""
    bundle = {
        "meta": {"scope_id": "contradiction-test", "level": "domain"},
        "contradiction_findings": [
            {"contradiction_id": "c-001", "severity": "blocking", "status": "open"},
            {"contradiction_id": "c-002", "severity": "blocking", "status": "open"},
            {"contradiction_id": "c-003", "severity": "warning", "status": "open"},
        ],
    }
    result = _score(bundle)
    c_dims = [d for d in result.dimensions if d.dimension == "contradiction_score"]
    assert len(c_dims) == 1
    assert c_dims[0].score < 0.50


@pytest.mark.unit
def test_resolved_contradictions_not_penalised() -> None:
    """Resolved/accepted_risk contradictions should not severely penalise the score."""
    bundle = {
        "meta": {"scope_id": "resolved-c", "level": "domain"},
        "contradiction_findings": [
            {"contradiction_id": "c-r-001", "severity": "blocking", "status": "resolved"},
            {"contradiction_id": "c-r-002", "severity": "blocking", "status": "accepted_risk"},
        ],
    }
    result = _score(bundle)
    c_dims = [d for d in result.dimensions if d.dimension == "contradiction_score"]
    assert len(c_dims) == 1
    # Resolved contradictions should yield a better score than open blocking ones
    assert c_dims[0].score >= 0.50


# ── Scope risk score ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_open_scope_drift_reduces_score() -> None:
    """Open scope drift findings reduce scope_risk_score."""
    bundle = {
        "meta": {"scope_id": "scope-drift-test", "level": "system"},
        "scope_drift_findings": [
            {"drift_id": "d-001", "severity": "blocking", "status": "open"},
            {"drift_id": "d-002", "severity": "blocking", "status": "open"},
        ],
    }
    result = _score(bundle)
    scope_dims = [d for d in result.dimensions if d.dimension == "scope_risk_score"]
    assert len(scope_dims) == 1
    assert scope_dims[0].score < 0.70


# ── Dependency confidence score ───────────────────────────────────────────────


@pytest.mark.unit
def test_all_low_confidence_edges_lower_score() -> None:
    """All-low-confidence dependency edges reduce dependency_confidence_score."""
    bundle = {
        "meta": {"scope_id": "dep-test", "level": "domain"},
        "dependency_edges": [
            {"edge_id": "e-001", "confidence": "low"},
            {"edge_id": "e-002", "confidence": "low"},
            {"edge_id": "e-003", "confidence": "low"},
        ],
    }
    result = _score(bundle)
    dep_dims = [d for d in result.dimensions if d.dimension == "dependency_confidence_score"]
    assert len(dep_dims) == 1
    assert dep_dims[0].score < 0.70


@pytest.mark.unit
def test_all_high_confidence_edges_good_score() -> None:
    """All-high-confidence edges produce a good dependency_confidence_score."""
    bundle = {
        "meta": {"scope_id": "dep-high", "level": "domain"},
        "dependency_edges": [
            {"edge_id": "e-h-001", "confidence": "high"},
            {"edge_id": "e-h-002", "confidence": "high"},
        ],
    }
    result = _score(bundle)
    dep_dims = [d for d in result.dimensions if d.dimension == "dependency_confidence_score"]
    assert len(dep_dims) == 1
    assert dep_dims[0].score >= 0.70


# ── Decision validity score ───────────────────────────────────────────────────


@pytest.mark.unit
def test_superseded_decisions_reduce_validity() -> None:
    """Superseded decisions reduce decision_validity_score."""
    bundle = {
        "meta": {"scope_id": "dec-validity", "level": "issue"},
        "decisions": [
            {"decision_id": "dec-old", "status": "superseded"},
            {"decision_id": "dec-old2", "status": "superseded"},
            {"decision_id": "dec-cur", "status": "current"},
        ],
    }
    result = _score(bundle)
    dec_dims = [d for d in result.dimensions if d.dimension == "decision_validity_score"]
    assert len(dec_dims) == 1
    assert dec_dims[0].score < 1.0


@pytest.mark.unit
def test_all_current_decisions_good() -> None:
    """All-current decisions produce a good decision_validity_score."""
    bundle = {
        "meta": {"scope_id": "dec-all-current", "level": "issue"},
        "decisions": [
            {"decision_id": "dec-1", "status": "current"},
            {"decision_id": "dec-2", "status": "current"},
        ],
    }
    result = _score(bundle)
    dec_dims = [d for d in result.dimensions if d.dimension == "decision_validity_score"]
    assert len(dec_dims) == 1
    assert dec_dims[0].score >= 0.70


# ── Memory trust score ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_blocked_memory_reduces_trust() -> None:
    """Blocked memory items reduce memory_trust_score."""
    bundle = {
        "meta": {"scope_id": "mem-trust", "level": "domain"},
        "memory_items": [
            {"memory_id": "m-blocked", "trust_level": "blocked"},
            {"memory_id": "m-weak", "trust_level": "weak"},
        ],
    }
    result = _score(bundle)
    mem_dims = [d for d in result.dimensions if d.dimension == "memory_trust_score"]
    assert len(mem_dims) == 1
    assert mem_dims[0].score < 0.70


# ── Result structure ──────────────────────────────────────────────────────────


@pytest.mark.unit
def test_result_has_all_8_dimensions() -> None:
    """QualityScoreResult has exactly 8 DimensionScore entries."""
    result = _score(_clean_bundle())
    dims = {d.dimension for d in result.dimensions}
    assert dims == set(SCORE_DIMENSIONS)


@pytest.mark.unit
def test_dimension_score_range() -> None:
    """All dimension scores are in [0.0, 1.0]."""
    result = _score(_blocking_bundle())
    for d in result.dimensions:
        assert 0.0 <= d.score <= 1.0, f"Out of range: {d.dimension}={d.score}"


@pytest.mark.unit
def test_to_dict_structure() -> None:
    """to_dict() returns all required keys."""
    result = _score(_clean_bundle())
    d = result.to_dict()
    required = {
        "schema_version", "scope_id", "level", "scored_at",
        "overall_score", "overall_grade", "blocking_dimensions",
        "watch_dimensions", "recommended_next_reads", "guardrails", "dimensions",
    }
    assert required.issubset(d.keys())


@pytest.mark.unit
def test_to_dict_schema_version() -> None:
    """to_dict() includes correct schema_version."""
    result = _score(_minimal_bundle())
    assert result.to_dict()["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
def test_guardrails_in_result() -> None:
    """QualityScoreResult.guardrails contains all GUARDRAILS strings."""
    result = _score(_minimal_bundle())
    assert set(GUARDRAILS).issubset(set(result.guardrails))


@pytest.mark.unit
def test_no_live_go_in_guardrails() -> None:
    """Guardrails must not imply live-go or action authority."""
    combined = " ".join(GUARDRAILS).lower()
    assert "live-go" in combined or "no live" in combined or "no-go" in combined or "no live-go" in combined


# ── Error cases ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_non_mapping_bundle_raises() -> None:
    """Non-mapping bundle raises QualityScoringError."""
    with pytest.raises(QualityScoringError):
        score_knowledge_quality_v1("not a dict")  # type: ignore[arg-type]


@pytest.mark.unit
def test_missing_meta_raises() -> None:
    """Bundle without meta raises QualityScoringError."""
    with pytest.raises(QualityScoringError):
        score_knowledge_quality_v1({})


@pytest.mark.unit
def test_meta_not_mapping_raises() -> None:
    """Bundle with non-mapping meta raises QualityScoringError."""
    with pytest.raises(QualityScoringError):
        score_knowledge_quality_v1({"meta": "not-a-dict"})


# ── Determinism ───────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_same_input_same_scope_id() -> None:
    """Same bundle produces the same scope_id."""
    b = _clean_bundle()
    r1 = _score(b)
    r2 = _score(b)
    assert r1.scope_id == r2.scope_id


@pytest.mark.unit
def test_same_input_same_dimension_scores() -> None:
    """Same bundle produces identical dimension scores (deterministic)."""
    b = _clean_bundle()
    r1 = _score(b)
    r2 = _score(b)
    scores1 = {d.dimension: d.score for d in r1.dimensions}
    scores2 = {d.dimension: d.score for d in r2.dimensions}
    assert scores1 == scores2


# ── CLI behaviour tests ───────────────────────────────────────────────────────


def _weak_bundle() -> dict[str, Any]:
    """Bundle that produces overall_grade=='weak' with no blocking dimensions."""
    return {
        "meta": {"scope_id": "weak-grade-test", "level": "system"},
        "sources": [
            {
                "source_path": "core/a.py",
                "has_documentation": True,
                "has_tests": True,
                "status": "current",
                "file_type": "python",
            },
            {
                "source_path": "core/b.py",
                "has_documentation": True,
                "has_tests": True,
                "status": "current",
                "file_type": "python",
            },
            {
                "source_path": "core/c.py",
                "has_documentation": False,
                "has_tests": False,
                "status": "current",
                "file_type": "python",
            },
            {
                "source_path": "core/d.py",
                "has_documentation": False,
                "has_tests": False,
                "status": "stale",
                "stale": True,
                "file_type": "python",
            },
        ],
        "decisions": [
            {"decision_id": "d1", "status": "current", "evidence_refs": ["e1"]},
            {"decision_id": "d2", "status": "superseded", "evidence_refs": []},
        ],
        "evidence_items": [
            {"evidence_id": "e1", "strength": "moderate", "expired": False},
            {"evidence_id": "e2", "strength": "moderate", "expired": False},
        ],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [
            {"edge_id": "edge-1", "confidence": "medium"},
            {"edge_id": "edge-2", "confidence": "medium"},
        ],
        "memory_items": [
            {"memory_id": "mem-1", "trust_level": "weak"},
            {"memory_id": "mem-2", "trust_level": "weak"},
        ],
        "scope_drift_findings": [],
    }


@pytest.mark.unit
def test_weak_bundle_produces_weak_grade() -> None:
    """_weak_bundle() must produce overall_grade=='weak' with no blocking dims."""
    result = _score(_weak_bundle())
    assert result.overall_grade == GRADE_WEAK
    assert result.blocking_dimensions == ()


@pytest.mark.unit
def test_cli_fail_on_weak_exits_1_for_weak_grade(tmp_path: Any) -> None:
    """--fail-on-weak must exit EXIT_WEAK (1) when overall grade is 'weak'."""
    import json

    from tools.surrealdb.quality_scoring_cli import EXIT_WEAK, main

    bundle_file = tmp_path / "weak_bundle.json"
    bundle_file.write_text(json.dumps(_weak_bundle()))
    exit_code = main(
        ["score-knowledge", "--input", str(bundle_file), "--fail-on-weak"]
    )
    assert exit_code == EXIT_WEAK


@pytest.mark.unit
def test_cli_fail_on_weak_exits_0_for_good_grade(tmp_path: Any) -> None:
    """--fail-on-weak must exit 0 when overall grade is 'good'."""
    import json

    from tools.surrealdb.quality_scoring_cli import EXIT_OK, main

    bundle_file = tmp_path / "good_bundle.json"
    bundle_file.write_text(json.dumps(_clean_bundle()))
    exit_code = main(
        ["score-knowledge", "--input", str(bundle_file), "--fail-on-weak"]
    )
    assert exit_code == EXIT_OK


@pytest.mark.unit
def test_cli_report_quality_format_markdown_as_subcommand_arg(tmp_path: Any) -> None:
    """report-quality --format markdown must not raise unrecognized arguments."""
    import json

    from tools.surrealdb.quality_scoring_cli import EXIT_OK, main

    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(json.dumps(_clean_bundle()))
    exit_code = main(
        ["report-quality", "--input", str(bundle_file), "--format", "markdown"]
    )
    assert exit_code == EXIT_OK


@pytest.mark.unit
def test_cli_score_knowledge_format_markdown_as_subcommand_arg(tmp_path: Any) -> None:
    """score-knowledge --format markdown must not raise unrecognized arguments."""
    import json

    from tools.surrealdb.quality_scoring_cli import EXIT_OK, main

    bundle_file = tmp_path / "bundle.json"
    bundle_file.write_text(json.dumps(_clean_bundle()))
    exit_code = main(
        ["score-knowledge", "--input", str(bundle_file), "--format", "markdown"]
    )
    assert exit_code == EXIT_OK
