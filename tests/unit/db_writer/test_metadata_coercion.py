"""
Unit-Tests: DB-Writer _coerce_metadata Helper
Issue #1488
"""

import json
import sys
from pathlib import Path

import pytest

services_db = Path(__file__).parent.parent.parent.parent / "services" / "db_writer"
if str(services_db) not in sys.path:
    sys.path.insert(0, str(services_db))

from db_writer import DatabaseWriter  # noqa: E402


@pytest.mark.unit
def test_coerce_metadata_dict():
    """dict-Metadata direkt zurückgegeben."""
    raw = {"decision": "ALLOW", "signal_id": "sig-abc"}
    result = DatabaseWriter._coerce_metadata(raw)
    assert result == raw


@pytest.mark.unit
def test_coerce_metadata_json_string():
    """JSON-String wird zu dict geparst."""
    raw = json.dumps({"strategy_id": "mom", "regime_id": 1})
    result = DatabaseWriter._coerce_metadata(raw)
    assert result == {"strategy_id": "mom", "regime_id": 1}


@pytest.mark.unit
def test_coerce_metadata_invalid_string():
    """Ungültiger JSON-String → leeres dict, kein Crash."""
    result = DatabaseWriter._coerce_metadata("not-json{}")
    assert result == {}


@pytest.mark.unit
def test_coerce_metadata_none():
    """None → leeres dict."""
    result = DatabaseWriter._coerce_metadata(None)
    assert result == {}


@pytest.mark.unit
def test_coerce_metadata_json_array_string():
    """JSON-Array-String (kein Objekt) → leeres dict."""
    result = DatabaseWriter._coerce_metadata(json.dumps([1, 2, 3]))
    assert result == {}


@pytest.mark.unit
def test_coerce_metadata_no_double_encoding():
    """json.dumps(_coerce_metadata(json_string)) erzeugt kein quoted JSON in JSONB.

    Stellt sicher: das Ergebnis ist ein valides JSONB-Objekt, kein escaped String.
    """
    original = {"strategy_id": "mom", "decision": "ALLOW"}
    json_string = json.dumps(original)  # Wie sanitize_payload es für Redis serialisiert

    coerced = DatabaseWriter._coerce_metadata(json_string)
    db_value = json.dumps(coerced)

    # Kein quoted JSON: db_value darf nicht mit '"' beginnen
    assert db_value.startswith("{"), f"Quoted JSON in JSONB: {db_value[:50]}"
    parsed_back = json.loads(db_value)
    assert isinstance(parsed_back, dict)
    assert parsed_back["strategy_id"] == "mom"
