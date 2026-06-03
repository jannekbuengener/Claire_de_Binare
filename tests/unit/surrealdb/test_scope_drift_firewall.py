"""Unit tests for scope_drift_firewall.py — Scope Drift Firewall Service v1.

Issues:
    #2163 — [SURREALDB][CONTEXT][SCOPE-FIREWALL] Implement scope drift firewall service v1
    Parent: #2162 (Wave-17 anchor)
    Epic: #1976

Scope:
    Unit tests for tools/surrealdb/scope_drift_firewall.py.
    All fixtures are inline (no file loading — keeps slice narrow).
    No DB access. No SurrealDB SDK. No MCP. No networking. No writes.
    No real datetime.now() — validated by test_no_wall_clock_direct.

Coverage:
    - All 9 drift_type rules produce at least one finding with triggering input.
    - All 9 drift_type rules produce no finding with non-triggering input.
    - Blocking findings have human_go_required=True.
    - Deterministic IDs: same input → same drift_id.
    - blocking_count aggregation is correct.
    - Empty bundle → empty ScopeDriftScanResult (no error).
    - Invalid bundle → ScopeDriftFirewallError.
    - All 5 guardrail strings present in result.
    - Output does not grant live-go, write, or delete authorization.
    - to_dict() produces severity_summary with all severity levels.
    - status is 'blocked_scope_drift' when blocking findings present.
    - status is 'ok' when no blocking findings present.
"""

from __future__ import annotations

import hashlib
import inspect
import sys

import pytest

from tools.surrealdb.scope_drift_firewall import (
    DRIFT_TYPES,
    GUARDRAILS,
    REQUIRED_ACTIONS,
    SCHEMA_VERSION,
    SEVERITY_LEVELS,
    STATUS_VALUES,
    TOOL_NAME,
    ScopeDriftFinding,
    ScopeDriftFirewallError,
    ScopeDriftScanResult,
    _make_drift_id,
    scan_scope_drift_v1,
)

# Module reference for inspect.getsource in guardrail tests
_mod = sys.modules["tools.surrealdb.scope_drift_firewall"]

# Fixed reference timestamp used across all tests for determinism
_AS_OF = "2026-05-06T12:00:00+00:00"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _assert_valid_finding(f: ScopeDriftFinding) -> None:
    """Assert all mandatory fields on a ScopeDriftFinding are valid."""
    assert isinstance(f.drift_id, str) and len(f.drift_id) > 0
    assert f.drift_type in DRIFT_TYPES, f"unexpected drift_type: {f.drift_type!r}"
    assert f.severity in SEVERITY_LEVELS, f"unexpected severity: {f.severity!r}"
    assert isinstance(f.allowed_scope, str) and len(f.allowed_scope) > 0
    assert isinstance(f.observed_scope, str) and len(f.observed_scope) > 0
    assert isinstance(f.affected_artifacts, tuple)
    assert f.required_action in REQUIRED_ACTIONS, f"unexpected action: {f.required_action!r}"
    assert isinstance(f.human_go_required, bool)
    assert isinstance(f.stop_conditions, tuple)
    assert isinstance(f.recommended_next_reads, tuple) and len(f.recommended_next_reads) > 0
    assert isinstance(f.detected_by, str) and len(f.detected_by) > 0
    assert isinstance(f.detected_at, str) and len(f.detected_at) > 0
    assert f.status in STATUS_VALUES, f"unexpected status: {f.status!r}"


def _scan(bundle: dict, as_of: str = _AS_OF) -> ScopeDriftScanResult:
    """Convenience wrapper with fixed as_of for deterministic tests."""
    return scan_scope_drift_v1(bundle, as_of=as_of)


# ── Constants / Schema Guards ─────────────────────────────────────────────────


@pytest.mark.unit
def test_drift_types_count() -> None:
    assert len(DRIFT_TYPES) == 9


@pytest.mark.unit
def test_drift_types_all_present() -> None:
    expected = {
        "path_out_of_scope",
        "domain_out_of_scope",
        "issue_out_of_scope",
        "parked_topic_activated",
        "runtime_surface_touched",
        "trading_surface_touched",
        "unexpected_dependency_expansion",
        "unauthorized_write_intent",
        "missing_human_go",
    }
    assert DRIFT_TYPES == expected


@pytest.mark.unit
def test_guardrails_count() -> None:
    assert len(GUARDRAILS) == 5


@pytest.mark.unit
def test_guardrails_all_present() -> None:
    guardrail_set = set(GUARDRAILS)
    assert "Scope Drift Detection is signal, not authorization." in guardrail_set
    assert "No auto-fix. No auto-write." in guardrail_set
    assert "No Live-Readiness-Go." in guardrail_set
    assert "No Echtgeld-Go." in guardrail_set
    assert "Human-GO required for any write after blocking scope drift." in guardrail_set


@pytest.mark.unit
def test_schema_version() -> None:
    assert SCHEMA_VERSION == "scope-drift-firewall/v1"


@pytest.mark.unit
def test_required_actions_set() -> None:
    assert REQUIRED_ACTIONS == frozenset({"stop", "review", "split_scope", "request_go"})


# ── No-wall-clock guardrail ───────────────────────────────────────────────────


@pytest.mark.unit
def test_no_wall_clock_direct() -> None:
    """Service module must not call datetime.now() or datetime.utcnow() directly."""
    source = inspect.getsource(_mod)
    assert "datetime.now()" not in source, "datetime.now() found — use cdb_utcnow"
    assert "datetime.utcnow()" not in source, "datetime.utcnow() found — use cdb_utcnow"


@pytest.mark.unit
def test_no_write_authorized_field() -> None:
    """write_authorized must not appear in the service module (no refresh-plan pattern)."""
    source = inspect.getsource(_mod)
    assert "write_authorized" not in source


# ── Empty bundle ──────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_empty_bundle_returns_empty_result() -> None:
    result = _scan({})
    assert isinstance(result, ScopeDriftScanResult)
    assert result.findings == ()
    assert result.blocking_count == 0
    assert result.status == "ok"


@pytest.mark.unit
def test_empty_bundle_has_guardrails() -> None:
    result = _scan({})
    assert result.guardrails == GUARDRAILS


@pytest.mark.unit
def test_empty_bundle_schema_version() -> None:
    result = _scan({})
    assert result.schema_version == SCHEMA_VERSION
    assert result.tool == TOOL_NAME


# ── Invalid bundle ────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_invalid_bundle_none_raises() -> None:
    with pytest.raises(ScopeDriftFirewallError):
        scan_scope_drift_v1(None)  # type: ignore[arg-type]


@pytest.mark.unit
def test_invalid_bundle_list_raises() -> None:
    with pytest.raises(ScopeDriftFirewallError):
        scan_scope_drift_v1([])  # type: ignore[arg-type]


@pytest.mark.unit
def test_declared_scope_string_label_no_attribute_error() -> None:
    """#2844: plain-string declared_scope must not break rule evaluation."""
    bundle = {
        "declared_scope": "benchmark",
        "touched_artifacts": [],
        "issue_refs": [],
    }
    result = scan_scope_drift_v1(bundle, as_of=_AS_OF)
    assert result.status == "ok"
    assert len(result.findings) == 0


@pytest.mark.unit
def test_declared_scope_invalid_type_raises() -> None:
    with pytest.raises(ScopeDriftFirewallError, match="declared_scope"):
        scan_scope_drift_v1({"declared_scope": 42}, as_of=_AS_OF)


# ── Deterministic IDs ─────────────────────────────────────────────────────────


@pytest.mark.unit
def test_make_drift_id_is_deterministic() -> None:
    id1 = _make_drift_id("path_out_of_scope", "tools/bad/", "tools/bad/file.py")
    id2 = _make_drift_id("path_out_of_scope", "tools/bad/", "tools/bad/file.py")
    assert id1 == id2


@pytest.mark.unit
def test_make_drift_id_differs_for_different_inputs() -> None:
    id1 = _make_drift_id("path_out_of_scope", "tools/bad/", "tools/bad/file.py")
    id2 = _make_drift_id("domain_out_of_scope", "runtime", "services/foo.py")
    assert id1 != id2


@pytest.mark.unit
def test_make_drift_id_is_sha256_prefix() -> None:
    raw = "path_out_of_scope|observed|affected"
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    assert _make_drift_id("path_out_of_scope", "observed", "affected") == expected


# ── blocking_count and status aggregation ────────────────────────────────────


@pytest.mark.unit
def test_blocking_count_correct_for_multiple_violations() -> None:
    bundle = {
        "declared_scope": {
            "target_paths": ["tools/surrealdb/"],
            "target_issue": "2163",
        },
        "touched_artifacts": [
            {"path": "services/risk/risk_service.py", "surface_type": "runtime"},
        ],
        "meta": {"operation_mode": "write"},
    }
    result = _scan(bundle)
    # Expect: path_out_of_scope (blocking) + parked_topic (blocking) +
    #         runtime_surface (blocking) + trading_surface (blocking) +
    #         missing_human_go (blocking) — all blocking
    assert result.blocking_count > 0
    assert result.status == "blocked_scope_drift"
    assert all(f.human_go_required for f in result.findings if f.severity == "blocking")


@pytest.mark.unit
def test_status_ok_when_no_blocking() -> None:
    bundle = {
        "declared_scope": {
            "target_paths": ["tools/surrealdb/"],
            "target_issue": "2163",
        },
        "touched_artifacts": [
            {"path": "tools/surrealdb/scope_drift_firewall.py", "surface_type": "tools"},
        ],
        "issue_refs": [{"issue_id": "2163", "state": "OPEN", "label": "Wave-17"}],
    }
    result = _scan(bundle)
    assert result.blocking_count == 0
    assert result.status == "ok"


# ── to_dict() contract ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_to_dict_has_severity_summary() -> None:
    bundle = {
        "declared_scope": {"target_paths": ["tools/"], "target_issue": "2163"},
        "touched_artifacts": [
            {"path": "services/bad.py", "surface_type": "runtime"},
        ],
    }
    d = _scan(bundle).to_dict()
    assert "severity_summary" in d
    for level in SEVERITY_LEVELS:
        assert level in d["severity_summary"]


@pytest.mark.unit
def test_to_dict_has_no_live_go_field_in_guardrails() -> None:
    result = _scan({})
    d = result.to_dict()
    guardrails_text = " ".join(d["guardrails"])
    assert "Live-Readiness-Go" in guardrails_text
    assert "Echtgeld-Go" in guardrails_text


# ── Rule 1: path_out_of_scope ─────────────────────────────────────────────────


@pytest.mark.unit
def test_path_out_of_scope_triggers() -> None:
    bundle = {
        "declared_scope": {"target_paths": ["tools/surrealdb/"]},
        "touched_artifacts": [
            {"path": "services/risk/risk_service.py", "surface_type": "service"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" in types
    finding = next(f for f in result.findings if f.drift_type == "path_out_of_scope")
    _assert_valid_finding(finding)
    assert finding.severity == "blocking"
    assert finding.human_go_required is True
    assert finding.required_action == "stop"
    assert len(finding.stop_conditions) > 0


@pytest.mark.unit
def test_path_out_of_scope_no_trigger_within_scope() -> None:
    bundle = {
        "declared_scope": {"target_paths": ["tools/surrealdb/"]},
        "touched_artifacts": [
            {"path": "tools/surrealdb/scope_drift_firewall.py", "surface_type": "tools"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" not in types


@pytest.mark.unit
def test_path_out_of_scope_no_trigger_when_no_target_paths() -> None:
    bundle = {
        "declared_scope": {"target_issue": "2163"},
        "touched_artifacts": [
            {"path": "services/risk/anything.py", "surface_type": "service"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" not in types


# ── Rule 2: domain_out_of_scope ───────────────────────────────────────────────


@pytest.mark.unit
def test_domain_out_of_scope_triggers() -> None:
    bundle = {
        "declared_scope": {"allowed_domains": ["tools", "tests"]},
        "touched_artifacts": [
            {"path": "services/signal/signal.py", "surface_type": "service"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "domain_out_of_scope" in types
    finding = next(f for f in result.findings if f.drift_type == "domain_out_of_scope")
    _assert_valid_finding(finding)
    assert finding.severity == "warning"


@pytest.mark.unit
def test_domain_out_of_scope_no_trigger_within_allowed() -> None:
    bundle = {
        "declared_scope": {"allowed_domains": ["tools", "tests", "service"]},
        "touched_artifacts": [
            {"path": "services/signal/signal.py", "surface_type": "service"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "domain_out_of_scope" not in types


@pytest.mark.unit
def test_domain_out_of_scope_no_trigger_when_no_allowed_domains() -> None:
    bundle = {
        "declared_scope": {"target_paths": ["tools/"]},
        "touched_artifacts": [
            {"path": "services/x.py", "surface_type": "runtime"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "domain_out_of_scope" not in types


# ── Rule 3: issue_out_of_scope ────────────────────────────────────────────────


@pytest.mark.unit
def test_issue_out_of_scope_triggers() -> None:
    bundle = {
        "declared_scope": {"target_issue": "2163"},
        "issue_refs": [{"issue_id": "9999", "state": "OPEN", "label": "unrelated"}],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "issue_out_of_scope" in types
    finding = next(f for f in result.findings if f.drift_type == "issue_out_of_scope")
    _assert_valid_finding(finding)
    assert finding.severity == "warning"


@pytest.mark.unit
def test_issue_out_of_scope_no_trigger_for_target_issue() -> None:
    bundle = {
        "declared_scope": {"target_issue": "2163"},
        "issue_refs": [{"issue_id": "2163", "state": "OPEN", "label": "Wave-17"}],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "issue_out_of_scope" not in types


@pytest.mark.unit
def test_issue_out_of_scope_no_trigger_when_no_target_issue() -> None:
    bundle = {
        "declared_scope": {},
        "issue_refs": [{"issue_id": "9999", "state": "OPEN"}],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "issue_out_of_scope" not in types


# ── Rule 4: parked_topic_activated ────────────────────────────────────────────


@pytest.mark.unit
def test_parked_topic_activated_triggers_hardcoded_pattern() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "services/risk/risk_service.py", "surface_type": "service"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "parked_topic_activated" in types
    finding = next(f for f in result.findings if f.drift_type == "parked_topic_activated")
    _assert_valid_finding(finding)
    assert finding.severity == "blocking"
    assert finding.human_go_required is True


@pytest.mark.unit
def test_parked_topic_activated_triggers_bundle_forbidden_surface() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "docs/special-secret/file.md", "surface_type": "docs"}
        ],
        "forbidden_surfaces": [
            {"surface": "docs/special-secret/", "reason": "locked by governance"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "parked_topic_activated" in types


@pytest.mark.unit
def test_parked_topic_activated_no_trigger_for_safe_path() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "tools/surrealdb/scope_drift_firewall.py", "surface_type": "tools"}
        ],
        "forbidden_surfaces": [],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "parked_topic_activated" not in types


# ── Rule 5: runtime_surface_touched ──────────────────────────────────────────


@pytest.mark.unit
def test_runtime_surface_touched_triggers_runtime() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "services/cdb_market/service.py", "surface_type": "runtime"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "runtime_surface_touched" in types
    finding = next(f for f in result.findings if f.drift_type == "runtime_surface_touched")
    _assert_valid_finding(finding)
    assert finding.severity == "blocking"
    assert finding.human_go_required is True
    assert finding.required_action == "stop"


@pytest.mark.unit
def test_runtime_surface_touched_triggers_service_type() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "services/cdb_signal/signal.py", "surface_type": "service"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "runtime_surface_touched" in types


@pytest.mark.unit
def test_runtime_surface_touched_no_trigger_for_tools() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "tools/surrealdb/scope_drift_firewall.py", "surface_type": "tools"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "runtime_surface_touched" not in types


# ── Rule 6: trading_surface_touched ──────────────────────────────────────────


@pytest.mark.unit
def test_trading_surface_touched_triggers_by_surface_type() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "some/path.py", "surface_type": "trading"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "trading_surface_touched" in types
    finding = next(f for f in result.findings if f.drift_type == "trading_surface_touched")
    _assert_valid_finding(finding)
    assert finding.severity == "blocking"
    assert finding.human_go_required is True
    assert "NO-GO" in " ".join(finding.stop_conditions)


@pytest.mark.unit
def test_trading_surface_touched_triggers_by_risk_path() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "services/risk/models.py", "surface_type": "tools"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "trading_surface_touched" in types


@pytest.mark.unit
def test_trading_surface_touched_no_trigger_for_docs() -> None:
    bundle = {
        "touched_artifacts": [
            {"path": "docs/surrealdb/wave17-gates.md", "surface_type": "docs"}
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "trading_surface_touched" not in types


# ── Rule 7: unexpected_dependency_expansion ───────────────────────────────────


@pytest.mark.unit
def test_unexpected_dependency_expansion_triggers_over_max() -> None:
    bundle = {
        "declared_scope": {
            "target_paths": ["tools/surrealdb/"],
            "max_artifact_count": 2,
        },
        "touched_artifacts": [
            {"path": "tools/surrealdb/a.py", "surface_type": "tools"},
            {"path": "tools/surrealdb/b.py", "surface_type": "tools"},
            {"path": "tools/surrealdb/c.py", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unexpected_dependency_expansion" in types
    finding = next(f for f in result.findings if f.drift_type == "unexpected_dependency_expansion")
    _assert_valid_finding(finding)
    assert finding.severity == "warning"
    assert finding.required_action == "split_scope"


@pytest.mark.unit
def test_unexpected_dependency_expansion_no_trigger_within_max() -> None:
    bundle = {
        "declared_scope": {
            "target_paths": ["tools/surrealdb/"],
            "max_artifact_count": 5,
        },
        "touched_artifacts": [
            {"path": "tools/surrealdb/a.py", "surface_type": "tools"},
            {"path": "tools/surrealdb/b.py", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unexpected_dependency_expansion" not in types


@pytest.mark.unit
def test_unexpected_dependency_expansion_no_trigger_without_scope() -> None:
    """No target_paths AND no max_artifact_count → no expansion finding."""
    bundle = {
        "declared_scope": {},
        "touched_artifacts": [
            {"path": f"tools/file{i}.py", "surface_type": "tools"}
            for i in range(50)
        ],
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unexpected_dependency_expansion" not in types


# ── Rule 8: unauthorized_write_intent ─────────────────────────────────────────


@pytest.mark.unit
def test_unauthorized_write_intent_triggers_explicit_flag() -> None:
    bundle = {
        "generated_findings": [
            {
                "type": "plan",
                "content": "Implement the feature",
                "source": "agent",
                "write_intent": True,
                "human_go_token": None,
            }
        ]
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unauthorized_write_intent" in types
    finding = next(f for f in result.findings if f.drift_type == "unauthorized_write_intent")
    _assert_valid_finding(finding)
    assert finding.severity == "blocking"
    assert finding.human_go_required is True
    assert finding.required_action == "stop"


@pytest.mark.unit
def test_unauthorized_write_intent_triggers_keyword_detection() -> None:
    bundle = {
        "generated_findings": [
            {
                "type": "analysis",
                "content": "We should commit the changes and push to main.",
                "source": "agent",
                "write_intent": False,
                "human_go_token": None,
            }
        ]
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unauthorized_write_intent" in types


@pytest.mark.unit
def test_unauthorized_write_intent_no_trigger_with_go_token() -> None:
    bundle = {
        "generated_findings": [
            {
                "type": "plan",
                "content": "Write file to disk",
                "source": "agent",
                "write_intent": True,
                "human_go_token": "GO-2026-05-06-WAVE17",
            }
        ]
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unauthorized_write_intent" not in types


@pytest.mark.unit
def test_unauthorized_write_intent_no_trigger_for_read_only_content() -> None:
    bundle = {
        "generated_findings": [
            {
                "type": "analysis",
                "content": "Reading the file to understand the structure.",
                "source": "agent",
                "write_intent": False,
                "human_go_token": None,
            }
        ]
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "unauthorized_write_intent" not in types


# ── Rule 9: missing_human_go ──────────────────────────────────────────────────


@pytest.mark.unit
def test_missing_human_go_triggers_write_mode() -> None:
    bundle = {
        "meta": {"operation_mode": "write", "human_go_token": None},
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "missing_human_go" in types
    finding = next(f for f in result.findings if f.drift_type == "missing_human_go")
    _assert_valid_finding(finding)
    assert finding.severity == "blocking"
    assert finding.human_go_required is True
    assert finding.required_action == "request_go"


@pytest.mark.unit
def test_missing_human_go_triggers_commit_mode() -> None:
    bundle = {
        "meta": {"operation_mode": "commit", "human_go_token": ""},
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "missing_human_go" in types


@pytest.mark.unit
def test_missing_human_go_no_trigger_with_go_token() -> None:
    bundle = {
        "meta": {"operation_mode": "write", "human_go_token": "GO-2026-05-06"},
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "missing_human_go" not in types


@pytest.mark.unit
def test_missing_human_go_no_trigger_for_read_mode() -> None:
    bundle = {
        "meta": {"operation_mode": "read", "human_go_token": None},
    }
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "missing_human_go" not in types


@pytest.mark.unit
def test_missing_human_go_no_trigger_when_no_meta() -> None:
    bundle: dict = {}
    result = _scan(bundle)
    types = {f.drift_type for f in result.findings}
    assert "missing_human_go" not in types


# ── human_go_required contract ────────────────────────────────────────────────


@pytest.mark.unit
def test_human_go_required_true_for_all_blocking() -> None:
    """All blocking findings must have human_go_required=True."""
    bundle = {
        "meta": {"operation_mode": "write"},
        "touched_artifacts": [
            {"path": "services/risk/risk_service.py", "surface_type": "runtime"},
        ],
    }
    result = _scan(bundle)
    blocking = [f for f in result.findings if f.severity == "blocking"]
    assert len(blocking) > 0
    assert all(f.human_go_required for f in blocking)


@pytest.mark.unit
def test_human_go_required_false_for_warnings() -> None:
    """Warning-severity findings must have human_go_required=False."""
    bundle = {
        "declared_scope": {
            "target_paths": ["tools/surrealdb/"],
            "max_artifact_count": 1,
        },
        "touched_artifacts": [
            {"path": "tools/surrealdb/a.py", "surface_type": "tools"},
            {"path": "tools/surrealdb/b.py", "surface_type": "tools"},
            {"path": "tools/surrealdb/c.py", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle)
    warnings = [f for f in result.findings if f.severity == "warning"]
    assert len(warnings) > 0
    assert all(not f.human_go_required for f in warnings)


# ── recommended_next_reads defaults ──────────────────────────────────────────


@pytest.mark.unit
def test_recommended_next_reads_always_contains_agents_md() -> None:
    bundle = {
        "declared_scope": {"target_paths": ["tools/"]},
        "touched_artifacts": [{"path": "services/bad.py", "surface_type": "tools"}],
    }
    result = _scan(bundle)
    assert len(result.findings) > 0
    for f in result.findings:
        assert "AGENTS.md" in f.recommended_next_reads


# ── P1 hardening: prefixed write modes ───────────────────────────────────────


@pytest.mark.unit
def test_missing_human_go_triggers_write_prefixed_mode() -> None:
    """Prefixed write modes like 'write_code', 'write_docs' must trigger without GO."""
    for mode in ("write_code", "write_docs", "write_authorized", "commit_staged"):
        bundle = {"meta": {"operation_mode": mode, "human_go_token": None}}
        result = _scan(bundle, as_of=_AS_OF)
        types = {f.drift_type for f in result.findings}
        assert "missing_human_go" in types, f"Expected finding for mode={mode!r}"


@pytest.mark.unit
def test_missing_human_go_no_trigger_for_non_write_prefixed_mode() -> None:
    """Non-write prefixed modes like 'readonly', 'analyze', 'inspect' must not trigger."""
    for mode in ("readonly", "analyze", "inspect"):
        bundle = {"meta": {"operation_mode": mode, "human_go_token": None}}
        result = _scan(bundle, as_of=_AS_OF)
        types = {f.drift_type for f in result.findings}
        assert "missing_human_go" not in types, f"Unexpected finding for mode={mode!r}"


# ── P2 hardening: sibling-prefix path boundary ───────────────────────────────


@pytest.mark.unit
def test_path_out_of_scope_sibling_prefix_detected() -> None:
    """Sibling paths sharing only a non-slash prefix must be out of scope."""
    bundle = {
        "declared_scope": {"target_paths": ["tools/surrealdb"]},
        "touched_artifacts": [
            {"path": "tools/surrealdb_extra/file.py", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle, as_of=_AS_OF)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" in types, (
        "tools/surrealdb_extra/ must be out of scope for target 'tools/surrealdb'"
    )


@pytest.mark.unit
def test_path_out_of_scope_exact_file_sibling_detected() -> None:
    """A .bak extension file must not match the original file as scope."""
    bundle = {
        "declared_scope": {"target_paths": ["core/utils/clock.py"]},
        "touched_artifacts": [
            {"path": "core/utils/clock.py.bak", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle, as_of=_AS_OF)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" in types, (
        "core/utils/clock.py.bak must be out of scope for target 'core/utils/clock.py'"
    )


@pytest.mark.unit
def test_path_in_scope_with_no_trailing_slash_target() -> None:
    """A real subpath must still be in scope for a non-slash-terminated target."""
    bundle = {
        "declared_scope": {"target_paths": ["tools/surrealdb"]},
        "touched_artifacts": [
            {"path": "tools/surrealdb/scope_drift_firewall.py", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle, as_of=_AS_OF)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" not in types, (
        "tools/surrealdb/scope_drift_firewall.py must be in scope for target 'tools/surrealdb'"
    )


# ── Thread A hardening: glob pattern target_paths ────────────────────────────


@pytest.mark.unit
def test_path_in_scope_glob_pattern() -> None:
    """Schema documents target_paths as glob patterns; fnmatch must apply."""
    bundle = {
        "declared_scope": {"target_paths": ["tools/surrealdb/*.py"]},
        "touched_artifacts": [
            {"path": "tools/surrealdb/scope_drift_firewall.py", "surface_type": "tools"},
        ],
    }
    result = _scan(bundle, as_of=_AS_OF)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" not in types, (
        "tools/surrealdb/scope_drift_firewall.py must match glob 'tools/surrealdb/*.py'"
    )


@pytest.mark.unit
def test_path_out_of_scope_glob_no_match() -> None:
    """Paths outside the glob scope must be flagged."""
    bundle = {
        "declared_scope": {"target_paths": ["tools/surrealdb/*.py"]},
        "touched_artifacts": [
            {"path": "services/risk/other.py", "surface_type": "service"},
        ],
    }
    result = _scan(bundle, as_of=_AS_OF)
    types = {f.drift_type for f in result.findings}
    assert "path_out_of_scope" in types, (
        "services/risk/other.py must not match glob 'tools/surrealdb/*.py'"
    )


# ── Thread B hardening: parked surface sibling-prefix boundary ───────────────


@pytest.mark.unit
def test_parked_topic_activated_sibling_prefix_not_flagged() -> None:
    """Sibling paths that only share a prefix must NOT trigger parked_topic_activated."""
    bundle = {
        "forbidden_surfaces": [
            {"surface": "docs/runbooks", "reason": "production runbooks"}
        ],
        "touched_artifacts": [
            {"path": "docs/runbooks_old/a.md", "surface_type": "docs"},
        ],
    }
    result = _scan(bundle, as_of=_AS_OF)
    types = {f.drift_type for f in result.findings}
    assert "parked_topic_activated" not in types, (
        "docs/runbooks_old/a.md must NOT be flagged for forbidden surface 'docs/runbooks'"
    )
