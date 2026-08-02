"""Unit tests for Hetzner hcloud-preflight classification (#4289)."""

from __future__ import annotations

from typing import Any

import pytest

from tools.hermes_ops import hcloud_preflight as hp

pytestmark = [pytest.mark.unit]


def test_missing_token_classifies() -> None:
    report = hp.run_hcloud_preflight(token="")
    assert report.ok is False
    assert report.classification == "MISSING_TOKEN"


def test_server_create_forbidden_when_firewall_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_call(
        token: str, method: str, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        calls.append((method, path))
        if method == "GET" and path == "/servers":
            return 200, {"servers": []}
        if method == "POST" and path == "/firewalls":
            return 201, {"firewall": {"id": 1}}
        if method == "DELETE" and path.startswith("/firewalls/"):
            return 204, {}
        if method == "POST" and path == "/servers":
            return 403, {"error": {"code": "forbidden", "message": "permission denied"}}
        return 500, {"error": {"code": "unexpected"}}

    monkeypatch.setattr(hp, "_call", fake_call)
    report = hp.run_hcloud_preflight(token="x" * 64)
    assert report.ok is False
    assert report.classification == "SERVER_CREATE_FORBIDDEN"
    assert report.auth_ok is True
    assert report.server_create_ok is False
    assert any("Full-account" in a or "Owner/Admin" in a for a in report.human_actions)
    assert ("POST", "/servers") in calls


def test_server_create_ok_deletes_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    deleted: list[str] = []

    def fake_call(
        token: str, method: str, path: str, body: dict[str, Any] | None = None
    ) -> tuple[int, dict[str, Any]]:
        if method == "GET" and path == "/servers":
            return 200, {"servers": []}
        if method == "POST" and path == "/firewalls":
            return 201, {"firewall": {"id": 9}}
        if method == "DELETE" and path.startswith("/firewalls/"):
            deleted.append(path)
            return 204, {}
        if method == "POST" and path == "/servers":
            return 201, {"server": {"id": 42}}
        if method == "DELETE" and path.startswith("/servers/"):
            deleted.append(path)
            return 204, {}
        return 500, {}

    monkeypatch.setattr(hp, "_call", fake_call)
    report = hp.run_hcloud_preflight(token="x" * 64)
    assert report.ok is True
    assert report.classification == "SERVER_CREATE_OK"
    assert "/servers/42" in deleted
