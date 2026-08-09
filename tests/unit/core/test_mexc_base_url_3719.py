"""
Regression tests for MEXC spot base-URL / "testnet" semantics (Issue #3719).

Guards the LR-050 venue-endpoint-semantics finding that ``contract.mexc.com`` is a
deprecated MEXC *Futures* host (discontinued 2026-01-19) and NOT a MEXC spot
testnet/sandbox. These tests fail-close the stale "testnet" routing and lock the
mainnet spot defaults.

Zielaussagen (task #3719):
1. ``contract.mexc.com`` is not a default for a spot "testnet".
2. ``MEXC_TESTNET=true`` / ``testnet=True`` does not create a no-send claim.
3. Mainnet spot REST/WS defaults remain correct.
4. Unsupported spot-testnet is handled fail-closed.

Test-First metadata (knowledge/testing/TEST_FIRST_PROCESSING_CONTRACT.md §4):
    test_id: tc_mexc_base_url_3719
    test_name: mexc_spot_base_url_and_testnet_semantics
    test_type: schutz
    cdb_area: execution
    rule_ref: LR-050-VENUE-ENDPOINT-SEMANTICS-2026-07-03 §3.3/§4/§5
    decision_ref: contract.mexc.com is not a valid MEXC spot testnet or no-send path
    issue_ref: "#3719"
    pr_ref: "[LR-050][VENUE] Fix stale MEXC testnet URL defaults"
    evidence_ref: docs/live-readiness/LR-050-VENUE-ENDPOINT-SEMANTICS-2026-07-03.md
    code_area: core/clients/mexc.py, services/execution/config.py, services/risk/balance_fetcher.py, services/ws/mexc_v3_client.py
    security_relevant: true
    live_relevant: true
    profitability_relevant: false
    surrealdb_export: true
    ci_artifact: false
"""

from __future__ import annotations

import importlib

import pytest

from core.clients.mexc import MexcClient

DEPRECATED_FUTURES_HOST = "contract.mexc.com"
MAINNET_SPOT_REST = "https://api.mexc.com"
MAINNET_SPOT_WS = "wss://wbs-api.mexc.com/ws"


@pytest.mark.unit
def test_mainnet_spot_rest_base_is_default():
    """testnet defaults to False and yields the mainnet spot REST base (#3719 #3)."""
    client = MexcClient(api_key="k", api_secret="s")
    assert client.base_url == MAINNET_SPOT_REST
    assert DEPRECATED_FUTURES_HOST not in client.base_url


@pytest.mark.unit
def test_spot_testnet_is_fail_closed():
    """testnet=True is unsupported and must raise; no spot testnet exists (#3719 #4)."""
    with pytest.raises(ValueError) as excinfo:
        MexcClient(api_key="k", api_secret="s", testnet=True)

    message = str(excinfo.value).lower()
    assert "testnet" in message
    assert "unsupported" in message or "no spot api testnet" in message
    # If the deprecated host is named at all, it must be flagged as deprecated,
    # never offered as a usable testnet base URL.
    if DEPRECATED_FUTURES_HOST in message:
        assert "deprecated" in message


@pytest.mark.unit
def test_testnet_true_is_not_a_no_send_claim():
    """testnet=True fails closed instead of producing a usable "safe" client that
    could be mistaken for a no-send path (#3719 #2).

    No-send for CDB depends on DRY_RUN=true + MOCK_TRADING=true, not on this flag.
    """
    with pytest.raises(ValueError):
        MexcClient(api_key="k", api_secret="s", testnet=True)


@pytest.mark.unit
def test_execution_config_base_url_default_is_mainnet(monkeypatch):
    """services/execution/config.py defaults MEXC_BASE_URL to the mainnet spot host,
    not the deprecated futures host (#3719 #1)."""
    monkeypatch.delenv("MEXC_BASE_URL", raising=False)
    import services.execution.config as exec_config

    exec_config = importlib.reload(exec_config)
    try:
        assert exec_config.MEXC_BASE_URL == MAINNET_SPOT_REST
        assert DEPRECATED_FUTURES_HOST not in exec_config.MEXC_BASE_URL
    finally:
        importlib.reload(exec_config)


@pytest.mark.unit
def test_balance_fetcher_base_url_default_is_mainnet(monkeypatch):
    """services/risk/balance_fetcher.py defaults its spot base to the mainnet host,
    not the deprecated futures host (#3719 #1)."""
    monkeypatch.delenv("MEXC_BASE_URL", raising=False)
    monkeypatch.setenv("MEXC_API_KEY", "unit-test-key")
    monkeypatch.setenv("MEXC_API_SECRET", "unit-test-secret")

    from services.risk.balance_fetcher import RealBalanceFetcher

    fetcher = RealBalanceFetcher()
    assert fetcher.base_url == MAINNET_SPOT_REST
    assert DEPRECATED_FUTURES_HOST not in fetcher.base_url


@pytest.mark.unit
def test_mainnet_spot_ws_url_unchanged():
    """The spot WebSocket base stays the correct mainnet host (#3719 #3).

    Guarded import: skip when optional WS runtime deps are unavailable in this env.
    """
    pytest.importorskip("websockets")
    try:
        from services.ws.mexc_v3_client import WS_URL
    except Exception as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"services.ws.mexc_v3_client not importable here: {exc}")

    assert WS_URL == MAINNET_SPOT_WS
    assert DEPRECATED_FUTURES_HOST not in WS_URL
