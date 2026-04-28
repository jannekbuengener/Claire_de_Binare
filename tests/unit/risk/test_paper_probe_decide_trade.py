"""
Unit-Tests fuer decide_trade() Paper Evidence Probe Bypasses.

Verifies:
- Probe OFF: RC_001/010/020/021 block as normal
- Probe ON:  RC_001/010/020/021 allow through
- Probe ON:  RC_002/003/004 still enforce (never bypassed)
- Probe ON:  threshold limits still enforce (values too high still block)

Governance: Issue #2141 / Phase 3
"""

import importlib
import sys
from pathlib import Path

import pytest

# Ensure repo root is on sys.path
repo_root = Path(__file__).resolve().parents[3]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

risk_service = importlib.import_module("services.risk.service")
decide_trade = risk_service.decide_trade

DECISION_ALLOW = risk_service.DECISION_ALLOW
DECISION_BLOCK = risk_service.DECISION_BLOCK

# Reason-code constants
RC_001 = "RC_001"
RC_002 = "RC_002"
RC_003 = "RC_003"
RC_004 = "RC_004"
RC_010 = "RC_010"
RC_020 = "RC_020"
RC_021 = "RC_021"

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW_MS = 1_700_000_000_000  # Fixed reference timestamp


@pytest.fixture
def probe_on(monkeypatch):
    """Activate the paper evidence probe (both guards)."""
    monkeypatch.setenv("PAPER_EVIDENCE_PROBE_MODE", "1")
    monkeypatch.setenv("MOCK_TRADING", "true")


@pytest.fixture
def probe_off(monkeypatch):
    """Ensure the paper evidence probe is OFF (default)."""
    monkeypatch.delenv("PAPER_EVIDENCE_PROBE_MODE", raising=False)
    monkeypatch.delenv("MOCK_TRADING", raising=False)


def _base_signal(now_ms=NOW_MS, pct_change_15m=0.5, volume_15m=0.01):
    """Minimal signal dict — values intentionally below RC_010 thresholds."""
    return {
        "signal_id": "sig-probe-test-001",
        "symbol": "BTCUSDT",
        "pct_change_15m": pct_change_15m,
        "volume_15m": volume_15m,
        "ts_ms": now_ms - 500,
    }


def _base_market_state(now_ms=NOW_MS, regime_id=2):
    """Market state with regime=2 (HIGH_VOL_CHAOTIC) and healthy return/price values."""
    return {
        "regime_id": regime_id,
        "return_1m": 0.3,
        "return_5m": 0.5,
        "price_change_5m": 0.5,
        "ts_ms": now_ms - 500,
        "last_tick_ts_ms": now_ms - 500,
    }


# ---------------------------------------------------------------------------
# Probe OFF — baseline blocking behaviour unchanged
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDecideTradeProbeOff:
    def test_rc001_blocks_when_regime_2(self, probe_off):
        """RC_001: regime=2 blocks when probe is OFF."""
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=2),
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_BLOCK
        assert reason == RC_001

    def test_rc001_blocks_when_regime_3(self, probe_off):
        """RC_001: regime=3 blocks when probe is OFF."""
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=3),
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_BLOCK
        assert reason == RC_001


# ---------------------------------------------------------------------------
# Probe ON — RC_001 bypassed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDecideTradeProbeOnRegime:
    def test_probe_bypasses_rc001_regime_2(self, probe_on):
        """Probe ON: regime=2 does not produce RC_001 block."""
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=2),
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        # RC_001 is bypassed; chain proceeds to ALLOW (RC_020/021 defaulted to 0.0)
        assert decision == DECISION_ALLOW
        assert reason is None

    def test_probe_bypasses_rc001_regime_3(self, probe_on):
        """Probe ON: regime=3 does not produce RC_001 block."""
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=3),
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_ALLOW
        assert reason is None


# ---------------------------------------------------------------------------
# Probe ON — RC_010 bypassed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDecideTradeProbeOnSignal:
    def test_probe_bypasses_rc010_low_pct_change(self, probe_on):
        """Probe ON: pct_change_15m below threshold does not produce RC_010 block."""
        decision, reason, _ = decide_trade(
            signal=_base_signal(pct_change_15m=0.001),  # << 3.0 threshold
            market_state=_base_market_state(regime_id=0),  # regime OK
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_ALLOW
        assert reason is None

    def test_probe_bypasses_rc010_low_volume(self, probe_on):
        """Probe ON: volume_15m below threshold does not produce RC_010 block."""
        decision, reason, _ = decide_trade(
            signal=_base_signal(volume_15m=0.0001),  # << 0.165 threshold
            market_state=_base_market_state(regime_id=0),
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_ALLOW
        assert reason is None


# ---------------------------------------------------------------------------
# Probe ON — RC_020/021 None defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDecideTradeProbeOnAccountState:
    def test_probe_defaults_daily_drawdown_none(self, probe_on):
        """Probe ON: daily_drawdown_pct=None is defaulted to 0.0, not blocked."""
        # account_state=None → daily_drawdown_pct=None → defaulted to 0.0 in probe
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=2),
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_ALLOW
        assert reason is None

    def test_probe_defaults_total_exposure_none(self, probe_on):
        """Probe ON: total_exposure_pct=None is defaulted to 0.0, not blocked."""
        account_state = {
            "daily_drawdown_pct": 0.5,
            "total_exposure_pct": None,  # explicitly None
            "ts_ms": NOW_MS - 500,
        }
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=2),
            account_state=account_state,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_ALLOW
        assert reason is None


# ---------------------------------------------------------------------------
# Probe ON — safety/freshness gates still enforced
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDecideTradeProbeOnSafetyGatesStillEnforced:
    def test_rc002_still_blocks_when_return_1m_none(self, probe_on):
        """RC_002 is never bypassed: return_1m=None still blocks."""
        market_state = _base_market_state(regime_id=2)
        market_state["return_1m"] = None
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=market_state,
            account_state=None,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_BLOCK
        assert reason == RC_002

    def test_rc003_still_blocks_when_staleness_exceeded(self, probe_on):
        """RC_003 is never bypassed: stale signal still blocks."""
        stale_now_ms = NOW_MS + 10_000  # signal is 10s old, limit is 5s
        decision, reason, _ = decide_trade(
            signal=_base_signal(now_ms=NOW_MS),
            market_state=_base_market_state(regime_id=2, now_ms=NOW_MS),
            account_state=None,
            market_health=None,
            now_ms=stale_now_ms,
        )
        assert decision == DECISION_BLOCK
        assert reason == RC_003

    def test_rc020_limit_still_enforced(self, probe_on):
        """RC_020 limit still blocks when daily_drawdown_pct >= 5%."""
        account_state = {
            "daily_drawdown_pct": 6.0,  # > 5.0 threshold
            "total_exposure_pct": 10.0,
            "ts_ms": NOW_MS - 500,
        }
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=2),
            account_state=account_state,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_BLOCK
        assert reason == RC_020

    def test_rc021_limit_still_enforced(self, probe_on):
        """RC_021 limit still blocks when total_exposure_pct >= 50%."""
        account_state = {
            "daily_drawdown_pct": 1.0,
            "total_exposure_pct": 55.0,  # > 50.0 threshold
            "ts_ms": NOW_MS - 500,
        }
        decision, reason, _ = decide_trade(
            signal=_base_signal(),
            market_state=_base_market_state(regime_id=2),
            account_state=account_state,
            market_health=None,
            now_ms=NOW_MS,
        )
        assert decision == DECISION_BLOCK
        assert reason == RC_021
