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


# ── stale_findings freshness tests (active vs. terminal statuses) ─────────────


def _all_current_bundle_with_stale_findings(count: int = 1) -> dict[str, Any]:
    """Bundle where all sources are current but stale_findings is non-empty."""
    return {
        "meta": {"scope_id": "stale-findings-test", "level": "system"},
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
        ],
        "decisions": [
            {"decision_id": "d1", "status": "current", "evidence_refs": ["e1"]},
        ],
        "evidence_items": [
            {"evidence_id": "e1", "strength": "strong", "expired": False},
        ],
        "contradiction_findings": [],
        "stale_findings": [
            {"stale_id": f"s-{i:03d}", "status": "stale", "source_path": f"docs/old-{i}.md"}
            for i in range(count)
        ],
        "dependency_edges": [
            {"edge_id": "edge-1", "confidence": "high"},
        ],
        "memory_items": [
            {"memory_id": "mem-1", "trust_level": "high"},
        ],
        "scope_drift_findings": [],
    }


@pytest.mark.unit
def test_stale_findings_lower_freshness_below_perfect() -> None:
    """A bundle with all-current sources but 1 stale_finding must score < 1.0 freshness."""
    result = _score(_all_current_bundle_with_stale_findings(count=1))
    freshness_dim = next(d for d in result.dimensions if d.dimension == "freshness_score")
    assert freshness_dim.score < 1.0, (
        f"Expected freshness < 1.0 with 1 stale finding, got {freshness_dim.score}"
    )


@pytest.mark.unit
def test_stale_findings_freshness_score_decreases_with_more_findings() -> None:
    """More stale findings produce lower freshness than fewer stale findings."""
    result_few = _score(_all_current_bundle_with_stale_findings(count=1))
    result_many = _score(_all_current_bundle_with_stale_findings(count=5))
    fresh_few = next(d.score for d in result_few.dimensions if d.dimension == "freshness_score")
    fresh_many = next(d.score for d in result_many.dimensions if d.dimension == "freshness_score")
    assert fresh_many < fresh_few, (
        f"Expected freshness to decrease with more stale findings: {fresh_many} >= {fresh_few}"
    )


@pytest.mark.unit
def test_empty_stale_findings_preserves_perfect_freshness() -> None:
    """A bundle with no stale_findings and all-current sources scores 1.0 freshness."""
    bundle = _all_current_bundle_with_stale_findings(count=0)
    result = _score(bundle)
    freshness_dim = next(d for d in result.dimensions if d.dimension == "freshness_score")
    assert freshness_dim.score == 1.0, (
        f"Expected freshness 1.0 with no stale findings, got {freshness_dim.score}"
    )


@pytest.mark.unit
def test_terminal_stale_findings_do_not_lower_freshness() -> None:
    """refreshed / accepted_risk / false_positive stale findings must not penalise freshness."""
    terminal_statuses = ["refreshed", "accepted_risk", "false_positive"]
    for status in terminal_statuses:
        bundle = {
            **_all_current_bundle_with_stale_findings(count=0),
            "stale_findings": [
                {"stale_id": "s-001", "status": status, "source_path": "docs/old.md"},
                {"stale_id": "s-002", "status": status, "source_path": "docs/older.md"},
            ],
        }
        result = _score(bundle)
        freshness_dim = next(d for d in result.dimensions if d.dimension == "freshness_score")
        assert freshness_dim.score == 1.0, (
            f"status={status!r}: expected freshness 1.0 (exempt), got {freshness_dim.score}"
        )


@pytest.mark.unit
def test_mixed_stale_findings_only_active_penalise() -> None:
    """Only active stale findings lower freshness; terminal ones are exempt."""
    bundle = {
        **_all_current_bundle_with_stale_findings(count=0),
        "sources": [
            {"source_path": "core/a.py", "has_documentation": True, "has_tests": True, "status": "current", "file_type": "python"},
            {"source_path": "core/b.py", "has_documentation": True, "has_tests": True, "status": "current", "file_type": "python"},
        ],
        "decisions": [{"decision_id": "d1", "status": "current", "evidence_refs": ["e1"]}],
        "stale_findings": [
            {"stale_id": "s-active", "status": "stale", "source_path": "docs/active.md"},
            {"stale_id": "s-exempt1", "status": "refreshed", "source_path": "docs/done1.md"},
            {"stale_id": "s-exempt2", "status": "accepted_risk", "source_path": "docs/done2.md"},
        ],
    }
    result = _score(bundle)
    freshness_dim = next(d for d in result.dimensions if d.dimension == "freshness_score")
    # 3 items (2 sources + 1 decision) are current; 1 active stale adds to total → 3/4 = 0.75
    expected = 3 / 4
    assert abs(freshness_dim.score - expected) < 1e-9, (
        f"Expected freshness {expected} (3 current / 4 total including 1 active stale), "
        f"got {freshness_dim.score}"
    )


# ── architect signal tests: dependency edge paths ─────────────────────────────


@pytest.mark.unit
def test_high_dependency_risk_source_target_edges_have_non_empty_affected_paths() -> None:
    """Dependency edges with source/target schema must produce non-empty affected_paths."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    bundle = {
        "meta": {"scope_id": "dep-path-test", "level": "system"},
        "sources": [],
        "decisions": [],
        "evidence_items": [],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [
            {"edge_id": "e1", "confidence": "low", "source": "core/risk.py", "target": "core/execution.py"},
            {"edge_id": "e2", "confidence": "low", "source": "core/signal.py", "target": "core/regime.py"},
        ],
        "memory_items": [],
        "scope_drift_findings": [],
    }
    result = scan_architect_signals_v1(bundle)
    dep_signals = [s for s in result.signals if s.signal_type == "high_dependency_risk"]
    assert dep_signals, "Expected at least one high_dependency_risk signal"
    sig = dep_signals[0]
    assert len(sig.affected_paths) > 0, (
        f"Expected non-empty affected_paths for source/target edge schema, got {sig.affected_paths}"
    )


@pytest.mark.unit
def test_high_dependency_risk_affected_paths_include_both_endpoints() -> None:
    """Both source and target endpoints must appear in affected_paths."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    bundle = {
        "meta": {"scope_id": "dep-endpoints-test", "level": "system"},
        "sources": [],
        "decisions": [],
        "evidence_items": [],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [
            {"edge_id": "e1", "confidence": "low", "source": "core/risk.py", "target": "core/execution.py"},
        ],
        "memory_items": [],
        "scope_drift_findings": [],
    }
    result = scan_architect_signals_v1(bundle)
    dep_signals = [s for s in result.signals if s.signal_type == "high_dependency_risk"]
    assert dep_signals
    paths = dep_signals[0].affected_paths
    assert "core/risk.py" in paths, f"Expected 'core/risk.py' in affected_paths: {paths}"
    assert "core/execution.py" in paths, f"Expected 'core/execution.py' in affected_paths: {paths}"


@pytest.mark.unit
def test_high_dependency_risk_source_path_key_fallback_still_works() -> None:
    """Edges using the source_path key (not source/target) still produce affected_paths."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    bundle = {
        "meta": {"scope_id": "dep-path-fallback-test", "level": "system"},
        "sources": [],
        "decisions": [],
        "evidence_items": [],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [
            {"edge_id": "e1", "confidence": "low", "source_path": "core/legacy.py"},
            {"edge_id": "e2", "confidence": "low", "source_path": "core/old.py"},
        ],
        "memory_items": [],
        "scope_drift_findings": [],
    }
    result = scan_architect_signals_v1(bundle)
    dep_signals = [s for s in result.signals if s.signal_type == "high_dependency_risk"]
    assert dep_signals
    paths = dep_signals[0].affected_paths
    assert len(paths) > 0, f"Expected non-empty affected_paths for source_path key, got {paths}"


# ── architect signal tests: as_of / detected_at determinism (T12) ─────────────


def _signal_bundle_with_low_conf_edges() -> dict:
    """Bundle that reliably produces a high_dependency_risk signal."""
    return {
        "meta": {"scope_id": "det-ts-test", "level": "system"},
        "sources": [],
        "decisions": [],
        "evidence_items": [],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [
            {"edge_id": "e1", "confidence": "low", "source": "core/a.py", "target": "core/b.py"},
            {"edge_id": "e2", "confidence": "low", "source": "core/c.py", "target": "core/d.py"},
        ],
        "memory_items": [],
        "scope_drift_findings": [],
    }


@pytest.mark.unit
def test_as_of_sets_signal_detected_at() -> None:
    """When as_of is provided, every signal's detected_at equals the as_of value."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    as_of = "2026-05-08T00:00:00"
    result = scan_architect_signals_v1(_signal_bundle_with_low_conf_edges(), as_of=as_of)
    assert result.signals, "Expected at least one signal from low-confidence edges"
    for sig in result.signals:
        assert sig.detected_at == as_of, (
            f"Signal {sig.signal_type}.detected_at={sig.detected_at!r} != as_of={as_of!r}"
        )


@pytest.mark.unit
def test_as_of_detected_at_matches_scanned_at() -> None:
    """scanned_at and all signal detected_at values are identical when as_of is supplied."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    as_of = "2026-05-08T12:34:56"
    result = scan_architect_signals_v1(_signal_bundle_with_low_conf_edges(), as_of=as_of)
    assert result.scanned_at == as_of
    for sig in result.signals:
        assert sig.detected_at == result.scanned_at, (
            f"Signal {sig.signal_type}.detected_at={sig.detected_at!r} != "
            f"scanned_at={result.scanned_at!r}"
        )


@pytest.mark.unit
def test_repeated_as_of_scan_is_identical() -> None:
    """Same bundle + same as_of produces identical to_dict() output on two calls."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    bundle = _signal_bundle_with_low_conf_edges()
    as_of = "2026-05-08T00:00:00"
    result1 = scan_architect_signals_v1(bundle, as_of=as_of)
    result2 = scan_architect_signals_v1(bundle, as_of=as_of)
    assert result1.to_dict() == result2.to_dict(), (
        "Expected identical to_dict() for same bundle+as_of on two calls"
    )


@pytest.mark.unit
def test_without_as_of_signals_still_generated() -> None:
    """When as_of is omitted, signals are still generated (wall-clock path not broken)."""
    from tools.surrealdb.architect_signals import scan_architect_signals_v1

    result = scan_architect_signals_v1(_signal_bundle_with_low_conf_edges())
    assert result.signals, "Expected signals even without as_of"
    # scanned_at and detected_at should still be consistent with each other
    for sig in result.signals:
        assert sig.detected_at == result.scanned_at, (
            f"Even without as_of, detected_at should equal scanned_at; "
            f"got detected_at={sig.detected_at!r} scanned_at={result.scanned_at!r}"
        )


# ── CLI contract tests: --format global vs subcommand (T13) + EXIT_NOT_FOUND (T14) ─


def _good_bundle_file(tmp_path: Any) -> Any:
    """Write a minimal valid bundle JSON to tmp_path and return the path."""
    bundle = {
        "meta": {"scope_id": "cli-contract-test", "level": "system"},
        "sources": [{"source_id": "s1", "status": "current", "trust_score": 0.9}],
        "decisions": [],
        "evidence_items": [{"evidence_id": "e1", "strength": "strong", "expired": False}],
        "contradiction_findings": [],
        "stale_findings": [],
        "dependency_edges": [],
        "memory_items": [],
        "scope_drift_findings": [],
    }
    p = tmp_path / "bundle.json"
    import json as _json
    p.write_text(_json.dumps(bundle), encoding="utf-8")
    return p


@pytest.mark.unit
def test_cli_global_format_markdown_not_overwritten_by_subparser(tmp_path: Any, capsys: Any) -> None:
    """Global --format markdown before subcommand must produce Markdown, not JSON (T13)."""
    from tools.surrealdb.quality_scoring_cli import EXIT_OK, main

    bundle_file = _good_bundle_file(tmp_path)
    exit_code = main(["--format", "markdown", "report-quality", "--input", str(bundle_file)])
    captured = capsys.readouterr()

    assert exit_code == EXIT_OK
    assert captured.out.startswith("# "), (
        f"Expected Markdown output (starting with '# ') for global --format markdown; "
        f"got: {captured.out[:120]!r}"
    )


@pytest.mark.unit
def test_cli_subcommand_format_markdown_overrides_global_json(tmp_path: Any, capsys: Any) -> None:
    """Subcommand-level --format markdown overrides the global default of json (T13 precedence)."""
    from tools.surrealdb.quality_scoring_cli import EXIT_OK, main

    bundle_file = _good_bundle_file(tmp_path)
    # global default = json; subcommand explicitly sets markdown → markdown must win
    exit_code = main(["report-quality", "--input", str(bundle_file), "--format", "markdown"])
    captured = capsys.readouterr()

    assert exit_code == EXIT_OK
    assert captured.out.startswith("# "), (
        f"Expected Markdown output when subcommand specifies --format markdown; "
        f"got: {captured.out[:120]!r}"
    )


@pytest.mark.unit
def test_cli_missing_bundle_exits_not_found(tmp_path: Any) -> None:
    """Missing input bundle path must return EXIT_NOT_FOUND = 3, not EXIT_ERROR = 2 (T14)."""
    from tools.surrealdb.quality_scoring_cli import EXIT_NOT_FOUND, main

    missing = tmp_path / "nonexistent.json"
    exit_code = main(["report-quality", "--input", str(missing)])
    assert exit_code == EXIT_NOT_FOUND, (
        f"Expected EXIT_NOT_FOUND (3) for missing bundle, got {exit_code}"
    )


@pytest.mark.unit
def test_cli_missing_bundle_score_knowledge_exits_not_found(tmp_path: Any) -> None:
    """Missing bundle on score-knowledge also returns EXIT_NOT_FOUND = 3 (T14)."""
    from tools.surrealdb.quality_scoring_cli import EXIT_NOT_FOUND, main

    missing = tmp_path / "nonexistent.json"
    exit_code = main(["score-knowledge", "--input", str(missing)])
    assert exit_code == EXIT_NOT_FOUND, (
        f"Expected EXIT_NOT_FOUND (3) for missing bundle on score-knowledge, got {exit_code}"
    )
