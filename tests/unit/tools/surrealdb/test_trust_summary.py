from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from tests.local.tools.mcp.wave14_smoke_helpers import (
    build_record_plan,
    materialize_fixture_records,
)
from tools.mcp.context_evidence_memory_tools import (
    _normalize_evidence_ref_row,
    _normalize_claim_row,
    _normalize_memory_row,
)
from tools.surrealdb.evidence_lookup import lookup_evidence_v1, EvidenceLookupRequest
from tools.surrealdb.claim_resolver import resolve_claims_v1, ClaimResolveRequest
from tools.surrealdb.memory_read import read_memory_v1, MemoryReadRequest
from tools.surrealdb.decision_history_query import (
    query_decision_history_v1,
    DecisionHistoryQueryRequest,
)
from tools.surrealdb.trust_summary import (
    build_trust_summary_v1,
    TrustSummaryRequest,
    TrustContextSignals,
)

pytestmark = pytest.mark.unit

FIXED_NOW = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)
PLAN = build_record_plan("trust-summary-unit")
TRUSTED_SIGNALS = TrustContextSignals(
    record_source="surrealdb-local",
    freshness_ok=True,
    repo_crosscheck_present=True,
)


def _load_jsonl(filename: str) -> list[dict]:
    text = materialize_fixture_records(
        filename, run_id=PLAN.run_id, plan=PLAN, materialized_at=FIXED_NOW
    )
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _run_lookups():
    ev_list = _load_jsonl("evidence_refs.jsonl")
    ev_input = [_normalize_evidence_ref_row(r) for r in ev_list]
    ev_result = lookup_evidence_v1(
        ev_input,
        EvidenceLookupRequest(mode="by_freshness", freshness_days=36500, limit=200),
    )

    cl_list = _load_jsonl("claims.jsonl")
    cl_input = [_normalize_claim_row(r) for r in cl_list]
    cl_result = resolve_claims_v1(
        cl_input,
        ClaimResolveRequest(mode="by_scope", scope="wave14", limit=200),
    )

    dec_list = _load_jsonl("decision_events.jsonl")
    dec_result = query_decision_history_v1(
        dec_list,
        DecisionHistoryQueryRequest(mode="by_scope", scope="wave14", limit=200),
    )

    mem_list = _load_jsonl("agent_memories.jsonl")
    mem_input = [_normalize_memory_row(r) for r in mem_list]
    mem_result = read_memory_v1(
        mem_input,
        MemoryReadRequest(mode="by_scope", scope="wave14", limit=200),
    )

    return ev_result, cl_result, dec_result, mem_result


class TestTrustSummaryWithFixtureData:
    def test_composite_score_matches_expected_value(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
            context_signals=TRUSTED_SIGNALS,
        )
        assert ts["composite_score"] == pytest.approx(0.7825, abs=1e-4)

    def test_trust_level_is_acceptable(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
            context_signals=TRUSTED_SIGNALS,
        )
        assert ts["trust_level"] == "acceptable"

    def test_operator_trust_level_is_medium_with_good_signals(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
            context_signals=TRUSTED_SIGNALS,
        )
        assert ts["operator_trust_level"] == "MEDIUM"

    def test_operator_trust_level_medium_even_without_signals(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        assert ts["operator_trust_level"] == "MEDIUM"

    def test_evidence_strength_is_strong(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        assert ts["evidence_strength"] == "strong"
        assert ts["evidence_strength_score"] == pytest.approx(0.90, abs=1e-4)

    def test_claim_score_is_max(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        assert ts["claim_score"] == pytest.approx(1.00, abs=1e-4)

    def test_decision_score_penalized_by_invalidated_decision(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        assert ts["decision_score"] == pytest.approx(0.25, abs=1e-4)
        assert ts["decision_currentness"] == {
            "current": 1,
            "superseded": 0,
            "invalidated": 1,
            "total": 2,
        }

    def test_memory_score_is_max(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        assert ts["memory_score"] == pytest.approx(1.00, abs=1e-4)

    def test_no_blocking_findings_or_warnings(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
            context_signals=TRUSTED_SIGNALS,
        )
        assert ts["blocking_trust_findings"] == []
        assert ts["stale_flags"] == []
        assert ts["disputed_flags"] == []
        assert ts["missing_evidence"] == []

    def test_composite_formula_breakdown(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        expected = (
            0.30 * ts["evidence_strength_score"]
            + 0.25 * ts["claim_score"]
            + 0.25 * ts["decision_score"]
            + 0.20 * ts["memory_score"]
        )
        assert ts["composite_score"] == pytest.approx(expected, abs=1e-4)

    def test_confidence_summary_contains_dimensional_breakdown(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        cs = ts["confidence_summary"]
        assert cs["composite_score"] == ts["composite_score"]
        assert cs["trust_level"] == ts["trust_level"]
        assert cs["operator_trust_level"] == ts["operator_trust_level"]
        assert cs["dimensions"]["evidence"] == ts["evidence_strength_score"]
        assert cs["dimensions"]["claims"] == ts["claim_score"]
        assert cs["dimensions"]["decisions"] == ts["decision_score"]
        assert cs["dimensions"]["memory"] == ts["memory_score"]

    def test_operator_trust_mapping_contains_base_and_gates(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
            context_signals=TRUSTED_SIGNALS,
        )
        m = ts["operator_trust_mapping"]
        assert m["legacy_trust_level"] == "acceptable"
        assert m["base_operator_level"] == "MEDIUM"
        assert m["gates_applied"] == []
        assert m["context_signals_supplied"] is True

    def test_gap_to_high_is_approximately_0_0175(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
            context_signals=TRUSTED_SIGNALS,
        )
        gap = 0.80 - ts["composite_score"]
        assert gap == pytest.approx(0.0175, abs=1e-4)

    def test_requires_scope(self):
        with pytest.raises(ValueError, match="scope is required"):
            build_trust_summary_v1(
                TrustSummaryRequest(scope=""),
            )

    def test_authorization_semantics_always_deny(self):
        ev, cl, dec, mem = _run_lookups()
        ts = build_trust_summary_v1(
            TrustSummaryRequest(scope="wave14"),
            evidence_result=ev,
            claim_result=cl,
            decision_result=dec,
            memory_result=mem,
        )
        auth = ts["authorization_semantics"]
        assert auth["operational_truth_allowed"] is False
        assert auth["no_human_go"] is True
        assert auth["no_live_go"] is True
        assert auth["no_echtgeld_go"] is True
        assert auth["no_persist"] is True
        assert auth["no_mutation"] is True
