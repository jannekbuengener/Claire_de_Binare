from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from jsonschema import ValidationError, validate

from core.replay.emitter import _build_envelope
from core.replay.time import created_at_from_ts_ms

SCHEMA_PATH = Path("core/replay/contracts/envelope_v1.schema.json")
SCHEMA: Dict[str, Any] = json.loads(SCHEMA_PATH.read_text())


def make_sample_envelope(
    *, event_type: str, ts_ms: int = 1700000000000, **kwargs: Any
) -> Dict[str, Any]:
    base = {
        "event_id": "env-001",
        "ts_ms": ts_ms,
        "payload": {"decision": "ALLOW"},
    }
    return _build_envelope(event_type=event_type, **base, **kwargs)


def test_schema_accepts_decision_envelope():
    env = make_sample_envelope(
        event_type="DECISION",
        decision_context={"inputs": {"symbol": "BTCUSDT"}},
        signal_id="sig-001",
    )
    validate(env, SCHEMA)


def test_optional_fields_omitted_when_none():
    env = make_sample_envelope(event_type="ORDER")
    assert "correlation_id" not in env
    assert "trace_id" not in env


def test_schema_catches_missing_created_at():
    env = make_sample_envelope(event_type="ORDER")
    env.pop("created_at")
    with pytest.raises(ValidationError):
        validate(env, SCHEMA)


def test_schema_detects_invalid_event_type():
    env = make_sample_envelope(event_type="DECISION")
    env["event_type"] = "UNKNOWN"
    with pytest.raises(ValidationError):
        validate(env, SCHEMA)


def test_created_at_format_respected_in_schema():
    ts_ms = 1700000000123
    env = make_sample_envelope(event_type="FILL", ts_ms=ts_ms)
    assert env["created_at"] == created_at_from_ts_ms(ts_ms)
    validate(env, SCHEMA)
