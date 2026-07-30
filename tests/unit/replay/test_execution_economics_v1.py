"""Unit tests for execution economics gross-to-net contract v1 (#4150)."""

from __future__ import annotations

import json
import math
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from core.replay.execution_economics_v1 import (
    ALLOWED_SCENARIO_OVERRIDE_KEYS,
    CONTRACT_VERSION,
    LEGACY_SCENARIO_OVERRIDE_KEYS,
    SCENARIO_OVERRIDE_KEY_TO_SIMULATOR,
    ExecutionEconomicsError,
    bps_to_rate,
    build_assumptions_snapshot,
    compare_economics_components,
    economics_evidence_fingerprint,
    fill_price_embedded_gross_pnl,
    partial_fill_impact_quote,
    rate_to_bps,
    reconcile_gross_to_net,
    reference_gross_pnl,
    resolve_scenario_overrides,
    slippage_cost_from_bps,
    validate_bps,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = (
    REPO_ROOT / "docs" / "contracts" / "execution_economics_gross_to_net.v1.schema.json"
)

pytestmark = [pytest.mark.unit]


class TestScenarioMapping:
    def test_usable_depth_fraction_maps_to_fill_threshold(self) -> None:
        resolved = resolve_scenario_overrides({"usable_depth_fraction": 0.7})
        assert resolved["simulator_config"]["FILL_THRESHOLD"] == 0.7

    def test_depth_impact_factor_maps_to_depth_impact(self) -> None:
        resolved = resolve_scenario_overrides({"depth_impact_factor": 0.3})
        assert resolved["simulator_config"]["DEPTH_IMPACT_FACTOR"] == 0.3

    def test_legacy_fill_rate_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="usable_depth_fraction"):
            resolve_scenario_overrides({"fill_rate": 0.7})

    def test_legacy_fill_depth_factor_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="depth_impact_factor"):
            resolve_scenario_overrides({"fill_depth_factor": 0.3})

    def test_unknown_key_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="unknown keys"):
            resolve_scenario_overrides({"VOLATILITY_SLIPPAGE_FACTOR": 1.0})

    def test_override_order_deterministic(self) -> None:
        a = resolve_scenario_overrides(
            {
                "execution_slippage_bps": 30,
                "usable_depth_fraction": 0.7,
                "execution_posture": "pessimistic",
            }
        )
        b = resolve_scenario_overrides(
            {
                "usable_depth_fraction": 0.7,
                "execution_posture": "pessimistic",
                "execution_slippage_bps": 30,
            }
        )
        assert a == b

    def test_mapping_table_matches_ssot(self) -> None:
        assert SCENARIO_OVERRIDE_KEY_TO_SIMULATOR["usable_depth_fraction"] == (
            "FILL_THRESHOLD"
        )
        assert SCENARIO_OVERRIDE_KEY_TO_SIMULATOR["depth_impact_factor"] == (
            "DEPTH_IMPACT_FACTOR"
        )
        assert "fill_rate" not in ALLOWED_SCENARIO_OVERRIDE_KEYS
        assert LEGACY_SCENARIO_OVERRIDE_KEYS["fill_rate"] == "usable_depth_fraction"


class TestGrossToNet:
    def test_no_costs_net_equals_gross(self) -> None:
        result = reconcile_gross_to_net(gross_pnl="100", taker_fee_cost="0")
        assert result.net_pnl == Decimal("100.00000000")
        assert result.reconciled is True

    def test_fees_only(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100", maker_fee_cost="1", taker_fee_cost="2"
        )
        assert result.total_fee_cost.amount == Decimal("3.00000000")
        assert result.net_pnl == Decimal("97.00000000")

    def test_slippage_only(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100", taker_fee_cost="0", slippage_cost="5"
        )
        assert result.net_pnl == Decimal("95.00000000")

    def test_fees_spread_slippage_combined(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="2",
            spread_cost="1",
            spread_status="active",
            slippage_cost="3",
        )
        assert result.net_pnl == Decimal("94.00000000")

    def test_partial_fill_impact(self) -> None:
        impact = partial_fill_impact_quote(
            requested_size="1.0",
            filled_size="0.5",
            reference_pnl_per_unit="10",
        )
        assert impact == Decimal("5.00000000")
        # gross is on filled size only; forgone unfilled PnL is an additional cost.
        result = reconcile_gross_to_net(
            gross_pnl="5",
            taker_fee_cost="0.1",
            partial_fill_impact=impact,
        )
        assert result.net_pnl == Decimal("-0.10000000")

    def test_reject_not_applicable(self) -> None:
        result = reconcile_gross_to_net(gross_pnl="10", taker_fee_cost="1")
        assert result.reject_impact.status == "not_applicable"
        assert result.reject_impact.amount is None
        assert result.net_pnl == Decimal("9.00000000")

    def test_latency_not_applicable_by_default(self) -> None:
        result = reconcile_gross_to_net(gross_pnl="10", taker_fee_cost="0")
        assert result.latency_or_delay_impact.status == "not_applicable"

    def test_latency_active_when_measured(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="10",
            taker_fee_cost="0",
            latency_or_delay_impact="1.5",
            latency_status="active",
        )
        assert result.net_pnl == Decimal("8.50000000")

    def test_no_double_count_embedded_slippage(self) -> None:
        # Reference gross 100; fill-embedded gross already reduced by 5 slippage.
        embedded = fill_price_embedded_gross_pnl(
            side="buy",
            filled_size="1",
            entry_fill_price="100",
            exit_fill_price="195",
        )
        # If someone mistakenly treats embedded as gross and also subtracts slippage:
        wrong = reconcile_gross_to_net(
            gross_pnl=embedded, taker_fee_cost="0", slippage_cost="5"
        )
        right = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="0",
            slippage_cost="5",
            fill_price_embedded_gross=embedded,
        )
        assert right.net_pnl == Decimal("95.00000000")
        assert wrong.net_pnl != right.net_pnl

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="must be >= 0"):
            reconcile_gross_to_net(gross_pnl="10", taker_fee_cost="-1")

    def test_spread_not_applicable_not_silently_zero_measured(self) -> None:
        result = reconcile_gross_to_net(gross_pnl="10", taker_fee_cost="0")
        assert result.spread_cost.status == "not_applicable"
        assert result.spread_cost.amount is None

    def test_funding_inactive(self) -> None:
        result = reconcile_gross_to_net(gross_pnl="10", taker_fee_cost="0")
        assert result.funding_cost_when_active.status == "inactive_not_wired"

    def test_reference_gross_uses_filled_size(self) -> None:
        gross = reference_gross_pnl(
            side="buy",
            filled_size="0.5",
            entry_reference_price="100",
            exit_reference_price="110",
        )
        assert gross == Decimal("5.00000000")


class TestRatesAndBps:
    def test_zero_bps(self) -> None:
        assert validate_bps(0) == Decimal("0.0000")

    def test_one_bps(self) -> None:
        assert validate_bps(1) == Decimal("1.0000")
        assert rate_to_bps("0.0001") == Decimal("1.0000")

    def test_hundred_bps(self) -> None:
        assert validate_bps(100) == Decimal("100.0000")
        assert bps_to_rate(100) == Decimal("0.0100000000")

    def test_max_bps(self) -> None:
        assert validate_bps(10000) == Decimal("10000.0000")

    def test_negative_bps_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError):
            validate_bps(-1)

    def test_nan_inf_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError):
            validate_bps(math.nan)
        with pytest.raises(ExecutionEconomicsError):
            validate_bps(math.inf)

    def test_slippage_cost_from_bps(self) -> None:
        cost = slippage_cost_from_bps(notional="100000", slippage_bps="5")
        assert cost == Decimal("50.00000000")


class TestAssumptionsSnapshot:
    def test_order_size_and_depth_present(self) -> None:
        snap = build_assumptions_snapshot()
        assert snap["order_size"]["value"] == "1.0"
        assert snap["book_depth"]["depth_multiplier"] == "10000"
        assert snap["order_size"]["synthetic"] is True
        assert "fingerprint" in snap

    def test_fingerprint_changes_when_assumption_changes(self) -> None:
        a = build_assumptions_snapshot(order_size="1.0")
        b = build_assumptions_snapshot(order_size="2.0")
        assert a["fingerprint"] != b["fingerprint"]

    def test_no_secret_keys(self) -> None:
        snap = build_assumptions_snapshot()
        blob = json.dumps(snap).lower()
        for banned in ("password", "api_key", "api_secret", "token", "dsn"):
            assert banned not in blob


class TestDeterminism:
    def test_identical_reconcile_fingerprint(self) -> None:
        r1 = reconcile_gross_to_net(
            gross_pnl="100", taker_fee_cost="1", slippage_cost="2"
        ).to_dict()
        r2 = reconcile_gross_to_net(
            gross_pnl="100", taker_fee_cost="1", slippage_cost="2"
        ).to_dict()
        assert economics_evidence_fingerprint(r1) == economics_evidence_fingerprint(r2)

    def test_component_compare_deterministic(self) -> None:
        replay = reconcile_gross_to_net(
            gross_pnl="100", taker_fee_cost="1", slippage_cost="2"
        ).to_dict()
        paper = reconcile_gross_to_net(
            gross_pnl="90", taker_fee_cost="0", slippage_cost="1"
        ).to_dict()
        d1 = compare_economics_components(replay, paper)
        d2 = compare_economics_components(replay, paper)
        assert d1 == d2
        assert d1["component_diffs"]["slippage_cost"]["delta"] == "1.00000000"


@pytest.mark.contract
class TestSchema:
    def test_result_validates_against_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        result = reconcile_gross_to_net(
            gross_pnl="100",
            maker_fee_cost="0",
            taker_fee_cost="1.5",
            slippage_cost="2.5",
            partial_fill_impact="0",
        ).to_dict()
        errors = sorted(validator.iter_errors(result), key=lambda e: e.path)
        assert not errors, errors[0].message if errors else ""
