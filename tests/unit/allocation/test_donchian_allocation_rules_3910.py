"""Donchian allocation rules contract tests (#3910)."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("ALLOCATION_REGIME_MIN_STABLE_SECONDS", "60")
os.environ.setdefault(
    "ALLOCATION_RULES_JSON",
    json.dumps(
        {
            "paper": {
                "STEADY_BULLISH": 0.3,
                "TREND": 0.3,
                "VOLATILE_RANGE": 0.1,
                "RANGE": 0.1,
                "HIGH_VOL_CHAOTIC": 0.02,
                "UNKNOWN": 0.0,
            },
            "primary_breakout_v1": {
                "STEADY_BULLISH": 0.3,
                "TREND": 0.3,
                "VOLATILE_RANGE": 0.1,
                "RANGE": 0.1,
                "HIGH_VOL_CHAOTIC": 0.02,
                "UNKNOWN": 0.0,
            },
        }
    ),
)

import pytest
from unittest.mock import MagicMock, patch

from services.allocation.config import AllocationConfig
from services.allocation.service import AllocationService
from services.allocation.service import AllocationState as AllocationServiceState
from services.risk.service import AllocationState as RiskAllocationState
from services.risk.service import RiskManager

pytestmark = [pytest.mark.unit, pytest.mark.contract]

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_BLUE = REPO_ROOT / "infrastructure" / "compose" / "compose.blue.yml"

CANONICAL_PB1_RULES = {
    "STEADY_BULLISH": 0.3,
    "TREND": 0.3,
    "VOLATILE_RANGE": 0.1,
    "RANGE": 0.1,
    "HIGH_VOL_CHAOTIC": 0.02,
    "UNKNOWN": 0.0,
}

DONCHIAN_RULES = {
    "STEADY_BULLISH": 0.15,
    "TREND": 0.15,
    "VOLATILE_RANGE": 0.05,
    "RANGE": 0.05,
    "HIGH_VOL_CHAOTIC": 0.01,
    "UNKNOWN": 0.0,
}

PAPER_RULES = dict(CANONICAL_PB1_RULES)


def _natural_paper_rules() -> dict:
    return {
        "paper": PAPER_RULES,
        "primary_breakout_v1": dict(CANONICAL_PB1_RULES),
        "donchian_breakout_v1": dict(DONCHIAN_RULES),
    }


def _allocation_service(rules: dict | None = None) -> AllocationService:
    config = AllocationConfig(rules=rules or _natural_paper_rules(), regime_min_stable_seconds=60)
    service = AllocationService.__new__(AllocationService)
    service.config = config
    service.allocations = defaultdict(AllocationServiceState)
    service.shutdown_strategy_ids = set()
    service.trades = {}
    service.positions = {}
    service.current_regime = "UNKNOWN"
    service.redis_client = MagicMock()
    return service


def _extract_allocation_rules_json(compose_text: str) -> dict:
    match = re.search(r"ALLOCATION_RULES_JSON:\s*'(\{.*\})'", compose_text)
    assert match, "ALLOCATION_RULES_JSON not found in compose.blue.yml"
    return json.loads(match.group(1))


def test_compose_blue_includes_donchian_and_leaves_pb1_unchanged() -> None:
    rules = _extract_allocation_rules_json(COMPOSE_BLUE.read_text(encoding="utf-8"))
    assert rules["primary_breakout_v1"] == CANONICAL_PB1_RULES
    assert rules["donchian_breakout_v1"] == DONCHIAN_RULES


def test_donchian_emits_non_zero_allocation_under_allowed_regime() -> None:
    rules = {"donchian_breakout_v1": dict(DONCHIAN_RULES)}
    service = _allocation_service(rules=rules)
    service.current_regime = "TREND"
    with (
        patch.object(service, "_compute_performance", return_value=(0.5, True)),
        patch("services.allocation.service.median", return_value=0.0),
    ):
        service._recompute_allocations(ts=1_700_000_000)
    assert service.allocations["donchian_breakout_v1"].allocation_pct == 0.15


def test_donchian_fail_closed_on_unknown_regime() -> None:
    service = _allocation_service()
    service.current_regime = "UNKNOWN"
    with patch.object(service, "_compute_performance", return_value=(0.5, True)):
        service._recompute_allocations(ts=1_700_000_000)
    assert service.allocations["donchian_breakout_v1"].allocation_pct == 0.0


def test_donchian_missing_rule_fail_closed() -> None:
    rules = _natural_paper_rules()
    del rules["donchian_breakout_v1"]
    service = _allocation_service(rules=rules)
    service.current_regime = "TREND"
    with patch.object(service, "_compute_performance", return_value=(0.5, True)):
        service._recompute_allocations(ts=1_700_000_000)
    assert "donchian_breakout_v1" not in service.allocations


def test_risk_allocation_allowed_passes_for_donchian_when_pct_positive() -> None:
    manager = RiskManager()
    manager.allocation_state["donchian_breakout_v1"] = RiskAllocationState(
        allocation_pct=0.15, cooldown_until=None
    )
    allowed, reason = manager._allocation_allowed("donchian_breakout_v1")
    assert allowed is True
    assert "allokation ok" in reason.lower()


def test_risk_allocation_allowed_blocks_donchian_when_pct_zero() -> None:
    manager = RiskManager()
    allowed, reason = manager._allocation_allowed("donchian_breakout_v1")
    assert allowed is False
    assert "keine allokation" in reason.lower()


def test_pb1_rules_unchanged_in_recompute() -> None:
    rules = {"primary_breakout_v1": dict(CANONICAL_PB1_RULES)}
    service = _allocation_service(rules=rules)
    service.current_regime = "TREND"
    with (
        patch.object(service, "_compute_performance", return_value=(0.5, True)),
        patch("services.allocation.service.median", return_value=0.0),
    ):
        service._recompute_allocations(ts=1_700_000_000)
    assert service.allocations["primary_breakout_v1"].allocation_pct == 0.3


def test_compose_docstring_has_no_live_go_claim() -> None:
    compose_text = COMPOSE_BLUE.read_text(encoding="utf-8").lower()
    assert "live-go" not in compose_text
    assert "echtgeld" not in compose_text
