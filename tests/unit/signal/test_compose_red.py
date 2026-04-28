from pathlib import Path

import pytest
import yaml

COMPOSE_RED_PATH = (
    Path(__file__).resolve().parents[3]
    / "infrastructure"
    / "compose"
    / "compose.red.yml"
)


@pytest.mark.unit
def test_compose_red_wires_signal_bot_id_for_cdb_signal() -> None:
    compose = yaml.safe_load(COMPOSE_RED_PATH.read_text(encoding="utf-8"))

    assert compose["services"]["cdb_signal"]["environment"]["SIGNAL_BOT_ID"] == (
        "${SIGNAL_BOT_ID:-}"
    )
