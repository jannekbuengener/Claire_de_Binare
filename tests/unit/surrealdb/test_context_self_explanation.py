"""Unit tests for Self-Explanation Builder v1 (#2189)."""

from __future__ import annotations

import pytest

from tools.surrealdb.context_self_explanation import (
    InvalidExplanationTypeError,
    InvalidInputError,
    SelfExplanationInput,
    SelfExplanationOutput,
    build_self_explanation,
    supported_explanation_types,
)


@pytest.mark.unit
def test_build_why_blocked_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="Merge auf main ist blockiert wegen fehlender CI-Checks.",
        reasons=(
            "Required Check 'ci (Unit/Integration)' ist noch pending.",
            "Policy Gate erwartet approval.",
        ),
        evidence_refs=("#2278", "#2279"),
        required_next_step="Auf CI-Ergebnis warten oder Human-GO pruefen.",
        confidence=0.9,
        scope_context="pr-merge",
    )
    result = build_self_explanation(inp)
    payload = result.to_payload()

    assert result.explanation_type == "why_blocked"
    assert "blockiert" in result.summary
    assert len(result.reasons) == 2
    assert payload["evidence_refs"] == ["#2278", "#2279"]
    assert len(result.guardrails) == 5
    assert result.confidence == 0.9
    assert payload["schema_version"] == "self-explanation/v1"
    assert "Freigabe" in result.guardrails[-1]


@pytest.mark.unit
def test_build_why_risky_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_risky",
        summary="Aenderung an core/risk/service.py ohne Test-Coverage.",
        reasons=(
            "Keine Unit-Tests fuer die geaenderte Funktion.",
            "Blast-Radius umfasst Risk-Service-Kill-Switch.",
        ),
        evidence_refs=("core/risk/service.py",),
        required_next_step="Vor Merge zwingend Unit-Tests ergaenzen.",
        scope_context="core-risk",
    )
    result = build_self_explanation(inp)
    payload = result.to_payload()

    assert result.explanation_type == "why_risky"
    assert "Risk-Service" in result.reasons[1]
    assert result.scope_context == "core-risk"
    assert all(isinstance(g, str) and len(g) > 0 for g in result.guardrails)
    assert payload["required_next_step"] == "Vor Merge zwingend Unit-Tests ergaenzen."


@pytest.mark.unit
def test_build_why_stale_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_stale",
        summary="Runbook seit 180 Tagen nicht aktualisiert.",
        reasons=(
            "Letztes Update: 2024-11-03.",
            "Referenziert veraltete Container-Images.",
        ),
        evidence_refs=("docs/runbooks/old-runbook.md",),
        required_next_step="Runbook gegen aktuellen Stack-Canon pruefen und aktualisieren.",
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_stale"
    assert "180" in result.summary
    assert result.confidence is None
    assert len(result.evidence_refs) == 1


@pytest.mark.unit
def test_build_why_decision_current_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_decision_current",
        summary="Decision #1492: Stage trade-capable ratifiziert 2026-04-08.",
        reasons=(
            "Board-Ratifikation erfolgt via Issue #1492.",
            "LR bleibt NO-GO trotz Stage.",
        ),
        evidence_refs=("#1492", "docs/runbooks/CONTROL_REGISTER.md"),
        required_next_step="Keine Aenderung noetig; Decision bleibt aktiv.",
        confidence=1.0,
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_decision_current"
    assert "#1492" in result.summary
    assert result.confidence == 1.0


@pytest.mark.unit
def test_build_why_decision_superseded_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_decision_superseded",
        summary="Alte Decision durch neuen Canon ersetzt.",
        reasons=(
            "Neuer Canon in WORKING_REPO_CANON.md definiert.",
            "Alte Docs-Hub-Struktur nicht mehr autoritativ.",
        ),
        evidence_refs=("docs/meta/WORKING_REPO_CANON.md",),
        required_next_step="Alte Referenzen auf neue Canon-Pfade aktualisieren.",
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_decision_superseded"
    assert "superseded" in result.explanation_type


@pytest.mark.unit
def test_build_why_scope_blocked_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_scope_blocked",
        summary="Scope-Erweiterung auf Live-Trading ist blockiert.",
        reasons=(
            "LR-050 ist NO-GO.",
            "Kein Human-GO fuer Echtgeld.",
        ),
        evidence_refs=("docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md",),
        required_next_step="Human-GO pruefen oder Scope reduzieren.",
        scope_context="live-trading",
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_scope_blocked"
    assert "NO-GO" in result.reasons[0]


@pytest.mark.unit
def test_build_why_evidence_weak_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_evidence_weak",
        summary="Claim fehlt direkter Commit-Beweis.",
        reasons=(
            "Keine Evidence-Datei unter docs/evidence/.",
            "Nur Issue-Kommentar, kein Repo-Artefakt.",
        ),
        evidence_refs=("#1234",),
        required_next_step="Evidence-Commit anlegen oder Claim zurueckziehen.",
        confidence=0.3,
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_evidence_weak"
    assert result.confidence == 0.3
    assert "Commit" in result.required_next_step


@pytest.mark.unit
def test_build_why_agent_needs_go_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_agent_needs_go",
        summary="Agent plant Merge von PR #2279 auf main.",
        reasons=(
            "PR betrifft Governance-Gates-Dokument.",
            "Kein auto-merge erlaubt.",
        ),
        evidence_refs=("#2279",),
        required_next_step="Human-GO anfordern oder Merge-Approval abwarten.",
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_agent_needs_go"
    assert "Merge" in result.summary


@pytest.mark.unit
def test_build_why_doc_untrusted_explanation() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_doc_untrusted",
        summary="Dokument enthaelt keine SourceRefs oder Hash-Chain.",
        reasons=(
            "Kein source_commit im Dokument.",
            "Keine deterministische Hash-Referenz.",
        ),
        evidence_refs=("docs/legacy/untrusted-doc.md",),
        required_next_step="Dokument gegen Repo-Stand pruefen und mit SourceRefs versehen.",
    )
    result = build_self_explanation(inp)

    assert result.explanation_type == "why_doc_untrusted"
    assert "SourceRefs" in result.required_next_step


@pytest.mark.unit
def test_guardrails_always_present() -> None:
    for etype in sorted(supported_explanation_types()):
        inp = SelfExplanationInput(
            explanation_type=etype,
            summary=f"Test explanation for {etype}.",
            reasons=("Reason 1",),
            evidence_refs=("#test",),
            required_next_step="Next step.",
        )
        result = build_self_explanation(inp)

        assert len(result.guardrails) == 5
        assert all(isinstance(g, str) and len(g) > 0 for g in result.guardrails)
        assert "Handlungserlaubnis" in result.guardrails[0]
        assert "Freigabe" in result.guardrails[-1]


@pytest.mark.unit
def test_unsupported_explanation_type_raises() -> None:
    with pytest.raises(InvalidExplanationTypeError, match="unsupported explanation_type"):
        SelfExplanationInput(
            explanation_type="why_whatever",
            summary="Invalid.",
            reasons=("R1",),
            evidence_refs=("#x",),
            required_next_step="N/A",
        )


@pytest.mark.unit
def test_empty_summary_raises() -> None:
    with pytest.raises(InvalidInputError, match="summary must be non-empty"):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="   ",
            reasons=("R1",),
            evidence_refs=("#x",),
            required_next_step="N/A",
        )


@pytest.mark.unit
def test_empty_reasons_raises() -> None:
    with pytest.raises(InvalidInputError, match="at least one reason"):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="S",
            reasons=(),
            evidence_refs=("#x",),
            required_next_step="N/A",
        )


@pytest.mark.unit
def test_empty_evidence_refs_raises() -> None:
    with pytest.raises(
        InvalidInputError, match="evidence_refs must contain at least one reference"
    ):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="S",
            reasons=("R1",),
            evidence_refs=(),
            required_next_step="N/A",
        )


@pytest.mark.unit
def test_empty_evidence_ref_value_raises() -> None:
    with pytest.raises(
        InvalidInputError, match="each evidence_ref must be non-empty"
    ):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="S",
            reasons=("R1",),
            evidence_refs=("#x", "   "),
            required_next_step="N/A",
        )


@pytest.mark.unit
def test_empty_required_next_step_raises() -> None:
    with pytest.raises(InvalidInputError, match="required_next_step must be non-empty"):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="S",
            reasons=("R1",),
            evidence_refs=("#x",),
            required_next_step="",
        )


@pytest.mark.unit
def test_confidence_out_of_range_raises() -> None:
    with pytest.raises(InvalidInputError, match="confidence must be"):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="S",
            reasons=("R1",),
            evidence_refs=("#x",),
            required_next_step="N/A",
            confidence=1.5,
        )

    with pytest.raises(InvalidInputError, match="confidence must be"):
        SelfExplanationInput(
            explanation_type="why_blocked",
            summary="S",
            reasons=("R1",),
            evidence_refs=("#x",),
            required_next_step="N/A",
            confidence=-0.1,
        )


@pytest.mark.unit
def test_to_payload_outputs_all_fields() -> None:
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="Test",
        reasons=("R1", "R2"),
        evidence_refs=("E1",),
        required_next_step="Next",
        confidence=0.5,
        scope_context="test-scope",
    )
    result = build_self_explanation(inp)
    payload = result.to_payload()

    assert "schema_version" in payload
    assert payload["summary"] == "Test"
    assert payload["reasons"] == ["R1", "R2"]
    assert payload["evidence_refs"] == ["E1"]
    assert "guardrails" in payload
    assert payload["confidence"] == 0.5
    assert payload["scope_context"] == "test-scope"
    # AC #2031: graph_path and uncertainties always present in payload
    assert "graph_path" in payload
    assert "uncertainties" in payload
    assert isinstance(payload["graph_path"], list)
    assert isinstance(payload["uncertainties"], list)


# ---------------------------------------------------------------------------
# AC #2031 — Explanations contain graph-path and evidence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_output_contains_graph_path_field_default_empty() -> None:
    """graph_path is always present on output, defaults to empty tuple."""
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="No graph path provided.",
        reasons=("Reason.",),
        evidence_refs=("#ref",),
        required_next_step="Check.",
    )
    result = build_self_explanation(inp)

    assert hasattr(result, "graph_path")
    assert result.graph_path == ()
    assert result.to_payload()["graph_path"] == []


@pytest.mark.unit
def test_output_graph_path_passes_through_from_input() -> None:
    """graph_path provided in input is preserved in output."""
    inp = SelfExplanationInput(
        explanation_type="why_stale",
        summary="Stale docs in context graph.",
        reasons=("Last updated 2024.",),
        evidence_refs=("docs/old.md",),
        required_next_step="Refresh docs.",
        graph_path=("context", "docs", "docs/old.md"),
    )
    result = build_self_explanation(inp)

    assert result.graph_path == ("context", "docs", "docs/old.md")
    assert result.to_payload()["graph_path"] == ["context", "docs", "docs/old.md"]


@pytest.mark.unit
def test_output_graph_path_included_in_payload_when_nonempty() -> None:
    """graph_path appears in to_payload even when non-empty."""
    inp = SelfExplanationInput(
        explanation_type="why_decision_current",
        summary="Decision is current.",
        reasons=("Ratified via #1492.",),
        evidence_refs=("#1492",),
        required_next_step="None needed.",
        graph_path=("governance", "decisions", "#1492"),
    )
    result = build_self_explanation(inp)
    payload = result.to_payload()

    assert payload["graph_path"] == ["governance", "decisions", "#1492"]


# ---------------------------------------------------------------------------
# AC #2031 — Uncertainties are visible
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_output_contains_uncertainties_field_default_empty() -> None:
    """uncertainties is always present on output, defaults to empty tuple."""
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="No uncertainties.",
        reasons=("Reason.",),
        evidence_refs=("#ref",),
        required_next_step="Check.",
        confidence=0.95,
    )
    result = build_self_explanation(inp)

    assert hasattr(result, "uncertainties")
    assert result.uncertainties == ()
    assert result.to_payload()["uncertainties"] == []


@pytest.mark.unit
def test_explicit_uncertainties_pass_through() -> None:
    """Caller-supplied uncertainties are preserved as-is."""
    inp = SelfExplanationInput(
        explanation_type="why_risky",
        summary="Risk assessment.",
        reasons=("High blast radius.",),
        evidence_refs=("core/risk/service.py",),
        required_next_step="Add tests.",
        uncertainties=("Blast radius not fully mapped.", "No rollback plan."),
    )
    result = build_self_explanation(inp)

    assert result.uncertainties == ("Blast radius not fully mapped.", "No rollback plan.")
    assert result.to_payload()["uncertainties"] == [
        "Blast radius not fully mapped.",
        "No rollback plan.",
    ]


@pytest.mark.unit
def test_why_evidence_weak_infers_uncertainty_when_none_given() -> None:
    """why_evidence_weak type auto-populates uncertainty when caller omits it."""
    inp = SelfExplanationInput(
        explanation_type="why_evidence_weak",
        summary="Evidence is weak.",
        reasons=("Only an issue comment, no repo artefact.",),
        evidence_refs=("#1234",),
        required_next_step="Add evidence commit.",
    )
    result = build_self_explanation(inp)

    assert len(result.uncertainties) >= 1
    assert any("unvollstaendig" in u.lower() or "evidence" in u.lower() for u in result.uncertainties)


@pytest.mark.unit
def test_why_evidence_weak_explicit_uncertainties_not_overridden() -> None:
    """Explicit uncertainties on why_evidence_weak are not replaced by inference."""
    inp = SelfExplanationInput(
        explanation_type="why_evidence_weak",
        summary="Evidence is weak.",
        reasons=("No repo artefact.",),
        evidence_refs=("#1234",),
        required_next_step="Add evidence.",
        uncertainties=("My custom uncertainty.",),
    )
    result = build_self_explanation(inp)

    assert result.uncertainties == ("My custom uncertainty.",)


@pytest.mark.unit
def test_blank_uncertainties_treated_as_empty_and_inference_fires() -> None:
    """Blank/whitespace-only uncertainty strings are normalized out; inference then fires."""
    inp = SelfExplanationInput(
        explanation_type="why_evidence_weak",
        summary="Evidence is weak.",
        reasons=("No repo artefact.",),
        evidence_refs=("#1234",),
        required_next_step="Add evidence.",
        uncertainties=("   ",),
    )
    result = build_self_explanation(inp)

    # blank entry must be stripped; inference must have fired
    assert len(result.uncertainties) >= 1
    assert all(u.strip() for u in result.uncertainties)
    assert any("unvollstaendig" in u.lower() or "evidence" in u.lower() for u in result.uncertainties)


@pytest.mark.unit
def test_empty_string_uncertainty_treated_as_absent_for_low_confidence() -> None:
    """Empty-string uncertainty on low-confidence case is normalized; inference fires."""
    inp = SelfExplanationInput(
        explanation_type="why_stale",
        summary="Possibly stale.",
        reasons=("Not updated.",),
        evidence_refs=("docs/some.md",),
        required_next_step="Review.",
        confidence=0.2,
        uncertainties=("",),
    )
    result = build_self_explanation(inp)

    # blank entry stripped; inference should have added a low-confidence warning
    assert len(result.uncertainties) >= 1
    assert all(u.strip() for u in result.uncertainties)


@pytest.mark.unit
def test_low_confidence_infers_uncertainty() -> None:
    """Confidence < 0.5 without explicit uncertainties triggers inference."""
    inp = SelfExplanationInput(
        explanation_type="why_stale",
        summary="Possibly stale.",
        reasons=("Not recently updated.",),
        evidence_refs=("docs/some.md",),
        required_next_step="Review.",
        confidence=0.3,
    )
    result = build_self_explanation(inp)

    assert len(result.uncertainties) >= 1
    uncertainty_text = " ".join(result.uncertainties)
    assert "0.30" in uncertainty_text or "Konfidenz" in uncertainty_text


@pytest.mark.unit
def test_high_confidence_no_inferred_uncertainty() -> None:
    """Confidence >= 0.5 without explicit uncertainties: no inference."""
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="Clearly blocked.",
        reasons=("CI failing.",),
        evidence_refs=("#ci-check",),
        required_next_step="Fix CI.",
        confidence=0.8,
    )
    result = build_self_explanation(inp)

    assert result.uncertainties == ()


@pytest.mark.unit
def test_no_confidence_no_inferred_uncertainty_for_non_weak_type() -> None:
    """Missing confidence on a non-why_evidence_weak type: no inference."""
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="Blocked.",
        reasons=("Policy gate.",),
        evidence_refs=("#policy",),
        required_next_step="Request approval.",
    )
    result = build_self_explanation(inp)

    assert result.uncertainties == ()


# ---------------------------------------------------------------------------
# AC #2031 — Explanation gives no live/Echtgeld-Go (explicit guardrail check)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_guardrail_no_live_readiness_go() -> None:
    """Output guardrails explicitly prohibit Live-Readiness-Go."""
    inp = SelfExplanationInput(
        explanation_type="why_agent_needs_go",
        summary="Agent needs GO for merge.",
        reasons=("Governance gate active.",),
        evidence_refs=("#2279",),
        required_next_step="Human GO required.",
    )
    result = build_self_explanation(inp)

    guardrail_text = " ".join(result.guardrails)
    assert "Live-Readiness-Go" in guardrail_text
    assert "Echtgeld-Go" in guardrail_text
    assert "Handlungserlaubnis" in guardrail_text


# ---------------------------------------------------------------------------
# AC #2031 — Optional spec fields pass through
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_optional_spec_fields_pass_through() -> None:
    """decision_refs, claim_refs, memory_refs, contradictions, stale_context,
    recommended_next_reads all pass through input → output."""
    inp = SelfExplanationInput(
        explanation_type="why_decision_current",
        summary="Decision still current.",
        reasons=("Ratified 2026-04-08.",),
        evidence_refs=("#1492",),
        required_next_step="No action needed.",
        decision_refs=("#1492", "#2033"),
        claim_refs=("claim:trade-capable-stage",),
        memory_refs=("knowledge/ACTIVE_ROADMAP.md",),
        contradictions=("old-decision:stage-blocked",),
        stale_context=("docs/archive/old-stage.md",),
        recommended_next_reads=(
            "docs/runbooks/CONTROL_REGISTER.md",
            "knowledge/governance/CDB_CONSTITUTION.md",
        ),
    )
    result = build_self_explanation(inp)

    assert result.decision_refs == ("#1492", "#2033")
    assert result.claim_refs == ("claim:trade-capable-stage",)
    assert result.memory_refs == ("knowledge/ACTIVE_ROADMAP.md",)
    assert result.contradictions == ("old-decision:stage-blocked",)
    assert result.stale_context == ("docs/archive/old-stage.md",)
    assert result.recommended_next_reads == (
        "docs/runbooks/CONTROL_REGISTER.md",
        "knowledge/governance/CDB_CONSTITUTION.md",
    )


@pytest.mark.unit
def test_optional_spec_fields_in_payload_when_nonempty() -> None:
    """Non-empty optional fields appear in to_payload()."""
    inp = SelfExplanationInput(
        explanation_type="why_stale",
        summary="Doc is stale.",
        reasons=("Not updated.",),
        evidence_refs=("docs/old.md",),
        required_next_step="Update.",
        decision_refs=("#999",),
        recommended_next_reads=("docs/new.md",),
    )
    result = build_self_explanation(inp)
    payload = result.to_payload()

    assert "decision_refs" in payload
    assert payload["decision_refs"] == ["#999"]
    assert "recommended_next_reads" in payload
    assert payload["recommended_next_reads"] == ["docs/new.md"]


@pytest.mark.unit
def test_optional_spec_fields_absent_from_payload_when_empty() -> None:
    """Empty optional fields are omitted from to_payload()."""
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="Blocked.",
        reasons=("Gate.",),
        evidence_refs=("#ref",),
        required_next_step="Approve.",
    )
    result = build_self_explanation(inp)
    payload = result.to_payload()

    for optional_key in (
        "decision_refs",
        "claim_refs",
        "memory_refs",
        "contradictions",
        "stale_context",
        "recommended_next_reads",
    ):
        assert optional_key not in payload, f"{optional_key} should be absent when empty"


@pytest.mark.unit
def test_output_is_selfexplanationoutput_instance() -> None:
    """build_self_explanation always returns a SelfExplanationOutput."""
    inp = SelfExplanationInput(
        explanation_type="why_blocked",
        summary="Blocked.",
        reasons=("Reason.",),
        evidence_refs=("#ref",),
        required_next_step="Step.",
    )
    result = build_self_explanation(inp)

    assert isinstance(result, SelfExplanationOutput)
