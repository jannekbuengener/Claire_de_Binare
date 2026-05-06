"""
Unit tests for MCP Briefing Enrichment (#2122).

Tests the briefing enrichment logic in context_briefing_handler
from tools.mcp.context_bridge.

Covers:
- Fail-closed (no records) → controlled-empty enrichment
- Real enrichment with Wave-14 fixture records
- Stale/missing/blocking evidence surfaces correctly
- Registry/Bridge completeness for Wave-14 tools
- Guardrails: no_echtgeld_go, no Live-Go
"""

import json
from pathlib import Path

import pytest
from tools.mcp.context_bridge import context_briefing_handler

pytestmark = pytest.mark.unit


FIXTURE_PATH = Path("tests/fixtures/surrealdb/wave14/wave14_v1.json")


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _minimal_kwargs(**extra) -> dict:
    base = dict(
        task_id="test-enrich",
        task_scope="test enrichment",
        target_issue=None,
        requested_depth="quick",
        operation_mode="read_only",
    )
    base.update(extra)
    return base


class TestBriefingEnrichmentFailClosed:
    """Tests for fail-closed (no records) enrichment behavior."""

    def test_enrichment_id_present(self) -> None:
        """Briefing result includes enrichment_id."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-1"))
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert "enrichment_id" in briefing
        assert briefing["enrichment_id"].startswith("cdb-enrich-")
        assert "enriched_briefing_id" in briefing
        assert briefing["enriched_briefing_id"] == briefing["briefing_id"]

    def test_trust_summary_reports_no_records_provided(self) -> None:
        """Trust summary indicates enrichment was skipped (no records)."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-2"))
        assert result["status"] == "ok"
        summary = result["briefing"]["trust_summary"]
        assert "Enrichment skipped" in summary
        assert "no evidence_records" in summary.lower() or "supply records" in summary.lower()

    def test_no_records_returns_empty_enriched_fields(self) -> None:
        """No records provided → enriched fields are empty (fail-closed)."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-3"))
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert briefing["enriched_decisions"] == []
        assert briefing["enriched_evidence"] == []
        assert briefing["enriched_memory"] == []

    def test_no_records_missing_evidence_notice(self) -> None:
        """No records provided → missing_evidence_notice indicates missing inputs."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-4"))
        assert result["status"] == "ok"
        notice = result["briefing"]["missing_evidence_notice"]
        assert any("no_evidence_records_provided" in n for n in notice)
        assert any("no_decision_events_provided" in n for n in notice)

    def test_no_records_stop_condition_s5(self) -> None:
        """No records → S5 stop condition about missing enrichment records."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-5"))
        assert result["status"] == "ok"
        assert any("S5" in sc for sc in result["briefing"]["stop_conditions"])

    def test_enriched_fields_completeness(self) -> None:
        """All required enrichment fields are present in the output."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-6"))
        assert result["status"] == "ok"
        briefing = result["briefing"]
        required_fields = {
            "enrichment_id",
            "enriched_briefing_id",
            "trust_summary",
            "enriched_decisions",
            "enriched_evidence",
            "enriched_memory",
            "enriched_stop_conditions",
            "stale_evidence_notice",
            "contradictory_evidence_notice",
            "missing_evidence_notice",
            "blocking_trust_findings",
            "recommended_next_reads",
            "approval_semantics",
        }
        for field in required_fields:
            assert field in briefing, f"Missing enrichment field: {field}"

    def test_approval_semantics_no_echtgeld_go(self) -> None:
        """approval_semantics.no_echtgeld_go is always True (no records)."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-enrich-7"))
        assert result["status"] == "ok"
        sem = result["briefing"]["approval_semantics"]
        assert sem["no_echtgeld_go"] is True


class TestBriefingEnrichmentWithRecords:
    """Tests for real enrichment when Wave-14 records are provided."""

    def test_enrichment_with_evidence_records(self) -> None:
        """Briefing with evidence_records → enriched_evidence populated from service."""
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-ev-1",
                evidence_records=fx["evidence_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        # Real enrichment: evidence comes from service, not stub
        assert len(briefing["enriched_evidence"]) > 0
        ids = {e["evidence_id"] for e in briefing["enriched_evidence"]}
        assert "ev-001" in ids  # present in fixture

    def test_enrichment_with_memory_records(self) -> None:
        """Briefing with memory_records → enriched_memory populated from service."""
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-mem-1",
                memory_records=fx["memory_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert len(briefing["enriched_memory"]) > 0
        ids = {m["memory_id"] for m in briefing["enriched_memory"]}
        # mem-001 and mem-002 are wave14 scope
        assert "mem-001" in ids or "mem-002" in ids

    def test_enrichment_with_all_records(self) -> None:
        """Briefing with all record types → all enriched fields populated from services."""
        fx = _load_fixture()
        result = context_briefing_handler(
            task_id="test-enrich-all",
            task_scope="wave14 full enrichment test",
            target_issue="#2122",
            requested_depth="standard",
            operation_mode="read_only",
            evidence_records=fx["evidence_records"],
            claim_records=fx["claim_records"],
            memory_records=fx["memory_records"],
            enrichment_scope="wave14",
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        # Evidence: from service (not empty stub)
        assert len(briefing["enriched_evidence"]) > 0
        # Memory: from service (not empty stub)
        assert len(briefing["enriched_memory"]) > 0
        # Trust summary: from real trust_summary_v1 service
        ts = briefing["trust_summary"]
        assert "Trust level:" in ts
        assert "Composite score:" in ts
        assert "no_echtgeld_go: true" in ts

    def test_enrichment_trust_summary_includes_trust_level(self) -> None:
        """Trust summary from real service includes trust_level."""
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-ts",
                evidence_records=fx["evidence_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        ts = result["briefing"]["trust_summary"]
        # Must include trust level from real service output
        assert any(level in ts for level in ("blocked", "weak", "acceptable", "strong"))

    def test_enrichment_blocking_missing_evidence_visible(self) -> None:
        """Blocking missing evidence (ev-004 in fixture) surfaces in blocking_trust_findings."""
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-blocking",
                evidence_records=fx["evidence_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        # ev-004 has blocking_missing=true → must surface
        blocking = briefing["blocking_trust_findings"]
        assert any("ev-004" in str(b) for b in blocking), (
            f"Expected ev-004 in blocking_trust_findings, got: {blocking}"
        )

    def test_enrichment_stale_evidence_visible(self) -> None:
        """Stale evidence (ev-005 in fixture) surfaces in stale_evidence_notice."""
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-stale",
                evidence_records=fx["evidence_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        # ev-005 has stale=true → must surface
        stale = briefing["stale_evidence_notice"]
        assert any("ev-005" in str(s) for s in stale), (
            f"Expected ev-005 in stale_evidence_notice, got: {stale}"
        )

    def test_enrichment_approval_semantics_no_echtgeld_go_with_records(self) -> None:
        """approval_semantics.no_echtgeld_go is True even when records are provided."""
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-sem",
                evidence_records=fx["evidence_records"],
            )
        )
        assert result["status"] == "ok"
        sem = result["briefing"]["approval_semantics"]
        assert sem["no_echtgeld_go"] is True

    def test_enrichment_no_crash_on_empty_lists(self) -> None:
        """Empty lists for records → fail-closed, no crash."""
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-empty",
                evidence_records=[],
                claim_records=[],
                decision_events=[],
                memory_records=[],
            )
        )
        assert result["status"] == "ok"
        assert result["briefing"]["enriched_evidence"] == []
        assert result["briefing"]["enriched_memory"] == []

    def test_enrichment_no_db_no_network(self) -> None:
        """Enrichment with records must NOT require DB or network (pure in-memory)."""
        fx = _load_fixture()
        # If this runs without network/DB, the test passes — services are in-memory
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-no-db",
                evidence_records=fx["evidence_records"],
                memory_records=fx["memory_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"

    def test_enrichment_custom_scope(self) -> None:
        """enrichment_scope kwarg controls which records are retrieved."""
        fx = _load_fixture()
        # Using a non-existent scope → no matching claims/memory
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-enrich-scope",
                claim_records=fx["claim_records"],
                memory_records=fx["memory_records"],
                enrichment_scope="nonexistent_scope_xyz",
            )
        )
        assert result["status"] == "ok"
        # No claim/memory records match a nonexistent scope
        assert result["briefing"]["enriched_memory"] == []

    def test_undated_evidence_not_silently_dropped(self) -> None:
        """Evidence records without created_at must not be silently excluded.

        by_freshness excludes records where _created_at_dt is None. The bridge
        must detect and preserve undated records rather than reporting 0 evidence.
        They must appear in enriched_evidence and be flagged in blocking_trust_findings.
        """
        undated_records = [
            {
                "evidence_id": "ev-undated-001",
                "title": "Undated Evidence Record",
                "confidence": 0.75,
                "stale": False,
                "blocking_missing": False,
                "evidence_type": "test_run",
                "scope": "wave14",
                # No created_at — would be silently dropped by by_freshness alone
            }
        ]
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-undated-ev",
                evidence_records=undated_records,
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert briefing["approval_semantics"]["no_echtgeld_go"] is True

        enriched = briefing["enriched_evidence"]
        trust_findings = briefing.get("blocking_trust_findings", [])

        undated_in_enriched = any(
            ev.get("evidence_id") == "ev-undated-001" for ev in enriched
        )
        undated_in_findings = any(
            "undated" in str(f) or "ev-undated-001" in str(f)
            for f in trust_findings
        )
        assert undated_in_enriched or undated_in_findings, (
            "Undated evidence must appear in enriched_evidence or blocking_trust_findings, "
            f"got enriched={enriched}, findings={trust_findings}"
        )

    def test_undated_evidence_visible_in_blocking_findings(self) -> None:
        """Undated records must be explicitly flagged in blocking_trust_findings."""
        undated_records = [
            {
                "evidence_id": "ev-nodatestamp",
                "title": "No Timestamp Evidence",
                "confidence": 0.6,
                "scope": "wave14",
                # No created_at
            }
        ]
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-undated-findings",
                evidence_records=undated_records,
            )
        )
        assert result["status"] == "ok"
        findings = result["briefing"].get("blocking_trust_findings", [])
        assert any("undated" in str(f) for f in findings), (
            f"Expected undated_evidence finding, got: {findings}"
        )

    def test_malformed_evidence_records_do_not_crash(self) -> None:
        """Non-dict items in evidence_records must not raise AttributeError.

        A malformed MCP payload may include strings, None, or ints in the
        evidence_records list. The undated-record pass must skip them safely
        and return a controlled result, never propagate AttributeError.
        """
        mixed_records = [
            {
                "evidence_id": "ev-valid-001",
                "title": "Valid Record",
                "confidence": 0.8,
                "created_at": "2025-01-01T00:00:00Z",
                "scope": "wave14",
            },
            "bad-record-string",  # non-dict
            None,                 # non-dict
            42,                   # non-dict
        ]
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-malformed-ev",
                evidence_records=mixed_records,
            )
        )
        # Must not crash
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert briefing["approval_semantics"]["no_echtgeld_go"] is True
        # Valid record must be visible in enriched_evidence
        enriched = briefing["enriched_evidence"]
        assert any(ev.get("evidence_id") == "ev-valid-001" for ev in enriched), (
            f"Valid evidence record missing from enriched_evidence: {enriched}"
        )
        # Malformed records must be flagged, not silently treated as evidence
        findings = briefing.get("blocking_trust_findings", [])
        assert any("malformed" in str(f) for f in findings), (
            f"Expected malformed_evidence_records finding, got: {findings}"
        )

    def test_all_malformed_evidence_records_do_not_crash(self) -> None:
        """evidence_records containing only non-dict items is controlled-empty."""
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-all-malformed-ev",
                evidence_records=["bad", None, 0],
            )
        )
        assert result["status"] == "ok"
        assert result["briefing"]["approval_semantics"]["no_echtgeld_go"] is True

    def test_trust_summary_blocking_findings_key_surfaced(self) -> None:
        """Trust summary blocking findings must appear in briefing blocking_trust_findings.

        build_trust_summary_v1 returns results under 'blocking_trust_findings'.
        The bridge must read that key (not the non-existent 'blocking_findings')
        so that S6 stop condition fires and blocking count appears in trust_summary.
        """
        # ev-004 in fixture has blocking_missing=True → trust summary sets
        # blocking_trust_findings: ["blocking_missing_evidence"].
        fx = _load_fixture()
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-ts-blocking-key",
                evidence_records=fx["evidence_records"],
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        # S6 stop condition must fire when trust summary has blocking findings
        assert any("S6" in sc for sc in briefing["stop_conditions"]), (
            f"S6 stop condition missing; stop_conditions={briefing['stop_conditions']}"
        )
        # trust_summary string must mention blocking count
        ts = briefing["trust_summary"]
        assert "Blocking findings:" in ts, (
            f"Expected 'Blocking findings:' in trust_summary, got: {ts}"
        )

    def test_local_blocking_findings_trigger_s6_and_trust_summary(self) -> None:
        """Local blocking findings (undated evidence) must trigger S6 and blocking count.

        Thread PRRT_kwDOQUkXUM5_1I9X: only _ts_blocking from build_trust_summary_v1
        drove S6 and the trust_summary blocking count. Locally detected findings
        (undated records, malformed items) were in blocking_trust_findings but
        never surfaced in the stop conditions or trust_summary string.
        Fix: S6 and blocking count use blocking_trust_findings (which includes
        both local and ts findings) after the trust summary call.
        """
        # An undated wave14 record has no created_at → by_freshness drops it →
        # bridge adds it to blocking_trust_findings as undated_evidence_missing_created_at.
        # build_trust_summary_v1 has no evidence_result blocking items (empty service
        # result since by_freshness matched nothing), so _ts_blocking is [].
        # The fix ensures S6 still fires from the local finding.
        undated_scoped = [
            {
                "evidence_id": "ev-local-blocking",
                "title": "Undated Scoped Record",
                "confidence": 0.7,
                "stale": False,
                "blocking_missing": False,
                "evidence_type": "test_run",
                "scope": "wave14",
                # No created_at → by_freshness misses it, bridge flags it locally
            }
        ]
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-local-blocking-s6",
                evidence_records=undated_scoped,
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        briefing = result["briefing"]
        assert briefing["approval_semantics"]["no_echtgeld_go"] is True
        # S6 must fire because local blocking_trust_findings has undated entry
        assert any("S6" in sc for sc in briefing["stop_conditions"]), (
            f"S6 missing from stop_conditions: {briefing['stop_conditions']}"
        )
        # trust_summary must mention blocking count
        ts = briefing["trust_summary"]
        assert "Blocking findings:" in ts, (
            f"Expected 'Blocking findings:' in trust_summary, got: {ts}"
        )

    def test_claims_exact_scope_filter_excludes_prefix_match(self) -> None:
        """Claims with scope='wave14' must not appear when enrichment_scope='wave1'.

        Thread PRRT_kwDOQUkXUM5_1I9Z: ClaimResolver.by_scope uses substring
        matching — 'wave1' in 'wave14' is True. A scoped briefing for 'wave1'
        would include wave14 claims. Fix: pre-filter claim records to exact scope
        before calling the service.
        """
        claim_records = [
            {
                "claim_id": "cl-wave14-001",
                "title": "Wave14 Claim",
                "scope": "wave14",        # must NOT match scope='wave1'
                "status": "disputed",
                "created_at": "2025-01-01T00:00:00Z",
            },
            {
                "claim_id": "cl-wave1-001",
                "title": "Wave1 Claim",
                "scope": "wave1",         # must match scope='wave1'
                "status": "supported",
                "created_at": "2025-01-01T00:00:00Z",
            },
        ]
        result_wave1 = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-claim-scope-exact",
                claim_records=claim_records,
                enrichment_scope="wave1",
            )
        )
        assert result_wave1["status"] == "ok"
        # wave14 claim is disputed — if it leaked in, contradictory_evidence_notice
        # would contain it. With exact-scope filter it must NOT appear.
        notice = result_wave1["briefing"]["contradictory_evidence_notice"]
        assert not any("cl-wave14-001" in str(n) for n in notice), (
            f"wave14 claim must not appear in wave1 briefing: {notice}"
        )

    def test_decisions_exact_scope_filter_excludes_prefix_match(self) -> None:
        """Decisions with scope='wave14' must not appear when enrichment_scope='wave1'.

        Thread PRRT_kwDOQUkXUM5_1I9b: DecisionHistoryQuery.by_scope uses
        substring matching. Fix: pre-filter decision events to exact scope
        before calling the service, and post-filter matched_decisions.
        """
        decision_events = [
            {
                "decision_id": "dec-wave14-001",
                "title": "Wave14 Decision",
                "scope": "wave14",        # must NOT appear under scope='wave1'
                "status": "current",
                "created_at": "2025-01-01T00:00:00Z",
            },
            {
                "decision_id": "dec-wave1-001",
                "title": "Wave1 Decision",
                "scope": "wave1",         # must appear under scope='wave1'
                "status": "current",
                "created_at": "2025-01-01T00:00:00Z",
            },
        ]
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-decision-scope-exact",
                decision_events=decision_events,
                enrichment_scope="wave1",
            )
        )
        assert result["status"] == "ok"
        enriched = result["briefing"]["enriched_decisions"]
        ids = [d.get("decision_id") for d in enriched]
        assert "dec-wave14-001" not in ids, (
            f"wave14 decision must not appear in wave1 briefing: {ids}"
        )

    def test_evidence_scope_filter_excludes_other_scopes(self) -> None:
        """Evidence records outside enrichment_scope must not appear in enriched_evidence.

        by_freshness returns all dated records regardless of scope. The bridge
        must post-filter to _enrichment_scope so that out-of-scope records
        (e.g. wave13 evidence) do not pollute the scoped briefing.
        """
        mixed_scope_records = [
            {
                "evidence_id": "ev-in-scope",
                "title": "In-scope Evidence",
                "confidence": 0.9,
                "created_at": "2025-01-01T00:00:00Z",
                "stale": False,
                "blocking_missing": False,
                "evidence_type": "test_run",
                "scope": "wave14",
            },
            {
                "evidence_id": "ev-out-of-scope",
                "title": "Out-of-scope Evidence",
                "confidence": 0.9,
                "created_at": "2025-01-01T00:00:00Z",
                "stale": False,
                "blocking_missing": False,
                "evidence_type": "test_run",
                "scope": "wave13",  # different scope
            },
        ]
        result = context_briefing_handler(
            **_minimal_kwargs(
                task_id="test-scope-filter",
                evidence_records=mixed_scope_records,
                enrichment_scope="wave14",
            )
        )
        assert result["status"] == "ok"
        enriched = result["briefing"]["enriched_evidence"]
        ev_ids = [ev.get("evidence_id") for ev in enriched]
        assert "ev-in-scope" in ev_ids, (
            f"In-scope evidence missing from enriched_evidence: {ev_ids}"
        )
        assert "ev-out-of-scope" not in ev_ids, (
            f"Out-of-scope evidence must not appear in enriched_evidence: {ev_ids}"
        )


class TestBriefingEnrichmentGuardrails:
    """Tests for guardrail enforcement in briefing enrichment."""

    def test_guardrails_always_present(self) -> None:
        """Guardrails list is always present and contains no-write/no-live entries."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-guard-1"))
        assert result["status"] == "ok"
        guards = result["briefing"]["guardrails"]
        assert any("No" in g for g in guards)
        assert any("Live" in g or "Echtgeld" in g for g in guards)

    def test_no_live_go_in_stop_conditions(self) -> None:
        """Stop conditions always include no-live-go/no-echtgeld entries."""
        result = context_briefing_handler(**_minimal_kwargs(task_id="test-guard-2"))
        assert result["status"] == "ok"
        stop = result["briefing"]["stop_conditions"]
        # At minimum, LR/stage stop condition should be present
        assert any("LR" in sc or "S10" in sc or "S5" in sc for sc in stop)


class TestRegistryWave14Completeness:
    """Tests for Wave-14 tool registry/bridge completeness (#2122)."""

    def test_all_wave14_tools_registered(self) -> None:
        """All 6 Wave-14 tool names are registered in the registry."""
        from tools.mcp.registry import ContextToolRegistry

        required_names = {
            "cdb_context_evidence_resolve",
            "cdb_context_claim_resolve",
            "cdb_context_memory_get",
            "cdb_context_trust_summary",
            "cdb_context_decision_history",
            "cdb_context_decision_replay",
        }
        registered = set(ContextToolRegistry.list_tool_names())
        missing = required_names - registered
        assert not missing, f"Wave-14 tools missing from registry: {missing}"

    def test_wave14_tools_are_read_only(self) -> None:
        """All Wave-14 tools in registry have read_only=True."""
        from tools.mcp.registry import ContextToolRegistry

        wave14_names = [
            "cdb_context_evidence_resolve",
            "cdb_context_claim_resolve",
            "cdb_context_memory_get",
            "cdb_context_trust_summary",
            "cdb_context_decision_history",
            "cdb_context_decision_replay",
        ]
        for name in wave14_names:
            tool = ContextToolRegistry.get_tool(name)
            assert tool is not None, f"Tool {name} not found in registry"
            assert tool.read_only is True, f"Tool {name} is not read_only"

    def test_wave14_handlers_wired_in_bridge(self) -> None:
        """Wave-14 tools have real handlers (not just not_implemented stubs) in bridge."""
        from tools.mcp.context_bridge import create_bridge

        bridge = create_bridge()
        wave14_names = [
            "cdb_context_evidence_resolve",
            "cdb_context_claim_resolve",
            "cdb_context_memory_get",
            "cdb_context_trust_summary",
            "cdb_context_decision_history",
            "cdb_context_decision_replay",
        ]
        for name in wave14_names:
            tool = bridge._registry.get_tool(name)
            assert tool is not None, f"Tool {name} not found in bridge registry"
            # Handler must be a real function, not the not_implemented placeholder
            fn_name = tool.handler.__name__
            assert "not_implemented" not in fn_name, (
                f"Tool {name} still uses not_implemented handler: {fn_name}"
            )

    def test_bridge_execute_evidence_resolve(self) -> None:
        """Bridge can execute cdb_context_evidence_resolve via execute_tool."""
        from tools.mcp.context_bridge import create_bridge

        fx = _load_fixture()
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_evidence_resolve",
            {
                "mode": "by_confidence",
                "min_confidence": 0.0,
                "evidence_records": fx["evidence_records"],
            },
        )
        assert result["status"] == "ok", f"Expected ok, got: {result}"
        assert result["tool"] == "cdb_context_evidence_resolve"

    def test_bridge_execute_memory_get(self) -> None:
        """Bridge can execute cdb_context_memory_get via execute_tool."""
        from tools.mcp.context_bridge import create_bridge

        fx = _load_fixture()
        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_memory_get",
            {
                "mode": "by_scope",
                "scope": "wave14",
                "memory_records": fx["memory_records"],
            },
        )
        assert result["status"] == "ok", f"Expected ok, got: {result}"

    def test_bridge_execute_trust_summary(self) -> None:
        """Bridge can execute cdb_context_trust_summary via execute_tool."""
        from tools.mcp.context_bridge import create_bridge

        bridge = create_bridge()
        result = bridge.execute_tool(
            "cdb_context_trust_summary",
            {"scope": "wave14"},
        )
        assert result["status"] == "ok", f"Expected ok, got: {result}"
        assert result["result"]["approval_semantics"]["no_echtgeld_go"] is True
