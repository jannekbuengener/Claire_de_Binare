"""Campaign supervisor state-machine contract tests (#3823).

Terminal states, probe-layer boundaries, chain detector integration, and
GitHub reporter read-only semantics. No Docker, Windows supervisor, or live GitHub.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from tools.arvp_campaign_supervisor import (
    EXIT_BLOCKED_DB_READONLY,
    EXIT_BLOCKED_GOVERNANCE,
    EXIT_BLOCKED_RUNTIME,
    EXIT_CHAIN_FOUND,
    EXIT_CODE_MAP,
    EXIT_INTERRUPTED,
    EXIT_TIMEOUT_NO_CHAIN,
    STATE_BLOCKED_DB_READONLY,
    STATE_BLOCKED_GOVERNANCE,
    STATE_BLOCKED_RUNTIME,
    STATE_CHAIN_FOUND,
    STATE_INTERRUPTED,
    STATE_RUNNING,
    STATE_TIMEOUT_NO_CHAIN,
    detect_chain,
    evaluate_state,
    load_manifest,
)
from tools.arvp_chain_detector import ChainDetector
from tools.arvp_github_reporter import GitHubReporter, render_body

pytestmark = [pytest.mark.unit, pytest.mark.contract]

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "arvp_campaigns"

_TERMINAL_STATES = (
    STATE_CHAIN_FOUND,
    STATE_TIMEOUT_NO_CHAIN,
    STATE_INTERRUPTED,
    STATE_BLOCKED_RUNTIME,
    STATE_BLOCKED_DB_READONLY,
    STATE_BLOCKED_GOVERNANCE,
)

_PROBE_CASES = (
    ("probe_set_complete_chain.json", STATE_CHAIN_FOUND, EXIT_CHAIN_FOUND),
    ("probe_set_all_ok_running.json", STATE_RUNNING, None),
    ("probe_set_host_interrupted.json", STATE_INTERRUPTED, EXIT_INTERRUPTED),
    ("probe_set_docker_blocked.json", STATE_BLOCKED_RUNTIME, EXIT_BLOCKED_RUNTIME),
    ("probe_set_db_blocked.json", STATE_BLOCKED_DB_READONLY, EXIT_BLOCKED_DB_READONLY),
    ("probe_set_candles_gap.json", STATE_BLOCKED_DB_READONLY, EXIT_BLOCKED_DB_READONLY),
    ("probe_set_safety_blocked.json", STATE_BLOCKED_RUNTIME, EXIT_BLOCKED_RUNTIME),
)


def _load_fixture(name: str) -> list[dict]:
    path = _FIXTURE_DIR / name
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _minimal_manifest(**overrides: object) -> dict:
    manifest = {
        "schema_version": "1.0",
        "campaign_id": "arvp_p0_contract",
        "parent_issue": 3820,
        "related_issues": [3821, 3822, 3823],
        "symbol": "BTCUSDT",
        "strategy_id": "primary_breakout_v1",
        "evidence_class": "natural_paper_evidence",
        "start_utc": "2026-06-10T08:00:00Z",
        "timeout_utc": "2099-01-01T00:00:00Z",
        "max_duration_hours": 8.0,
        "start_criteria": {"pre_documented": True},
        "safety_flags": {
            "mock_trading": True,
            "use_real_balance": False,
            "dry_run": True,
            "mexc_testnet": True,
        },
        "runtime_targets": ["cdb_execution", "cdb_regime"],
        "db_readonly_targets": ["public.correlation_ledger"],
        "evidence_doc": "docs/evidence/test.md",
        "evidence_log_jsonl": "artifacts/test/evidence.jsonl",
        "github_reporting": {
            "post_on_issue_3820": True,
            "pr_create_on_chain_found": True,
            "issue_close_after_acceptance": False,
        },
        "allowed_statuses": ["running", "chain_found"],
        "terminal_statuses": ["chain_found"],
    }
    manifest.update(overrides)
    return manifest


def test_manifest_campaign_3_declares_all_terminal_states() -> None:
    manifest = yaml.safe_load((_FIXTURE_DIR / "manifest_campaign_3.yaml").read_text())
    terminal = {str(s).upper() for s in manifest["terminal_statuses"]}
    expected = {
        "CHAIN_FOUND",
        "TIMEOUT_NO_CHAIN",
        "INTERRUPTED",
        "BLOCKED_RUNTIME",
        "BLOCKED_DB_READONLY",
        "BLOCKED_GOVERNANCE",
    }
    assert expected.issubset(terminal)


@pytest.mark.parametrize("fixture_name,expected_state,expected_exit", _PROBE_CASES)
def test_evaluate_state_from_fixture_probe_sets(
    fixture_name: str, expected_state: str, expected_exit: int | None
) -> None:
    probes = _load_fixture(fixture_name)
    manifest = _minimal_manifest()
    if expected_state == STATE_TIMEOUT_NO_CHAIN:
        manifest["timeout_utc"] = "2020-01-01T00:00:00Z"
    state = evaluate_state(probes, manifest, cycle_count=1)
    assert state == expected_state
    if expected_exit is not None:
        assert EXIT_CODE_MAP[state] == expected_exit


def test_timeout_no_chain_when_past_deadline_without_chain() -> None:
    probes = _load_fixture("probe_set_all_ok_running.json")
    manifest = _minimal_manifest(timeout_utc="2020-01-01T00:00:00Z")
    assert evaluate_state(probes, manifest, 3) == STATE_TIMEOUT_NO_CHAIN


def test_partial_chain_never_triggers_chain_found() -> None:
    probes = _load_fixture("probe_set_partial_chain.json")
    manifest = _minimal_manifest()
    assert evaluate_state(probes, manifest, 1) == STATE_RUNNING
    assert detect_chain(probes) is None


def test_chain_detector_integration_from_complete_chain_fixture() -> None:
    probes = _load_fixture("probe_set_complete_chain.json")
    chain = detect_chain(probes)
    assert chain is not None
    assert chain["chain_status"] == "complete_chain"
    assert chain["complete"] is True
    ledger = next(p for p in probes if p["probe"] == "correlation_ledger")
    detector = ChainDetector.from_probe_result(ledger)
    assert detector.classify() == "complete_chain"


def test_state_transition_running_to_chain_found_is_deterministic() -> None:
    running = _load_fixture("probe_set_all_ok_running.json")
    complete = _load_fixture("probe_set_complete_chain.json")
    manifest = _minimal_manifest()
    assert evaluate_state(running, manifest, 1) == STATE_RUNNING
    assert evaluate_state(complete, manifest, 2) == STATE_CHAIN_FOUND


@pytest.mark.parametrize("state", _TERMINAL_STATES)
def test_github_reporter_renders_terminal_without_auto_close(state: str) -> None:
    entry = {
        "observed_at_utc": "2026-06-10T12:00:00Z",
        "cycle": 1,
        "campaign_id": "arvp_p0_contract",
        "state": state,
        "probe_statuses": {"host": "ok"},
        "event_count_since_start": 0,
        "chain_detected": state == STATE_CHAIN_FOUND,
        "no_mutation": True,
        "limitations": [],
    }
    body = render_body(state, entry, _minimal_manifest())
    assert "LR remains NO-GO" in body
    assert "closes #" not in body.lower()
    assert "gh issue close" not in body


def test_github_reporter_dry_run_never_calls_subprocess() -> None:
    reporter = GitHubReporter(_minimal_manifest())
    entry = {
        "state": STATE_TIMEOUT_NO_CHAIN,
        "campaign_id": "arvp_p0_contract",
        "observed_at_utc": "2026-06-10T12:00:00Z",
        "probe_statuses": {"host": "ok"},
        "event_count_since_start": 0,
        "chain_detected": False,
        "no_mutation": True,
        "limitations": [],
    }
    with patch("subprocess.run") as mock_run:
        results = reporter.report_terminal(entry)
        mock_run.assert_not_called()
    assert all(r["action"].startswith("dry_run_") for r in results)


def test_blocked_governance_exit_code_is_distinct() -> None:
    assert EXIT_CODE_MAP[STATE_BLOCKED_GOVERNANCE] == EXIT_BLOCKED_GOVERNANCE
    codes = list(EXIT_CODE_MAP.values())
    assert len(codes) == len(set(codes))


def test_all_probe_fixtures_mark_no_mutation() -> None:
    for name in os.listdir(_FIXTURE_DIR):
        if not name.startswith("probe_set_") or not name.endswith(".json"):
            continue
        for probe in _load_fixture(name):
            assert probe.get("no_mutation") is True, f"{name}:{probe.get('probe')}"


def test_load_manifest_from_campaign_fixture() -> None:
    path = str(_FIXTURE_DIR / "manifest_campaign_3.yaml")
    manifest = load_manifest(path)
    assert manifest["campaign_id"] == "test_campaign_3"
    assert manifest["github_reporting"]["issue_close_after_acceptance"] is False
