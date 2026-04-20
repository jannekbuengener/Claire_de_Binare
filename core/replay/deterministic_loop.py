"""Deterministic replay event loop with explicit state and two-pass signature check.

This module provides a narrow, pure-function-oriented replay event loop for
deterministic evaluation of historical strategy requests. It:

  - accepts a deterministically ordered sequence of StrategyAdapterRequest
  - accepts an evaluator callback (strategy-agnostic)
  - threads explicit loop state through each evaluation step
  - collects serialized responses as a canonical replay signature
  - performs a first pass and a clean second pass
  - compares signatures to validate determinism
  - returns an immutable ReplayLoopResult (in-memory only)

Design rules:
  - No I/O, no file writes, no Redis, no network calls
  - No wall-clock dependency
  - Request ordering is deterministic and stable (caller's responsibility)
  - Signature comparison uses canonical_hash, not repr() or object identity
  - State is explicit: no hidden side-effects via callback closures
  - The loop does not implement execution simulation or risk evaluation

Governance: Issue #1803 (LR-021 Deterministic Replay Event Loop)

relations:
  role: deterministic_replay_event_loop
  domain: replay
  upstream:
    - core.replay.canonical_json
    - core.contracts.external_adapter_contracts
  downstream:
    - core.replay.execution  (optional: #1802 wrapper may be supplied as evaluator)
    - services.validation.strategy_backtest_runner (structural reference)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from core.contracts.external_adapter_contracts import (
    StrategyAdapterRequest,
    StrategyAdapterResponse,
)
from core.replay.canonical_json import canonical_hash

# ---------------------------------------------------------------------------
# Evaluator callback type
# ---------------------------------------------------------------------------

EvaluatorCallbackT = Callable[
    [StrategyAdapterRequest, bool, Optional[int]],
    Tuple[StrategyAdapterResponse, Optional[int]],
]
"""Type alias for replay evaluator callbacks.

Signature: (request, position_open, last_entry_ts_ms) -> (response, next_last_entry_ts_ms)

  - request: current StrategyAdapterRequest
  - position_open: current position state from loop state
  - last_entry_ts_ms: last recorded entry timestamp (None if no entry yet)
  - response: StrategyAdapterResponse with zero or more signal candidates
  - next_last_entry_ts_ms: updated last entry timestamp (or the incoming value unchanged)
"""


# ---------------------------------------------------------------------------
# Internal pass state (mutable accumulator, not exposed)
# ---------------------------------------------------------------------------

@dataclass
class _PassState:
    """Mutable accumulator for a single replay pass.

    Internal only — not part of the public API. Tracks all state that changes
    across requests in one pass through the full request sequence.
    """

    position_open: bool = False
    last_entry_ts_ms: Optional[int] = None
    processed_request_index: int = 0
    cumulative_signals: List[Dict[str, Any]] = field(default_factory=list)
    replay_responses: List[Dict[str, Any]] = field(default_factory=list)
    market_state_fresh_count: int = 0
    regime_fresh_count: int = 0


# ---------------------------------------------------------------------------
# Public result dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ReplayLoopResult:
    """Immutable result of a DeterministicReplayEventLoop run.

    Captures final state from the first pass, together with the determinism
    verdict from comparing the first-pass and second-pass canonical signatures.

    Attributes:
        processed_count: Number of requests processed (first pass).
        signal_count: Total signals emitted during first pass.
        market_state_fresh_count: Requests with market_state_fresh=True (first pass).
        regime_fresh_count: Requests with regime_fresh=True (first pass).
        replay_signature: Canonical SHA-256 hash of all serialized first-pass responses.
        determinism_ok: True if first-pass and second-pass signatures are equal.
        position_open: Final position state after first pass.
        last_entry_ts_ms: Last recorded entry timestamp after first pass (None if no entry).
    """

    processed_count: int
    signal_count: int
    market_state_fresh_count: int
    regime_fresh_count: int
    replay_signature: str
    determinism_ok: bool
    position_open: bool
    last_entry_ts_ms: Optional[int]

    def to_dict(self) -> dict:
        """Convert to dict, omitting None-valued optional fields."""
        result: dict = {
            "processed_count": self.processed_count,
            "signal_count": self.signal_count,
            "market_state_fresh_count": self.market_state_fresh_count,
            "regime_fresh_count": self.regime_fresh_count,
            "replay_signature": self.replay_signature,
            "determinism_ok": self.determinism_ok,
            "position_open": self.position_open,
        }
        if self.last_entry_ts_ms is not None:
            result["last_entry_ts_ms"] = self.last_entry_ts_ms
        return result


# ---------------------------------------------------------------------------
# Pure serialization and signature helpers
# ---------------------------------------------------------------------------

def _serialize_response(response: StrategyAdapterResponse) -> Dict[str, Any]:
    """Serialize a StrategyAdapterResponse to a canonical-safe dict.

    Mirrors strategy_backtest_runner._serialize_response for structural
    consistency. Suitable for canonical_hash input.

    Args:
        response: Strategy adapter output from one evaluation step.

    Returns:
        Dict with ``signals`` list and ``diagnostics`` dict.
    """
    return {
        "signals": [
            {
                "strategy_id": s.strategy_id,
                "symbol": s.symbol,
                "side": s.side,
                "reason": s.reason,
                "price": s.price,
                "metadata": dict(s.metadata or {}),
            }
            for s in response.signals
        ],
        "diagnostics": dict(response.diagnostics or {}),
    }


def _compute_signature(responses: List[Dict[str, Any]]) -> str:
    """Compute a deterministic canonical signature over a response list.

    Uses canonical_hash (sorted-key JSON + SHA-256). Identical response
    sequences always produce identical 64-char hex signatures, regardless
    of Python object identity or memory address.

    Args:
        responses: List of _serialize_response() outputs for a full pass.

    Returns:
        64-character lowercase SHA-256 hex string.
    """
    return canonical_hash({"responses": responses})


def _extract_freshness_flags(request: StrategyAdapterRequest) -> Tuple[bool, bool]:
    """Extract market_state_fresh / regime_fresh flags from a request.

    Reads from ``request.market_event["market_state"]`` when present.
    Missing or non-Mapping market_state → both flags default to False.

    Args:
        request: StrategyAdapterRequest from the historical bridge.

    Returns:
        (market_state_fresh, regime_fresh) as booleans.
    """
    market_state = request.market_event.get("market_state")
    if not isinstance(market_state, Mapping):
        return False, False
    return (
        bool(market_state.get("market_state_fresh", False)),
        bool(market_state.get("regime_fresh", False)),
    )


# ---------------------------------------------------------------------------
# Inner loop: single pass
# ---------------------------------------------------------------------------

def _run_single_pass(
    requests: Sequence[StrategyAdapterRequest],
    evaluator: EvaluatorCallbackT,
    *,
    initial_position_open: bool,
    initial_last_entry_ts_ms: Optional[int],
) -> _PassState:
    """Execute one full pass over a request sequence, accumulating state.

    The pass is stateless with respect to external systems: no I/O, no wall-clock.
    State transitions are driven exclusively by evaluator outputs and explicit
    initial state.

    BUY signals set position_open=True; SELL signals set position_open=False.
    The evaluator is responsible for returning the updated last_entry_ts_ms.

    Args:
        requests: Deterministically ordered StrategyAdapterRequest sequence.
        evaluator: Callback: (request, position_open, last_entry_ts_ms) ->
            (StrategyAdapterResponse, Optional[int]).
        initial_position_open: Whether a position is open at pass start.
        initial_last_entry_ts_ms: Last known entry timestamp at pass start.

    Returns:
        Populated _PassState after processing all requests.
    """
    state = _PassState(
        position_open=initial_position_open,
        last_entry_ts_ms=initial_last_entry_ts_ms,
    )

    for idx, request in enumerate(requests):
        ms_fresh, reg_fresh = _extract_freshness_flags(request)
        state.market_state_fresh_count += int(ms_fresh)
        state.regime_fresh_count += int(reg_fresh)

        response, next_last_entry_ts_ms = evaluator(
            request,
            state.position_open,
            state.last_entry_ts_ms,
        )
        state.last_entry_ts_ms = next_last_entry_ts_ms
        state.replay_responses.append(_serialize_response(response))
        state.processed_request_index = idx + 1

        for signal in response.signals:
            side = signal.side.upper()
            state.cumulative_signals.append(
                {
                    "idx": idx,
                    "side": side,
                    "symbol": signal.symbol,
                    "reason": signal.reason,
                }
            )
            if side == "BUY":
                state.position_open = True
            elif side == "SELL":
                state.position_open = False

    return state


# ---------------------------------------------------------------------------
# Main loop class
# ---------------------------------------------------------------------------

class DeterministicReplayEventLoop:
    """Deterministic replay event loop with explicit state and two-pass signature check.

    Usage::

        loop = DeterministicReplayEventLoop()
        result = loop.run(requests=adapter_requests, evaluator=my_evaluator)
        assert result.determinism_ok
        print(result.replay_signature)  # 64-char SHA-256 hex

    The loop performs:
    1. First pass: evaluates full request sequence, collects replay signature.
    2. Second pass: evaluates same sequence from (same or different) initial state.
    3. Compares canonical signatures → determinism_ok.

    The second pass uses the same initial state as the first pass by default,
    giving a clean determinism proof. You can inject a different initial state
    for the second pass to test determinism sensitivity to initial conditions.
    """

    def run(
        self,
        requests: Sequence[StrategyAdapterRequest],
        evaluator: EvaluatorCallbackT,
        *,
        initial_position_open: bool = False,
        initial_last_entry_ts_ms: Optional[int] = None,
        second_pass_initial_position_open: Optional[bool] = None,
        second_pass_initial_last_entry_ts_ms: Optional[int] = None,
    ) -> ReplayLoopResult:
        """Run two passes and return a determinism-validated result.

        The returned ReplayLoopResult reflects first-pass state and metrics.
        determinism_ok=True iff first-pass and second-pass canonical signatures match.

        Args:
            requests: Deterministically ordered StrategyAdapterRequest sequence.
            evaluator: Callback with signature compatible with EvaluatorCallbackT.
            initial_position_open: Initial position state for first pass. Default False.
            initial_last_entry_ts_ms: Initial last-entry ts_ms for first pass. Default None.
            second_pass_initial_position_open: Initial position for second pass.
                Defaults to ``initial_position_open``. Supply a different value to
                demonstrate determinism sensitivity to initial state.
            second_pass_initial_last_entry_ts_ms: Initial last-entry ts_ms for second pass.
                Defaults to ``initial_last_entry_ts_ms``.

        Returns:
            ReplayLoopResult with determinism_ok=True iff both passes match.
        """
        first_pass = _run_single_pass(
            requests=requests,
            evaluator=evaluator,
            initial_position_open=initial_position_open,
            initial_last_entry_ts_ms=initial_last_entry_ts_ms,
        )
        first_signature = _compute_signature(first_pass.replay_responses)

        second_pos_open = (
            initial_position_open
            if second_pass_initial_position_open is None
            else second_pass_initial_position_open
        )
        second_last_entry = (
            initial_last_entry_ts_ms
            if second_pass_initial_last_entry_ts_ms is None
            else second_pass_initial_last_entry_ts_ms
        )

        second_pass = _run_single_pass(
            requests=requests,
            evaluator=evaluator,
            initial_position_open=second_pos_open,
            initial_last_entry_ts_ms=second_last_entry,
        )
        second_signature = _compute_signature(second_pass.replay_responses)

        return ReplayLoopResult(
            processed_count=first_pass.processed_request_index,
            signal_count=len(first_pass.cumulative_signals),
            market_state_fresh_count=first_pass.market_state_fresh_count,
            regime_fresh_count=first_pass.regime_fresh_count,
            replay_signature=first_signature,
            determinism_ok=(first_signature == second_signature),
            position_open=first_pass.position_open,
            last_entry_ts_ms=first_pass.last_entry_ts_ms,
        )


# ---------------------------------------------------------------------------
# Convenience facade
# ---------------------------------------------------------------------------

def run_deterministic_replay(
    requests: Sequence[StrategyAdapterRequest],
    evaluator: EvaluatorCallbackT,
    *,
    initial_position_open: bool = False,
    initial_last_entry_ts_ms: Optional[int] = None,
) -> ReplayLoopResult:
    """Convenience facade: run a deterministic replay from clean initial state.

    Equivalent to ``DeterministicReplayEventLoop().run(requests, evaluator)``.
    Performs a two-pass determinism check. Both passes start from the same
    initial state.

    Args:
        requests: Deterministically ordered StrategyAdapterRequest sequence.
        evaluator: Evaluator callback (EvaluatorCallbackT).
        initial_position_open: Initial position state. Default False.
        initial_last_entry_ts_ms: Initial last-entry timestamp. Default None.

    Returns:
        ReplayLoopResult. Check determinism_ok before trusting the signature.
    """
    return DeterministicReplayEventLoop().run(
        requests=requests,
        evaluator=evaluator,
        initial_position_open=initial_position_open,
        initial_last_entry_ts_ms=initial_last_entry_ts_ms,
    )
