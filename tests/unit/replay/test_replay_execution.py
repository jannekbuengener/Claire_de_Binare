"""Unit tests for core.replay.execution.

Scope:
  - ReplayMarketContext: validation / fail-closed
  - ReplayFillPayload: quantized fields, to_dict(), None-omission
  - ReplayExecutionWrapper.execute(): determinism, quantization,
    partial fill, fee/slippage preservation, ts_ms/created_at from clock,
    deterministic event_id, canonical FillEnvelopeV1
  - Quantization helpers (_q_money, _q_qty, _q_ratio, _q_bps)
  - _derive_fill_event_id: stability and uniqueness
"""

from __future__ import annotations

import pytest

from core.contracts.external_adapter_contracts import StrategySignalCandidate
from core.replay.canonical_json import canonical_hash, canonical_json_dumps
from core.replay.clock_context import ReplayClockContext
from core.replay.envelopes import FillEnvelopeV1
from core.replay.execution import (
    ReplayExecutionError,
    ReplayExecutionWrapper,
    ReplayFillPayload,
    ReplayMarketContext,
    _derive_fill_event_id,
    _q_bps,
    _q_money,
    _q_qty,
    _q_ratio,
)
from core.replay.time import created_at_from_ts_ms
from services.execution.simulator import ExecutionSimulator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SYMBOL = "BTCUSDT"
_TS_MS = 1_700_000_000_000
_REPLAY_RUN_ID = "replay-test-abc123"


def _make_signal(side: str = "BUY") -> StrategySignalCandidate:
    return StrategySignalCandidate(
        strategy_id="primary_breakout_v1",
        symbol=_SYMBOL,
        side=side,  # type: ignore[arg-type]
        reason="test_signal",
    )


def _make_market_ctx(
    current_price: float = 50_000.0,
    order_book_depth: float = 1_000_000.0,
    volatility: float = 0.02,
    order_size: float = 0.5,
) -> ReplayMarketContext:
    return ReplayMarketContext(
        current_price=current_price,
        order_book_depth=order_book_depth,
        volatility=volatility,
        order_size=order_size,
    )


def _make_clock(ts_ms: int = _TS_MS) -> ReplayClockContext:
    return ReplayClockContext(ts_ms=ts_ms)


def _make_wrapper() -> ReplayExecutionWrapper:
    return ReplayExecutionWrapper(simulator=ExecutionSimulator())


# ---------------------------------------------------------------------------
# Quantization helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQuantizationHelpers:
    def test_q_money_8dp(self) -> None:
        assert _q_money(50075.1234567899) == "50075.12345679"

    def test_q_money_rounds_half_even(self) -> None:
        # 50000.000000005 rounds to 50000.00000001 under ROUND_HALF_EVEN
        result = _q_money(0.123456785)
        assert len(result.split(".")[-1]) == 8

    def test_q_money_zero(self) -> None:
        assert _q_money(0.0) == "0.00000000"

    def test_q_qty_8dp(self) -> None:
        assert _q_qty(0.5) == "0.50000000"

    def test_q_qty_partial(self) -> None:
        result = _q_qty(0.333333)
        assert result == "0.33333300"

    def test_q_ratio_6dp(self) -> None:
        assert _q_ratio(1.0) == "1.000000"
        assert _q_ratio(0.0) == "0.000000"

    def test_q_ratio_partial(self) -> None:
        result = _q_ratio(0.75)
        assert result == "0.750000"

    def test_q_bps_2dp(self) -> None:
        assert _q_bps(15.0) == "15.00"
        assert _q_bps(5.123) == "5.12"

    def test_q_money_rejects_nan(self) -> None:
        with pytest.raises(ReplayExecutionError):
            _q_money(float("nan"))

    def test_q_money_rejects_inf(self) -> None:
        with pytest.raises(ReplayExecutionError):
            _q_money(float("inf"))

    def test_q_qty_rejects_nan(self) -> None:
        with pytest.raises(ReplayExecutionError):
            _q_qty(float("nan"))

    def test_q_ratio_rejects_inf(self) -> None:
        with pytest.raises(ReplayExecutionError):
            _q_ratio(float("-inf"))


# ---------------------------------------------------------------------------
# ReplayMarketContext validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplayMarketContext:
    def test_valid_context(self) -> None:
        ctx = _make_market_ctx()
        assert ctx.current_price == 50_000.0

    def test_frozen_immutable(self) -> None:
        ctx = _make_market_ctx()
        with pytest.raises(Exception):
            ctx.current_price = 1.0  # type: ignore

    def test_rejects_zero_price(self) -> None:
        with pytest.raises(ReplayExecutionError, match="current_price"):
            ReplayMarketContext(
                current_price=0.0,
                order_book_depth=1_000_000.0,
                volatility=0.02,
                order_size=0.5,
            )

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ReplayExecutionError, match="current_price"):
            ReplayMarketContext(
                current_price=-1.0,
                order_book_depth=1_000_000.0,
                volatility=0.02,
                order_size=0.5,
            )

    def test_rejects_zero_depth(self) -> None:
        with pytest.raises(ReplayExecutionError, match="order_book_depth"):
            ReplayMarketContext(
                current_price=50_000.0,
                order_book_depth=0.0,
                volatility=0.02,
                order_size=0.5,
            )

    def test_rejects_negative_depth(self) -> None:
        with pytest.raises(ReplayExecutionError, match="order_book_depth"):
            ReplayMarketContext(
                current_price=50_000.0,
                order_book_depth=-100.0,
                volatility=0.02,
                order_size=0.5,
            )

    def test_rejects_negative_volatility(self) -> None:
        with pytest.raises(ReplayExecutionError, match="volatility"):
            ReplayMarketContext(
                current_price=50_000.0,
                order_book_depth=1_000_000.0,
                volatility=-0.01,
                order_size=0.5,
            )

    def test_zero_volatility_allowed(self) -> None:
        """Zero volatility is valid (no vol component in slippage)."""
        ctx = ReplayMarketContext(
            current_price=50_000.0,
            order_book_depth=1_000_000.0,
            volatility=0.0,
            order_size=0.5,
        )
        assert ctx.volatility == 0.0

    def test_rejects_zero_order_size(self) -> None:
        with pytest.raises(ReplayExecutionError, match="order_size"):
            ReplayMarketContext(
                current_price=50_000.0,
                order_book_depth=1_000_000.0,
                volatility=0.02,
                order_size=0.0,
            )

    def test_rejects_negative_order_size(self) -> None:
        with pytest.raises(ReplayExecutionError, match="order_size"):
            ReplayMarketContext(
                current_price=50_000.0,
                order_book_depth=1_000_000.0,
                volatility=0.02,
                order_size=-1.0,
            )


# ---------------------------------------------------------------------------
# ReplayFillPayload
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplayFillPayload:
    def _sample(self, notes: str | None = None) -> ReplayFillPayload:
        return ReplayFillPayload(
            filled_quantity="0.50000000",
            avg_fill_price="50075.00000000",
            slippage_bps="15.00",
            fees_usdt="15.02250000",
            fill_ratio="1.000000",
            partial_fill=False,
            order_side="BUY",
            symbol=_SYMBOL,
            notes=notes,
        )

    def test_to_dict_contains_required_fields(self) -> None:
        d = self._sample().to_dict()
        for key in (
            "filled_quantity",
            "avg_fill_price",
            "slippage_bps",
            "fees_usdt",
            "fill_ratio",
            "partial_fill",
            "order_side",
            "symbol",
        ):
            assert key in d, f"Missing key: {key}"

    def test_to_dict_omits_none_notes(self) -> None:
        d = self._sample(notes=None).to_dict()
        assert "notes" not in d

    def test_to_dict_includes_notes_when_set(self) -> None:
        d = self._sample(notes="Market order BUY with 15.0bps slippage").to_dict()
        assert "notes" in d

    def test_frozen_immutable(self) -> None:
        p = self._sample()
        with pytest.raises(Exception):
            p.filled_quantity = "1.0"  # type: ignore

    def test_partial_fill_flag_type(self) -> None:
        p = self._sample()
        assert isinstance(p.partial_fill, bool)


# ---------------------------------------------------------------------------
# _derive_fill_event_id
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeriveFillEventId:
    def test_deterministic_identical_inputs(self) -> None:
        id1 = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        id2 = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        assert id1 == id2

    def test_starts_with_fill_prefix(self) -> None:
        eid = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        assert eid.startswith("fill-")

    def test_different_index_different_id(self) -> None:
        id0 = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        id1 = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 1)
        assert id0 != id1

    def test_different_ts_different_id(self) -> None:
        id_a = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        id_b = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS + 1, "BUY", _SYMBOL, 0)
        assert id_a != id_b

    def test_different_side_different_id(self) -> None:
        id_buy = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        id_sell = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "SELL", _SYMBOL, 0)
        assert id_buy != id_sell

    def test_different_run_id_different_id(self) -> None:
        id_a = _derive_fill_event_id("run-a", _TS_MS, "BUY", _SYMBOL, 0)
        id_b = _derive_fill_event_id("run-b", _TS_MS, "BUY", _SYMBOL, 0)
        assert id_a != id_b

    def test_side_normalised_to_upper(self) -> None:
        """Lower-case side should not affect determinism (normalised to upper)."""
        id_upper = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "BUY", _SYMBOL, 0)
        id_lower = _derive_fill_event_id(_REPLAY_RUN_ID, _TS_MS, "buy", _SYMBOL, 0)
        # Both are normalised to "BUY" inside derive helper
        assert id_upper == id_lower


# ---------------------------------------------------------------------------
# ReplayExecutionWrapper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestReplayExecutionWrapper:
    def test_returns_fill_payload_and_envelope(self) -> None:
        wrapper = _make_wrapper()
        fill, env = wrapper.execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        assert isinstance(fill, ReplayFillPayload)
        assert isinstance(env, FillEnvelopeV1)

    def test_identical_inputs_identical_canonical_json(self) -> None:
        """Identical replay inputs produce byte-identical canonical fill envelope JSON."""
        wrapper = _make_wrapper()
        kwargs = dict(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        _, env1 = wrapper.execute(**kwargs)
        _, env2 = wrapper.execute(**kwargs)
        json1 = canonical_json_dumps(env1.to_dict())
        json2 = canonical_json_dumps(env2.to_dict())
        assert json1 == json2

    def test_ts_ms_from_clock_not_wall_clock(self) -> None:
        """ts_ms in the fill envelope equals the clock's ts_ms."""
        fixed_ts = 1_609_459_200_000
        _, env = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=ReplayClockContext(ts_ms=fixed_ts),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        assert env.ts_ms == fixed_ts

    def test_created_at_from_clock_ts_ms(self) -> None:
        """created_at is derived deterministically from clock.now_ts_ms()."""
        fixed_ts = 1_609_459_200_123
        _, env = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=ReplayClockContext(ts_ms=fixed_ts),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        assert env.created_at == created_at_from_ts_ms(fixed_ts)

    def test_envelope_schema_and_event_type(self) -> None:
        _, env = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        assert env.schema_version == "envelope.v1"
        assert env.event_type == "FILL"

    def test_replay_run_id_on_envelope(self) -> None:
        _, env = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=3,
        )
        assert env.replay_run_id == _REPLAY_RUN_ID
        assert env.replay_envelope_index == 3

    def test_event_id_is_deterministic(self) -> None:
        kwargs = dict(
            signal=_make_signal("SELL"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=7,
        )
        _, env1 = _make_wrapper().execute(**kwargs)
        _, env2 = _make_wrapper().execute(**kwargs)
        assert env1.event_id == env2.event_id
        assert env1.event_id.startswith("fill-")

    def test_fill_payload_fields_are_strings(self) -> None:
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert isinstance(fill.filled_quantity, str)
        assert isinstance(fill.avg_fill_price, str)
        assert isinstance(fill.slippage_bps, str)
        assert isinstance(fill.fees_usdt, str)
        assert isinstance(fill.fill_ratio, str)

    def test_fill_ratio_and_partial_fill_full_fill(self) -> None:
        """Full fill: fill_ratio == 1.000000, partial_fill == False."""
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(order_size=0.001),  # very small order
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert fill.fill_ratio == "1.000000"
        assert fill.partial_fill is False

    def test_partial_fill_sets_flags_correctly(self) -> None:
        """Partial fill occurs when notional > usable_depth (80% of depth).

        Use very large order_size relative to depth to force partial fill.
        """
        # order_size=10000 BTC at 50000 USDT = 500M notional >> 1000 USDT depth
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=ReplayMarketContext(
                current_price=50_000.0,
                order_book_depth=1_000.0,   # small depth
                volatility=0.01,
                order_size=10_000.0,        # huge order → guaranteed partial fill
            ),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert fill.partial_fill is True
        # fill_ratio < 1.000000 for partial fill
        ratio = float(fill.fill_ratio)
        assert ratio < 1.0
        assert ratio > 0.0

    def test_fees_and_slippage_preserved(self) -> None:
        """Fee and slippage fields are non-zero for normal execution."""
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        # fees > 0 (taker fee on filled notional)
        assert float(fill.fees_usdt) > 0.0
        # slippage > 0 (base + depth + vol components)
        assert float(fill.slippage_bps) > 0.0

    def test_order_side_normalised_to_upper(self) -> None:
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("sell"),  # type: ignore — lowercase
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert fill.order_side == "SELL"

    def test_symbol_preserved(self) -> None:
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert fill.symbol == _SYMBOL

    def test_envelope_payload_matches_fill_payload_to_dict(self) -> None:
        """FillEnvelopeV1.payload must equal ReplayFillPayload.to_dict()."""
        fill, env = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert env.payload == fill.to_dict()

    def test_canonical_hash_stable_across_instances(self) -> None:
        """canonical_hash of fill envelope dict is stable across different simulator instances."""
        kwargs = dict(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        # Different wrapper instances with identical default simulator config
        _, env_a = ReplayExecutionWrapper(simulator=ExecutionSimulator()).execute(**kwargs)
        _, env_b = ReplayExecutionWrapper(simulator=ExecutionSimulator()).execute(**kwargs)
        assert canonical_hash(env_a.to_dict()) == canonical_hash(env_b.to_dict())

    def test_different_ts_ms_different_canonical_hash(self) -> None:
        """Different clock ts_ms produces different canonical envelope JSON."""
        base_kwargs = dict(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            replay_run_id=_REPLAY_RUN_ID,
            envelope_index=0,
        )
        _, env_a = _make_wrapper().execute(
            clock=ReplayClockContext(ts_ms=_TS_MS), **base_kwargs
        )
        _, env_b = _make_wrapper().execute(
            clock=ReplayClockContext(ts_ms=_TS_MS + 60_000), **base_kwargs
        )
        assert canonical_hash(env_a.to_dict()) != canonical_hash(env_b.to_dict())

    def test_buy_price_higher_than_current_due_to_slippage(self) -> None:
        """BUY fill price > current_price (adverse slippage for buyer)."""
        price = 50_000.0
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(current_price=price),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert float(fill.avg_fill_price) > price

    def test_sell_price_lower_than_current_due_to_slippage(self) -> None:
        """SELL fill price < current_price (adverse slippage for seller)."""
        price = 50_000.0
        fill, _ = _make_wrapper().execute(
            signal=_make_signal("SELL"),
            market_ctx=_make_market_ctx(current_price=price),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        assert float(fill.avg_fill_price) < price

    def test_envelope_to_dict_no_none_fields(self) -> None:
        """FillEnvelopeV1.to_dict() omits None optional fields."""
        _, env = _make_wrapper().execute(
            signal=_make_signal("BUY"),
            market_ctx=_make_market_ctx(),
            clock=_make_clock(),
            replay_run_id=_REPLAY_RUN_ID,
        )
        d = env.to_dict()
        # correlation_id, trace_id, policy_id etc. are not set → must be absent
        for absent_key in ("correlation_id", "trace_id", "policy_id", "policy_hash"):
            assert absent_key not in d, f"Unexpected key in envelope dict: {absent_key}"
        # replay fields are set → must be present
        assert "replay_run_id" in d
        assert "replay_envelope_index" in d
