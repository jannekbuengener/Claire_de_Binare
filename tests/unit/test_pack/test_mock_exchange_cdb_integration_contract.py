"""MockExchange CDB integration contract tests (#3876).

Parent #3872. Simulation and repo reads only — no live exchange, no cdb_redis replacement.
"""

from __future__ import annotations

import pytest

from tests.unit.test_pack._test_pack_contract_helpers import (
    CANONICAL_REDIS_CONTAINER,
    MOCKEXCHANGE_TEST_MAP,
    MOCK_EXCHANGE_SHIM,
    TEST_PACK_ROOT,
    load_scenario_catalog,
    scan_text_for_valkey_drift,
    simulate_mock_exchange_cancel,
    simulate_mock_exchange_order,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_mock_exchange_shim_exists_as_pack_scenario_server() -> None:
    catalog = load_scenario_catalog()
    mock_scenario = next(s for s in catalog["scenarios"] if s["id"] == "S-MOCK-001")
    assert mock_scenario["server"] == "tools/mock_exchange/mock_exchange.py"
    assert MOCK_EXCHANGE_SHIM.is_file()


def test_mock_exchange_shim_documents_cdb_adapter_boundary() -> None:
    text = MOCK_EXCHANGE_SHIM.read_text(encoding="utf-8")
    assert "cdb_execution" in text
    assert "no real market access" in text.lower() or "without the real exchange" in text
    assert "generate_uuid" in text
    assert "redis" not in text.lower() or "cdb_redis" not in text.lower()


def test_mock_exchange_shim_has_no_valkey_drift() -> None:
    text = MOCK_EXCHANGE_SHIM.read_text(encoding="utf-8")
    assert scan_text_for_valkey_drift(text, label="mock_exchange_shim") == []


def test_mockexchange_test_map_preserves_cdb_redis_canonical_boundary() -> None:
    text = MOCKEXCHANGE_TEST_MAP.read_text(encoding="utf-8")
    assert CANONICAL_REDIS_CONTAINER in text
    assert "must not be staged" in text or "gitignored" in text
    assert "no Live-Go" in text or "No Live-Go" in text


def test_filled_order_when_price_provided() -> None:
    result = simulate_mock_exchange_order(
        symbol="BTCUSDT",
        side="BUY",
        qty=1.0,
        price=100.0,
    )
    assert result.http_status == 200
    assert result.order_status == "FILLED"
    assert result.filled_qty == 1.0


def test_new_order_when_price_missing() -> None:
    result = simulate_mock_exchange_order(
        symbol="BTCUSDT",
        side="SELL",
        qty=2.5,
        price=None,
    )
    assert result.http_status == 200
    assert result.order_status == "NEW"
    assert result.filled_qty is None


def test_rejected_order_on_bad_payload() -> None:
    result = simulate_mock_exchange_order(
        symbol="BTCUSDT",
        side="HOLD",
        qty=1.0,
        price=10.0,
    )
    assert result.http_status == 400
    assert result.order_status is None
    assert result.error == "bad_order_payload"


@pytest.mark.parametrize(
    ("ratio", "expected_status"),
    [
        (0.5, "PARTIAL"),
        (1.0, "FILLED"),
        (0.0, "REJECTED"),
    ],
)
def test_partial_and_terminal_fill_semantics(ratio: float, expected_status: str) -> None:
    result = simulate_mock_exchange_order(
        symbol="ETHUSDT",
        side="BUY",
        qty=10.0,
        price=50.0,
        partial_fill_ratio=ratio,
    )
    assert result.order_status == expected_status


def test_cancel_open_order_transitions_to_canceled() -> None:
    result = simulate_mock_exchange_cancel(order_status="NEW")
    assert result.http_status == 200
    assert result.order_status == "CANCELED"


def test_cancel_terminal_order_is_idempotent() -> None:
    for status in ("FILLED", "CANCELED"):
        result = simulate_mock_exchange_cancel(order_status=status)
        assert result.http_status == 200
        assert result.order_status == status


def test_test_pack_readme_documents_valkey_boundary_without_replacing_cdb_redis() -> None:
    readme = (TEST_PACK_ROOT / "README.md").read_text(encoding="utf-8")
    assert CANONICAL_REDIS_CONTAINER in readme
    assert "must never replace" in readme.lower() or "not CDB-canonical Redis" in readme
