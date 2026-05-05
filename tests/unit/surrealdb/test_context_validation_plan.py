"""Unit tests for Validation Plan Generator v1 (#2109)."""

from __future__ import annotations

import pytest

from tools.surrealdb.context_impact_radar import (
    ImpactRadarInput,
    compute_impact,
)
from tools.surrealdb.context_validation_plan import (
    SCHEMA_VERSION,
    ValidationPlanInput,
    build_validation_plan,
)

# ── Fixture builders ────────────────────────────────────────────────────────


def _make_artifact(
    artifact_id: str,
    artifact_type: str,
    source_path: str,
    source_hash: str = "",
) -> dict:
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "source_path": source_path,
        "source_hash": source_hash,
    }


def _make_symbol(
    symbol_id: str,
    name: str,
    source_path: str,
    symbol_type: str = "function",
    qualified_name: str = "",
) -> dict:
    return {
        "symbol_id": symbol_id,
        "name": name,
        "qualified_name": qualified_name or name,
        "symbol_type": symbol_type,
        "source_path": source_path,
    }


def _make_edge(
    edge_id: str,
    from_id: str,
    to_id: str,
    edge_type: str = "contains",
    inferred: bool = False,
) -> dict:
    return {
        "edge_id": edge_id,
        "from_id": from_id,
        "to_id": to_id,
        "edge_type": edge_type,
        "source_path": None,
        "confidence": "high",
        "inferred": inferred,
    }


def _make_test_case(
    test_id: str,
    test_name: str,
    source_path: str,
    test_type: str = "unit",
) -> dict:
    return {
        "test_id": test_id,
        "test_name": test_name,
        "source_path": source_path,
        "test_type": test_type,
    }


# ── Input validation ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_input_requires_either_impact_report_or_payload() -> None:
    with pytest.raises(ValueError, match="impact_report or payload"):
        ValidationPlanInput()


@pytest.mark.unit
def test_input_rejects_both_impact_report_and_payload() -> None:
    with pytest.raises(
        ValueError, match="exactly one of impact_report or payload"
    ):
        ValidationPlanInput(impact_report={}, payload={})


@pytest.mark.unit
def test_input_accepts_payload_dict() -> None:
    inp = ValidationPlanInput(payload={"impact_id": "test", "impact_level": "low"})
    assert inp.payload is not None


# ── Basic generation ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_empty_payload_produces_valid_plan() -> None:
    inp = ValidationPlanInput(payload={})
    plan = build_validation_plan(inp)

    assert plan.schema_version == SCHEMA_VERSION
    assert isinstance(plan.plan_id, str)
    assert len(plan.plan_id) == 16
    assert isinstance(plan.required_checks, tuple)
    assert isinstance(plan.suggested_tests, tuple)
    assert isinstance(plan.docs_to_review, tuple)
    assert isinstance(plan.evidence_to_collect, tuple)
    assert isinstance(plan.commands_to_consider, tuple)
    assert isinstance(plan.manual_review_needed, bool)
    assert isinstance(plan.blocking_preconditions, tuple)
    assert isinstance(plan.success_criteria, tuple)
    assert isinstance(plan.stop_conditions, tuple)


@pytest.mark.unit
def test_empty_payload_has_low_level_check_and_no_preconditions() -> None:
    plan = build_validation_plan(ValidationPlanInput(payload={}))

    assert len(plan.blocking_preconditions) == 0
    assert plan.manual_review_needed is False
    assert any("low impact" in c.lower() for c in plan.required_checks)


@pytest.mark.unit
def test_plan_produces_deterministic_id() -> None:
    payload = {"impact_id": "abc123", "impact_level": "high", "confidence": "high"}
    plan1 = build_validation_plan(ValidationPlanInput(payload=dict(payload)))
    plan2 = build_validation_plan(ValidationPlanInput(payload=dict(payload)))

    assert plan1.plan_id == plan2.plan_id


@pytest.mark.unit
def test_plan_to_payload_contains_all_fields() -> None:
    plan = build_validation_plan(ValidationPlanInput(payload={}))
    p = plan.to_payload()

    assert "schema_version" in p
    assert "plan_id" in p
    assert "required_checks" in p
    assert "suggested_tests" in p
    assert "docs_to_review" in p
    assert "evidence_to_collect" in p
    assert "commands_to_consider" in p
    assert "manual_review_needed" in p
    assert "blocking_preconditions" in p
    assert "success_criteria" in p
    assert "stop_conditions" in p


# ── ImpactReport integration ────────────────────────────────────────────────


@pytest.mark.unit
def test_accepts_impact_report_from_radar() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/some-doc.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation", "docs/surrealdb/some-doc.md"
            ),
        ),
    )
    report = compute_impact(inp)

    plan_input = ValidationPlanInput(impact_report=report)
    plan = build_validation_plan(plan_input)

    assert plan.plan_id is not None
    assert len(plan.docs_to_review) >= 0


@pytest.mark.unit
def test_accepts_impact_report_payload_dict() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/some-doc.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation", "docs/surrealdb/some-doc.md"
            ),
        ),
    )
    report = compute_impact(inp)
    payload = report.to_payload()

    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert plan.plan_id is not None


@pytest.mark.unit
def test_report_and_payload_produce_same_plan() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/some-doc.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation", "docs/surrealdb/some-doc.md"
            ),
        ),
    )
    report = compute_impact(inp)
    payload = report.to_payload()

    plan_from_report = build_validation_plan(
        ValidationPlanInput(impact_report=report)
    )
    plan_from_payload = build_validation_plan(
        ValidationPlanInput(payload=payload)
    )

    assert plan_from_report == plan_from_payload


# ── Low impact ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_low_impact_has_appropriate_checks() -> None:
    payload = {
        "impact_id": "test-low",
        "impact_level": "low",
        "confidence": "high",
        "gate_risks": [],
        "affected_artifacts": [
            {"source_path": "docs/readme.md", "artifact_type": "documentation"}
        ],
        "required_validation": {
            "docs_to_review": ["docs/readme.md"],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": False,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert plan.manual_review_needed is False
    assert len(plan.blocking_preconditions) == 0
    assert len(plan.required_checks) == 1
    assert any(
        "affected modules" in c.lower() for c in plan.required_checks
    )
    assert any(
        "affected artifacts" in c.lower() for c in plan.success_criteria
    )


# ── Medium impact ───────────────────────────────────────────────────────────


@pytest.mark.unit
def test_medium_impact_has_medium_check() -> None:
    payload = {
        "impact_id": "test-medium",
        "impact_level": "medium",
        "confidence": "high",
        "gate_risks": [],
        "affected_artifacts": [
            {"source_path": "core/utils/clock.py", "artifact_type": "source"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": ["test_clock"],
            "evidence_to_collect": [],
            "commands_to_consider": ["pytest tests/unit/test_clock.py"],
            "manual_review_needed": False,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "medium impact" in c.lower() for c in plan.required_checks
    )
    assert plan.commands_to_consider == ("pytest tests/unit/test_clock.py",)


# ── High impact ─────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_high_impact_has_high_check_and_manual_review() -> None:
    payload = {
        "impact_id": "test-high",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": [],
        "affected_artifacts": [
            {"source_path": "services/signal/service.py", "artifact_type": "source"}
        ],
        "affected_tests": [
            {"test_id": "t1", "test_name": "test_signal", "source_path": "tests/unit/test_signal.py"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": ["test_signal"],
            "evidence_to_collect": [],
            "commands_to_consider": ["pytest tests/unit/test_signal.py"],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert plan.manual_review_needed is True
    assert any(
        "high impact" in c.lower() for c in plan.required_checks
    )
    assert any(
        "services verified" in c.lower() for c in plan.success_criteria
    )


# ── Blocking impact ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_blocking_impact_propagates_all_checks() -> None:
    payload = {
        "impact_id": "test-blocking",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": ["governance_touched", "secrets_surface_touched"],
        "affected_artifacts": [
            {"source_path": "knowledge/governance/CDB_AGENT_POLICY.md"}
        ],
        "stop_conditions": [
            {
                "type": "scope_drift_risk",
                "severity": "blocking",
                "reason": "S5: blocking impact detected on knowledge/governance/",
                "required_action": "Seek Human-GO",
                "human_go_required": True,
            }
        ],
        "required_validation": {
            "docs_to_review": ["knowledge/governance/CDB_AGENT_POLICY.md"],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [
                "Blocking impact level — confirm change is authorized",
                "Secrets surface touched — verify no credential exposure",
            ],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert plan.manual_review_needed is True
    assert len(plan.blocking_preconditions) == 2
    assert len(plan.required_checks) >= 1
    assert any(
        "blocking impact" in c.lower() for c in plan.required_checks
    )
    assert any(
        "governance" in c.lower() for c in plan.required_checks
    )
    assert any(
        "secrets" in c.lower() for c in plan.required_checks
    )
    assert any(
        "Human-GO" in c for c in plan.success_criteria
    )
    assert any(
        "stop conditions" in c.lower() for c in plan.success_criteria
    )


# ── Gate risk propagation ───────────────────────────────────────────────────


@pytest.mark.unit
def test_governance_touched_adds_check() -> None:
    payload = {
        "impact_id": "test-gov",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": ["governance_touched"],
        "affected_artifacts": [
            {"source_path": "knowledge/governance/CDB_CONSTITUTION.md"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "governance" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_risk_surface_adds_check() -> None:
    payload = {
        "impact_id": "test-risk",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": ["risk_surface_touched"],
        "affected_artifacts": [
            {"source_path": "services/risk/service.py"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "risk" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_execution_surface_adds_check() -> None:
    payload = {
        "impact_id": "test-exec",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": ["execution_surface_touched"],
        "affected_artifacts": [
            {"source_path": "services/execution/service.py"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "execution" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_contract_drift_adds_check() -> None:
    payload = {
        "impact_id": "test-contract",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": ["contract_drift_possible"],
        "affected_artifacts": [
            {"source_path": "docs/contracts/some-contract.md"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "contract" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_lr_surface_adds_check() -> None:
    payload = {
        "impact_id": "test-lr",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": ["lr_surface_touched"],
        "affected_artifacts": [
            {"source_path": "docs/live-readiness/LR-AUDIT-STATUS.md"}
        ],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "live-readiness" in c.lower() for c in plan.required_checks
    )


# ── Success criteria ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_low_confidence_adds_criterion() -> None:
    payload = {
        "impact_id": "test",
        "impact_level": "medium",
        "confidence": "low",
        "gate_risks": [],
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": False,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "confidence is low" in c.lower() for c in plan.success_criteria
    )


@pytest.mark.unit
def test_high_confidence_omits_low_confidence_criterion() -> None:
    payload = {
        "impact_id": "test",
        "impact_level": "medium",
        "confidence": "high",
        "gate_risks": [],
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": False,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert not any(
        "confidence is low" in c.lower() for c in plan.success_criteria
    )
    assert any(
        "standard review" in c.lower() for c in plan.success_criteria
    )


@pytest.mark.unit
def test_governance_risk_adds_success_criterion() -> None:
    payload = {
        "impact_id": "test",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": ["governance_touched"],
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "governance review" in c.lower() for c in plan.success_criteria
    )


@pytest.mark.unit
def test_secrets_risk_adds_success_criterion() -> None:
    payload = {
        "impact_id": "test",
        "impact_level": "high",
        "confidence": "high",
        "gate_risks": ["secrets_surface_touched"],
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "secrets audit" in c.lower() for c in plan.success_criteria
    )


# ── Stop condition propagation ──────────────────────────────────────────────


@pytest.mark.unit
def test_stop_conditions_are_propagated() -> None:
    stop_conditions = [
        {
            "type": "scope_drift_risk",
            "severity": "blocking",
            "reason": "S5: blocking impact detected",
            "required_action": "Seek Human-GO",
            "human_go_required": True,
        }
    ]
    payload = {
        "impact_id": "test-stop",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": [],
        "stop_conditions": stop_conditions,
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert len(plan.stop_conditions) == 1
    assert plan.stop_conditions[0]["type"] == "scope_drift_risk"
    assert any(
        "stop condition" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_blocking_stop_conditions_become_checks() -> None:
    stop_conditions = [
        {
            "type": "forbidden_path",
            "severity": "blocking",
            "reason": "S8: forbidden path touched",
            "required_action": "Abort",
            "human_go_required": True,
        }
    ]
    payload = {
        "impact_id": "test-bs",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": [],
        "stop_conditions": stop_conditions,
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "S8" in c or "forbidden" in c.lower()
        for c in plan.required_checks
    )


# ── Commands are suggestions ────────────────────────────────────────────────


@pytest.mark.unit
def test_commands_are_preserved_as_suggestions() -> None:
    payload = {
        "impact_id": "test-cmd",
        "impact_level": "medium",
        "confidence": "high",
        "gate_risks": [],
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": ["test_a", "test_b"],
            "evidence_to_collect": [],
            "commands_to_consider": [
                "pytest -v tests/unit/test_a.py",
                "mypy core/ services/",
            ],
            "manual_review_needed": False,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert len(plan.commands_to_consider) == 2
    assert plan.commands_to_consider[0].startswith("pytest")
    assert plan.commands_to_consider[1].startswith("mypy")


# ── Payload edge cases ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_missing_required_validation_defaults() -> None:
    payload = {
        "impact_id": "test",
        "impact_level": "low",
        "confidence": "high",
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert len(plan.docs_to_review) == 0
    assert len(plan.suggested_tests) == 0
    assert len(plan.evidence_to_collect) == 0
    assert len(plan.commands_to_consider) == 0
    assert plan.manual_review_needed is False
    assert len(plan.blocking_preconditions) == 0


@pytest.mark.unit
def test_missing_required_validation_derives_manual_review_for_blocking() -> None:
    payload = {
        "impact_id": "test-blocking-default-review",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": ["governance_touched"],
        "stop_conditions": [
            {
                "type": "scope_drift_risk",
                "severity": "blocking",
                "reason": "S5: blocking impact detected",
                "required_action": "Seek Human-GO",
                "human_go_required": True,
            }
        ],
    }

    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert plan.manual_review_needed is True


@pytest.mark.unit
def test_payload_with_nested_impact_report_dict() -> None:
    report_payload = {
        "impact_id": "nested-123",
        "impact_level": "low",
        "confidence": "high",
        "gate_risks": [],
        "required_validation": {
            "docs_to_review": ["docs/x.md"],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": False,
            "blocking_preconditions": [],
        },
    }
    plan = build_validation_plan(
        ValidationPlanInput(payload=report_payload)
    )

    assert plan.plan_id is not None
    assert len(plan.docs_to_review) == 1
    assert plan.docs_to_review[0] == "docs/x.md"


# ── Blocking precondition integration ───────────────────────────────────────


@pytest.mark.unit
def test_blocking_preconditions_become_checks() -> None:
    payload = {
        "impact_id": "test-bp",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": ["secrets_surface_touched"],
        "affected_artifacts": [],
        "required_validation": {
            "docs_to_review": [],
            "suggested_tests": [],
            "evidence_to_collect": [],
            "commands_to_consider": [],
            "manual_review_needed": True,
            "blocking_preconditions": [
                "Secrets surface touched — verify no credential exposure",
            ],
        },
    }
    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert any(
        "BLOCKING:" in c for c in plan.required_checks
    )
    assert any(
        "credential" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_stop_conditions_participate_in_equality() -> None:
    payload = {
        "impact_id": "test-equality",
        "impact_level": "blocking",
        "confidence": "high",
        "stop_conditions": [
            {
                "type": "scope_drift_risk",
                "severity": "blocking",
                "reason": "S5: blocking impact detected",
            }
        ],
    }

    plan_a = build_validation_plan(ValidationPlanInput(payload=payload))
    changed_payload = {
        **payload,
        "stop_conditions": [
            {
                "type": "scope_drift_risk",
                "severity": "blocking",
                "reason": "S8: forbidden path touched",
            }
        ],
    }
    plan_b = build_validation_plan(
        ValidationPlanInput(payload=changed_payload)
    )

    assert plan_a != plan_b


@pytest.mark.unit
def test_plan_id_changes_when_stop_conditions_change() -> None:
    base_payload = {
        "impact_id": "test-plan-id",
        "impact_level": "blocking",
        "confidence": "high",
        "gate_risks": [],
        "stop_conditions": [
            {
                "type": "scope_drift_risk",
                "severity": "blocking",
                "reason": "S5: blocking impact detected",
            }
        ],
    }

    plan_a = build_validation_plan(ValidationPlanInput(payload=base_payload))
    plan_b = build_validation_plan(
        ValidationPlanInput(
            payload={
                **base_payload,
                "gate_risks": ["secrets_surface_touched"],
            }
        )
    )

    assert plan_a.plan_id != plan_b.plan_id


@pytest.mark.unit
def test_stop_conditions_are_copied_on_plan_creation() -> None:
    stop_conditions = [
        {
            "type": "scope_drift_risk",
            "severity": "blocking",
            "reason": "S5: blocking impact detected",
        }
    ]
    payload = {
        "impact_id": "test-copy-in",
        "impact_level": "blocking",
        "confidence": "high",
        "stop_conditions": stop_conditions,
    }

    plan = build_validation_plan(ValidationPlanInput(payload=payload))
    stop_conditions[0]["severity"] = "warning"

    assert plan.stop_conditions[0]["severity"] == "blocking"


@pytest.mark.unit
def test_to_payload_copies_stop_condition_dicts() -> None:
    payload = {
        "impact_id": "test-copy-out",
        "impact_level": "blocking",
        "confidence": "high",
        "stop_conditions": [
            {
                "type": "scope_drift_risk",
                "severity": "blocking",
                "reason": "S5: blocking impact detected",
            }
        ],
    }

    plan = build_validation_plan(ValidationPlanInput(payload=payload))
    exported = plan.to_payload()
    exported["stop_conditions"][0]["severity"] = "warning"

    assert plan.stop_conditions[0]["severity"] == "blocking"


@pytest.mark.unit
def test_non_dict_stop_conditions_fail_closed_in_payload_mode() -> None:
    payload = {
        "impact_id": "test-invalid-stop-condition",
        "impact_level": "low",
        "confidence": "high",
        "stop_conditions": ["S8: forbidden path touched"],
    }

    plan = build_validation_plan(ValidationPlanInput(payload=payload))

    assert plan.manual_review_needed is True
    assert len(plan.stop_conditions) == 1
    assert plan.stop_conditions[0]["type"] == "invalid_stop_condition_payload"
    assert plan.stop_conditions[0]["severity"] == "blocking"
    assert "S8" in plan.stop_conditions[0]["reason"]


# ── Full impact-radar-to-plan pipeline ──────────────────────────────────────


@pytest.mark.unit
def test_full_pipeline_docs_change() -> None:
    inp = ImpactRadarInput(
        target_paths=("docs/surrealdb/some-doc.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation", "docs/surrealdb/some-doc.md"
            ),
        ),
    )
    report = compute_impact(inp)
    plan = build_validation_plan(ValidationPlanInput(impact_report=report))

    assert plan.plan_id is not None
    assert "docs/surrealdb/some-doc.md" in plan.docs_to_review
    assert plan.manual_review_needed is False
    assert len(plan.blocking_preconditions) == 0


@pytest.mark.unit
def test_full_pipeline_governance_change() -> None:
    inp = ImpactRadarInput(
        target_paths=("knowledge/governance/CDB_AGENT_POLICY.md",),
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "knowledge/governance/CDB_AGENT_POLICY.md",
            ),
        ),
    )
    report = compute_impact(inp)
    plan = build_validation_plan(ValidationPlanInput(impact_report=report))

    assert plan.manual_review_needed is True
    assert len(plan.blocking_preconditions) > 0
    assert any(
        "blocking" in c.lower() for c in plan.required_checks
    )


@pytest.mark.unit
def test_full_pipeline_service_change() -> None:
    inp = ImpactRadarInput(
        target_paths=("services/signal/service.py",),
        artifacts=(
            _make_artifact("art-1", "source", "services/signal/service.py"),
        ),
        test_cases=(
            _make_test_case(
                "t1", "test_signal", "tests/unit/test_signal.py"
            ),
        ),
    )
    report = compute_impact(inp)
    plan = build_validation_plan(ValidationPlanInput(impact_report=report))

    assert plan.manual_review_needed is True
    assert any(
        "services verified" in c.lower() for c in plan.success_criteria
    )


@pytest.mark.unit
def test_full_pipeline_blocking_governance_plus_secrets() -> None:
    inp = ImpactRadarInput(
        target_paths=(
            "knowledge/governance/CDB_AGENT_POLICY.md",
            "secrets/some-secret.env",
        ),
        operation_mode="write",
        artifacts=(
            _make_artifact(
                "art-1", "documentation",
                "knowledge/governance/CDB_AGENT_POLICY.md",
            ),
            _make_artifact(
                "art-2", "secret", "secrets/some-secret.env",
            ),
        ),
    )
    report = compute_impact(inp)
    plan = build_validation_plan(ValidationPlanInput(impact_report=report))

    assert plan.manual_review_needed is True
    assert len(plan.blocking_preconditions) >= 1
    assert any(
        "governance" in c.lower() for c in plan.required_checks
    )
    assert any(
        "secrets" in c.lower() for c in plan.required_checks
    )
    assert any(
        "blocking" in c.lower() for c in plan.required_checks
    )
    assert len(plan.stop_conditions) > 0
