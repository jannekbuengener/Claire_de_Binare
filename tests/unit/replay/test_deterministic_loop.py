"""Unit tests for deterministic replay event loop (#1803).

Covers:
  - empty/no-signal input preserves initial state
  - BUY signal sets position_open=True
  - BUY then SELL returns position_open=False
  - last_entry_ts_ms tracked correctly
  - freshness counters increment only when flags present
  - identical request sequences produce identical canonical signatures across two fresh runs
  - manipulated second-pass initial state causes determinism_ok=False
  - boundary/warmup fixture (historical bridge output) stays stable
  - no wall-clock dependency
  - ReplayLoopResult.to_dict() semantics
  - run_deterministic_replay facade
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

import pytest

from core.contracts.external_adapter_contracts import (
    StrategyAdapterRequest,
    StrategyAdapterResponse,
    StrategySignalCandidate,
)
from core.replay.canonical_json import canonical_hash
from core.replay.deterministic_loop import (
    DeterministicReplayEventLoop,
    ReplayLoopResult,
    _compute_signature,
    _extract_freshness_flags,
    _run_single_pass,
    _serialize_response,
    run_deterministic_replay,
)


# ---------------------------------------------------------------------------
# Test fixtures / helpers
# ---------------------------------------------------------------------------

def _make_request(
    ts_ms: int = 1_700_000_000_000,
    *,
    desired_side: Optional[str] = None,
    market_state_fresh: bool = False,
    regime_fresh: bool = False,
    symbol: str = "BTCUSDT",
) -> StrategyAdapterRequest:
    """Build a minimal StrategyAdapterRequest for testing.

    Uses ``desired_side`` as a test hint in market_event so evaluators can
    be purely stateless (driven by request content, not call order).
    """
    market_state: dict[str, Any] = {
        "market_state_fresh": market_state_fresh,
        "regime_fresh": regime_fresh,
    }
    market_event: dict[str, Any] = {
        "ts_ms": ts_ms,
        "market_state": market_state,
    }
    if desired_side is not None:
        market_event["_test_side"] = desired_side
    return StrategyAdapterRequest(
        symbol=symbol,
        market_event=market_event,
        market_snapshot={},
        runtime_context={},
    )


def _side_driven_evaluator(
    request: StrategyAdapterRequest,
    position_open: bool,
    last_entry_ts_ms: Optional[int],
) -> Tuple[StrategyAdapterResponse, Optional[int]]:
    """Pure stateless evaluator: emits signal based on _test_side in market_event.

    BUY signal: emitted if _test_side=="BUY" and position is currently closed.
    SELL signal: emitted if _test_side=="SELL" and position is currently open.
    Otherwise: no signal.

    This evaluator is fully deterministic: output depends only on request
    content and position_open — no wall-clock, no call-count state.
    """
    side_hint = request.market_event.get("_test_side")
    ts_ms = int(request.market_event.get("ts_ms", 0))

    if side_hint == "BUY" and not position_open:
        return (
            StrategyAdapterResponse(
                signals=(
                    StrategySignalCandidate(
                        strategy_id="test_strategy",
                        symbol=request.symbol,
                        side="BUY",
                        reason="test_entry",
                        price=100.0,
                    ),
                ),
                diagnostics={"status": "signal_emitted"},
            ),
            ts_ms,
        )

    if side_hint == "SELL" and position_open:
        return (
            StrategyAdapterResponse(
                signals=(
                    StrategySignalCandidate(
                        strategy_id="test_strategy",
                        symbol=request.symbol,
                        side="SELL",
                        reason="test_exit",
                        price=110.0,
                    ),
                ),
                diagnostics={"status": "signal_emitted"},
            ),
            last_entry_ts_ms,
        )

    return (
        StrategyAdapterResponse(diagnostics={"status": "no_signal"}),
        last_entry_ts_ms,
    )


def _no_signal_evaluator(
    request: StrategyAdapterRequest,
    position_open: bool,
    last_entry_ts_ms: Optional[int],
) -> Tuple[StrategyAdapterResponse, Optional[int]]:
    """Stateless evaluator that always returns no signals."""
    return StrategyAdapterResponse(diagnostics={"status": "no_signal"}), last_entry_ts_ms


# ---------------------------------------------------------------------------
# _serialize_response
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_serialize_response_no_signals() -> None:
    response = StrategyAdapterResponse(diagnostics={"status": "no_signal"})
    result = _serialize_response(response)
    assert result["signals"] == []
    assert result["diagnostics"] == {"status": "no_signal"}


@pytest.mark.unit
def test_serialize_response_with_signal() -> None:
    response = StrategyAdapterResponse(
        signals=(
            StrategySignalCandidate(
                strategy_id="s1", symbol="BTCUSDT", side="BUY", reason="r",
                price=42.0, metadata={"k": "v"},
            ),
        )
    )
    result = _serialize_response(response)
    assert len(result["signals"]) == 1
    sig = result["signals"][0]
    assert sig["side"] == "BUY"
    assert sig["price"] == 42.0
    assert sig["metadata"] == {"k": "v"}


@pytest.mark.unit
def test_serialize_response_none_metadata_becomes_empty_dict() -> None:
    response = StrategyAdapterResponse(
        signals=(
            StrategySignalCandidate(
                strategy_id="s1", symbol="BTCUSDT", side="SELL", reason="exit",
                metadata=None,
            ),
        )
    )
    result = _serialize_response(response)
    assert result["signals"][0]["metadata"] == {}


@pytest.mark.unit
def test_serialize_response_none_diagnostics_becomes_empty_dict() -> None:
    response = StrategyAdapterResponse(diagnostics=None)
    result = _serialize_response(response)
    assert result["diagnostics"] == {}


# ---------------------------------------------------------------------------
# _compute_signature
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_compute_signature_empty_list() -> None:
    sig = _compute_signature([])
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA-256 hex


@pytest.mark.unit
def test_compute_signature_stable_for_same_input() -> None:
    responses = [{"signals": [], "diagnostics": {"status": "no_signal"}}]
    assert _compute_signature(responses) == _compute_signature(responses)


@pytest.mark.unit
def test_compute_signature_differs_for_different_input() -> None:
    sig_a = _compute_signature([{"signals": [], "diagnostics": {"status": "no_signal"}}])
    sig_b = _compute_signature([{"signals": [{"side": "BUY"}], "diagnostics": {}}])
    assert sig_a != sig_b


@pytest.mark.unit
def test_compute_signature_order_sensitive() -> None:
    resp_a = {"signals": [], "diagnostics": {"x": 1}}
    resp_b = {"signals": [], "diagnostics": {"x": 2}}
    sig_ab = _compute_signature([resp_a, resp_b])
    sig_ba = _compute_signature([resp_b, resp_a])
    assert sig_ab != sig_ba


# ---------------------------------------------------------------------------
# _extract_freshness_flags
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_extract_freshness_both_true() -> None:
    req = _make_request(market_state_fresh=True, regime_fresh=True)
    ms_fresh, reg_fresh = _extract_freshness_flags(req)
    assert ms_fresh is True
    assert reg_fresh is True


@pytest.mark.unit
def test_extract_freshness_both_false() -> None:
    req = _make_request(market_state_fresh=False, regime_fresh=False)
    ms_fresh, reg_fresh = _extract_freshness_flags(req)
    assert ms_fresh is False
    assert reg_fresh is False


@pytest.mark.unit
def test_extract_freshness_missing_market_state() -> None:
    req = StrategyAdapterRequest(
        symbol="BTCUSDT",
        market_event={"ts_ms": 1000},
        market_snapshot={},
        runtime_context={},
    )
    ms_fresh, reg_fresh = _extract_freshness_flags(req)
    assert ms_fresh is False
    assert reg_fresh is False


@pytest.mark.unit
def test_extract_freshness_non_mapping_market_state() -> None:
    req = StrategyAdapterRequest(
        symbol="BTCUSDT",
        market_event={"ts_ms": 1000, "market_state": "not-a-dict"},
        market_snapshot={},
        runtime_context={},
    )
    ms_fresh, reg_fresh = _extract_freshness_flags(req)
    assert ms_fresh is False
    assert reg_fresh is False


# ---------------------------------------------------------------------------
# _run_single_pass — state transitions
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_single_pass_empty_requests_initial_state_preserved() -> None:
    state = _run_single_pass(
        requests=[],
        evaluator=_no_signal_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.processed_request_index == 0
    assert state.position_open is False
    assert state.last_entry_ts_ms is None
    assert state.cumulative_signals == []
    assert state.replay_responses == []
    assert state.market_state_fresh_count == 0
    assert state.regime_fresh_count == 0


@pytest.mark.unit
def test_single_pass_no_signal_preserves_state() -> None:
    req = _make_request(ts_ms=1_000)
    state = _run_single_pass(
        requests=[req],
        evaluator=_no_signal_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.processed_request_index == 1
    assert state.position_open is False
    assert state.last_entry_ts_ms is None
    assert state.cumulative_signals == []


@pytest.mark.unit
def test_single_pass_buy_sets_position_open() -> None:
    req = _make_request(ts_ms=1_000, desired_side="BUY")
    state = _run_single_pass(
        requests=[req],
        evaluator=_side_driven_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.position_open is True
    assert state.last_entry_ts_ms == 1_000
    assert len(state.cumulative_signals) == 1
    assert state.cumulative_signals[0]["side"] == "BUY"


@pytest.mark.unit
def test_single_pass_buy_then_sell_closes_position() -> None:
    req_buy = _make_request(ts_ms=1_000, desired_side="BUY")
    req_sell = _make_request(ts_ms=2_000, desired_side="SELL")
    state = _run_single_pass(
        requests=[req_buy, req_sell],
        evaluator=_side_driven_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.position_open is False
    assert len(state.cumulative_signals) == 2
    assert state.cumulative_signals[0]["side"] == "BUY"
    assert state.cumulative_signals[1]["side"] == "SELL"


@pytest.mark.unit
def test_single_pass_last_entry_ts_ms_set_on_buy() -> None:
    req_buy = _make_request(ts_ms=5_000, desired_side="BUY")
    state = _run_single_pass(
        requests=[req_buy],
        evaluator=_side_driven_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.last_entry_ts_ms == 5_000


@pytest.mark.unit
def test_single_pass_last_entry_ts_ms_preserved_after_sell() -> None:
    req_buy = _make_request(ts_ms=5_000, desired_side="BUY")
    req_sell = _make_request(ts_ms=6_000, desired_side="SELL")
    state = _run_single_pass(
        requests=[req_buy, req_sell],
        evaluator=_side_driven_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    # Evaluator returns last_entry_ts_ms unchanged on SELL
    assert state.last_entry_ts_ms == 5_000


@pytest.mark.unit
def test_single_pass_freshness_counters_increment() -> None:
    req_fresh = _make_request(ts_ms=1_000, market_state_fresh=True, regime_fresh=True)
    req_stale = _make_request(ts_ms=2_000, market_state_fresh=False, regime_fresh=False)
    state = _run_single_pass(
        requests=[req_fresh, req_stale, req_fresh],
        evaluator=_no_signal_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.market_state_fresh_count == 2
    assert state.regime_fresh_count == 2


@pytest.mark.unit
def test_single_pass_freshness_counters_only_when_true() -> None:
    req_no_state = StrategyAdapterRequest(
        symbol="BTCUSDT",
        market_event={"ts_ms": 1_000},  # no market_state key
        market_snapshot={},
        runtime_context={},
    )
    state = _run_single_pass(
        requests=[req_no_state, req_no_state],
        evaluator=_no_signal_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.market_state_fresh_count == 0
    assert state.regime_fresh_count == 0


@pytest.mark.unit
def test_single_pass_processed_index_increments() -> None:
    requests = [_make_request(ts_ms=i * 1_000) for i in range(5)]
    state = _run_single_pass(
        requests=requests,
        evaluator=_no_signal_evaluator,
        initial_position_open=False,
        initial_last_entry_ts_ms=None,
    )
    assert state.processed_request_index == 5


# ---------------------------------------------------------------------------
# DeterministicReplayEventLoop — public API
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_loop_empty_requests_determinism_ok() -> None:
    loop = DeterministicReplayEventLoop()
    result = loop.run(requests=[], evaluator=_no_signal_evaluator)
    assert result.processed_count == 0
    assert result.signal_count == 0
    assert result.determinism_ok is True
    assert result.position_open is False
    assert result.last_entry_ts_ms is None


@pytest.mark.unit
def test_loop_no_signal_sequence_determinism_ok() -> None:
    requests = [_make_request(ts_ms=i * 1_000) for i in range(10)]
    result = run_deterministic_replay(requests=requests, evaluator=_no_signal_evaluator)
    assert result.determinism_ok is True
    assert result.signal_count == 0
    assert result.processed_count == 10


@pytest.mark.unit
def test_loop_buy_signal_state() -> None:
    req_buy = _make_request(ts_ms=1_000, desired_side="BUY")
    result = run_deterministic_replay(requests=[req_buy], evaluator=_side_driven_evaluator)
    assert result.signal_count == 1
    assert result.position_open is True
    assert result.last_entry_ts_ms == 1_000
    assert result.determinism_ok is True


@pytest.mark.unit
def test_loop_buy_then_sell_transitions_state() -> None:
    requests = [
        _make_request(ts_ms=1_000, desired_side="BUY"),
        _make_request(ts_ms=2_000, desired_side="SELL"),
    ]
    result = run_deterministic_replay(requests=requests, evaluator=_side_driven_evaluator)
    assert result.signal_count == 2
    assert result.position_open is False
    assert result.determinism_ok is True


@pytest.mark.unit
def test_loop_freshness_counters_in_result() -> None:
    requests = [
        _make_request(ts_ms=1_000, market_state_fresh=True, regime_fresh=True),
        _make_request(ts_ms=2_000, market_state_fresh=True, regime_fresh=False),
        _make_request(ts_ms=3_000, market_state_fresh=False, regime_fresh=False),
    ]
    result = run_deterministic_replay(requests=requests, evaluator=_no_signal_evaluator)
    assert result.market_state_fresh_count == 2
    assert result.regime_fresh_count == 1


# ---------------------------------------------------------------------------
# Determinism: identical inputs → identical signatures across two full runs
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_two_independent_runs_produce_identical_signatures() -> None:
    requests = [
        _make_request(ts_ms=1_000, desired_side="BUY"),
        _make_request(ts_ms=2_000),
        _make_request(ts_ms=3_000, desired_side="SELL"),
        _make_request(ts_ms=4_000),
    ]
    result_a = run_deterministic_replay(requests=requests, evaluator=_side_driven_evaluator)
    result_b = run_deterministic_replay(requests=requests, evaluator=_side_driven_evaluator)
    assert result_a.replay_signature == result_b.replay_signature
    assert result_a.determinism_ok is True
    assert result_b.determinism_ok is True


@pytest.mark.unit
def test_identical_requests_same_loop_instance_stable() -> None:
    loop = DeterministicReplayEventLoop()
    requests = [_make_request(ts_ms=i * 1_000) for i in range(20)]
    result_a = loop.run(requests=requests, evaluator=_no_signal_evaluator)
    result_b = loop.run(requests=requests, evaluator=_no_signal_evaluator)
    assert result_a.replay_signature == result_b.replay_signature


@pytest.mark.unit
def test_different_request_sequences_produce_different_signatures() -> None:
    requests_with_buy = [_make_request(ts_ms=1_000, desired_side="BUY")]
    requests_no_signal = [_make_request(ts_ms=1_000)]
    result_a = run_deterministic_replay(
        requests=requests_with_buy, evaluator=_side_driven_evaluator
    )
    result_b = run_deterministic_replay(
        requests=requests_no_signal, evaluator=_side_driven_evaluator
    )
    assert result_a.replay_signature != result_b.replay_signature


# ---------------------------------------------------------------------------
# Determinism: manipulated second-pass initial state → determinism_ok=False
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_manipulated_second_pass_position_open_causes_determinism_fail() -> None:
    """Second pass starting open-position diverges from first pass starting closed."""
    # Request sequence: SELL then BUY.
    # First pass (position_open=False): SELL hint ignored (not open), BUY emitted.
    # Second pass (position_open=True): SELL emitted, then BUY emitted.
    requests = [
        _make_request(ts_ms=1_000, desired_side="SELL"),
        _make_request(ts_ms=2_000, desired_side="BUY"),
    ]
    loop = DeterministicReplayEventLoop()
    result = loop.run(
        requests=requests,
        evaluator=_side_driven_evaluator,
        initial_position_open=False,
        second_pass_initial_position_open=True,  # manipulated
    )
    assert result.determinism_ok is False


@pytest.mark.unit
def test_manipulated_second_pass_last_entry_ts_causes_divergence() -> None:
    """SELL evaluator returns unchanged last_entry_ts_ms; injecting different value
    changes second-pass behavior if evaluator uses it."""

    def ts_sensitive_evaluator(
        request: StrategyAdapterRequest,
        position_open: bool,
        last_entry_ts_ms: Optional[int],
    ) -> Tuple[StrategyAdapterResponse, Optional[int]]:
        """Encodes last_entry_ts_ms value into diagnostics, making signature ts-sensitive."""
        ts_ms = int(request.market_event.get("ts_ms", 0))
        return (
            StrategyAdapterResponse(
                diagnostics={"last_entry": last_entry_ts_ms, "ts": ts_ms}
            ),
            last_entry_ts_ms,
        )

    requests = [_make_request(ts_ms=5_000)]
    loop = DeterministicReplayEventLoop()
    result = loop.run(
        requests=requests,
        evaluator=ts_sensitive_evaluator,
        initial_last_entry_ts_ms=None,
        second_pass_initial_last_entry_ts_ms=99_999,  # manipulated
    )
    assert result.determinism_ok is False


@pytest.mark.unit
def test_same_initial_state_both_passes_gives_determinism_ok() -> None:
    requests = [
        _make_request(ts_ms=1_000, desired_side="BUY"),
        _make_request(ts_ms=2_000, desired_side="SELL"),
    ]
    loop = DeterministicReplayEventLoop()
    result = loop.run(
        requests=requests,
        evaluator=_side_driven_evaluator,
        initial_position_open=False,
        second_pass_initial_position_open=False,  # explicit same
    )
    assert result.determinism_ok is True


# ---------------------------------------------------------------------------
# Signature is canonical hash (not positional repr)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_replay_signature_is_64_char_hex() -> None:
    result = run_deterministic_replay(requests=[], evaluator=_no_signal_evaluator)
    assert len(result.replay_signature) == 64
    assert all(c in "0123456789abcdef" for c in result.replay_signature)


@pytest.mark.unit
def test_replay_signature_matches_manual_canonical_hash() -> None:
    req = _make_request(ts_ms=1_000)
    result = run_deterministic_replay(requests=[req], evaluator=_no_signal_evaluator)
    # Manually compute expected signature
    serialized = _serialize_response(
        StrategyAdapterResponse(diagnostics={"status": "no_signal"})
    )
    expected = canonical_hash({"responses": [serialized]})
    assert result.replay_signature == expected


# ---------------------------------------------------------------------------
# ReplayLoopResult.to_dict()
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_result_to_dict_no_last_entry_omits_field() -> None:
    result = run_deterministic_replay(requests=[], evaluator=_no_signal_evaluator)
    d = result.to_dict()
    assert "last_entry_ts_ms" not in d
    assert "processed_count" in d
    assert "replay_signature" in d
    assert "determinism_ok" in d


@pytest.mark.unit
def test_result_to_dict_includes_last_entry_when_present() -> None:
    req_buy = _make_request(ts_ms=5_000, desired_side="BUY")
    result = run_deterministic_replay(
        requests=[req_buy], evaluator=_side_driven_evaluator
    )
    d = result.to_dict()
    assert "last_entry_ts_ms" in d
    assert d["last_entry_ts_ms"] == 5_000


@pytest.mark.unit
def test_result_to_dict_determinism_ok_field() -> None:
    result = run_deterministic_replay(requests=[], evaluator=_no_signal_evaluator)
    d = result.to_dict()
    assert d["determinism_ok"] is True


# ---------------------------------------------------------------------------
# run_deterministic_replay facade
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_facade_returns_replay_loop_result() -> None:
    result = run_deterministic_replay(requests=[], evaluator=_no_signal_evaluator)
    assert isinstance(result, ReplayLoopResult)


@pytest.mark.unit
def test_facade_matches_class_api() -> None:
    requests = [_make_request(ts_ms=1_000, desired_side="BUY")]
    result_facade = run_deterministic_replay(
        requests=requests, evaluator=_side_driven_evaluator
    )
    result_class = DeterministicReplayEventLoop().run(
        requests=requests, evaluator=_side_driven_evaluator
    )
    assert result_facade.replay_signature == result_class.replay_signature
    assert result_facade.determinism_ok == result_class.determinism_ok


# ---------------------------------------------------------------------------
# Boundary / warmup: loop stable with real historical bridge output
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_loop_stable_with_historical_bridge_output() -> None:
    """Smoke test: loop runs without error on a real historical bridge output.

    Uses the actual build_primary_breakout_historical_bridge to produce requests
    and a simple no-signal evaluator to exercise the full loop path.
    """
    from core.replay.historical_bridge import build_primary_breakout_historical_bridge

    # Build minimal valid candle series (> max_lookback=240)
    candles: list[dict] = []
    start_ts = 1_700_000_000_000
    for i in range(245):
        close = 100.0 + i * 0.01
        candles.append(
            {
                "symbol": "BTCUSDT",
                "ts_ms": start_ts + i * 60_000,
                "open": close - 0.01,
                "high": close + 0.02,
                "low": close - 0.02,
                "close": close,
                "volume": 10.0,
                "regime_id": 0,
                "market_state_fresh": True,
                "regime_fresh": True,
            }
        )

    bridge_requests = build_primary_breakout_historical_bridge(candles)
    assert len(bridge_requests) == 5  # 245 - 240 warmup

    result = run_deterministic_replay(
        requests=bridge_requests, evaluator=_no_signal_evaluator
    )
    assert result.processed_count == 5
    assert result.determinism_ok is True
    assert result.market_state_fresh_count == 5
    assert result.regime_fresh_count == 5


@pytest.mark.unit
def test_loop_stable_determinism_with_bridge_and_signal_evaluator() -> None:
    """Two independent replay runs on identical bridge output produce identical signatures."""
    from core.replay.historical_bridge import build_primary_breakout_historical_bridge

    candles: list[dict] = []
    start_ts = 1_700_000_000_000
    for i in range(245):
        close = 100.0 + i * 0.01
        candles.append(
            {
                "symbol": "BTCUSDT",
                "ts_ms": start_ts + i * 60_000,
                "high": close + 0.02,
                "low": close - 0.02,
                "close": close,
                "volume": 10.0,
                "regime_id": 0,
                "market_state_fresh": True,
                "regime_fresh": True,
            }
        )

    bridge_requests = build_primary_breakout_historical_bridge(candles)
    result_a = run_deterministic_replay(
        requests=bridge_requests, evaluator=_no_signal_evaluator
    )
    result_b = run_deterministic_replay(
        requests=bridge_requests, evaluator=_no_signal_evaluator
    )
    assert result_a.replay_signature == result_b.replay_signature
    assert result_a.determinism_ok is True


# ---------------------------------------------------------------------------
# No wall-clock dependency
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_no_wall_clock_in_loop_result() -> None:
    """ReplayLoopResult has no wall-clock fields — all timestamps come from requests."""
    result = run_deterministic_replay(requests=[], evaluator=_no_signal_evaluator)
    d = result.to_dict()
    # Wall-clock fields like 'generated_at', 'created_at', 'run_at' must not appear
    wall_clock_keys = {"generated_at", "created_at", "run_at", "timestamp"}
    assert not (wall_clock_keys & set(d.keys()))
