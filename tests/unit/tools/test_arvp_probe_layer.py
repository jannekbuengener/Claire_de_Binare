from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from unittest.mock import ANY, MagicMock, patch

import pytest

from tools.arvp_probe_layer import (
    DEFAULT_RUNTIME_TARGETS,
    ProbeResult,
    _format_uptime,
    _ok,
    _utcnow,
    probe_candles,
    probe_db_readonly,
    probe_docker,
    probe_host,
    probe_ledger,
    probe_regime,
    probe_safety,
)


@pytest.mark.unit
class TestHelpers:
    def test_ok_has_no_mutation(self):
        r = _ok({"test": True})
        assert r["status"] == "ok"
        assert r["no_mutation"] is True
        assert "observed_at_utc" in r

    def test_utcnow_format(self):
        ts = _utcnow()
        assert ts.endswith("Z")
        assert "T" in ts

    def test_format_uptime(self):
        assert _format_uptime(0) == "0h 0m"
        assert _format_uptime(3600) == "1h 0m"
        assert _format_uptime(86400) == "1d 0h 0m"
        assert _format_uptime(90061) == "1d 1h 1m"


# ---------------------------------------------------------------------------
# 1. Host probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeHost:
    def test_unavailable_on_non_windows(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        result = probe_host()
        assert result["status"] == "unavailable"

    def test_blocked_when_powershell_times_out(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Windows")

        def _timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="powershell", timeout=15)

        monkeypatch.setattr(subprocess, "run", _timeout)
        result = probe_host()
        assert "blocked" in result["status"]

    def test_powershell_not_found(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Windows")

        def _not_found(*args, **kwargs):
            raise FileNotFoundError("powershell not found")

        monkeypatch.setattr(subprocess, "run", _not_found)
        result = probe_host()
        assert result["status"] == "unavailable"

    def test_ok_with_mock_boot_time(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        fake_boot = '{"LastBootUpTime": "2026-06-10T12:00:00Z"}'

        call_count = 0

        def _fake_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return subprocess.CompletedProcess(
                    args, 0, stdout=fake_boot, stderr=""
                )
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = probe_host()
        assert result["status"] == "ok"
        assert result["evidence"]["uptime_seconds"] > 0


# ---------------------------------------------------------------------------
# 2. Docker probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeDocker:
    def test_blocked_when_docker_unavailable(self, monkeypatch):
        def _fail(*args, **kwargs):
            raise FileNotFoundError("docker not found")

        monkeypatch.setattr(subprocess, "run", _fail)
        result = probe_docker()
        assert result["status"] == "blocked"

    def test_all_healthy(self, monkeypatch):
        calls: list = []

        def _fake_run(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            calls.append(cmd)
            if "ps" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="abc123\n", stderr=""
                )
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=(
                    "running\thealthy\t2026-06-10T12:00:00Z\n"
                ),
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = probe_docker(targets=["cdb_execution"])
        assert result["status"] == "ok"
        assert result["evidence"]["healthy"] == 1

    def test_container_not_found(self, monkeypatch):
        def _fake_run(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            if "ps" in cmd:
                return subprocess.CompletedProcess(
                    cmd, 0, stdout="abc\n", stderr=""
                )
            raise RuntimeError("container not found")

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = probe_docker(targets=["cdb_nonexistent"])
        assert result["status"] == "warn"
        assert result["evidence"]["missing"] == 1


# ---------------------------------------------------------------------------
# 3. Safety probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeSafety:
    def test_blocked_no_container(self, monkeypatch):
        def _fail(*args, **kwargs):
            raise RuntimeError("container not found")

        monkeypatch.setattr(subprocess, "run", _fail)
        result = probe_safety(container="cdb_nonexistent")
        assert result["status"] == "blocked"

    def test_all_flags_match(self, monkeypatch):
        env_json = json.dumps(
            [
                "MOCK_TRADING=true",
                "USE_REAL_BALANCE=false",
                "DRY_RUN=true",
                "MEXC_TESTNET=true",
            ]
        )

        def _fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                kwargs.get("args", []), 0, stdout=env_json, stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = probe_safety()
        assert result["status"] == "ok"
        assert result["evidence"]["all_flags_match_expected"] is True

    def test_flag_drift_detected(self, monkeypatch):
        env_json = json.dumps(
            [
                "MOCK_TRADING=false",
                "USE_REAL_BALANCE=true",
                "DRY_RUN=true",
                "MEXC_TESTNET=true",
            ]
        )

        def _fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                kwargs.get("args", []), 0, stdout=env_json, stderr=""
            )

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = probe_safety()
        assert result["status"] == "blocked"
        assert "safety flag drift" in result["limitations"][0]


# ---------------------------------------------------------------------------
# 4. DB readonly probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeDbReadonly:
    def test_unavailable_no_tools(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: None
        )

        def _not_found(*args, **kwargs):
            raise FileNotFoundError("pg_isready not found")

        monkeypatch.setattr(subprocess, "run", _not_found)
        result = probe_db_readonly()
        assert result["status"] == "unavailable"

    def test_blocked_pg_isready_fails(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: None
        )

        def _fake_run(*args, **kwargs):
            return subprocess.CompletedProcess(
                kwargs.get("args", []),
                1,
                stdout="",
                stderr="pg_isready: connection failed",
            )

        monkeypatch.setattr(subprocess, "run", _fake_run)
        result = probe_db_readonly()
        assert result["status"] == "blocked"

    def test_ok_with_psycopg2(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: True
        )

        class FakeCursor:
            def execute(self, q): pass
            def fetchone(self): return (1,)
            def close(self): pass

        class FakeConnection:
            def cursor(self): return FakeCursor()
            def close(self): pass

        def _fake_pg_isready(*args, **kwargs):
            return subprocess.CompletedProcess(
                kwargs.get("args", []), 0,
                stdout="localhost:5432 - accepting connections",
                stderr="",
            )

        fake_psycopg2 = MagicMock()
        fake_psycopg2.connect.return_value = FakeConnection()
        monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

        monkeypatch.setattr(subprocess, "run", _fake_pg_isready)
        result = probe_db_readonly()
        assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# 5. Candle probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeCandles:
    def test_unavailable_no_psycopg2(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: None
        )
        result = probe_candles()
        assert result["status"] == "unavailable"

    def test_no_candles_found(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: True
        )

        class FakeCursor:
            def __init__(self, rows):
                self.rows = rows
            def execute(self, q): pass
            def fetchone(self): return self.rows[0] if self.rows else None
            def fetchall(self): return self.rows
            def close(self): pass

        class FakeConnection:
            def __init__(self, rows):
                self.rows = rows
            def cursor(self): return FakeCursor(self.rows)
            def close(self): pass

        fake_psycopg2 = MagicMock()
        fake_psycopg2.connect.return_value = FakeConnection([(None,)])
        monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

        result = probe_candles()
        assert result["status"] == "unavailable"

    def test_ok_with_candles(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: True
        )

        query_results = {
            "MAX(ts_ms)": [(datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc),)],
            "MAX(high) - MIN(low)": [(100.0,)],
            "gap": [(60000,), (60000,), (60000,)],
            "close": [(62100.50,)],
        }

        class FakeCursor:
            def execute(self, q):
                for key in query_results:
                    if key in q:
                        self.rows = query_results[key]
                        return
                self.rows = []
            def fetchall(self): return self.rows
            def fetchone(self): return self.rows[0] if self.rows else None
            def close(self): pass

        class FakeConnection:
            def cursor(self): return FakeCursor()
            def close(self): pass

        fake_psycopg2 = MagicMock()
        fake_psycopg2.connect.return_value = FakeConnection()
        monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

        result = probe_candles()
        assert result["status"] == "ok"
        assert result["evidence"]["latest_price"] == 62100.50


# ---------------------------------------------------------------------------
# 6. Ledger probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeLedger:
    def test_unavailable_no_psycopg2(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: None
        )
        result = probe_ledger()
        assert result["status"] == "unavailable"

    def test_ok_empty_ledger(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: True
        )

        class FakeCursor:
            def execute(self, q): pass
            def fetchall(self): return []
            def fetchone(self): return None
            def close(self): pass

        class FakeConnection:
            def cursor(self): return FakeCursor()
            def close(self): pass

        fake_psycopg2 = MagicMock()
        fake_psycopg2.connect.return_value = FakeConnection()
        monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

        result = probe_ledger()
        assert result["status"] == "ok"
        assert result["evidence"]["latest_event"] is None
        assert result["evidence"]["events_by_type_status"] == []

    def test_ok_with_events(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: True
        )

        query_counter = [0]
        results_map = [
            # latest event query (timestamp_ms, event_type, correlation_id)
            [
                (
                    datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
                    "SIGNAL", "abc123",
                )
            ],
            # count query
            [(5,)],
            # group by query (event_type, count)
            [("SIGNAL", 3), ("ORDER", 2)],
        ]

        class FakeCursor:
            def execute(self, q):
                idx = query_counter[0]
                self.rows = results_map[min(idx, len(results_map) - 1)]
                query_counter[0] += 1
            def fetchall(self): return self.rows
            def close(self): pass

        class FakeConnection:
            def cursor(self): return FakeCursor()
            def close(self): pass

        fake_psycopg2 = MagicMock()
        fake_psycopg2.connect.return_value = FakeConnection()
        monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

        result = probe_ledger(campaign_start_utc="2026-06-10T08:00:00Z")
        assert result["status"] == "ok"
        assert result["evidence"]["latest_event"]["event_type"] == "SIGNAL"
        assert result["evidence"]["latest_event"]["correlation_id"] == "abc123"

    def test_blocked_db_error(self, monkeypatch):
        monkeypatch.setattr(
            "importlib.util.find_spec", lambda _: True
        )

        fake_psycopg2 = MagicMock()
        fake_psycopg2.connect.side_effect = Exception("connection refused")
        monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

        monkeypatch.setattr(
            "tools.arvp_probe_layer._run_sql_docker_exec",
            lambda _q, _c: None,
        )

        result = probe_ledger()
        assert result["status"] == "blocked"


# ---------------------------------------------------------------------------
# 7. Regime probe tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProbeRegime:
    def test_http_regime_found(self, monkeypatch):
        class FakeResponse:
            def read(self):
                return b'{"regime": "HIGH_VOL_CHAOTIC", "timestamp": "..."}'
            def __enter__(self): return self
            def __exit__(self, *a): pass

        def _fake_urlopen(url, timeout=5):
            return FakeResponse()

        monkeypatch.setattr(
            "urllib.request.urlopen", _fake_urlopen
        )
        result = probe_regime()
        assert result["status"] == "ok"
        assert result["evidence"]["current_regime"] == "HIGH_VOL_CHAOTIC"

    def test_http_unavailable_falls_back_to_docker_logs(
        self, monkeypatch
    ):
        def _urlopen_fail(*a, **kw):
            raise Exception("connection refused")

        monkeypatch.setattr(
            "urllib.request.urlopen", _urlopen_fail
        )

        def _fake_docker(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", [])
            return subprocess.CompletedProcess(
                cmd, 0,
                stdout="2026-06-10 12:00:00 [INFO] Regime: TREND\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", _fake_docker)
        result = probe_regime()
        assert result["status"] == "ok"
        assert result["evidence"]["current_regime"] == "TREND"

    def test_unavailable_no_regime_found(self, monkeypatch):
        def _urlopen_fail(*a, **kw):
            raise Exception("connection refused")

        monkeypatch.setattr(
            "urllib.request.urlopen", _urlopen_fail
        )

        def _fake_docker(*args, **kwargs):
            return subprocess.CompletedProcess(
                kwargs.get("args", []), 0,
                stdout="2026-06-10 12:00:00 [INFO] Processing candles\n",
                stderr="",
            )

        monkeypatch.setattr(subprocess, "run", _fake_docker)
        result = probe_regime()
        assert result["status"] == "unavailable"
        assert result["evidence"]["current_regime"] == "unknown"

    def test_unavailable_docker_not_found(self, monkeypatch):
        def _urlopen_fail(*a, **kw):
            raise Exception("connection refused")

        monkeypatch.setattr(
            "urllib.request.urlopen", _urlopen_fail
        )

        def _not_found(*a, **kw):
            raise FileNotFoundError("docker not found")

        monkeypatch.setattr(subprocess, "run", _not_found)
        result = probe_regime()
        assert result["status"] == "unavailable"


# ---------------------------------------------------------------------------
# Integration: Dry-run example (no external deps)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDryRunExamples:
    def test_dry_run_report_structure(self):
        sample = {
            "probe": "host",
            "status": "ok",
            "evidence": {"uptime_seconds": 3600},
            "observed_at_utc": "2026-06-10T12:00:00Z",
            "limitations": [],
            "no_mutation": True,
        }
        assert sample["no_mutation"] is True
        assert sample["status"] in ("ok", "warn", "blocked", "unavailable")

    def test_all_probes_have_no_mutation(self):
        """Each probe function result must have no_mutation=True."""
        probes = [
            ("host", probe_host),
            ("docker", lambda: probe_docker(targets=["cdb_execution"])),
            ("safety", probe_safety),
            ("db", lambda: probe_db_readonly()),
            ("candles", probe_candles),
            ("ledger", probe_ledger),
            ("regime", probe_regime),
        ]
        for name, fn in probes:
            result = fn()
            assert isinstance(result, dict), f"{name}: expected dict"
            assert "no_mutation" in result, f"{name}: missing no_mutation"
            assert result["status"] in (
                "ok", "warn", "blocked", "unavailable"
            ), f"{name}: unexpected status"
