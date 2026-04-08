"""
Unit-Tests: Redis/Payload-Roundtrip für Phase-1 Metadata
Issue #1488

Stellt sicher:
- metadata als dict geht raus
- unterwegs ggf. als JSON-String (sanitize_payload)
- im Consumer wieder korrekt als Objekt
- kein quoted JSON in JSONB
"""

import json
import sys
from pathlib import Path

import pytest

# Paths for signal and db_writer
signal_path = Path(__file__).parent.parent / "services" / "signal"
db_writer_path = Path(__file__).parent.parent / "services" / "db_writer"
for p in (signal_path, db_writer_path):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from models import Signal  # signal service models  # noqa: E402
from db_writer import DatabaseWriter  # noqa: E402

try:
    from core.utils.redis_payload import sanitize_payload
except ImportError:
    core_path = Path(__file__).parent.parent / "core"
    sys.path.insert(0, str(core_path.parent))
    from core.utils.redis_payload import sanitize_payload


@pytest.mark.unit
def test_metadata_roundtrip_dict_to_db():
    """metadata als dict → sanitize_payload → _coerce_metadata → json.dumps → kein quoted JSON."""
    sig = Signal(
        signal_id="sig-abc",
        symbol="BTCUSDT",
        side="BUY",
        strategy_id="mom",
        ts_ms=1700000000000,
        price=50000.0,
    )
    sig.metadata = {
        "strategy_id": "mom",
        "signal_inputs": {"price": 50000.0},
        "timing": {"signal_ts_ms": 1700000000000},
    }

    # Schritt 1: to_dict() → metadata ist raw dict
    raw_payload = sig.to_dict()
    assert isinstance(raw_payload["metadata"], dict)

    # Schritt 2: sanitize_payload serialisiert dict zu JSON-String (wie Redis XADD)
    sanitized = sanitize_payload(raw_payload)
    assert isinstance(sanitized["metadata"], str)

    # Schritt 3: Consumer (db_writer) bekommt JSON-decodierten Wert
    # Simulation: pubsub liefert json.loads(json.dumps(sanitized))
    pubsub_payload = json.loads(json.dumps(sanitized))
    # nach json.dumps+loads ist sanitized["metadata"] wieder ein String

    # Schritt 4: _coerce_metadata parst ihn zu dict
    coerced = DatabaseWriter._coerce_metadata(pubsub_payload.get("metadata"))
    assert isinstance(coerced, dict)
    assert coerced["strategy_id"] == "mom"

    # Schritt 5: json.dumps für JSONB — kein quoted JSON
    db_value = json.dumps(coerced)
    assert db_value.startswith("{"), f"Quoted JSON in JSONB: {db_value[:60]}"


@pytest.mark.unit
def test_metadata_roundtrip_via_json_string():
    """metadata als dict → json.dumps (Redis XADD) → _coerce_metadata → JSONB korrekt."""
    original_meta = {"decision": "ALLOW", "signal_id": "sig-xyz"}

    # Schritt 1: sanitize_payload konvertiert dict zu JSON-String
    as_json_string = json.dumps(original_meta)

    # Schritt 2: Consumer parst
    result = DatabaseWriter._coerce_metadata(as_json_string)
    assert result == original_meta

    # Schritt 3: JSONB-Wert ist korrekt
    db_value = json.dumps(result)
    assert db_value.startswith("{")
    assert "ALLOW" in db_value


@pytest.mark.unit
def test_metadata_no_double_encoding():
    """metadata wird nicht doppelt serialisiert wenn es als JSON-String ankommt."""
    meta_dict = {"strategy_id": "mom", "regime_id": 1}
    json_str = json.dumps(meta_dict)  # Wie es aus Redis stream kommt

    # Wenn jemand naiv json.dumps(json_str) täte, wäre das ein quoted JSON-String
    naive_result = json.dumps(json_str)
    assert naive_result.startswith('"'), "Kontrolle: naive double-encode erzeugt quoted string"

    # Mit _coerce_metadata passiert das nicht
    coerced = DatabaseWriter._coerce_metadata(json_str)
    safe_result = json.dumps(coerced)
    assert safe_result.startswith("{"), "Kein double-encoding mit _coerce_metadata"
    assert json.loads(safe_result)["regime_id"] == 1
