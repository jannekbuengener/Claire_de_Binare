"""Unit tests for stale_knowledge_scan.py — Stale Knowledge Scan Service v1.

Issues:
    #2154 — [SURREALDB][CONTEXT][STALE-RUNTIME] Implement stale knowledge scan service v1
    Parent: #2153 (Wave-16 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/stale_knowledge_scan.py.
    All fixtures are inline (no file loading — keeps slice narrow).
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No real datetime.now() — validated by test_clock.py::test_guardrails_no_forbidden_calls.

Coverage:
    - All 8 stale_type rules produce at least one finding with triggering input.
    - source_deleted produces a blocking finding.
    - All other stale_types produce warning findings by default.
    - Severity and confidence are set and within allowed ranges.
    - Deterministic IDs: same input → same stale_id.
    - No findings for a fully fresh/clean bundle.
    - to_dict() produces severity_summary with all severity levels.
    - All 5 guardrail strings are present in to_dict() output.
    - Output does not grant live-go, write, or delete authorization.
"""

from __future__ import annotations

import pytest

from tools.surrealdb.stale_knowledge_scan import (
    DETECTED_BY,
    GUARDRAILS,
    SCHEMA_VERSION,
    SEVERITY_LEVELS,
    STALE_TYPES,
    STATUS_VALUES,
    TOOL_NAME,
    StaleFinding,
    StaleKnowledgeScanError,
    StaleKnowledgeScanResult,
    _stale_id,
    scan_stale_knowledge_v1,
)

# Fixed reference timestamp used across all tests for determinism
_AS_OF = "2026-05-06T12:00:00+00:00"
_PAST = "2026-01-01T00:00:00+00:00"
_FUTURE = "2027-01-01T00:00:00+00:00"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_valid_finding(f: StaleFinding) -> None:
    """Assert all mandatory fields on a StaleFinding are valid."""
    assert isinstance(f.stale_id, str) and len(f.stale_id) > 0
    assert f.stale_type in STALE_TYPES, f"unexpected stale_type: {f.stale_type!r}"
    assert isinstance(f.target_ref, str) and len(f.target_ref) > 0
    assert isinstance(f.reason, str) and len(f.reason) > 0
    assert f.severity in SEVERITY_LEVELS, f"unexpected severity: {f.severity!r}"
    assert isinstance(f.confidence, float)
    assert 0.0 <= f.confidence <= 1.0
    assert isinstance(f.source_refs, tuple)
    assert isinstance(f.evidence_refs, tuple)
    assert isinstance(f.detected_by, str) and len(f.detected_by) > 0
    assert isinstance(f.detected_at, str) and len(f.detected_at) > 0
    assert isinstance(f.recommended_refresh, str) and len(f.recommended_refresh) > 0
    assert isinstance(f.blocking, bool)
    assert f.status in STATUS_VALUES, f"unexpected status: {f.status!r}"


def _scan(bundle: dict, as_of: str = _AS_OF) -> StaleKnowledgeScanResult:
    """Convenience wrapper with fixed as_of for deterministic tests."""
    return scan_stale_knowledge_v1(bundle, as_of=as_of)


# ── Rule: source_hash_changed ─────────────────────────────────────────────────


@pytest.mark.unit
def test_rule_source_hash_changed_finding() -> None:
    """source_hash_changed: hash mismatch produces a warning finding."""
    bundle = {
        "sources": [
            {
                "source_id": "src-hash-001",
                "path": "docs/api.md",
                "current_hash": "abc123def456",
                "last_verified_hash": "000000000000",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "source_hash_changed"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.blocking is False
    assert f.target_ref == "src-hash-001"


@pytest.mark.unit
def test_rule_source_hash_unchanged_no_finding() -> None:
    """source_hash_changed: matching hashes produce no finding."""
    bundle = {
        "sources": [
            {
                "source_id": "src-fresh-001",
                "current_hash": "aabbccdd",
                "last_verified_hash": "aabbccdd",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "source_hash_changed"]
    assert len(findings) == 0


# ── Rule: source_deleted ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_rule_source_deleted_exists_false() -> None:
    """source_deleted: exists=False produces a blocking finding."""
    bundle = {
        "sources": [
            {
                "source_id": "src-gone-001",
                "exists": False,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "source_deleted"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.blocking is True
    assert f.target_ref == "src-gone-001"


@pytest.mark.unit
def test_rule_source_deleted_deleted_at_set() -> None:
    """source_deleted: deleted_at set produces a blocking finding."""
    bundle = {
        "sources": [
            {
                "source_id": "src-gone-002",
                "deleted_at": "2026-03-01T00:00:00+00:00",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "source_deleted"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "blocking"
    assert f.blocking is True


@pytest.mark.unit
def test_rule_source_exists_true_no_finding() -> None:
    """source_deleted: exists=True and no deleted_at → no finding."""
    bundle = {
        "sources": [
            {
                "source_id": "src-alive-001",
                "exists": True,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "source_deleted"]
    assert len(findings) == 0


# ── Rule: decision_superseded ─────────────────────────────────────────────────


@pytest.mark.unit
def test_rule_decision_superseded_by_field() -> None:
    """decision_superseded: superseded_by set → warning finding."""
    bundle = {
        "decisions": [
            {
                "decision_id": "dec-old-001",
                "superseded_by": "dec-new-002",
                "status": "open",
                "topic": "Old architecture decision",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "decision_superseded"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.blocking is False
    assert f.target_ref == "dec-old-001"
    assert "dec-new-002" in f.source_refs


@pytest.mark.unit
def test_rule_decision_superseded_by_status() -> None:
    """decision_superseded: status='superseded' → warning finding."""
    bundle = {
        "decisions": [
            {
                "decision_id": "dec-old-002",
                "superseded_by": None,
                "status": "superseded",
                "topic": "Old strategy choice",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "decision_superseded"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"


@pytest.mark.unit
def test_rule_decision_active_no_finding() -> None:
    """decision_superseded: active decision (no superseded_by, status=open) → no finding."""
    bundle = {
        "decisions": [
            {
                "decision_id": "dec-active-001",
                "status": "open",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "decision_superseded"]
    assert len(findings) == 0


# ── Rule: evidence_expired ────────────────────────────────────────────────────


@pytest.mark.unit
def test_rule_evidence_expired() -> None:
    """evidence_expired: expires_at before as_of → warning finding."""
    bundle = {
        "evidence_records": [
            {
                "evidence_id": "ev-exp-001",
                "expires_at": _PAST,
                "topic": "Expired run evidence",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "evidence_expired"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.target_ref == "ev-exp-001"


@pytest.mark.unit
def test_rule_evidence_not_expired_no_finding() -> None:
    """evidence_expired: expires_at after as_of → no finding."""
    bundle = {
        "evidence_records": [
            {
                "evidence_id": "ev-fresh-001",
                "expires_at": _FUTURE,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "evidence_expired"]
    assert len(findings) == 0


# ── Rule: memory_ttl_expired ──────────────────────────────────────────────────


@pytest.mark.unit
def test_rule_memory_ttl_expired() -> None:
    """memory_ttl_expired: memory expires_at before as_of → warning finding."""
    bundle = {
        "memory_records": [
            {
                "memory_id": "mem-exp-001",
                "expires_at": _PAST,
                "scope": "cdb",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "memory_ttl_expired"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.target_ref == "mem-exp-001"


@pytest.mark.unit
def test_rule_memory_ttl_not_expired_no_finding() -> None:
    """memory_ttl_expired: expires_at after as_of → no finding."""
    bundle = {
        "memory_records": [
            {
                "memory_id": "mem-fresh-001",
                "expires_at": _FUTURE,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "memory_ttl_expired"]
    assert len(findings) == 0


# ── Rule: dependency_edge_no_longer_observed ──────────────────────────────────


@pytest.mark.unit
def test_rule_dependency_edge_observed_false() -> None:
    """dependency_edge_no_longer_observed: observed=False → warning finding."""
    bundle = {
        "dependency_edges": [
            {
                "edge_id": "edge-001",
                "from_ref": "service-a",
                "to_ref": "service-b",
                "observed": False,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "dependency_edge_no_longer_observed"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.blocking is False
    assert f.target_ref == "edge-001"


@pytest.mark.unit
def test_rule_dependency_edge_run_id_changed() -> None:
    """dependency_edge_no_longer_observed: last_observed_run_id != current_run_id → finding."""
    bundle = {
        "dependency_edges": [
            {
                "edge_id": "edge-002",
                "from_ref": "svc-x",
                "to_ref": "svc-y",
                "observed": True,
                "last_observed_run_id": "run-abc123",
                "current_run_id": "run-xyz999",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "dependency_edge_no_longer_observed"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert "run-abc123" in f.reason
    assert "run-xyz999" in f.reason


@pytest.mark.unit
def test_rule_dependency_edge_fresh_no_finding() -> None:
    """dependency_edge_no_longer_observed: observed=True, run IDs match → no finding."""
    bundle = {
        "dependency_edges": [
            {
                "edge_id": "edge-003",
                "from_ref": "svc-a",
                "to_ref": "svc-b",
                "observed": True,
                "last_observed_run_id": "run-same",
                "current_run_id": "run-same",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "dependency_edge_no_longer_observed"]
    assert len(findings) == 0


# ── Rule: stale_context_package ───────────────────────────────────────────────


@pytest.mark.unit
def test_rule_stale_context_package_snapshot_changed() -> None:
    """stale_context_package: snapshot ID mismatch → warning finding."""
    bundle = {
        "context_packages": [
            {
                "package_id": "pkg-001",
                "source_snapshot_id": "snap-old-aaa",
                "current_snapshot_id": "snap-new-bbb",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "stale_context_package"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.target_ref == "pkg-001"
    assert "snap-old-aaa" in f.reason
    assert "snap-new-bbb" in f.reason


@pytest.mark.unit
def test_rule_stale_context_package_freshness_exceeded() -> None:
    """stale_context_package: generated_at too old → warning finding."""
    bundle = {
        "context_packages": [
            {
                "package_id": "pkg-002",
                "generated_at": _PAST,
                "freshness_window_seconds": 3600,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "stale_context_package"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"


@pytest.mark.unit
def test_rule_stale_context_package_fresh_no_finding() -> None:
    """stale_context_package: same snapshot IDs and fresh generated_at → no finding."""
    bundle = {
        "context_packages": [
            {
                "package_id": "pkg-fresh",
                "source_snapshot_id": "snap-current",
                "current_snapshot_id": "snap-current",
                "generated_at": _FUTURE,
                "freshness_window_seconds": 3600,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "stale_context_package"]
    assert len(findings) == 0


# ── Rule: stale_briefing ──────────────────────────────────────────────────────


@pytest.mark.unit
def test_rule_stale_briefing_snapshot_changed() -> None:
    """stale_briefing: snapshot ID mismatch → warning finding."""
    bundle = {
        "briefings": [
            {
                "briefing_id": "brief-001",
                "source_snapshot_id": "snap-old-x",
                "current_snapshot_id": "snap-new-y",
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "stale_briefing"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"
    assert f.target_ref == "brief-001"


@pytest.mark.unit
def test_rule_stale_briefing_freshness_exceeded() -> None:
    """stale_briefing: generated_at too old → warning finding."""
    bundle = {
        "briefings": [
            {
                "briefing_id": "brief-002",
                "generated_at": _PAST,
                "freshness_window_seconds": 7200,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "stale_briefing"]
    assert len(findings) >= 1
    f = findings[0]
    _assert_valid_finding(f)
    assert f.severity == "warning"


@pytest.mark.unit
def test_rule_stale_briefing_fresh_no_finding() -> None:
    """stale_briefing: matching snapshot and future generated_at → no finding."""
    bundle = {
        "briefings": [
            {
                "briefing_id": "brief-fresh",
                "source_snapshot_id": "snap-cur",
                "current_snapshot_id": "snap-cur",
                "generated_at": _FUTURE,
                "freshness_window_seconds": 3600,
            }
        ]
    }
    result = _scan(bundle)
    findings = [f for f in result.findings if f.stale_type == "stale_briefing"]
    assert len(findings) == 0


# ── Cross-cutting tests ───────────────────────────────────────────────────────


@pytest.mark.unit
def test_no_findings_for_fresh_bundle() -> None:
    """A fully fresh bundle (nothing stale) produces 0 findings."""
    bundle = {
        "sources": [
            {
                "source_id": "src-clean",
                "exists": True,
                "current_hash": "deadbeef",
                "last_verified_hash": "deadbeef",
            }
        ],
        "decisions": [
            {
                "decision_id": "dec-active",
                "status": "open",
            }
        ],
        "evidence_records": [
            {
                "evidence_id": "ev-fresh",
                "expires_at": _FUTURE,
            }
        ],
        "memory_records": [
            {
                "memory_id": "mem-fresh",
                "expires_at": _FUTURE,
            }
        ],
        "dependency_edges": [
            {
                "edge_id": "edge-fresh",
                "from_ref": "a",
                "to_ref": "b",
                "observed": True,
                "last_observed_run_id": "run-same",
                "current_run_id": "run-same",
            }
        ],
        "context_packages": [
            {
                "package_id": "pkg-fresh",
                "source_snapshot_id": "snap-cur",
                "current_snapshot_id": "snap-cur",
                "generated_at": _FUTURE,
            }
        ],
        "briefings": [
            {
                "briefing_id": "brief-fresh",
                "source_snapshot_id": "snap-cur",
                "current_snapshot_id": "snap-cur",
                "generated_at": _FUTURE,
            }
        ],
    }
    result = _scan(bundle)
    assert result.total_count == 0
    assert result.blocking_count == 0
    assert len(result.findings) == 0


@pytest.mark.unit
def test_deterministic_stale_ids() -> None:
    """Same input produces identical stale_id across two independent scan calls."""
    bundle = {
        "sources": [
            {
                "source_id": "src-det-001",
                "current_hash": "new-hash-xyz",
                "last_verified_hash": "old-hash-abc",
            }
        ]
    }
    result_a = _scan(bundle)
    result_b = _scan(bundle)

    ids_a = {f.stale_id for f in result_a.findings if f.stale_type == "source_hash_changed"}
    ids_b = {f.stale_id for f in result_b.findings if f.stale_type == "source_hash_changed"}
    assert ids_a == ids_b
    assert len(ids_a) >= 1


@pytest.mark.unit
def test_stale_id_helper_deterministic() -> None:
    """_stale_id() returns same value for same inputs, different for different inputs."""
    id1 = _stale_id("source_hash_changed", "src-001", "hash diff")
    id2 = _stale_id("source_hash_changed", "src-001", "hash diff")
    id3 = _stale_id("source_deleted", "src-001", "hash diff")
    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16  # SHA256 prefix, 16 hex chars


@pytest.mark.unit
def test_severity_summary_in_to_dict() -> None:
    """to_dict() contains severity_summary with counts for all severity levels."""
    bundle = {
        "sources": [
            {
                "source_id": "src-gone",
                "exists": False,
            },
            {
                "source_id": "src-hash",
                "current_hash": "new",
                "last_verified_hash": "old",
            },
        ]
    }
    result = _scan(bundle)
    d = result.to_dict()
    assert "severity_summary" in d
    summary = d["severity_summary"]
    assert set(summary.keys()) == set(SEVERITY_LEVELS)
    assert all(isinstance(v, int) for v in summary.values())
    # one blocking (source_deleted) + one warning (hash_changed) → totals check
    assert summary["blocking"] >= 1
    assert summary["warning"] >= 1
    assert summary["info"] >= 0


@pytest.mark.unit
def test_guardrails_present() -> None:
    """All 5 mandatory guardrail strings are present in to_dict() output."""
    result = _scan({})
    d = result.to_dict()
    assert "guardrails" in d
    guardrails_list = d["guardrails"]
    for expected in GUARDRAILS:
        assert expected in guardrails_list, f"Missing guardrail: {expected!r}"


@pytest.mark.unit
def test_guardrails_no_live_go_semantics() -> None:
    """Output guardrails explicitly deny live-go, write, and delete authorization."""
    result = _scan({})
    d = result.to_dict()
    full_text = " ".join(d["guardrails"])
    assert "No Live-Readiness-Go" in full_text
    assert "No Echtgeld-Go" in full_text
    assert "No automatic refresh write" in full_text
    assert "No automatic delete" in full_text
    assert "signal" in full_text


@pytest.mark.unit
def test_result_tool_and_schema_version() -> None:
    """Result has correct tool name and schema version."""
    result = _scan({})
    assert result.tool == TOOL_NAME
    assert result.schema_version == SCHEMA_VERSION
    assert result.status == "ok"


@pytest.mark.unit
def test_result_as_of_propagated() -> None:
    """as_of parameter is propagated to the result."""
    result = scan_stale_knowledge_v1({}, as_of=_AS_OF)
    assert result.as_of == _AS_OF


@pytest.mark.unit
def test_recommended_refresh_deduplicated() -> None:
    """recommended_refresh in result contains no duplicate strings."""
    bundle = {
        "sources": [
            {"source_id": "src-a", "exists": False},
            {"source_id": "src-b", "exists": False},
        ]
    }
    result = _scan(bundle)
    assert len(result.recommended_refresh) == len(set(result.recommended_refresh))


@pytest.mark.unit
def test_invalid_bundle_type_raises() -> None:
    """Passing a non-Mapping bundle raises StaleKnowledgeScanError."""
    with pytest.raises(StaleKnowledgeScanError):
        scan_stale_knowledge_v1(["not", "a", "mapping"])  # type: ignore[arg-type]


@pytest.mark.unit
def test_empty_bundle_returns_ok() -> None:
    """Empty dict bundle returns ok result with 0 findings."""
    result = _scan({})
    assert result.status == "ok"
    assert result.total_count == 0
    assert result.blocking_count == 0
    d = result.to_dict()
    assert d["tool"] == TOOL_NAME
    assert d["schema_version"] == SCHEMA_VERSION


@pytest.mark.unit
def test_finding_to_dict_has_all_fields() -> None:
    """StaleFinding.to_dict() contains all 13 mandatory fields."""
    bundle = {
        "sources": [
            {"source_id": "src-x", "current_hash": "new", "last_verified_hash": "old"}
        ]
    }
    result = _scan(bundle)
    assert len(result.findings) >= 1
    d = result.findings[0].to_dict()
    mandatory_keys = {
        "stale_id", "stale_type", "target_ref", "reason", "severity",
        "confidence", "source_refs", "evidence_refs", "detected_by",
        "detected_at", "recommended_refresh", "blocking", "status",
    }
    assert mandatory_keys <= set(d.keys()), f"Missing keys: {mandatory_keys - set(d.keys())}"


@pytest.mark.unit
def test_detected_by_matches_constant() -> None:
    """detected_by field equals the module-level DETECTED_BY constant."""
    bundle = {
        "sources": [
            {"source_id": "src-check", "current_hash": "abc", "last_verified_hash": "xyz"}
        ]
    }
    result = _scan(bundle)
    for f in result.findings:
        assert f.detected_by == DETECTED_BY


@pytest.mark.unit
def test_blocking_count_matches_findings() -> None:
    """blocking_count in result matches the actual count of blocking findings."""
    bundle = {
        "sources": [
            {"source_id": "src-dead", "exists": False},
            {"source_id": "src-hash", "current_hash": "new", "last_verified_hash": "old"},
        ]
    }
    result = _scan(bundle)
    expected_blocking = sum(1 for f in result.findings if f.blocking)
    assert result.blocking_count == expected_blocking


@pytest.mark.unit
def test_multiple_stale_types_in_one_bundle() -> None:
    """A bundle with multiple stale conditions yields findings across stale types."""
    bundle = {
        "sources": [
            {"source_id": "src-gone", "exists": False},
            {"source_id": "src-changed", "current_hash": "new", "last_verified_hash": "old"},
        ],
        "decisions": [
            {"decision_id": "dec-sup", "superseded_by": "dec-new", "status": "open"}
        ],
        "evidence_records": [
            {"evidence_id": "ev-old", "expires_at": _PAST}
        ],
        "memory_records": [
            {"memory_id": "mem-old", "expires_at": _PAST}
        ],
        "dependency_edges": [
            {
                "edge_id": "edge-gone",
                "from_ref": "a",
                "to_ref": "b",
                "observed": False,
            }
        ],
        "context_packages": [
            {
                "package_id": "pkg-stale",
                "source_snapshot_id": "snap-x",
                "current_snapshot_id": "snap-y",
            }
        ],
        "briefings": [
            {
                "briefing_id": "brief-stale",
                "source_snapshot_id": "snap-a",
                "current_snapshot_id": "snap-b",
            }
        ],
    }
    result = _scan(bundle)
    found_types = {f.stale_type for f in result.findings}
    assert "source_deleted" in found_types
    assert "source_hash_changed" in found_types
    assert "decision_superseded" in found_types
    assert "evidence_expired" in found_types
    assert "memory_ttl_expired" in found_types
    assert "dependency_edge_no_longer_observed" in found_types
    assert "stale_context_package" in found_types
    assert "stale_briefing" in found_types
    assert result.total_count >= 8
