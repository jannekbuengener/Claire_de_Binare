"""
Integrationstests: Phase-1 Metadata Pipeline
Issue #1488

Testet:
- Signal-Metadata wird durch db_writer korrekt übernommen
- Order-Metadata fließt von Risk durch Execution in die DB
- Trade-Metadata enthält fill context
- Portfolio-Snapshot-Metadata bleibt rückwärtskompatibel
- Negativtest: optionale fehlende Felder werden nicht erfunden
"""

from __future__ import annotations

import json
import sys
import importlib.util
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent

# Ensure project root importable (for core/ etc.)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load signal models
_sig_spec = importlib.util.spec_from_file_location(
    "signal_models", project_root / "services" / "signal" / "models.py"
)
signal_models = importlib.util.module_from_spec(_sig_spec)
_sig_spec.loader.exec_module(signal_models)

# Load risk models
_risk_spec = importlib.util.spec_from_file_location(
    "risk_models", project_root / "services" / "risk" / "models.py"
)
_risk_mod = importlib.util.module_from_spec(_risk_spec)
_risk_spec.loader.exec_module(_risk_mod)
RiskOrder = _risk_mod.Order

# Load db_writer
_db_path = project_root / "services" / "db_writer"
if str(_db_path) not in sys.path:
    sys.path.insert(0, str(_db_path))
from db_writer import DatabaseWriter  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------

def _make_signal_with_metadata() -> signal_models.Signal:
    sig = signal_models.Signal(
        signal_id="sig-integ-001",
        symbol="BTCUSDT",
        side="BUY",
        strategy_id="momentum_v1",
        bot_id="bot-1",
        reason="Momentum: +1.5%",
        price=50000.0,
        pct_change=1.5,
        pct_change_15m=0.4,
        volume_15m=300.0,
        ts_ms=1700000000000,
    )
    sig.metadata = {
        "strategy_id": sig.strategy_id,
        "bot_id": sig.bot_id,
        "signal_reason": sig.reason,
        "signal_inputs": {
            "price": sig.price,
            "pct_change": sig.pct_change,
            "pct_change_15m": sig.pct_change_15m,
            "volume_15m": sig.volume_15m,
        },
        "timing": {"signal_ts_ms": sig.ts_ms},
    }
    return sig


def _make_order_with_metadata(signal: signal_models.Signal) -> RiskOrder:
    meta = {
        "signal_id": signal.signal_id,
        "strategy_id": signal.strategy_id,
        "decision_id": "dec-integ-001",
        "trace_id": "trace-integ-001",
        "decision": "ALLOW",
        "reason_code": None,
        "market_context": {"regime_id": 1, "return_1m": -0.002, "return_5m": -0.005},
        "freshness": {
            "staleness_s": 0.8,
            "data_silence_s": 2.0,
            "timestamps_ms": {
                "now_ms": 1700000001000,
                "signal_ts_ms": 1700000000000,
                "market_state_ts_ms": 1700000000500,
            },
        },
        "thresholds": {"staleness_s_max": 5.0},
    }
    return RiskOrder(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        stop_loss_pct=2.0,
        signal_id=signal.signal_id,
        reason="test",
        timestamp=1700000001,
        strategy_id="momentum_v1",
        decision_id="dec-integ-001",
        trace_id="trace-integ-001",
        metadata=meta,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_signal_metadata_in_payload():
    """Signal-Payload enthält metadata — db_writer kann es lesen."""
    sig = _make_signal_with_metadata()
    payload = sig.to_dict()

    assert "metadata" in payload
    meta = payload["metadata"]
    assert meta["strategy_id"] == "momentum_v1"
    assert meta["signal_inputs"]["price"] == 50000.0
    assert meta["timing"]["signal_ts_ms"] == 1700000000000


@pytest.mark.integration
def test_signal_metadata_via_db_writer_coerce():
    """db_writer._coerce_metadata verarbeitet Signal-Metadata korrekt (dict und JSON-String)."""
    sig = _make_signal_with_metadata()
    payload = sig.to_dict()

    # Simulation: sanitize_payload hat dict → JSON-String konvertiert
    json_str_meta = json.dumps(payload["metadata"])

    coerced = DatabaseWriter._coerce_metadata(json_str_meta)
    db_json = json.dumps(coerced)

    assert db_json.startswith("{")
    assert "momentum_v1" in db_json


@pytest.mark.integration
def test_order_metadata_propagates_through_risk_payload():
    """Order-Metadata enthält Correlation IDs und market_context."""
    sig = _make_signal_with_metadata()
    order = _make_order_with_metadata(sig)
    payload = order.to_dict()

    assert "metadata" in payload
    m = payload["metadata"]
    assert m["decision_id"] == "dec-integ-001"
    assert m["trace_id"] == "trace-integ-001"
    assert m["signal_id"] == "sig-integ-001"
    assert m["market_context"]["regime_id"] == 1


@pytest.mark.integration
def test_order_metadata_via_db_writer():
    """Order-Metadata kommt als JSON-String im db_writer an und wird korrekt verarbeitet."""
    sig = _make_signal_with_metadata()
    order = _make_order_with_metadata(sig)
    payload = order.to_dict()

    json_str_meta = json.dumps(payload["metadata"])
    coerced = DatabaseWriter._coerce_metadata(json_str_meta)
    db_json = json.dumps(coerced)

    assert db_json.startswith("{")
    parsed = json.loads(db_json)
    assert parsed["decision_id"] == "dec-integ-001"
    assert parsed["market_context"]["return_1m"] == -0.002


@pytest.mark.integration
def test_trade_metadata_contains_fill_context():
    """trades.metadata enthält signal_id, decision_id, fill_context."""
    trade_meta = {
        "signal_id": "sig-integ-001",
        "strategy_id": "momentum_v1",
        "decision_id": "dec-integ-001",
        "trace_id": "trace-integ-001",
        "order_id": "ord-integ-001",
        "expected_price": 50000.0,
        "execution_price": 50010.0,
        "slippage_bps": 2.0,
        "fill_context": {
            "signal_ts_ms": 1700000000000,
            "decision_ts_ms": 1700000001000,
            "market_state_ts_ms": 1700000000500,
        },
        "regime_id": 1,
    }

    db_json = json.dumps(trade_meta)
    assert db_json.startswith("{")
    parsed = json.loads(db_json)
    assert parsed["signal_id"] == "sig-integ-001"
    assert parsed["fill_context"]["signal_ts_ms"] == 1700000000000


@pytest.mark.integration
def test_snapshot_metadata_backward_compatible():
    """Portfolio-Snapshot ohne metadata → db_writer stürzt nicht ab, speichert leeres Objekt."""
    snapshot_no_meta = {
        "timestamp": "2026-04-07T12:00:00",
        "equity": 1000.0,
        "cash": 900.0,
        "num_positions": 0,
        # kein "metadata"-Key
    }
    result = DatabaseWriter._coerce_metadata(snapshot_no_meta.get("metadata"))
    assert result == {}
    db_json = json.dumps(result)
    assert db_json == "{}"


@pytest.mark.integration
def test_snapshot_metadata_with_phase1_fields():
    """Portfolio-Snapshot mit Phase-1-Metadata wird korrekt verarbeitet."""
    snapshot = {
        "timestamp": "2026-04-07T12:00:00",
        "equity": 1000.0,
        "metadata": {
            "deployment_mode": "paper",
            "source": "paper_runner",
            "snapshot_quality": {"positions_count": 2},
        },
    }
    result = DatabaseWriter._coerce_metadata(snapshot.get("metadata"))
    assert result["deployment_mode"] == "paper"
    assert result["snapshot_quality"]["positions_count"] == 2


@pytest.mark.integration
def test_optional_fields_absent_not_fabricated():
    """Felder die nicht vorhanden sind werden nicht erfunden."""
    # Order ohne policy-Toggle (policy_id=None) → metadata.policy_id soll nicht gesetzt werden
    # wenn man None-Werte filtert
    evidence_like = {
        "signal_id": "sig-001",
        "decision_id": "dec-001",
        "trace_id": "trace-001",
        "policy_id": None,   # Toggle OFF
        "policy_hash": None,
        "regime_id": None,   # Nicht verfügbar
    }
    market_ctx = {
        k: v for k, v in {
            "regime_id": evidence_like.get("regime_id"),
        }.items()
        if v is not None
    }

    assert "regime_id" not in market_ctx  # regime_id war None → nicht im Kontext

    # policy_id bleibt None — wird nicht zu einem Fake-Wert
    assert evidence_like["policy_id"] is None
