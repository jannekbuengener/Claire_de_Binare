"""Unit tests for scripts/smoke_core_flow.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "smoke_core_flow.py"
    spec = importlib.util.spec_from_file_location("smoke_core_flow", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeRedis:
    def __init__(self, entries):
        self._entries = entries

    def xrevrange(self, stream, start, end, count=100):  # noqa: ARG002
        return self._entries


def test_latest_matching_result_finds_signal():
    mod = _load_module()
    client = _FakeRedis(
        [
            ("2-0", {"signal_id": "sig-2", "status": "FILLED"}),
            ("1-0", {"signal_id": "sig-1", "status": "REJECTED"}),
        ]
    )
    result = mod._latest_matching_result(client, signal_id="sig-2")
    assert result is not None
    assert result["status"] == "FILLED"
    assert result["entry_id"] == "2-0"


def test_latest_matching_result_returns_none_when_missing():
    mod = _load_module()
    client = _FakeRedis([("1-0", {"signal_id": "other", "status": "FILLED"})])
    assert mod._latest_matching_result(client, signal_id="sig-missing") is None


def test_write_report_generates_markdown(tmp_path):
    mod = _load_module()
    report_path = tmp_path / "CORE_FLOW_E2E_SMOKE.md"
    mod.REPORT_PATH = report_path
    outcome = mod.SmokeOutcome(
        passed=True,
        signal_id="sig-test",
        order_result_status="FILLED",
        order_count=1,
        trade_count=1,
        details=["detail-a", "detail-b"],
    )
    mod.write_report(outcome)

    content = report_path.read_text(encoding="utf-8")
    assert "CORE FLOW E2E SMOKE" in content
    assert "sig-test" in content
    assert "detail-a" in content
