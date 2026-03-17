"""Unit tests for LR-020 Tier-2 pre-run precondition checks.

Covers:
  TC-PRE-01  kill-switch active        → _check_kill_switch returns pass=False
  TC-PRE-02  runtime mode = "live"     → _check_runtime_mode returns pass=False
  TC-PRE-03  endpoint unreachable      → performed=False, pass=False (fail-closed)
  TC-PRE-04  malformed JSON            → performed=False, pass=False (fail-closed)
  TC-PRE-05  both prechecks pass       → _run_prechecks returns both pass=True
  TC-PRE-06  failing precheck in main  → SystemExit(1), abort artifact written,
                                         Redis publish NOT called
  TC-PRE-07  passing prechecks in main → written artifact contains prechecks section

No live stack required — all HTTP and Redis calls are mocked.
"""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from scripts.lr020_tier2_evidence_capture import (
    _ACCEPTED_EXECUTION_MODE,
    _check_kill_switch,
    _check_runtime_mode,
    _run_prechecks,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(payload: dict) -> MagicMock:
    """Return a mock urllib response that yields JSON payload."""
    body = json.dumps(payload).encode()
    mock = MagicMock()
    mock.read.return_value = body
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _risk_status(circuit_breaker: bool) -> dict:
    return {"risk_state": {"circuit_breaker": circuit_breaker}}


def _execution_status(mode: str) -> dict:
    return {"mode": mode}


def _passing_prechecks() -> dict:
    return {
        "kill_switch_precheck": {
            "performed": True,
            "pass": True,
            "source": "http://localhost:8002/status",
            "observed_value": False,
            "detail": "circuit_breaker=false — kill-switch inactive",
        },
        "runtime_mode_precheck": {
            "performed": True,
            "pass": True,
            "source": "http://localhost:8003/status",
            "observed_value": "mock",
            "detail": "mode='mock' — paper trading confirmed",
        },
    }


# ---------------------------------------------------------------------------
# TC-PRE-01: kill-switch active → pass=False
# ---------------------------------------------------------------------------


def test_kill_switch_active_fails_closed():
    resp = _mock_response(_risk_status(circuit_breaker=True))
    with patch("urllib.request.urlopen", return_value=resp):
        result = _check_kill_switch("localhost", 8002, timeout=5.0)

    assert result["performed"] is True
    assert result["pass"] is False
    assert result["observed_value"] is True
    assert "ACTIVE" in result["detail"]


# ---------------------------------------------------------------------------
# TC-PRE-02: runtime mode = "live" → pass=False
# ---------------------------------------------------------------------------


def test_runtime_mode_live_fails_closed():
    resp = _mock_response(_execution_status(mode="live"))
    with patch("urllib.request.urlopen", return_value=resp):
        result = _check_runtime_mode("localhost", 8003, timeout=5.0)

    assert result["performed"] is True
    assert result["pass"] is False
    assert result["observed_value"] == "live"
    assert _ACCEPTED_EXECUTION_MODE in result["detail"]


# ---------------------------------------------------------------------------
# TC-PRE-03: endpoint unreachable → performed=False, pass=False
# ---------------------------------------------------------------------------


def test_endpoint_unreachable_fails_closed_kill_switch():
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = _check_kill_switch("localhost", 8002, timeout=5.0)

    assert result["performed"] is False
    assert result["pass"] is False
    assert result["observed_value"] is None
    assert "unreachable" in result["detail"]


def test_endpoint_unreachable_fails_closed_runtime_mode():
    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        result = _check_runtime_mode("localhost", 8003, timeout=5.0)

    assert result["performed"] is False
    assert result["pass"] is False
    assert result["observed_value"] is None
    assert "unreachable" in result["detail"]


# ---------------------------------------------------------------------------
# TC-PRE-04: malformed JSON response → performed=False, pass=False
# ---------------------------------------------------------------------------


def test_malformed_response_kill_switch_fails_closed():
    resp = _mock_response({"unexpected": "payload"})
    with patch("urllib.request.urlopen", return_value=resp):
        result = _check_kill_switch("localhost", 8002, timeout=5.0)

    assert result["performed"] is False
    assert result["pass"] is False
    assert result["observed_value"] is None
    assert "malformed" in result["detail"]


def test_malformed_response_runtime_mode_fails_closed():
    resp = _mock_response({"unexpected": "payload"})
    with patch("urllib.request.urlopen", return_value=resp):
        result = _check_runtime_mode("localhost", 8003, timeout=5.0)

    assert result["performed"] is False
    assert result["pass"] is False
    assert result["observed_value"] is None
    assert "malformed" in result["detail"]


# ---------------------------------------------------------------------------
# TC-PRE-05: both prechecks pass → _run_prechecks returns both pass=True
# ---------------------------------------------------------------------------


def test_passing_prechecks_both_recorded():
    risk_resp = _mock_response(_risk_status(circuit_breaker=False))
    exec_resp = _mock_response(_execution_status(mode=_ACCEPTED_EXECUTION_MODE))

    call_count = 0

    def _urlopen_side_effect(req, timeout):
        nonlocal call_count
        call_count += 1
        return risk_resp if call_count == 1 else exec_resp

    args = MagicMock()
    args.risk_host = "localhost"
    args.risk_port = 8002
    args.execution_host = "localhost"
    args.execution_port = 8003
    args.timeout = 30.0

    with patch("urllib.request.urlopen", side_effect=_urlopen_side_effect):
        result = _run_prechecks(args)

    ks = result["kill_switch_precheck"]
    rm = result["runtime_mode_precheck"]

    assert ks["performed"] is True
    assert ks["pass"] is True
    assert ks["observed_value"] is False
    assert "http://localhost:8002/status" in ks["source"]

    assert rm["performed"] is True
    assert rm["pass"] is True
    assert rm["observed_value"] == _ACCEPTED_EXECUTION_MODE
    assert "http://localhost:8003/status" in rm["source"]


# ---------------------------------------------------------------------------
# TC-PRE-06: failing precheck in main() → abort before injection
# ---------------------------------------------------------------------------


def test_main_signals_mode_aborts_on_failing_precheck(tmp_path):
    """In signals mode, a failing precheck must:
    - raise SystemExit(1)
    - call _write_artefact with pass=False and abort_reason
    - NOT call redis_client.publish (probe not injected)
    """
    output_file = tmp_path / "evidence.json"

    failing_prechecks = {
        "kill_switch_precheck": {
            "performed": True,
            "pass": False,
            "source": "http://localhost:8002/status",
            "observed_value": True,
            "detail": "circuit_breaker=True — kill-switch ACTIVE; aborting",
        },
        "runtime_mode_precheck": {
            "performed": True,
            "pass": True,
            "source": "http://localhost:8003/status",
            "observed_value": "mock",
            "detail": "mode='mock' — paper trading confirmed",
        },
    }

    mock_redis = MagicMock()

    with (
        patch(
            "sys.argv",
            ["lr020_tier2_evidence_capture.py", "--inject-via", "signals",
             "--output", str(output_file)],
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._resolve_password",
            return_value="test-password",
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._connect",
            return_value=mock_redis,
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._run_prechecks",
            return_value=failing_prechecks,
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 1

    assert output_file.exists()
    artifact = json.loads(output_file.read_text(encoding="utf-8"))
    assert artifact["pass"] is False
    assert artifact["abort_reason"] == "precondition_check_failed"
    assert "prechecks" in artifact
    assert artifact["prechecks"]["kill_switch_precheck"]["pass"] is False

    mock_redis.publish.assert_not_called()


# ---------------------------------------------------------------------------
# TC-PRE-07: passing prechecks in main() → artifact contains prechecks section
# ---------------------------------------------------------------------------


def test_main_signals_mode_records_passing_prechecks_in_artifact(tmp_path):
    """In signals mode with passing prechecks, the written artifact must contain
    the prechecks structure with both subchecks recorded."""
    output_file = tmp_path / "evidence.json"

    mock_order_result = {
        "type": "order_result",
        "order_id": "MOCK_TEST001",
        "status": "FILLED",
        "strategy_id": "lr020-t2",
        "bot_id": "lr020-probe-TESTPROBE",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.001,
        "filled_quantity": 0.001,
        "timestamp": 1000000,
        "price": 50000.0,
        "client_id": "BTCUSDT-0.0",
    }

    mock_redis = MagicMock()
    mock_redis.xlen.side_effect = [100, 101]   # before / after stream.fills
    mock_redis.get.return_value = None          # account_state + market_price = None

    mock_collect = MagicMock(return_value=mock_order_result)

    with (
        patch(
            "sys.argv",
            ["lr020_tier2_evidence_capture.py", "--inject-via", "signals",
             "--output", str(output_file)],
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._resolve_password",
            return_value="test-password",
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._connect",
            return_value=mock_redis,
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._run_prechecks",
            return_value=_passing_prechecks(),
        ),
        patch(
            "scripts.lr020_tier2_evidence_capture._collect_result",
            mock_collect,
        ),
        patch("scripts.lr020_tier2_evidence_capture.time.sleep"),
        pytest.raises(SystemExit) as exc_info,
    ):
        main()

    assert exc_info.value.code == 0

    # Verify run-unique bot_id was used as correlation key
    call_args = mock_collect.call_args[0]
    assert call_args[1] == "bot_id"
    assert call_args[2].startswith("lr020-probe-")

    artifact = json.loads(output_file.read_text(encoding="utf-8"))
    assert "prechecks" in artifact
    assert artifact["prechecks"]["kill_switch_precheck"]["pass"] is True
    assert artifact["prechecks"]["runtime_mode_precheck"]["pass"] is True
    assert artifact["pass"] is True
