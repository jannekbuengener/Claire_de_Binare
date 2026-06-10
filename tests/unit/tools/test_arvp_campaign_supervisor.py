from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import yaml

from tools.arvp_campaign_supervisor import (
    EXIT_BLOCKED_DB_READONLY,
    EXIT_BLOCKED_GOVERNANCE,
    EXIT_BLOCKED_RUNTIME,
    EXIT_CHAIN_FOUND,
    EXIT_INTERRUPTED,
    EXIT_INVALID_USAGE,
    EXIT_OK,
    EXIT_TIMEOUT_NO_CHAIN,
    STATE_BLOCKED_DB_READONLY,
    STATE_BLOCKED_GOVERNANCE,
    STATE_BLOCKED_RUNTIME,
    STATE_CHAIN_FOUND,
    STATE_INTERRUPTED,
    STATE_RUNNING,
    STATE_TIMEOUT_NO_CHAIN,
    detect_chain,
    detect_interruption,
    evaluate_state,
    load_manifest,
    run_all_probes,
    write_jsonl_entry,
    write_status_md,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _minimal_manifest(**overrides) -> dict:
    m = {
        "schema_version": "1.0",
        "campaign_id": "test_campaign_1",
        "parent_issue": 3095,
        "related_issues": [3087, 3102],
        "symbol": "BTCUSDT",
        "strategy_id": "primary_breakout_v1",
        "evidence_class": "natural_paper_evidence",
        "start_utc": "2026-06-10T08:00:00Z",
        "timeout_utc": "2026-06-10T16:00:00Z",
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


# ---------------------------------------------------------------------------
# 1. Manifest loading
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadManifest:
    def test_invalid_path(self):
        with pytest.raises(ValueError, match="not found"):
            load_manifest("/nonexistent/path.yaml")

    def test_missing_required_field(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"schema_version": "1.0"}, f)
            path = f.name
        try:
            with pytest.raises(ValueError, match="missing required fields"):
                load_manifest(path)
        finally:
            os.unlink(path)

    def test_unsupported_schema_version(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({**_minimal_manifest(), "schema_version": "2.0"}, f)
            path = f.name
        try:
            with pytest.raises(ValueError, match="unsupported schema_version"):
                load_manifest(path)
        finally:
            os.unlink(path)

    def test_valid_yaml_manifest(self):
        m = _minimal_manifest()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump(m, f)
            path = f.name
        try:
            result = load_manifest(path)
            assert result["campaign_id"] == "test_campaign_1"
            assert result["schema_version"] == "1.0"
        finally:
            os.unlink(path)

    def test_valid_json_manifest(self):
        m = _minimal_manifest()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(m, f)
            path = f.name
        try:
            result = load_manifest(path)
            assert result["campaign_id"] == "test_campaign_1"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 2. State evaluation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEvaluateState:
    def test_running_before_timeout_no_chain(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles", {"latest_price": 62100}),
            _ok(
                "correlation_ledger",
                {
                    "latest_event": None,
                    "events_since_campaign_start": 0,
                    "events_by_type_status": [],
                },
            ),
            _ok("regime", {"current_regime": "RANGE"}),
        ]
        manifest = _minimal_manifest(timeout_utc="2099-01-01T00:00:00Z")
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_RUNNING

    def test_timeout_no_chain(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles", {"latest_price": 62100}),
            _ok(
                "correlation_ledger",
                {
                    "latest_event": None,
                    "events_since_campaign_start": 0,
                    "events_by_type_status": [],
                },
            ),
            _ok("regime", {"current_regime": "RANGE"}),
        ]
        manifest = _minimal_manifest(timeout_utc="2020-01-01T00:00:00Z")
        state = evaluate_state(probes, manifest, 5)
        assert state == STATE_TIMEOUT_NO_CHAIN

    def test_chain_found(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles", {"latest_price": 62100}),
            _ok(
                "correlation_ledger",
                {
                    "latest_event": {"event_type": "FILL", "status": "filled"},
                    "events_since_campaign_start": 4,
                    "events_by_type_status": [
                        {"event_type": "SIGNAL", "status": "active", "count": 1},
                        {"event_type": "DECISION", "status": "executed", "count": 1},
                        {"event_type": "ORDER", "status": "filled", "count": 1},
                        {"event_type": "FILL", "status": "confirmed", "count": 1},
                    ],
                },
            ),
            _ok("regime", {"current_regime": "TREND"}),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 3)
        assert state == STATE_CHAIN_FOUND

    def test_chain_found_with_order_paper_prefix(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles", {"latest_price": 62100}),
            _ok(
                "correlation_ledger",
                {
                    "events_since_campaign_start": 4,
                    "events_by_type_status": [
                        {"event_type": "SIGNAL", "status": "active", "count": 1},
                        {"event_type": "DECISION", "status": "executed", "count": 1},
                        {"event_type": "ORDER(paper_)", "status": "filled", "count": 1},
                        {"event_type": "FILL", "status": "confirmed", "count": 1},
                    ],
                },
            ),
            _ok("regime"),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_CHAIN_FOUND

    def test_interrupted_host_sleep_events(self):
        probes = [
            _ok(
                "host",
                {
                    "uptime_seconds": 3600,
                    "sleep_wake_indicators": ["Wake history count: 1"],
                },
            ),
            _ok("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles", {"latest_price": 62100}),
            _ok("correlation_ledger", {"events_by_type_status": []}),
            _ok("regime"),
        ]
        manifest = _minimal_manifest(timeout_utc="2099-01-01T00:00:00Z")
        state = evaluate_state(probes, manifest, 2)
        assert state == STATE_INTERRUPTED

    def test_interrupted_low_uptime(self):
        probes = [
            _ok(
                "host",
                {
                    "uptime_seconds": 120,
                    "sleep_wake_indicators": ["none detected"],
                },
            ),
            _ok("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles"),
            _ok("correlation_ledger", {"events_by_type_status": []}),
            _ok("regime"),
        ]
        manifest = _minimal_manifest(timeout_utc="2099-01-01T00:00:00Z")
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_INTERRUPTED

    def test_blocked_runtime_docker(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _blocked("docker"),
            _ok("safety"),
            _ok("db_readonly"),
            _ok("candles"),
            _ok("correlation_ledger", {"events_by_type_status": []}),
            _ok("regime"),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_RUNTIME

    def test_blocked_runtime_safety(self):
        probes = [
            _ok("host"),
            _ok("docker"),
            _blocked("safety"),
            _ok("db_readonly"),
            _ok("candles"),
            _ok("correlation_ledger", {"events_by_type_status": []}),
            _ok("regime"),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_RUNTIME

    def test_blocked_db_readonly(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("docker"),
            _ok("safety"),
            _blocked("db_readonly"),
            _ok("candles"),
            _ok("correlation_ledger", {"events_by_type_status": []}),
            _ok("regime"),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_DB_READONLY

    def test_blocked_governance_via_safety_drift(self):
        probes = [
            _ok(
                "host",
                {"uptime_seconds": 86400, "sleep_wake_indicators": ["none detected"]},
            ),
            _ok("docker"),
            {
                "probe": "safety",
                "status": "blocked",
                "evidence": {
                    "all_flags_match_expected": False,
                    "flags": [
                        {
                            "flag": "MOCK_TRADING",
                            "value": "false",
                            "expected": "true",
                            "match": False,
                        }
                    ],
                },
                "observed_at_utc": "2026-06-10T12:00:00Z",
                "limitations": ["safety flag drift: MOCK_TRADING"],
                "no_mutation": True,
            },
            _ok("db_readonly"),
            _ok("candles"),
            _ok("correlation_ledger", {"events_by_type_status": []}),
            _ok("regime"),
        ]
        manifest = _minimal_manifest()
        state = evaluate_state(probes, manifest, 1)
        assert state == STATE_BLOCKED_RUNTIME


# ---------------------------------------------------------------------------
# 3. Chain detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectChain:
    def test_no_ledger_probe(self):
        assert detect_chain([]) is False

    def test_ledger_not_ok(self):
        probes = [_blocked("correlation_ledger")]
        assert detect_chain(probes) is False

    def test_empty_events(self):
        probes = [_ok("correlation_ledger", {"events_by_type_status": []})]
        assert detect_chain(probes) is False

    def test_partial_chain(self):
        probes = [
            _ok(
                "correlation_ledger",
                {
                    "events_by_type_status": [
                        {"event_type": "SIGNAL", "status": "active", "count": 1}
                    ]
                },
            )
        ]
        assert detect_chain(probes) is False

    def test_full_chain(self):
        probes = [
            _ok(
                "correlation_ledger",
                {
                    "events_by_type_status": [
                        {"event_type": "SIGNAL", "status": "active", "count": 1},
                        {"event_type": "DECISION", "status": "executed", "count": 1},
                        {"event_type": "ORDER(paper_)", "status": "filled", "count": 1},
                        {"event_type": "FILL", "status": "confirmed", "count": 1},
                    ]
                },
            )
        ]
        assert detect_chain(probes) is True


# ---------------------------------------------------------------------------
# 4. Interruption detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectInterruption:
    def test_no_host_probe(self):
        assert detect_interruption([]) is False

    def test_no_sleep_events_high_uptime(self):
        probes = [
            _ok(
                "host",
                {
                    "uptime_seconds": 86400,
                    "sleep_wake_indicators": ["none detected"],
                },
            )
        ]
        assert detect_interruption(probes) is False

    def test_sleep_events_detected(self):
        probes = [
            _ok(
                "host",
                {
                    "uptime_seconds": 86400,
                    "sleep_wake_indicators": ["Wake history count: 1"],
                },
            )
        ]
        assert detect_interruption(probes) is True

    def test_low_uptime_triggers_interruption(self):
        probes = [
            _ok(
                "host",
                {
                    "uptime_seconds": 300,
                    "sleep_wake_indicators": ["none detected"],
                },
            )
        ]
        assert detect_interruption(probes) is True


# ---------------------------------------------------------------------------
# 5. Evidence writers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWriteJsonl:
    def test_append_only_jsonl(self):
        entry = {"cycle": 1, "state": "CAMPAIGN_RUNNING", "no_mutation": True}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            path = f.name
        try:
            write_jsonl_entry(path, entry)
            write_jsonl_entry(
                path, {"cycle": 2, "state": "CHAIN_FOUND", "no_mutation": True}
            )
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["cycle"] == 1
            assert json.loads(lines[1])["cycle"] == 2
        finally:
            os.unlink(path)

    def test_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "subdir", "test.jsonl")
            write_jsonl_entry(path, {"cycle": 1, "no_mutation": True})
            assert os.path.isfile(path)


@pytest.mark.unit
class TestWriteStatusMd:
    def test_writes_markdown(self):
        manifest = _minimal_manifest()
        entry = {
            "observed_at_utc": "2026-06-10T12:00:00Z",
            "cycle": 1,
            "campaign_id": "test_campaign_1",
            "state": "CAMPAIGN_RUNNING",
            "probe_statuses": {"host": "ok", "docker": "ok"},
            "event_count_since_start": 0,
            "chain_detected": False,
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
            assert "CAMPAIGN_RUNNING" in content
            assert "test_campaign_1" in content
            assert "no_mutation: True" in content
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 6. Integration: run_all_probes (mocked)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunAllProbes:
    def test_all_probes_in_result(self, monkeypatch):
        for fn_name in [
            "probe_host",
            "probe_docker",
            "probe_safety",
            "probe_db_readonly",
            "probe_candles",
            "probe_ledger",
            "probe_regime",
        ]:
            monkeypatch.setattr(
                f"tools.arvp_campaign_supervisor.{fn_name}",
                lambda: _ok("mocked"),
            )
        monkeypatch.setattr(
            "tools.arvp_campaign_supervisor.probe_docker",
            lambda targets=None: _ok("docker"),
        )
        monkeypatch.setattr(
            "tools.arvp_campaign_supervisor.probe_ledger",
            lambda campaign_start_utc=None: _ok("correlation_ledger"),
        )

        manifest = _minimal_manifest()
        results = run_all_probes(manifest)
        assert len(results) == 7
        assert all(r["status"] == "ok" for r in results)


# ---------------------------------------------------------------------------
# 7. Exit code mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExitCodes:
    def test_exit_codes_are_distinct(self):
        codes = {
            STATE_RUNNING: EXIT_OK,
            STATE_CHAIN_FOUND: EXIT_CHAIN_FOUND,
            STATE_TIMEOUT_NO_CHAIN: EXIT_TIMEOUT_NO_CHAIN,
            STATE_INTERRUPTED: EXIT_INTERRUPTED,
            STATE_BLOCKED_RUNTIME: EXIT_BLOCKED_RUNTIME,
            STATE_BLOCKED_DB_READONLY: EXIT_BLOCKED_DB_READONLY,
            STATE_BLOCKED_GOVERNANCE: EXIT_BLOCKED_GOVERNANCE,
        }
        vals = list(codes.values())
        assert len(vals) == len(set(vals)), "exit codes must be distinct"
        assert EXIT_INVALID_USAGE == 2
        assert EXIT_OK == 0


# ---------------------------------------------------------------------------
# 8. No secrets in output
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoSecrets:
    def test_no_secret_keywords_in_source(self):
        with open("tools/arvp_campaign_supervisor.py", encoding="utf-8") as f:
            source = f.read()
        for keyword in [
            "Live-Go",
            "Echtgeld-Go",
            "auto-merge",
            "gh issue comment",
            "gh pr merge",
        ]:
            assert keyword not in source, f"forbidden keyword found: {keyword}"
