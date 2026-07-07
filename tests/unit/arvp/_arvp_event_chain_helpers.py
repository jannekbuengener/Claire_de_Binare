"""Shared helpers for ARVP runtime event-chain contract tests (#3821)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.arvp_chain_detector import ChainDetector

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "arvp" / "event_chain"

_FORBIDDEN_OUTPUT_KEYWORDS = ("Live-Go", "Echtgeld", "live_trading", "auto-merge")
_FORBIDDEN_SOURCE_KEYWORDS = (
    "Live-Go",
    "Echtgeld-Go",
    "auto-merge",
    "INSERT",
    "UPDATE",
    "DELETE",
    "gh issue close",
)


def load_event_chain_fixture(name: str) -> list[dict[str, Any]]:
    payload = json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))
    events = payload.get("events", payload)
    if not isinstance(events, list):
        raise ValueError(f"fixture {name} must contain an events list")
    return events


def detect_chain_from_fixture(name: str) -> dict[str, Any]:
    return ChainDetector(events=load_event_chain_fixture(name)).detect()


def assert_no_live_keywords_in_output(result: dict[str, Any]) -> None:
    output = json.dumps(result, default=str)
    for keyword in _FORBIDDEN_OUTPUT_KEYWORDS:
        assert keyword not in output, f"forbidden keyword in chain output: {keyword}"


def assert_chain_detector_source_boundaries() -> None:
    source_path = Path(__file__).resolve().parents[3] / "tools" / "arvp_chain_detector.py"
    source = source_path.read_text(encoding="utf-8")
    for keyword in _FORBIDDEN_SOURCE_KEYWORDS:
        assert keyword not in source, f"forbidden keyword in chain detector: {keyword}"
