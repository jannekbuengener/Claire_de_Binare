"""Unit tests for control_room_signal_layer.py — Control Room signal layer v1.

Issues:
    #2802 — [PHASE-2][SURREALDB][SLICE-6] Visual control-room read-only signal layer
    Parent: #2778

Scope:
    Fixture-based unit tests. No DB. No MCP. No networking. No writes.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from tools.surrealdb.control_room_signal_layer import (
    GUARDRAILS,
    SCHEMA_VERSION,
    ControlRoomSignalLayerError,
    ControlRoomSignalLayerRequest,
    build_control_room_signal_layer_v1,
)

_AS_OF = "2026-06-02T12:00:00+00:00"

_FORBIDDEN_PHRASE_RE = re.compile(
    r"(?<!no )(?<!not )live[- ]go|(?<!no )(?<!not )echtgeld[- ]go|"
    r"approved for trading|authorized for live",
    re.IGNORECASE,
)

REQUIRED_FIELDS = (
    "schema_version",
    "generated_for_scope",
    "generated_at_or_as_of",
    "source_artifacts",
    "summary_status",
    "signal_cards",
    "blocking_findings",
    "warnings",
    "required_validation",
    "guardrails",
    "limitations",
    "determinism",
)


def _base_request(**overrides: Any) -> ControlRoomSignalLayerRequest:
    defaults: dict[str, Any] = {
        "generated_for_scope": "issue:2802",
        "generated_at_or_as_of": _AS_OF,
    }
    defaults.update(overrides)
    return ControlRoomSignalLayerRequest(**defaults)


@pytest.mark.unit
def test_envelope_has_required_schema_fields() -> None:
    envelope = build_control_room_signal_layer_v1(_base_request())
    for field in REQUIRED_FIELDS:
        assert field in envelope


@pytest.mark.unit
def test_minimal_inputs_not_pass() -> None:
    envelope = build_control_room_signal_layer_v1(_base_request())
    assert envelope["summary_status"] in {"UNKNOWN", "WARN"}
    assert envelope["summary_status"] != "PASS"
    assert envelope["limitations"]
    assert "context_package_not_provided" in envelope["limitations"]


@pytest.mark.unit
def test_certification_fail_becomes_blocking() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={
                "adoption_status": "fail",
                "final_verdict": "fail",
            }
        )
    )
    assert envelope["summary_status"] in {"FAIL", "BLOCKED"}
    assert envelope["blocking_findings"]
    assert any("adoption_status=fail" in b for b in envelope["blocking_findings"])


@pytest.mark.unit
def test_certification_blocked_severity() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={"adoption_status": "blocked"},
        )
    )
    assert envelope["summary_status"] == "BLOCKED"
    severities = {c["severity"] for c in envelope["signal_cards"]}
    assert "BLOCKED" in severities


@pytest.mark.unit
def test_certification_warn_creates_validation() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={"adoption_status": "warn", "final_verdict": "certified"},
        )
    )
    assert envelope["summary_status"] == "WARN"
    assert envelope["warnings"]
    assert envelope["required_validation"]
    assert any("adoption" in v.lower() for v in envelope["required_validation"])


@pytest.mark.unit
def test_certification_invalid_adoption_status_not_pass() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={
                "adoption_status": "bogus",
                "final_verdict": "certified",
            },
        )
    )
    assert envelope["summary_status"] == "WARN"
    assert any("invalid adoption_status" in w for w in envelope["warnings"])
    assert envelope["required_validation"]


@pytest.mark.unit
def test_certification_missing_final_verdict_not_pass() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={"adoption_status": "pass"},
        )
    )
    assert envelope["summary_status"] == "WARN"
    assert any("missing final_verdict" in w for w in envelope["warnings"])
    assert envelope["required_validation"]


@pytest.mark.unit
def test_certification_invalid_final_verdict_not_pass() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={
                "adoption_status": "pass",
                "final_verdict": "maybe",
            },
        )
    )
    assert envelope["summary_status"] == "WARN"
    assert any("invalid final_verdict" in w for w in envelope["warnings"])


@pytest.mark.unit
def test_ranking_secret_warning_redacted_in_envelope_warnings() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            ranked_results=[
                {
                    "result_id": "api_key=sk-testsecretvalue123456789",
                    "warnings": ["api_key=sk-testsecretvalue123456789"],
                    "ranking_explanation": {"final_score": 0.1, "warnings": []},
                }
            ],
        )
    )
    serialized = json.dumps(envelope)
    assert "sk-testsecretvalue" not in serialized
    assert "[REDACTED]" in serialized


@pytest.mark.unit
def test_ranking_invalid_factor_warnings_propagate() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            ranked_results=[
                {
                    "result_id": "doc-2",
                    "warnings": ["invalid_factor:confidence"],
                    "ranking_explanation": {"final_score": 0.5, "warnings": []},
                }
            ],
        )
    )
    assert envelope["summary_status"] == "WARN"
    card = next(c for c in envelope["signal_cards"] if c["card_id"] == "ranking.doc-2")
    assert card["severity"] == "WARN"
    assert any("invalid_factor:confidence" in w for w in envelope["warnings"])


@pytest.mark.unit
def test_ranking_inferred_creates_warn_card() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            ranked_results=[
                {
                    "result_id": "doc-1",
                    "inferred": True,
                    "ranking_explanation": {
                        "final_score": 0.42,
                        "warnings": ["weak_match:inferred_result"],
                        "caveats": ["Result is inferred; verify against repo or live evidence."],
                    },
                }
            ],
        )
    )
    assert envelope["summary_status"] == "WARN"
    card = next(c for c in envelope["signal_cards"] if c["source"] == "hybrid_retrieval_ranking")
    assert card["severity"] == "WARN"
    assert card.get("caveats")


@pytest.mark.unit
def test_replay_unresolved_evidence_warning() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            decision_replay={
                "schema_version": "decision-replay-query/v2",
                "replay_id": "replay-1",
                "unresolved_evidence_refs": ["ev-missing-1"],
                "evidence_warnings": ["unresolved_evidence_refs_present"],
            },
        )
    )
    assert envelope["summary_status"] == "WARN"
    assert any("unresolved" in w.lower() for w in envelope["warnings"])
    assert any("unresolved" in c["title"].lower() for c in envelope["signal_cards"])


@pytest.mark.unit
def test_context_package_guardrails_propagate() -> None:
    extra = "Context Package is orientation, not authorization."
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            context_package={
                "schema_version": "context-package/v2",
                "package_id": "pkg_test",
                "guardrails": [extra],
                "limitations": [],
                "artifacts": [{"artifact_id": "a1", "artifact_type": "doc"}],
            },
        )
    )
    assert extra in envelope["guardrails"]
    for guardrail in GUARDRAILS:
        assert guardrail in envelope["guardrails"]


@pytest.mark.unit
def test_secret_fields_redacted_in_cards() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={
                "adoption_status": "warn",
                "gate_matrix": [
                    {
                        "check_id": "secret-check",
                        "status": "fail",
                        "blocking": False,
                        "detail": "api_key=sk-testsecretvalue123456789",
                    }
                ],
            },
        )
    )
    serialized = json.dumps(envelope)
    assert "sk-testsecretvalue" not in serialized
    assert "[REDACTED]" in serialized


@pytest.mark.unit
def test_determinism_same_hash_for_equivalent_inputs() -> None:
    cert = {"adoption_status": "pass", "final_verdict": "certified"}
    req1 = _base_request(operator_certification=cert)
    req2 = _base_request(operator_certification=dict(cert))
    e1 = build_control_room_signal_layer_v1(req1)
    e2 = build_control_room_signal_layer_v1(req2)
    assert e1["determinism"]["content_hash"] == e2["determinism"]["content_hash"]


@pytest.mark.unit
def test_readiness_blocked_not_downgraded() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            agent_os_readiness={
                "readiness_id": "r1",
                "readiness_level": "blocked",
                "blocking_findings": ["scope drift open"],
                "weak_findings": [],
                "missing_inputs": [],
                "required_validation": ["Human review required"],
                "guardrails": list(GUARDRAILS[:3]),
            },
        )
    )
    assert envelope["summary_status"] == "BLOCKED"
    assert envelope["blocking_findings"]


@pytest.mark.unit
def test_no_authorization_wording_in_output() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            context_package={
                "schema_version": "context-package/v2",
                "package_id": "pkg_ok",
                "guardrails": list(GUARDRAILS),
                "limitations": ["ranked_context_not_provided"],
                "artifacts": [{"artifact_id": "a1", "artifact_type": "doc"}],
            },
            operator_certification={"adoption_status": "pass", "final_verdict": "certified"},
        )
    )
    text = json.dumps(envelope)
    assert not _FORBIDDEN_PHRASE_RE.search(text)


@pytest.mark.unit
def test_empty_scope_raises() -> None:
    with pytest.raises(ControlRoomSignalLayerError, match="generated_for_scope"):
        build_control_room_signal_layer_v1(
            ControlRoomSignalLayerRequest(generated_for_scope="  ")
        )


@pytest.mark.unit
def test_signal_cards_stable_sort_order() -> None:
    envelope = build_control_room_signal_layer_v1(
        _base_request(
            operator_certification={"adoption_status": "warn"},
            agent_os_readiness={
                "readiness_id": "r1",
                "readiness_level": "weak",
                "blocking_findings": [],
                "weak_findings": ["stale source"],
                "missing_inputs": [],
                "required_validation": [],
                "guardrails": [],
            },
        )
    )
    cards = envelope["signal_cards"]
    severity_rank = {
        "BLOCKED": 6,
        "FAIL": 5,
        "WARN": 4,
        "UNKNOWN": 3,
        "SKIPPED": 2,
        "PASS": 1,
    }

    def _sort_key(card: dict[str, Any]) -> tuple[int, str, str]:
        sev = card["severity"]
        return (-severity_rank.get(sev, 0), str(card["card_id"]), str(card["source"]))

    sort_keys = [_sort_key(c) for c in cards]
    assert sort_keys == sorted(sort_keys)


@pytest.mark.unit
def test_schema_version_constant() -> None:
    envelope = build_control_room_signal_layer_v1(_base_request())
    assert envelope["schema_version"] == SCHEMA_VERSION
