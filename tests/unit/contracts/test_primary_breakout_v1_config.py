import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from core.contracts import (
    PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG,
    PRIMARY_BREAKOUT_V1_STRATEGY_ID,
    PRIMARY_BREAKOUT_V1_SYMBOL,
    PRIMARY_BREAKOUT_V1_TRADE_SIDE_MODE,
    PrimaryBreakoutV1Config,
)


SCHEMA_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "contracts"
    / "primary_breakout_v1_config.schema.json"
)


def load_schema() -> dict:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_default_config_matches_canonical_values():
    config = PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG

    assert config.strategy_id == PRIMARY_BREAKOUT_V1_STRATEGY_ID
    assert config.symbol == PRIMARY_BREAKOUT_V1_SYMBOL
    assert config.entry_lookback_minutes == 240
    assert config.exit_lookback_minutes == 120
    assert config.breakout_buffer == 0.0005
    assert config.min_minutes_between_entries == 60
    assert config.trade_side_mode == PRIMARY_BREAKOUT_V1_TRADE_SIDE_MODE


def test_from_mapping_without_values_uses_defaults():
    config = PrimaryBreakoutV1Config.from_mapping()

    assert config == PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG


def test_from_mapping_rejects_unknown_fields():
    with pytest.raises(ValueError, match="Unknown primary_breakout_v1 config field"):
        PrimaryBreakoutV1Config.from_mapping({"unexpected_field": True})


def test_trade_side_mode_is_fail_closed():
    with pytest.raises(ValueError, match="trade_side_mode must be 'long_only'"):
        PrimaryBreakoutV1Config(trade_side_mode="short_only")  # type: ignore[arg-type]


def test_strategy_id_is_fail_closed():
    with pytest.raises(ValueError, match="strategy_id must be 'primary_breakout_v1'"):
        PrimaryBreakoutV1Config(strategy_id="breakout_v2")  # type: ignore[arg-type]


def test_symbol_is_fail_closed():
    with pytest.raises(ValueError, match="symbol must be 'BTCUSDT'"):
        PrimaryBreakoutV1Config(symbol="ETHUSDT")  # type: ignore[arg-type]


def test_numeric_fields_reject_wrong_types():
    with pytest.raises(ValueError, match="entry_lookback_minutes must be an integer"):
        PrimaryBreakoutV1Config(entry_lookback_minutes="240")  # type: ignore[arg-type]


def test_schema_is_strict_and_canonical():
    schema = load_schema()

    assert schema["additionalProperties"] is False
    assert schema["properties"]["strategy_id"]["const"] == "primary_breakout_v1"
    assert schema["properties"]["symbol"]["const"] == "BTCUSDT"
    assert schema["properties"]["trade_side_mode"]["const"] == "long_only"
    assert schema["properties"]["entry_lookback_minutes"]["default"] == 240
    assert schema["properties"]["exit_lookback_minutes"]["default"] == 120
    assert schema["properties"]["breakout_buffer"]["default"] == 0.0005
    assert schema["properties"]["min_minutes_between_entries"]["default"] == 60


def test_default_config_validates_against_schema():
    validator = Draft7Validator(load_schema())
    errors = list(validator.iter_errors(PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.to_dict()))

    assert errors == []


def test_schema_rejects_non_long_only_trade_side_mode():
    validator = Draft7Validator(load_schema())
    payload = PRIMARY_BREAKOUT_V1_DEFAULT_CONFIG.to_dict()
    payload["trade_side_mode"] = "short_only"

    errors = list(validator.iter_errors(payload))

    assert errors
