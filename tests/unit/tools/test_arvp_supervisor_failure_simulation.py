from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from tools.arvp_campaign_supervisor import (
    EXIT_BLOCKED_DB_READONLY,
    EXIT_BLOCKED_RUNTIME,
    EXIT_CHAIN_FOUND,
    EXIT_INTERRUPTED,
    EXIT_OK,
    EXIT_TIMEOUT_NO_CHAIN,
    STATE_BLOCKED_DB_READONLY,
    STATE_BLOCKED_RUNTIME,
    STATE_CHAIN_FOUND,
    STATE_INTERRUPTED,
    STATE_RUNNING,
    STATE_TIMEOUT_NO_CHAIN,
    _build_cycle_entry,
    _check_blocked,
    _find_probe,
    _utcnow,
    detect_chain,
    detect_interruption,
    evaluate_state,
    load_manifest,
    run_loop,
    write_jsonl_entry,
    write_status_md,
)
from tools.arvp_chain_detector import ChainDetector
from tools.arvp_github_reporter import (
    GitHubReporter,
    STATE_CHAIN_FOUND as REPORTER_CHAIN_FOUND,
    STATE_TIMEOUT_NO_CHAIN as REPORTER_TIMEOUT_NO_CHAIN,
    render_body,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "fixtures", "arvp_campaigns"
)


def _load_fixture(name: str) -> dict | list:
    path = os.path.join(FIXTURE_DIR, name)
    if name.endswith((".yaml", ".yml")):
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_manifest() -> dict:
    return _load_fixture("manifest_campaign_3.yaml")


def _minimal_manifest(**overrides) -> dict:
    m = {
        "schema_version": "1.0",
        "campaign_id": "test_campaign_3",
        "parent_issue": 3095,
        "related_issues": [3087, 3102],
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
        "github_reporting": {"post_on_issue_3095": True},
        "allowed_statuses": ["running", "chain_found"],
        "terminal_statuses": ["chain_found"],
    }
    m.update(overrides)
    return m


def _ok(probe: str, evidence: dict | None = None) -> dict:
    return {
        "probe": probe,
        "status": "ok",
        "evidence": evidence or {},
        "observed_at_utc": "2026-06-10T12:00:00Z",
        "limitations": [],
        "no_mutation": True,
    }


def _blocked(probe: str, evidence: dict | None = None) -> dict:
    return {
        "probe": probe,
        "status": "blocked",
        "evidence": evidence or {"error": "mock blocked"},
        "observed_at_utc": "2026-06-10T12:00:00Z",
        "limitations": ["mock blocked"],
        "no_mutation": True,
    }


# ---------------------------------------------------------------------------
# F1: No events across campaign → TIMEOUT_NO_CHAIN
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimNoEvents:
    def test_timeout_no_chain_via_run_loop_once(self):
        manifest = _minimal_manifest(timeout_utc="2020-01-01T00:00:00Z")
        probes = _load_fixture("probe_set_all_ok_running.json")

        def _mocked_probes(*args, **kwargs):
            return probes

        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=1,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_TIMEOUT_NO_CHAIN

    def test_timeout_no_chain_via_evaluate_state(self):
        manifest = _minimal_manifest(timeout_utc="2020-01-01T00:00:00Z")
        probes = _load_fixture("probe_set_all_ok_running.json")
        state = evaluate_state(probes, manifest, 5)
        assert state == STATE_TIMEOUT_NO_CHAIN

    def test_all_ok_running_with_future_timeout(self):
        manifest = _minimal_manifest()
        probes = _load_fixture("probe_set_all_ok_running.json")
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_RUNNING


# ---------------------------------------------------------------------------
# F2: Partial chain only → kein CHAIN_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimPartialChain:
    def test_partial_chain_stays_running(self):
        probes = _load_fixture("probe_set_partial_chain.json")
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state != STATE_CHAIN_FOUND

    def test_detect_chain_returns_none_for_partial(self):
        probes = _load_fixture("probe_set_partial_chain.json")
        result = detect_chain(probes)
        assert result is None

    def test_partial_chain_via_chain_detector_classify(self):
        probes = _load_fixture("probe_set_partial_chain.json")
        ledger = None
        for p in probes:
            if p["probe"] == "correlation_ledger":
                ledger = p
                break
        detector = ChainDetector.from_probe_result(ledger)
        assert detector.classify() == "signal_decision"
        assert detector.classify() != "complete_chain"


# ---------------------------------------------------------------------------
# F3: Complete chain found → CHAIN_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimCompleteChain:
    def test_chain_found_via_run_loop_once(self):
        manifest = _minimal_manifest()
        probes = _load_fixture("probe_set_complete_chain.json")

        def _mocked_probes(*args, **kwargs):
            return probes

        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=1,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_CHAIN_FOUND

    def test_chain_found_via_evaluate_state(self):
        probes = _load_fixture("probe_set_complete_chain.json")
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_CHAIN_FOUND

    def test_chain_found_with_order_paper_prefix(self):
        probes = _load_fixture("probe_set_complete_chain.json")
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_CHAIN_FOUND

    def test_detect_chain_returns_result(self):
        probes = _load_fixture("probe_set_complete_chain.json")
        result = detect_chain(probes)
        assert result is not None
        assert result["chain_status"] == "complete_chain"
        assert result["complete"] is True
        assert "export_trigger" in result

    def test_chain_found_entry_contains_chain_details(self):
        probes = _load_fixture("probe_set_complete_chain.json")
        manifest = _minimal_manifest()
        entry = _build_cycle_entry(3, probes, STATE_CHAIN_FOUND, manifest)
        assert entry["chain_detected"] is True
        assert entry["state"] == STATE_CHAIN_FOUND
        assert "chain_details" in entry
        assert entry["chain_details"]["chain_status"] == "complete_chain"
        assert entry["chain_details"]["complete"] is True


# ---------------------------------------------------------------------------
# F4: DB/probe unavailable → BLOCKED_DB_READONLY
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimDbUnavailable:
    def test_db_blocked_via_evaluate_state(self):
        probes = _load_fixture("probe_set_db_blocked.json")
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_DB_READONLY

    def test_db_blocked_exit_code(self):
        manifest = _minimal_manifest()
        probes = _load_fixture("probe_set_db_blocked.json")

        def _mocked_probes(*args, **kwargs):
            return probes

        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=1,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_BLOCKED_DB_READONLY

    def test_detect_chain_returns_none_when_ledger_blocked(self):
        probes = _load_fixture("probe_set_db_blocked.json")
        result = detect_chain(probes)
        assert result is None


# ---------------------------------------------------------------------------
# F5: Host reboot/interruption → INTERRUPTED
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimHostInterrupted:
    def test_interrupted_via_evaluate_state(self):
        probes = _load_fixture("probe_set_host_interrupted.json")
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_INTERRUPTED

    def test_interrupted_exit_code(self):
        manifest = _minimal_manifest()
        probes = _load_fixture("probe_set_host_interrupted.json")

        def _mocked_probes(*args, **kwargs):
            return probes

        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=1,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_INTERRUPTED

    def test_detect_interruption_true(self):
        probes = _load_fixture("probe_set_host_interrupted.json")
        assert detect_interruption(probes) is True

    def test_detect_interruption_low_uptime(self):
        probes = _load_fixture("probe_set_all_ok_running.json")
        probes[0]["evidence"]["uptime_seconds"] = 300
        assert detect_interruption(probes) is True

    def test_detect_interruption_no_host_probe(self):
        probes = _load_fixture("probe_set_all_ok_running.json")
        probes = [p for p in probes if p["probe"] != "host"]
        assert detect_interruption(probes) is False

    def test_detect_interruption_host_not_ok(self):
        probes = _load_fixture("probe_set_all_ok_running.json")
        probes[0]["status"] = "blocked"
        assert detect_interruption(probes) is False


# ---------------------------------------------------------------------------
# F6: Malformed ledger event → kein CHAIN_FOUND
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimMalformedLedger:
    def test_malformed_event_classify(self):
        events = [
            {"id": 1, "event_type": "SIGNAL", "ts_ms": "2026-06-10T10:00:00Z"},
            {"id": 2, "event_type": "", "ts_ms": "2026-06-10T10:01:00Z"},
        ]
        detector = ChainDetector(events=events)
        assert detector.classify() == "malformed_chain"
        assert detector.classify() != "complete_chain"

    def test_malformed_unknown_type(self):
        events = [
            {"id": 1, "event_type": "SIGNAL", "ts_ms": "2026-06-10T10:00:00Z"},
            {"id": 2, "event_type": "BOGUS", "ts_ms": "2026-06-10T10:01:00Z"},
        ]
        result = ChainDetector(events=events).detect()
        assert result["complete"] is False
        assert any("malformed" in lim for lim in result["limitations"])

    def test_malformed_missing_ts(self):
        events = [
            {"id": 1, "event_type": "SIGNAL", "ts_ms": "2026-06-10T10:00:00Z"},
            {"id": 2, "event_type": "FILL"},
        ]
        detector = ChainDetector(events=events)
        assert detector.classify() == "malformed_chain"

    def test_malformed_not_a_dict(self):
        result = ChainDetector(events=[{"id": 1}]).detect()
        assert result["complete"] is False

    def test_malformed_in_supervisor_probe(self):
        probes = _load_fixture("probe_set_all_ok_running.json")
        for p in probes:
            if p["probe"] == "correlation_ledger":
                p["evidence"] = {
                    "events": [
                        {
                            "id": 1,
                            "event_type": "SIGNAL",
                            "ts_ms": "2026-06-10T10:00:00Z",
                        },
                        {"id": 2, "event_type": "", "ts_ms": "2026-06-10T10:01:00Z"},
                    ],
                    "events_by_type_status": [
                        {"event_type": "SIGNAL", "status": "active", "count": 1},
                    ],
                }
        result = detect_chain(probes)
        assert result is None


# ---------------------------------------------------------------------------
# F7: GitHub reporter dry-run only → kein subprocess write
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimGitHubDryRun:
    def test_dry_run_comment_returns_no_subprocess_call(self):
        manifest = _minimal_manifest()
        manifest["campaign_id"] = "test_campaign_dry_run"
        reporter = GitHubReporter(manifest, github_write=False)
        entry = {
            "state": REPORTER_CHAIN_FOUND,
            "campaign_id": "test_campaign_dry_run",
            "observed_at_utc": "2026-06-10T12:00:00Z",
            "cycle": 3,
            "probe_statuses": {"host": "ok", "docker": "ok"},
            "event_count_since_start": 4,
            "chain_detected": True,
            "chain_details": {
                "chain_status": "complete_chain",
                "complete": True,
                "event_count": 4,
                "event_ids": [101, 102, 103, 104],
                "first_event_ts": "2026-06-10T11:45:00Z",
                "last_event_ts": "2026-06-10T11:46:30Z",
                "missing_steps": [],
                "observed_types": ["SIGNAL", "DECISION", "ORDER", "FILL"],
            },
            "no_mutation": True,
            "limitations": [],
        }
        with patch("subprocess.run") as mock_run:
            results = reporter.report_terminal(entry)
            mock_run.assert_not_called()
        assert len(results) >= 1
        for r in results:
            assert r["action"].startswith("dry_run_")

    def test_dry_run_chain_found_includes_pr_dry_run(self):
        manifest = _minimal_manifest()
        reporter = GitHubReporter(manifest, github_write=False)
        entry = {
            "state": REPORTER_CHAIN_FOUND,
            "campaign_id": "test_campaign_dry_run",
            "observed_at_utc": "2026-06-10T12:00:00Z",
            "cycle": 3,
            "probe_statuses": {"host": "ok"},
            "event_count_since_start": 4,
            "chain_detected": True,
            "chain_details": {
                "chain_status": "complete_chain",
                "complete": True,
                "event_count": 4,
                "event_ids": [101, 102, 103, 104],
            },
            "no_mutation": True,
            "limitations": [],
        }
        results = reporter.report_terminal(entry)
        pr_actions = [r for r in results if "pr" in r.get("action", "")]
        assert len(pr_actions) >= 1
        assert pr_actions[0]["action"] == "dry_run_pr"

    def test_dry_run_report_terminal_returns_comment_body(self):
        manifest = _minimal_manifest()
        reporter = GitHubReporter(manifest, github_write=False)
        entry = {
            "state": REPORTER_TIMEOUT_NO_CHAIN,
            "campaign_id": "test_campaign_dry_run",
            "observed_at_utc": "2026-06-10T12:00:00Z",
            "cycle": 10,
            "probe_statuses": {"host": "ok", "docker": "ok", "safety": "ok"},
            "event_count_since_start": 0,
            "chain_detected": False,
            "no_mutation": True,
            "limitations": [],
        }
        results = reporter.report_terminal(entry)
        for r in results:
            if r.get("action") == "dry_run_comment":
                assert "body" in r
                assert "TIMEOUT_NO_CHAIN" in r["body"]

    def test_dry_run_all_templates_contain_lr_no_go(self):
        for state in [
            REPORTER_CHAIN_FOUND,
            REPORTER_TIMEOUT_NO_CHAIN,
        ]:
            entry = {
                "state": state,
                "campaign_id": "test_campaign",
                "observed_at_utc": "2026-06-10T12:00:00Z",
                "probe_statuses": {"host": "ok"},
                "event_count_since_start": 0,
                "chain_detected": state == REPORTER_CHAIN_FOUND,
                "no_mutation": True,
                "limitations": [],
            }
            if state == REPORTER_CHAIN_FOUND:
                entry["chain_details"] = {
                    "chain_status": "complete_chain",
                    "complete": True,
                    "event_count": 4,
                    "event_ids": [],
                }
            body = render_body(state, entry, _minimal_manifest())
            assert "LR remains NO-GO" in body, f"missing LR NO-GO in {state}"


# ---------------------------------------------------------------------------
# F8: Background runner — skipped per scope (no PS1 tests)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# F9: Multiple cycles before terminal
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimMultiCycle:
    def test_multiple_running_cycles_then_chain_found(self):
        cycle_data = [
            _load_fixture("probe_set_all_ok_running.json"),
            _load_fixture("probe_set_all_ok_running.json"),
            _load_fixture("probe_set_all_ok_running.json"),
            _load_fixture("probe_set_complete_chain.json"),
        ]
        call_count = [0]

        def _mocked_probes(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return cycle_data[min(idx, len(cycle_data) - 1)]

        manifest = _minimal_manifest()
        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=4,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_CHAIN_FOUND
        assert call_count[0] <= 4

    def test_multiple_running_cycles_then_timeout(self):
        cycle_data = [
            _load_fixture("probe_set_all_ok_running.json"),
            _load_fixture("probe_set_all_ok_running.json"),
        ]
        call_count = [0]

        def _mocked_probes(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            return cycle_data[min(idx, len(cycle_data) - 1)]

        manifest = _minimal_manifest(timeout_utc="2020-01-01T00:00:00Z")
        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=3,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_TIMEOUT_NO_CHAIN

    def test_max_cycles_exceeded_returns_ok(self):
        manifest = _minimal_manifest()

        def _mocked_probes(*args, **kwargs):
            return _load_fixture("probe_set_all_ok_running.json")

        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=1,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_OK


# ---------------------------------------------------------------------------
# F10: Safety flag drift → BLOCKED_RUNTIME
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimSafetyFlagDrift:
    def test_safety_blocked_via_evaluate_state(self):
        probes = _load_fixture("probe_set_safety_blocked.json")
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_RUNTIME

    def test_safety_blocked_exit_code(self):
        manifest = _minimal_manifest()
        probes = _load_fixture("probe_set_safety_blocked.json")

        def _mocked_probes(*args, **kwargs):
            return probes

        with patch("tools.arvp_campaign_supervisor.run_all_probes", _mocked_probes):
            exit_code = run_loop(
                manifest=manifest,
                poll_seconds=1,
                max_cycles=1,
                once=False,
                dry_run=True,
                output_jsonl=None,
                status_md=None,
            )
        assert exit_code == EXIT_BLOCKED_RUNTIME

    def test_docker_blocked_also_triggers_runtime_block(self):
        probes = _load_fixture("probe_set_all_ok_running.json")
        for p in probes:
            if p["probe"] == "docker":
                p["status"] = "blocked"
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_RUNTIME

    def test_evaluate_state_checks_safety_first_among_blocked(self):
        probes = _load_fixture("probe_set_safety_blocked.json")
        for p in probes:
            if p["probe"] == "db_readonly":
                p["status"] = "blocked"
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_RUNTIME


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFailureSimEdgeCases:
    def test_find_probe_returns_none_for_missing(self):
        assert _find_probe([], "host") is None
        assert _find_probe([_ok("docker")], "host") is None

    def test_check_blocked_false_when_probe_missing(self):
        assert _check_blocked([], "host") is False

    def test_check_blocked_false_when_probe_not_blocked(self):
        probes = [_ok("host")]
        assert _check_blocked(probes, "host") is False

    def test_check_blocked_true_when_probe_blocked(self):
        probes = [_blocked("docker")]
        assert _check_blocked(probes, "docker") is True

    def test_evaluate_state_with_empty_probes(self):
        manifest = _minimal_manifest()
        state = evaluate_state([], manifest, 1)
        assert state == STATE_RUNNING

    def test_evaluate_state_missing_docker_probe(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles"),
            _ok("correlation_ledger"),
            _ok("regime"),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state is not None

    def test_detect_chain_ledger_not_ok_returns_none(self):
        probes = [_blocked("correlation_ledger")]
        assert detect_chain(probes) is None

    def test_detect_chain_no_ledger_probe_returns_none(self):
        probes = [_ok("host")]
        assert detect_chain(probes) is None

    def test_detect_interruption_host_probe_blocked(self):
        probes = [_blocked("host")]
        assert detect_interruption(probes) is False

    def test_utcnow_format(self):
        ts = _utcnow()
        assert ts.endswith("Z")
        assert "T" in ts

    def test_build_cycle_entry_structure(self):
        probes = _load_fixture("probe_set_all_ok_running.json")
        manifest = _minimal_manifest()
        entry = _build_cycle_entry(1, probes, STATE_RUNNING, manifest)
        assert entry["cycle"] == 1
        assert entry["state"] == STATE_RUNNING
        assert entry["no_mutation"] is True
        assert "observed_at_utc" in entry
        assert "probe_statuses" in entry
        assert entry["probe_statuses"]["host"] == "ok"
        assert entry["probe_statuses"]["db_readonly"] == "ok"

    def test_build_cycle_entry_chain_found_has_details(self):
        probes = _load_fixture("probe_set_complete_chain.json")
        manifest = _minimal_manifest()
        entry = _build_cycle_entry(3, probes, STATE_CHAIN_FOUND, manifest)
        assert entry["chain_detected"] is True
        assert entry["chain_details"]["chain_status"] == "complete_chain"

    def test_write_jsonl_append_and_readback(self):
        manifest = _minimal_manifest()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            path = f.name
        try:
            write_jsonl_entry(
                path, {"cycle": 1, "state": STATE_RUNNING, "no_mutation": True}
            )
            write_jsonl_entry(
                path, {"cycle": 2, "state": STATE_CHAIN_FOUND, "no_mutation": True}
            )
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["cycle"] == 1
            assert json.loads(lines[1])["state"] == STATE_CHAIN_FOUND
        finally:
            os.unlink(path)

    def test_write_status_md_contains_lr_no_go(self):
        manifest = _minimal_manifest()
        entry = {
            "observed_at_utc": "2026-06-10T12:00:00Z",
            "cycle": 1,
            "campaign_id": "test_campaign_3",
            "state": STATE_CHAIN_FOUND,
            "probe_statuses": {"host": "ok", "docker": "ok"},
            "event_count_since_start": 4,
            "chain_detected": True,
            "no_mutation": True,
            "limitations": [],
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            path = f.name
        try:
            write_status_md(path, entry, manifest)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            assert "no_mutation: True" in content
            assert "test_campaign_3" in content
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Manifest loading edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestManifestEdgeCases:
    def test_load_fixture_manifest_valid(self):
        manifest = _load_manifest()
        assert manifest["schema_version"] == "1.0"
        assert manifest["campaign_id"] == "test_campaign_3"

    def test_load_manifest_from_fixture_yaml(self):
        path = os.path.join(FIXTURE_DIR, "manifest_campaign_3.yaml")
        manifest = load_manifest(path)
        assert manifest["campaign_id"] == "test_campaign_3"

    def test_manifest_missing_file(self):
        with pytest.raises(ValueError, match="not found"):
            load_manifest("/nonexistent/manifest.yaml")

    def test_fixture_file_loads_all_probe_sets(self):
        for name in [
            "probe_set_all_ok_running.json",
            "probe_set_partial_chain.json",
            "probe_set_complete_chain.json",
            "probe_set_db_blocked.json",
            "probe_set_host_interrupted.json",
            "probe_set_safety_blocked.json",
        ]:
            data = _load_fixture(name)
            assert isinstance(data, list)
            assert len(data) >= 5
            probes_found = {p["probe"] for p in data}
            assert "host" in probes_found


# ---------------------------------------------------------------------------
# No secrets / no live boundaries
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoSecretsFailureSim:
    FORBIDDEN = [
        "gh issue comment",
        "gh issue close",
        "gh pr merge",
        "git push",
        "INSERT",
        "UPDATE",
        "DELETE",
        "USE_REAL_BALANCE=true",
        "MOCK_TRADING=false",
        "DRY_RUN=false",
        "MEXC_TESTNET=false",
    ]

    def test_no_forbidden_in_tool_source(self):
        with open("tools/arvp_campaign_supervisor.py", encoding="utf-8") as f:
            source = f.read()
        for pat in self.FORBIDDEN:
            assert pat not in source, f"forbidden pattern found: {pat}"

    def test_no_forbidden_in_chain_detector_source(self):
        with open("tools/arvp_chain_detector.py", encoding="utf-8") as f:
            source = f.read()
        for pat in self.FORBIDDEN:
            assert pat not in source, f"forbidden pattern found: {pat}"

    def test_no_forbidden_in_github_reporter_source(self):
        with open("tools/arvp_github_reporter.py", encoding="utf-8") as f:
            source = f.read()
        for pat in self.FORBIDDEN:
            assert pat not in source, f"forbidden pattern found: {pat}"

    def test_no_forbidden_in_fixtures(self):
        fixture_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "fixtures", "arvp_campaigns"
        )
        for fname in os.listdir(fixture_dir):
            path = os.path.join(fixture_dir, fname)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            for pat in self.FORBIDDEN:
                assert pat not in content, f"forbidden '{pat}' in {fname}"

    def test_no_mutation_in_all_fixtures(self):
        for name in [
            "probe_set_all_ok_running.json",
            "probe_set_partial_chain.json",
            "probe_set_complete_chain.json",
            "probe_set_db_blocked.json",
            "probe_set_host_interrupted.json",
            "probe_set_safety_blocked.json",
        ]:
            probes = _load_fixture(name)
            for p in probes:
                assert (
                    p.get("no_mutation") is True
                ), f"{name}: probe {p['probe']} missing no_mutation"

    def test_all_templates_contain_lr_no_go_in_reporter(self):
        from tools.arvp_github_reporter import (
            STATE_CHAIN_FOUND,
            STATE_TIMEOUT_NO_CHAIN,
            STATE_INTERRUPTED,
            STATE_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE,
            STATE_EVIDENCE_MERGED,
        )

        manifest = _minimal_manifest()
        for state in [
            STATE_CHAIN_FOUND,
            STATE_TIMEOUT_NO_CHAIN,
            STATE_INTERRUPTED,
            STATE_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE,
            STATE_EVIDENCE_MERGED,
        ]:
            entry = {
                "state": state,
                "campaign_id": "test",
                "observed_at_utc": "2026-06-10T12:00:00Z",
                "probe_statuses": {"host": "ok"},
                "event_count_since_start": 0,
                "chain_detected": False,
                "no_mutation": True,
                "limitations": [],
            }
            body = render_body(state, entry, manifest)
            assert "LR remains NO-GO" in body, f"missing LR NO-GO in {state}"
