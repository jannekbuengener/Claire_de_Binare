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
    COMPONENT_STATUS_INACTIVE,
    COMPONENT_STATUS_UNAVAILABLE,
    CONTRACT_VERSION,
    FUNDING_INPUT_AVAILABILITY,
    LEGACY_SCENARIO_OVERRIDE_KEYS,
    LIMIT_ORDER_MODEL_STATUS,
    SCENARIO_OVERRIDE_KEY_TO_SIMULATOR,
    ExecutionEconomicsError,
    bps_to_rate,
    build_assumptions_snapshot,
    compare_economics_components,
    economics_evidence_fingerprint,
    fill_price_embedded_gross_pnl,
    funding_cost_from_rate,
    partial_fill_impact_quote,
    rate_to_bps,
    reconcile_gross_to_net,
    reference_gross_pnl,
    resolve_funding_basis,
    resolve_scenario_overrides,
    slippage_cost_from_bps,
    validate_bps,
)
from services.execution.simulator import (
    ExecutionSimulator,
    PARKED_NOT_ECONOMICS_BILLABLE,
)

SOURCED_FUNDING_BASIS = {
    "position_value": "50000",
    "funding_rate": "0.0001",
    "funding_rate_source": "mexc_funding_history_export",
    "hours_held": "8",
}

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
            gross_pnl="100",
            maker_fee_cost="1",
            taker_fee_cost="2",
            order_type="limit",
            maker_fill_evidence=True,
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
            fill_status="partially_filled",
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
        assert result.funding_cost_when_active.amount is None

    def test_reference_gross_uses_filled_size(self) -> None:
        gross = reference_gross_pnl(
            side="buy",
            filled_size="0.5",
            entry_reference_price="100",
            exit_reference_price="110",
        )
        assert gross == Decimal("5.00000000")


class TestStatusValueContradictions:
    """A supplied cost must never be silently dropped by a non-billable status."""

    @pytest.mark.parametrize(
        ("kwargs", "component"),
        [
            ({"spread_cost": "1", "spread_status": "not_applicable"}, "spread_cost"),
            (
                {"slippage_cost": "1", "slippage_status": "not_applicable"},
                "slippage_cost",
            ),
            ({"slippage_cost": "0", "slippage_status": "unavailable"}, "slippage_cost"),
            (
                {"reject_impact": "1", "reject_status": "inactive_not_wired"},
                "reject_impact",
            ),
            (
                {"latency_or_delay_impact": "1", "latency_status": "not_applicable"},
                "latency_or_delay_impact",
            ),
            (
                {"partial_fill_impact": "1", "partial_fill_status": "unavailable"},
                "partial_fill_impact",
            ),
            (
                {"funding_cost": "1", "funding_status": "inactive_not_wired"},
                "funding_cost_when_active",
            ),
        ],
    )
    def test_value_under_non_billable_status_rejected(
        self, kwargs: dict, component: str
    ) -> None:
        with pytest.raises(ExecutionEconomicsError, match="silently dropped"):
            reconcile_gross_to_net(gross_pnl="10", taker_fee_cost="0", **kwargs)

    def test_unknown_component_status_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="not a valid component"):
            reconcile_gross_to_net(
                gross_pnl="10", taker_fee_cost="0", spread_status="probably_fine"
            )

    def test_unavailable_status_is_null_not_measured_zero(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="10",
            taker_fee_cost="1",
            spread_status=COMPONENT_STATUS_UNAVAILABLE,
        )
        assert result.spread_cost.status == COMPONENT_STATUS_UNAVAILABLE
        assert result.spread_cost.amount is None
        # Missing input must not be subtracted as if it were measured.
        assert result.net_pnl == Decimal("9.00000000")

    def test_embedded_slippage_is_not_subtracted_again(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="0",
            slippage_cost="5",
            slippage_status="embedded_in_fill_price",
        )
        assert result.slippage_cost.amount == Decimal("5.00000000")
        assert result.net_pnl == Decimal("100.00000000")


class TestMakerTakerSemantics:
    def test_market_path_rejects_maker_fee(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="maker_fee_cost > 0"):
            reconcile_gross_to_net(
                gross_pnl="100", maker_fee_cost="1", taker_fee_cost="0"
            )

    def test_limit_without_evidence_rejects_maker_fee(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="maker_fill_evidence"):
            reconcile_gross_to_net(
                gross_pnl="100",
                maker_fee_cost="1",
                taker_fee_cost="0",
                order_type="limit",
            )

    def test_maker_evidence_requires_limit_order_type(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="order_type='limit'"):
            reconcile_gross_to_net(
                gross_pnl="100", taker_fee_cost="0", maker_fill_evidence=True
            )

    def test_zero_maker_fee_allowed_on_market_path(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100", maker_fee_cost="0", taker_fee_cost="2"
        )
        assert result.maker_fee_cost.status == "zero"
        assert result.total_fee_cost.amount == Decimal("2.00000000")

    def test_unknown_order_type_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="order_type"):
            reconcile_gross_to_net(
                gross_pnl="100", taker_fee_cost="0", order_type="iceberg"
            )


class TestFillSemantics:
    def test_no_fill_requires_zero_gross(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="requires gross_pnl == 0"):
            reconcile_gross_to_net(
                gross_pnl="10", taker_fee_cost="0", fill_status="not_filled"
            )

    def test_no_fill_forbids_fees(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="non-zero total_fee_cost"):
            reconcile_gross_to_net(
                gross_pnl="0", taker_fee_cost="1", fill_status="not_filled"
            )

    def test_no_fill_is_representable(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="0",
            taker_fee_cost="0",
            slippage_status="not_applicable",
            partial_fill_impact="7",
            fill_status="not_filled",
        )
        assert result.fill_status == "not_filled"
        assert result.net_pnl == Decimal("-7.00000000")

    def test_partial_fill_requires_billable_impact(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="partially_filled"):
            reconcile_gross_to_net(
                gross_pnl="10",
                taker_fee_cost="0",
                partial_fill_status="not_applicable",
                fill_status="partially_filled",
            )

    def test_full_fill_forbids_partial_impact(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="forbids a non-zero"):
            reconcile_gross_to_net(
                gross_pnl="10", taker_fee_cost="0", partial_fill_impact="1"
            )

    def test_unknown_fill_status_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="fill_status"):
            reconcile_gross_to_net(
                gross_pnl="10", taker_fee_cost="0", fill_status="maybe"
            )


class TestFundingWireOrRetire:
    """Funding stays retired unless a sourced rate and duration are supplied."""

    def test_active_funding_requires_basis(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="requires funding_basis"):
            reconcile_gross_to_net(
                gross_pnl="100",
                taker_fee_cost="0",
                funding_cost="5",
                funding_status="active",
            )

    def test_synthetic_rate_source_rejected(self) -> None:
        basis = dict(SOURCED_FUNDING_BASIS, funding_rate_source="synthetic_default")
        with pytest.raises(ExecutionEconomicsError, match="not admissible"):
            reconcile_gross_to_net(
                gross_pnl="100",
                taker_fee_cost="0",
                funding_status="active",
                funding_basis=basis,
            )

    def test_incomplete_basis_rejected(self) -> None:
        basis = dict(SOURCED_FUNDING_BASIS)
        basis.pop("hours_held")
        with pytest.raises(ExecutionEconomicsError, match="missing required keys"):
            reconcile_gross_to_net(
                gross_pnl="100",
                taker_fee_cost="0",
                funding_status="active",
                funding_basis=basis,
            )

    def test_basis_under_inactive_status_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="funding_basis must not"):
            reconcile_gross_to_net(
                gross_pnl="100",
                taker_fee_cost="0",
                funding_status=COMPONENT_STATUS_INACTIVE,
                funding_basis=SOURCED_FUNDING_BASIS,
            )

    def test_supplied_cost_must_match_basis(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="does not reconcile"):
            reconcile_gross_to_net(
                gross_pnl="100",
                taker_fee_cost="0",
                funding_cost="99",
                funding_status="active",
                funding_basis=SOURCED_FUNDING_BASIS,
            )

    def test_sourced_funding_is_derived_and_subtracted(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="0",
            funding_status="active",
            funding_basis=SOURCED_FUNDING_BASIS,
        )
        assert result.funding_cost_when_active.amount == Decimal("5.00000000")
        assert result.net_pnl == Decimal("95.00000000")
        assert result.funding_basis is not None
        assert (
            result.funding_basis["funding_rate_source"] == "mexc_funding_history_export"
        )

    def test_funding_cost_from_rate_scales_with_periods(self) -> None:
        eight = funding_cost_from_rate(
            position_value="50000", funding_rate="0.0001", hours_held="8"
        )
        sixteen = funding_cost_from_rate(
            position_value="50000", funding_rate="0.0001", hours_held="16"
        )
        assert eight == Decimal("5.00000000")
        assert sixteen == eight * 2

    def test_funding_cost_from_rate_matches_simulator_arithmetic(self) -> None:
        simulator = ExecutionSimulator()
        legacy = simulator.calculate_funding_fees(
            position_size=1.0,
            position_value=50000.0,
            funding_rate=0.0001,
            hours_held=8.0,
        )
        derived = funding_cost_from_rate(
            position_value="50000", funding_rate="0.0001", hours_held="8"
        )
        assert derived == Decimal(str(legacy)).quantize(Decimal("0.00000001"))

    def test_negative_funding_rate_rejected(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="negative funding rates"):
            funding_cost_from_rate(
                position_value="50000", funding_rate="-0.0001", hours_held="8"
            )

    def test_resolve_funding_basis_is_deterministic(self) -> None:
        first = resolve_funding_basis(SOURCED_FUNDING_BASIS)
        second = resolve_funding_basis(dict(SOURCED_FUNDING_BASIS))
        assert first == second


class TestParkedSurfaceParity:
    """Contract status and simulator status must not drift apart."""

    def test_limit_order_model_status_matches_simulator(self) -> None:
        assert LIMIT_ORDER_MODEL_STATUS == PARKED_NOT_ECONOMICS_BILLABLE

    def test_simulator_limit_result_is_not_economics_billable(self) -> None:
        simulator = ExecutionSimulator()
        filled = simulator.simulate_limit_order(
            side="buy", size=0.5, limit_price=50000.0, current_price=50000.0
        )
        assert filled.economics_billable is False
        assert filled.order_type == "limit"
        assert filled.fee_role == "maker_assumed_unproven"

    def test_simulator_market_result_is_billable_taker(self) -> None:
        simulator = ExecutionSimulator()
        result = simulator.simulate_market_order(
            side="buy",
            size=0.5,
            current_price=50000.0,
            order_book_depth=1_000_000.0,
            volatility=0.02,
        )
        assert result.economics_billable is True
        assert result.fee_role == "taker"

    def test_snapshot_reports_parked_limit_and_unavailable_funding(self) -> None:
        snap = build_assumptions_snapshot()
        assert snap["limit_order_model"]["status"] == LIMIT_ORDER_MODEL_STATUS
        assert snap["limit_order_model"]["wired_into_arvp_runners"] is False
        assert snap["funding_model"]["status"] == COMPONENT_STATUS_INACTIVE
        assert snap["funding_model"]["input_availability"] == FUNDING_INPUT_AVAILABILITY
        assert snap["funding_model"]["wired_into_replay_pnl"] is False

    def test_snapshot_funding_active_requires_sourced_rate(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="non-synthetic"):
            build_assumptions_snapshot(funding_active=True)

    def test_snapshot_limit_active_requires_fill_model(self) -> None:
        with pytest.raises(ExecutionEconomicsError, match="limit_order_fill_model"):
            build_assumptions_snapshot(limit_orders_active=True)

    def test_snapshot_activation_flips_wiring_flags(self) -> None:
        snap = build_assumptions_snapshot(
            funding_active=True,
            funding_rate_source="mexc_funding_history_export",
            limit_orders_active=True,
            limit_order_fill_model="queue_position_v1",
        )
        assert snap["funding_model"]["wired_into_replay_pnl"] is True
        assert snap["limit_order_model"]["wired_into_arvp_runners"] is True


class TestReconciliationInvariant:
    def test_reported_net_matching_reconciles(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="2",
            slippage_cost="3",
            reported_net_pnl="95",
        )
        assert result.net_pnl == Decimal("95.00000000")
        assert result.residual == Decimal("0E-8")
        assert result.reconciled is True

    def test_reported_net_mismatch_fails_reconciliation(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="2",
            slippage_cost="3",
            reported_net_pnl="97",
        )
        assert result.reconciled is False
        assert result.residual == Decimal("2.00000000")

    def test_gross_minus_active_costs_equals_net(self) -> None:
        result = reconcile_gross_to_net(
            gross_pnl="100",
            taker_fee_cost="2",
            spread_cost="1",
            spread_status="active",
            slippage_cost="3",
            reject_impact="0.5",
            reject_status="active",
            latency_or_delay_impact="0.25",
            latency_status="active",
            funding_status="active",
            funding_basis=SOURCED_FUNDING_BASIS,
        )
        active_costs = (
            result.total_fee_cost.amount
            + result.spread_cost.amount
            + result.slippage_cost.amount
            + result.reject_impact.amount
            + result.latency_or_delay_impact.amount
            + result.funding_cost_when_active.amount
        )
        assert result.gross_pnl - active_costs == result.net_pnl


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

    def test_active_funding_and_maker_fill_validate(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        result = reconcile_gross_to_net(
            gross_pnl="100",
            maker_fee_cost="0.5",
            taker_fee_cost="0",
            order_type="limit",
            maker_fill_evidence=True,
            funding_status="active",
            funding_basis=SOURCED_FUNDING_BASIS,
            reported_net_pnl="94.5",
        ).to_dict()
        errors = sorted(validator.iter_errors(result), key=lambda e: e.path)
        assert not errors, errors[0].message if errors else ""
        assert result["execution_semantics"]["order_type"] == "limit"
        assert result["execution_semantics"]["funding_basis"] is not None

    def test_unavailable_status_validates(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        result = reconcile_gross_to_net(
            gross_pnl="10",
            taker_fee_cost="0",
            slippage_status=COMPONENT_STATUS_UNAVAILABLE,
        ).to_dict()
        errors = sorted(validator.iter_errors(result), key=lambda e: e.path)
        assert not errors, errors[0].message if errors else ""
        assert result["components"]["slippage_cost"]["status"] == "unavailable"
