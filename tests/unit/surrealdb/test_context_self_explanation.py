"""Unit tests for Self-Explanation Builder v1 (#2189)."""

from __future__ import annotations

import pytest

from tools.surrealdb.context_self_explanation import (
    InvalidExplanationTypeError,
    InvalidInputError,
    SelfExplanationInput,
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
