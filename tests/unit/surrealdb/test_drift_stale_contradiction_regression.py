"""Drift / stale / contradiction regression tests (#3779).

Refs #3771. Fixture-backed regression for known stale documentation patterns,
repo-vs-context contradictions, ledger-vs-live contradictions, and scope drift
firewall signals. Uses in-memory bundles only — no live SurrealDB or GitHub in CI.
"""

from __future__ import annotations

import copy
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.mcp.context_contradiction_tools import (
    TOOL_CDB_CONTEXT_CONTRADICTIONS,
    handle_cdb_context_contradictions,
)
from tools.mcp.scope_drift_tools import (
    TOOL_CDB_CONTEXT_SCOPE_DRIFT,
    handle_cdb_context_scope_drift,
)
from tools.mcp.stale_context_tools import (
    TOOL_CDB_CONTEXT_STALE,
    handle_cdb_context_stale,
)
from tools.surrealdb.contradiction_scan import scan_contradictions_v1
from tools.surrealdb.scope_drift_firewall import GUARDRAILS as SCOPE_GUARDRAILS
from tools.surrealdb.scope_drift_firewall import scan_scope_drift_v1
from tools.surrealdb.stale_knowledge_scan import GUARDRAILS as STALE_GUARDRAILS
from tools.surrealdb.stale_knowledge_scan import scan_stale_knowledge_v1

pytestmark = [pytest.mark.unit, pytest.mark.contract]

FIXTURE_PATH = Path(
    "tests/fixtures/surrealdb/drift_stale_contradiction/regression_bundle_v1.json"
)
CONTRACT_ARTIFACT_PATH = Path(
    "artifacts/surrealdb/context_drift_stale_contradiction_contract.json"
)
_AS_OF = "2026-07-06T12:00:00+00:00"

_FORBIDDEN_RUNTIME_IMPORTS = frozenset(
    {"requests", "httpx", "subprocess", "surrealdb", "gh"}
)
_NON_AUTHORITATIVE_PHRASES = (
    "signal",
    "not authorization",
    "not action",
    "no auto",
    "no live",
    "no write",
)
_AUTO_FIX_ACTION_TOKENS = (
    "auto_fix_enabled",
    "auto_correct_enabled",
    "automatically corrected",
    "automatically updated",
    "auto_delete_memory",
)


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _stale_request(bundle: dict[str, Any], **extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"bundle": bundle, "as_of": _AS_OF}
    params.update(extra)
    return {"tool": TOOL_CDB_CONTEXT_STALE, "parameters": params}


def _scope_request(bundle: dict[str, Any], **extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"bundle": bundle, "as_of": _AS_OF}
    params.update(extra)
    return {"tool": TOOL_CDB_CONTEXT_SCOPE_DRIFT, "parameters": params}


def _contradiction_request(records: dict[str, Any], **extra: Any) -> dict[str, Any]:
    params: dict[str, Any] = {"records": records}
    params.update(extra)
    return {"tool": TOOL_CDB_CONTEXT_CONTRADICTIONS, "parameters": params}


def _assert_guardrails_are_non_authoritative(guardrails: list[str]) -> None:
    joined = " ".join(guardrails).lower()
    assert any(phrase in joined for phrase in _NON_AUTHORITATIVE_PHRASES), (
        "guardrails must frame detection as signal/limitation, not authority"
    )
    assert "authoritative truth" not in joined
    assert "authoritative wahrheit" not in joined


def _assert_no_auto_fix_actions(payload: dict[str, Any]) -> None:
    """Outputs may prohibit auto-fix in guardrails; they must not enable it."""
    findings_blob = json.dumps(
        {
            "findings": payload.get("findings", []),
            "recommended_refresh": payload.get("recommended_refresh", []),
            "recommended_next_reads": payload.get("recommended_next_reads", []),
            "blocking_output": payload.get("blocking_output"),
        }
    ).lower()
    for token in _AUTO_FIX_ACTION_TOKENS:
        assert token not in findings_blob, f"unexpected auto-fix action in output: {token}"
    assert payload.get("auto_fix") is not True


# ---------------------------------------------------------------------------
# stale_doc_known_pattern
# ---------------------------------------------------------------------------


def test_stale_doc_known_pattern_source_hash_changed(regression_fixture: dict[str, Any]) -> None:
    """Known stale documentation pattern: source_hash_changed on docs path."""
    bundle = regression_fixture["stale_bundle"]
    scan = scan_stale_knowledge_v1(bundle, as_of=_AS_OF)
    stale_types = {f.stale_type for f in scan.findings}
    assert "source_hash_changed" in stale_types

    mcp = handle_cdb_context_stale(_stale_request(bundle))
    assert mcp["status"] == "ok"
    mcp_types = {f["stale_type"] for f in mcp["findings"]}
    assert "source_hash_changed" in mcp_types
    doc_markers = {
        text
        for finding in mcp["findings"]
        for text in (
            finding.get("recommended_refresh", ""),
            finding.get("reason", ""),
            finding.get("target_ref", ""),
        )
        if "docs/" in str(text)
    }
    assert doc_markers, "stale doc finding should reference a docs path"


# ---------------------------------------------------------------------------
# repo_vs_context_contradiction
# ---------------------------------------------------------------------------


def test_repo_vs_context_contradiction_flagged(regression_fixture: dict[str, Any]) -> None:
    """Repo file vs context memory record contradiction is flagged."""
    records = regression_fixture["repo_vs_context_records"]
    scan = scan_contradictions_v1(records)
    findings = [f for f in scan.findings if f.contradiction_type == "memory_vs_source"]
    assert findings, "expected memory_vs_source contradiction between repo and context"

    mcp = handle_cdb_context_contradictions(_contradiction_request(records))
    assert mcp["status"] == "ok"
    mcp_types = {f["contradiction_type"] for f in mcp["findings"]}
    assert "memory_vs_source" in mcp_types
    assert mcp["blocking_count"] >= 0


# ---------------------------------------------------------------------------
# github_ledger_vs_repo_contradiction
# ---------------------------------------------------------------------------


def test_github_ledger_vs_repo_contradiction_flagged(
    regression_fixture: dict[str, Any],
) -> None:
    """Ledger closed/green vs live open/red contradiction is flagged as limitation."""
    records = regression_fixture["ledger_vs_live_records"]
    scan = scan_contradictions_v1(records)
    findings = [
        f
        for f in scan.findings
        if f.contradiction_type == "current_status_vs_live_surface"
    ]
    assert findings, "ledger vs live surface contradiction expected"
    assert all(f.blocking for f in findings)

    mcp = handle_cdb_context_contradictions(_contradiction_request(records))
    assert mcp["status"] == "ok"
    assert mcp["blocking_count"] >= 1
    joined_guardrails = " ".join(mcp["guardrails"]).lower()
    assert "github" in joined_guardrails or "no write" in joined_guardrails


# ---------------------------------------------------------------------------
# scope_drift_issue_vs_paths + scope_drift_firewall
# ---------------------------------------------------------------------------


def test_scope_drift_issue_vs_paths_detected(regression_fixture: dict[str, Any]) -> None:
    """Issue scope (tests paths) mismatches changed runtime paths."""
    bundle = regression_fixture["scope_drift_bundle"]
    scan = scan_scope_drift_v1(bundle, as_of=_AS_OF)
    drift_types = {f.drift_type for f in scan.findings}
    assert "path_out_of_scope" in drift_types

    mcp = handle_cdb_context_scope_drift(_scope_request(bundle))
    assert mcp["status"] == "ok"
    mcp_types = {f["drift_type"] for f in mcp["findings"]}
    assert "path_out_of_scope" in mcp_types
    assert "services/risk/service.py" in {
        path
        for finding in mcp["findings"]
        for path in finding.get("affected_artifacts", [])
    }


def test_scope_drift_firewall_emits_stop_without_auto_correction(
    regression_fixture: dict[str, Any],
) -> None:
    """Scope drift firewall signals stop/review but does not auto-correct scope."""
    bundle = regression_fixture["scope_drift_bundle"]
    mcp = handle_cdb_context_scope_drift(_scope_request(bundle))
    assert mcp["status"] == "ok"
    assert mcp["scan_status"] == "blocked_scope_drift"
    assert mcp["summary"]["blocking_count"] >= 1
    assert mcp["blocking_output"] is not None
    anti_actions = mcp["blocking_output"]["anti_actions"]
    assert "no_auto_fix" in anti_actions
    assert "no_auto_write" in anti_actions


# ---------------------------------------------------------------------------
# outputs_include_limitations / no_auto_fix
# ---------------------------------------------------------------------------


def test_outputs_include_limitations_via_guardrails(regression_fixture: dict[str, Any]) -> None:
    """Tool outputs carry guardrails/limitations — not authoritative truth claims."""
    stale = handle_cdb_context_stale(
        _stale_request(regression_fixture["stale_bundle"], include_guardrails=True)
    )
    contradictions = handle_cdb_context_contradictions(
        _contradiction_request(regression_fixture["ledger_vs_live_records"])
    )
    scope = handle_cdb_context_scope_drift(
        _scope_request(regression_fixture["scope_drift_bundle"])
    )

    for label, result, guardrail_key in (
        ("stale", stale, "guardrails"),
        ("contradictions", contradictions, "guardrails"),
        ("scope_drift", scope, "guardrails"),
    ):
        assert result["status"] == "ok", label
        guardrails = result[guardrail_key]
        assert isinstance(guardrails, list) and guardrails
        _assert_guardrails_are_non_authoritative(guardrails)
        _assert_no_auto_fix_actions(result)


def test_no_auto_fix_contract_blocklist_present() -> None:
    """Contract artifact blocks unsafe auto-resolution actions."""
    contract = json.loads(CONTRACT_ARTIFACT_PATH.read_text(encoding="utf-8"))
    blocked = set(contract.get("forbidden_auto_resolution", {}).keys())
    assert "auto_mutate_db" in blocked
    assert "auto_close_issue" in blocked


def test_handlers_do_not_mutate_input_bundles(regression_fixture: dict[str, Any]) -> None:
    """Detection tools are read-only over caller-supplied fixtures."""
    stale_bundle = copy.deepcopy(regression_fixture["stale_bundle"])
    scope_bundle = copy.deepcopy(regression_fixture["scope_drift_bundle"])
    records = copy.deepcopy(regression_fixture["repo_vs_context_records"])

    handle_cdb_context_stale(_stale_request(stale_bundle))
    handle_cdb_context_scope_drift(_scope_request(scope_bundle))
    handle_cdb_context_contradictions(_contradiction_request(records))

    assert stale_bundle == regression_fixture["stale_bundle"]
    assert scope_bundle == regression_fixture["scope_drift_bundle"]
    assert records == regression_fixture["repo_vs_context_records"]


# ---------------------------------------------------------------------------
# standard_ci_no_live_github / standard_ci_no_live_db
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "module_name",
    [
        "tools.mcp.stale_context_tools",
        "tools.mcp.context_contradiction_tools",
        "tools.mcp.scope_drift_tools",
    ],
)
def test_standard_ci_adapter_modules_avoid_live_dependencies(module_name: str) -> None:
    """MCP adapters used in regression must not import live GitHub/DB clients."""
    if module_name not in sys.modules:
        importlib.import_module(module_name)
    mod = sys.modules[module_name]
    for forbidden in _FORBIDDEN_RUNTIME_IMPORTS:
        assert forbidden not in vars(mod), (
            f"forbidden import {forbidden!r} in {module_name}"
        )


def test_regression_fixture_has_no_secret_like_keys(regression_fixture: dict[str, Any]) -> None:
    """Fixture JSON must not embed secret-like field names or live host paths."""
    raw = json.dumps(regression_fixture).lower()
    for token in ("api_key", "api_secret", "password", "token", "bearer "):
        assert token not in raw
    assert "http://" not in raw and "https://" not in raw


# ---------------------------------------------------------------------------
# deterministic_output
# ---------------------------------------------------------------------------


def test_deterministic_output_across_repeated_mcp_calls(
    regression_fixture: dict[str, Any],
) -> None:
    """Same fixture produces stable MCP outputs (IDs, counts, guardrails)."""
    stale_bundle = regression_fixture["stale_bundle"]
    scope_bundle = regression_fixture["scope_drift_bundle"]
    records = regression_fixture["ledger_vs_live_records"]

    stale_a = handle_cdb_context_stale(_stale_request(stale_bundle))
    stale_b = handle_cdb_context_stale(_stale_request(stale_bundle))
    assert [f["stale_id"] for f in stale_a["findings"]] == [
        f["stale_id"] for f in stale_b["findings"]
    ]
    assert stale_a["summary"] == stale_b["summary"]
    assert stale_a.get("guardrails") == stale_b.get("guardrails")

    scope_a = handle_cdb_context_scope_drift(_scope_request(scope_bundle))
    scope_b = handle_cdb_context_scope_drift(_scope_request(scope_bundle))
    assert [f["drift_id"] for f in scope_a["findings"]] == [
        f["drift_id"] for f in scope_b["findings"]
    ]
    assert scope_a["summary"] == scope_b["summary"]
    assert scope_a["guardrails"] == scope_b["guardrails"]

    contra_a = handle_cdb_context_contradictions(_contradiction_request(records))
    contra_b = handle_cdb_context_contradictions(_contradiction_request(records))
    assert [f["contradiction_id"] for f in contra_a["findings"]] == [
        f["contradiction_id"] for f in contra_b["findings"]
    ]
    assert contra_a["blocking_count"] == contra_b["blocking_count"]
    assert contra_a["guardrails"] == contra_b["guardrails"]


def test_domain_guardrails_match_mcp_outputs(regression_fixture: dict[str, Any]) -> None:
    """MCP guardrails include domain-level guardrail strings."""
    stale = handle_cdb_context_stale(
        _stale_request(regression_fixture["stale_bundle"], include_guardrails=True)
    )
    scope = handle_cdb_context_scope_drift(
        _scope_request(regression_fixture["scope_drift_bundle"])
    )
    for guardrail in STALE_GUARDRAILS:
        assert guardrail in stale["guardrails"]
    for guardrail in SCOPE_GUARDRAILS:
        assert guardrail in scope["guardrails"]


# ---------------------------------------------------------------------------
# fixture
# ---------------------------------------------------------------------------


@pytest.fixture(name="regression_fixture")
def fixture_regression_bundle() -> dict[str, Any]:
    data = _load_fixture()
    assert data["meta"]["as_of"] == _AS_OF
    return data
