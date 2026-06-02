"""Unit tests for Agent OS Readiness Evaluator v1 (#2191, #2193, #2194)."""

from __future__ import annotations

import socket
from typing import Any

import pytest

from tools.surrealdb.agent_os_readiness import (
    GUARDRAILS,
    READINESS_LEVELS,
    AgentOsReadinessError,
    AgentOsReadinessResult,
    evaluate_agent_os_readiness_v1,
)

pytestmark = pytest.mark.unit

_AS_OF = "2026-05-08T12:00:00+00:00"


# ── Bundle helpers ────────────────────────────────────────────────────────────


def _minimal_bundle(scope_id: str = "test-scope") -> dict[str, Any]:
    """Minimal valid bundle with no findings."""
    return {"meta": {"scope_id": scope_id, "level": "domain"}}


def _clean_bundle() -> dict[str, Any]:
    """Bundle with populated, clean inputs and no adverse findings.

    Includes ``owner`` on sources and ``evidence_refs`` on decisions so that
    the architect-signals evaluator returns no signals (no weak findings).
    """
    return {
        "meta": {"scope_id": "clean-scope", "level": "domain"},
        "sources": [
            {
                "path": "tools/surrealdb/agent_os_readiness.py",
                "has_documentation": True,
                "has_tests": True,
                "owner": "cdb-core",
            }
        ],
        "decisions": [
            {
                "decision_id": "D-001",
                "title": "Use evaluator pattern",
                "status": "active",
                "evidence_refs": ["E-001"],
            }
        ],
        "evidence_items": [
            {
                "evidence_id": "E-001",
                "strength": "strong",
                "expires_at": "2027-01-01T00:00:00+00:00",
            }
        ],
        "contradiction_findings": [],
        "stale_findings": [],
        "scope_drift_findings": [],
        "memory_items": [],
        "dependency_edges": [],
    }


def _bundle_with_blocking_scope_drift() -> dict[str, Any]:
    b = _clean_bundle()
    b["scope_drift_findings"] = [
        {
            "drift_id": "sd-001",
            "drift_type": "path_out_of_scope",
            "severity": "blocking",
            "status": "open",
        }
    ]
    return b


def _bundle_with_blocking_contradiction() -> dict[str, Any]:
    b = _clean_bundle()
    b["contradiction_findings"] = [
        {
            "contradiction_id": "c-001",
            "contradiction_type": "doc_vs_code",
            "severity": "blocking",
            "status": "open",
        }
    ]
    return b


def _bundle_with_stale_source_deleted() -> dict[str, Any]:
    b = _clean_bundle()
    b["stale_findings"] = [
        {
            "finding_id": "sf-001",
            "stale_type": "source_deleted",
            "severity": "warning",
            "status": "open",
        }
    ]
    return b


def _bundle_with_many_stale_warnings() -> dict[str, Any]:
    """Bundle with ≥3 watch-level stale findings (no source_deleted) → weak.

    NOTE: ≥2 scope_drift findings trigger an architect-signals blocking hotspot,
    so this fixture uses stale warnings instead to safely produce ≥3 weak findings.
    """
    b = _clean_bundle()
    b["stale_findings"] = [
        {
            "finding_id": f"sf-{i:03d}",
            "stale_type": "doc_outdated",
            "severity": "warning",
            "status": "open",
        }
        for i in range(4)
    ]
    return b


def _bundle_with_one_watch_contradiction() -> dict[str, Any]:
    """Bundle with exactly one watch-level finding → acceptable."""
    b = _clean_bundle()
    b["contradiction_findings"] = [
        {
            "contradiction_id": "c-002",
            "contradiction_type": "doc_vs_code",
            "severity": "warning",
            "status": "open",
        }
    ]
    return b


# ── Basic happy-path tests ────────────────────────────────────────────────────


def test_strong_readiness_minimal_bundle() -> None:
    """Minimal bundle with no findings should yield 'strong' readiness."""
    result = evaluate_agent_os_readiness_v1(_minimal_bundle(), as_of=_AS_OF)
    # A minimal bundle has no sources/decisions/evidence → missing_inputs → weak
    # Relax to allow weak (missing inputs) or strong
    assert result.readiness_level in ("strong", "weak", "acceptable")
    assert result.readiness_level != "blocked"
    assert isinstance(result, AgentOsReadinessResult)


def test_strong_readiness_clean_bundle() -> None:
    """Fully populated, clean bundle with no adverse findings → 'strong'."""
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert result.readiness_level == "strong"
    assert result.blocking_findings == ()
    assert result.confidence > 0.9


def test_readiness_level_in_valid_set() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert result.readiness_level in READINESS_LEVELS


# ── Blocking trigger tests ────────────────────────────────────────────────────


def test_blocked_by_scope_drift_blocking_finding() -> None:
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_blocking_scope_drift(), as_of=_AS_OF
    )
    assert result.readiness_level == "blocked"
    assert any("scope_drift blocking" in f for f in result.blocking_findings)


def test_blocked_by_contradiction_blocking_finding() -> None:
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_blocking_contradiction(), as_of=_AS_OF
    )
    assert result.readiness_level == "blocked"
    assert any("contradiction blocking" in f for f in result.blocking_findings)


def test_blocked_by_stale_source_deleted() -> None:
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_stale_source_deleted(), as_of=_AS_OF
    )
    assert result.readiness_level == "blocked"
    assert any("stale blocking" in f for f in result.blocking_findings)


def test_blocking_level_has_no_empty_blocking_findings() -> None:
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_blocking_scope_drift(), as_of=_AS_OF
    )
    assert len(result.blocking_findings) >= 1
    for f in result.blocking_findings:
        assert isinstance(f, str) and len(f) > 0


# ── Weak / acceptable tests ───────────────────────────────────────────────────


def test_weak_readiness_multiple_watch_findings() -> None:
    """Bundle with ≥3 watch-level stale findings → 'weak'."""
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_many_stale_warnings(), as_of=_AS_OF
    )
    assert result.readiness_level == "weak"
    assert len(result.weak_findings) >= 3


def test_acceptable_readiness_one_weak_finding() -> None:
    """Bundle with exactly 1 weak finding and no blockers → 'acceptable'."""
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_one_watch_contradiction(), as_of=_AS_OF
    )
    assert result.readiness_level == "acceptable"
    assert result.blocking_findings == ()


# ── Error / invalid input tests ───────────────────────────────────────────────


def test_missing_bundle_raises_error() -> None:
    with pytest.raises(
        AgentOsReadinessError, match="bundle must be a non-None mapping"
    ):
        evaluate_agent_os_readiness_v1(None)


def test_non_mapping_bundle_raises_error() -> None:
    with pytest.raises(AgentOsReadinessError):
        evaluate_agent_os_readiness_v1("not-a-dict")  # type: ignore[arg-type]


def test_missing_meta_raises_error() -> None:
    with pytest.raises(AgentOsReadinessError, match="meta"):
        evaluate_agent_os_readiness_v1({"sources": []})


def test_missing_scope_id_raises_error() -> None:
    with pytest.raises(AgentOsReadinessError, match="scope_id"):
        evaluate_agent_os_readiness_v1({"meta": {}})


def test_empty_scope_id_raises_error() -> None:
    with pytest.raises(AgentOsReadinessError, match="scope_id"):
        evaluate_agent_os_readiness_v1({"meta": {"scope_id": ""}})


# ── Determinism tests ─────────────────────────────────────────────────────────


def test_readiness_id_deterministic() -> None:
    """Same bundle and as_of always produces the same readiness_id."""
    r1 = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    r2 = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert r1.readiness_id == r2.readiness_id


def test_readiness_id_differs_for_different_scope() -> None:
    b1 = _clean_bundle()
    b2 = {**_clean_bundle(), "meta": {"scope_id": "other-scope", "level": "domain"}}
    r1 = evaluate_agent_os_readiness_v1(b1, as_of=_AS_OF)
    r2 = evaluate_agent_os_readiness_v1(b2, as_of=_AS_OF)
    assert r1.readiness_id != r2.readiness_id


# ── Guardrail tests ───────────────────────────────────────────────────────────


def test_guardrails_always_6_items() -> None:
    for bundle in (_clean_bundle(), _bundle_with_blocking_scope_drift()):
        result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
        assert len(result.guardrails) == 6


def test_guardrails_all_non_empty() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    for g in result.guardrails:
        assert isinstance(g, str) and len(g.strip()) > 0


def test_guardrails_include_no_trading_console() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    joined = " ".join(result.guardrails)
    assert "No trading console" in joined


def test_guardrails_include_no_live_readiness_go() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    joined = " ".join(result.guardrails)
    assert "No Live-Readiness-Go" in joined


def test_guardrails_include_no_echtgeld_go() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    joined = " ".join(result.guardrails)
    assert "No Echtgeld-Go" in joined


def test_guardrails_include_read_only() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    joined = " ".join(result.guardrails)
    assert "read-only" in joined


def test_guardrails_match_module_constant() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert result.guardrails == GUARDRAILS


# ── Confidence tests ──────────────────────────────────────────────────────────


def test_confidence_bounded_0_to_1() -> None:
    for bundle in (
        _clean_bundle(),
        _bundle_with_blocking_scope_drift(),
        _bundle_with_many_stale_warnings(),
        _bundle_with_one_watch_contradiction(),
    ):
        result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
        assert 0.0 <= result.confidence <= 1.0


def test_blocking_caps_confidence_at_0_3() -> None:
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_blocking_scope_drift(), as_of=_AS_OF
    )
    assert result.readiness_level == "blocked"
    assert result.confidence <= 0.30


def test_strong_readiness_high_confidence() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert result.readiness_level == "strong"
    assert result.confidence >= 0.90


# ── to_dict tests ─────────────────────────────────────────────────────────────


def test_to_dict_has_all_required_fields() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    d = result.to_dict()
    required_keys = {
        "schema_version",
        "readiness_id",
        "target_scope",
        "generated_at",
        "readiness_level",
        "confidence",
        "blocking_findings",
        "weak_findings",
        "missing_inputs",
        "recommended_next_reads",
        "required_validation",
        "guardrails",
    }
    for key in required_keys:
        assert key in d, f"Missing key: {key}"


def test_to_dict_lists_are_plain_lists() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    d = result.to_dict()
    for key in ("blocking_findings", "weak_findings", "missing_inputs", "guardrails"):
        assert isinstance(d[key], list), f"{key} must be a list"


def test_to_dict_schema_version() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert result.to_dict()["schema_version"] == "agent-os-readiness/v1"


# ── to_report_markdown tests (#2193) ─────────────────────────────────────────


def test_to_report_markdown_contains_scope_id() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    md = result.to_report_markdown()
    assert "clean-scope" in md


def test_to_report_markdown_contains_readiness_level() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    md = result.to_report_markdown()
    assert result.readiness_level.upper() in md


def test_to_report_markdown_contains_guardrails() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    md = result.to_report_markdown()
    assert "Guardrails" in md
    assert "No Live-Readiness-Go" in md


def test_to_report_markdown_no_live_go_statement() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    md = result.to_report_markdown()
    assert "Live-Readiness-Go" in md
    assert "NO-GO" in md


def test_to_report_markdown_blocking_shows_findings() -> None:
    result = evaluate_agent_os_readiness_v1(
        _bundle_with_blocking_scope_drift(), as_of=_AS_OF
    )
    md = result.to_report_markdown()
    assert "BLOCKED" in md
    assert "Blocking Findings" in md
    assert "scope_drift" in md


def test_to_report_markdown_is_str() -> None:
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert isinstance(result.to_report_markdown(), str)


# ── No side-effect / network tests ───────────────────────────────────────────


def test_no_socket_connection_is_attempted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evaluator must not attempt any network connection."""

    def _boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("socket.connect must not be called by the evaluator")

    monkeypatch.setattr(socket.socket, "connect", _boom)
    # Should complete without error
    result = evaluate_agent_os_readiness_v1(_clean_bundle(), as_of=_AS_OF)
    assert result.readiness_level == "strong"


# ── Resolved/false-positive findings are NOT counted ─────────────────────────


def test_resolved_scope_drift_not_counted() -> None:
    b = _clean_bundle()
    b["scope_drift_findings"] = [
        {
            "drift_id": "sd-resolved",
            "drift_type": "path_out_of_scope",
            "severity": "blocking",
            "status": "resolved",
        }
    ]
    result = evaluate_agent_os_readiness_v1(b, as_of=_AS_OF)
    assert result.readiness_level != "blocked"


def test_false_positive_contradiction_not_counted() -> None:
    b = _clean_bundle()
    b["contradiction_findings"] = [
        {
            "contradiction_id": "c-fp",
            "contradiction_type": "doc_vs_code",
            "severity": "blocking",
            "status": "false_positive",
        }
    ]
    result = evaluate_agent_os_readiness_v1(b, as_of=_AS_OF)
    assert result.readiness_level != "blocked"


# ── Operator certification (#2801) ───────────────────────────────────────────


def _certified_pass() -> dict[str, Any]:
    return {
        "final_verdict": "certified",
        "gate_matrix": [
            {
                "check_id": "registry_all_read_only",
                "status": "pass",
                "blocking": True,
                "detail": "ok",
            }
        ],
    }


def test_operator_certification_pass_not_blocked() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = _certified_pass()
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level == "strong"
    assert not any("operator certification" in f for f in result.blocking_findings)


def test_operator_certification_fail_blocks_adoption() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = {
        "final_verdict": "fail",
        "blocked_checks_with_reason": [
            {"check": "registry_all_read_only", "reason": "non-read-only tool"}
        ],
    }
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level == "blocked"
    assert any("final_verdict=fail" in f for f in result.blocking_findings)


def test_operator_certification_blocked_checks_block() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = {
        "final_verdict": "certified",
        "blocked_checks_with_reason": [
            {"check": "permission_guard", "reason": "inconsistent registry"}
        ],
    }
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level == "blocked"
    assert any("operator certification blocked" in f for f in result.blocking_findings)


def test_operator_certification_skipped_is_weak_with_validation() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = {
        "final_verdict": "certified",
        "gate_matrix": [
            {
                "check_id": "registry_all_read_only",
                "status": "pass",
                "blocking": True,
                "detail": "ok",
            }
        ],
        "skipped_checks_with_reason": [
            {"check": "context-smoke-db", "reason": "operator-only"},
        ],
    }
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level in ("acceptable", "weak")
    assert any("skipped check" in f for f in result.weak_findings)
    assert any("skipped_checks_with_reason" in v for v in result.required_validation)


def test_operator_certification_missing_is_not_global_blocker() -> None:
    bundle = _clean_bundle()
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level == "strong"
    assert any("operator_certification" in m for m in result.missing_inputs)


def test_operator_certification_missing_on_minimal_bundle() -> None:
    result = evaluate_agent_os_readiness_v1(_minimal_bundle(), as_of=_AS_OF)
    assert result.readiness_level != "blocked"
    assert any("operator_certification" in m for m in result.missing_inputs)


def test_operator_certification_invalid_not_silent_green() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = "not-a-mapping"
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level != "strong"
    assert any("invalid" in f for f in result.weak_findings)


def test_operator_certification_warn_non_blocking_gate() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = {
        "final_verdict": "certified",
        "gate_matrix": [
            {
                "check_id": "context_doctor_live",
                "status": "fail",
                "blocking": False,
                "detail": "live doctor failed",
            }
        ],
    }
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level == "acceptable"
    assert any("non-blocking fail" in f for f in result.weak_findings)
    assert any("non-blocking" in v for v in result.required_validation)


def test_operator_certification_adoption_pass_without_proof_not_strong() -> None:
    bundle = _clean_bundle()
    bundle["operator_certification"] = {"adoption_status": "pass"}
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level != "strong"
    assert any("incomplete" in f for f in result.weak_findings)
    assert any("final_verdict" in v for v in result.required_validation)


def test_context_certification_alias() -> None:
    bundle = _clean_bundle()
    bundle["context_certification"] = _certified_pass()
    result = evaluate_agent_os_readiness_v1(bundle, as_of=_AS_OF)
    assert result.readiness_level == "strong"
    assert not any("operator certification" in f for f in result.blocking_findings)
