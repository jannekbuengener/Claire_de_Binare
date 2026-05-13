from __future__ import annotations

import builtins
from pathlib import Path
import re
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
WS_SERVICE_DIR = REPO_ROOT / "services" / "ws"
if str(WS_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(WS_SERVICE_DIR))

import services.ws.service as svc


def _metric_value(metrics_text: str, metric_name: str) -> float:
    match = re.search(rf"^{metric_name}\s+([0-9eE\.\+\-]+)$", metrics_text, re.MULTILINE)
    assert match is not None, f"Metric {metric_name} not found in payload"
    return float(match.group(1))


class _DummyClient:
    def __init__(self, snapshots: list[dict[str, int | float]]) -> None:
        self._snapshots = snapshots
        self._index = 0

    def get_metrics(self) -> dict[str, int | float]:
        if self._index >= len(self._snapshots):
            return self._snapshots[-1]
        value = self._snapshots[self._index]
        self._index += 1
        return value


@pytest.fixture(autouse=True)
def _reset_ws_metrics_state():
    original_client = svc.ws_client
    svc.ws_client = None
    svc._last_client_counter_values["decoded_messages_total"] = None
    svc._last_client_counter_values["decode_errors_total"] = None
    yield
    svc.ws_client = original_client
    svc._last_client_counter_values["decoded_messages_total"] = None
    svc._last_client_counter_values["decode_errors_total"] = None


@pytest.mark.unit
def test_metrics_stub_mode_without_ws_client_returns_200() -> None:
    client = svc.app.test_client()
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.content_type


@pytest.mark.unit
def test_metrics_with_dummy_client_returns_all_expected_metrics() -> None:
    svc.ws_client = _DummyClient(
        [
            {
                "decoded_messages_total": 12,
                "decode_errors_total": 3,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000000,
            }
        ]
    )

    client = svc.app.test_client()
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.data.decode()
    assert "decoded_messages_total" in body
    assert "decode_errors_total" in body
    assert "ws_connected" in body
    assert "last_message_ts_ms" in body


@pytest.mark.unit
def test_repeated_scrape_same_absolute_values_does_not_double_increment() -> None:
    svc.ws_client = _DummyClient(
        [
            {
                "decoded_messages_total": 10,
                "decode_errors_total": 2,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000100,
            },
            {
                "decoded_messages_total": 10,
                "decode_errors_total": 2,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000200,
            },
        ]
    )

    client = svc.app.test_client()
    first = client.get("/metrics")
    second = client.get("/metrics")

    first_text = first.data.decode()
    second_text = second.data.decode()
    assert _metric_value(second_text, "decoded_messages_total") == _metric_value(
        first_text, "decoded_messages_total"
    )
    assert _metric_value(second_text, "decode_errors_total") == _metric_value(
        first_text, "decode_errors_total"
    )


@pytest.mark.unit
def test_scrape_with_increasing_absolute_values_increments_by_delta() -> None:
    svc.ws_client = _DummyClient(
        [
            {
                "decoded_messages_total": 10,
                "decode_errors_total": 2,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000100,
            },
            {
                "decoded_messages_total": 15,
                "decode_errors_total": 3,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000200,
            },
        ]
    )

    client = svc.app.test_client()
    first = client.get("/metrics")
    second = client.get("/metrics")

    first_text = first.data.decode()
    second_text = second.data.decode()
    assert _metric_value(second_text, "decoded_messages_total") == _metric_value(
        first_text, "decoded_messages_total"
    ) + 5
    assert _metric_value(second_text, "decode_errors_total") == _metric_value(
        first_text, "decode_errors_total"
    ) + 1


@pytest.mark.unit
def test_counter_reset_lower_value_does_not_crash_or_negative_increment() -> None:
    svc.ws_client = _DummyClient(
        [
            {
                "decoded_messages_total": 10,
                "decode_errors_total": 2,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000100,
            },
            {
                "decoded_messages_total": 3,
                "decode_errors_total": 1,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000200,
            },
            {
                "decoded_messages_total": 4,
                "decode_errors_total": 1,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000300,
            },
        ]
    )

    client = svc.app.test_client()
    first = client.get("/metrics")
    second = client.get("/metrics")
    third = client.get("/metrics")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200

    first_text = first.data.decode()
    second_text = second.data.decode()
    third_text = third.data.decode()

    first_decoded = _metric_value(first_text, "decoded_messages_total")
    second_decoded = _metric_value(second_text, "decoded_messages_total")
    third_decoded = _metric_value(third_text, "decoded_messages_total")
    first_errors = _metric_value(first_text, "decode_errors_total")
    second_errors = _metric_value(second_text, "decode_errors_total")
    third_errors = _metric_value(third_text, "decode_errors_total")

    assert second_decoded == first_decoded
    assert second_errors == first_errors
    assert third_decoded == second_decoded + 1
    assert third_errors == second_errors


@pytest.mark.unit
def test_first_scrape_seeds_counter_from_absolute_client_value() -> None:
    client = svc.app.test_client()
    baseline = _metric_value(client.get("/metrics").data.decode(), "decoded_messages_total")

    svc.ws_client = _DummyClient(
        [
            {
                "decoded_messages_total": 12,
                "decode_errors_total": 0,
                "ws_connected": 1,
                "last_message_ts_ms": 1700000000001,
            }
        ]
    )

    seeded = _metric_value(client.get("/metrics").data.decode(), "decoded_messages_total")
    assert seeded == baseline + 12


@pytest.mark.unit
def test_load_mexc_client_class_raises_runtime_error_when_dependency_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def _blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "mexc_v3_client":
            raise ModuleNotFoundError("No module named 'websockets'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(
        RuntimeError, match="MEXC WS client dependencies are required for WS_SOURCE=mexc_pb"
    ):
        svc._load_mexc_client_class()
