"""Systemd unit contract for Hermes dashboard (#4289)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.hermes_ops.systemd_contract import validate_gateway_unit, validate_unit
from tools.hermes_ops.tailnet_transport_contract import validate_transport_unit

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_hermes_dashboard_unit_is_hardened_loopback() -> None:
    errors = validate_unit()
    assert errors == [], errors


def test_legacy_serve_unit_absent() -> None:
    legacy = Path("infrastructure/hermes/systemd/hermes-serve@.service")
    assert not legacy.exists()


def test_hermes_runs_gateway_unit_is_hardened_and_loopback_only() -> None:
    errors = validate_gateway_unit()
    assert errors == [], errors


def test_gateway_host_is_enforced_after_environment_file_loading() -> None:
    text = Path(
        "infrastructure/hermes/systemd/hermes-gateway-cdb-engineer.service"
    ).read_text(encoding="utf-8")
    assert (
        "ExecStart=/usr/bin/env API_SERVER_HOST=127.0.0.1 "
        "/opt/hermes/bin/hermes gateway"
    ) in text
    assert "Environment=API_SERVER_HOST=127.0.0.1" not in text


def test_hermes_runs_transport_is_root_owned_tailnet_only() -> None:
    errors = validate_transport_unit()
    assert errors == [], errors

    text = Path(
        "infrastructure/hermes/systemd/hermes-runs-tailnet-transport.service"
    ).read_text(encoding="utf-8")
    assert "User=root" in text
    assert "EnvironmentFile=/etc/hermes/cdb-engineer.env" in text
    assert "tailscale serve --bg --yes --tcp=${API_SERVER_PORT}" in text
    assert "tcp://127.0.0.1:${API_SERVER_PORT}" in text
    assert "tailscale serve --bg --yes --tcp=${API_SERVER_PORT} off" in text
    assert "tailscale funnel" not in text.lower()
    assert "0.0.0.0" not in text


def test_gateway_does_not_expand_api_key_into_process_argv() -> None:
    text = Path(
        "infrastructure/hermes/systemd/hermes-gateway-cdb-engineer.service"
    ).read_text(encoding="utf-8")
    command_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith(("ExecStart=", "ExecStartPre="))
    ]
    assert command_lines
    assert all("API_SERVER_KEY" not in line for line in command_lines)


def test_version_pin_schema_and_live_fields() -> None:
    pin = yaml.safe_load(
        Path("infrastructure/hermes/VERSION_PIN.yaml").read_text(encoding="utf-8")
    )
    assert pin["schema_version"] == "cdb.hermes.version_pin/v1"
    assert pin["hermes"]["install_url"].startswith("https://")
    assert pin["hermes"]["git_ref"]
    assert pin["hermes"]["git_commit"]
    assert pin["hermes"]["install_script_sha256"]
    assert pin["hermes"]["dashboard_command"] == "hermes dashboard"
    assert pin["ports"]["jannek-assistant"] != pin["ports"]["cdb-engineer"]
    assert pin["hetzner"]["backups"] is True
    assert float(pin["hetzner"]["monthly_cost_eur_estimate"]["total_estimate"]) <= 15


def test_firewall_forbids_public_hermes_ports() -> None:
    fw = yaml.safe_load(
        Path("infrastructure/hermes/hetzner/firewall.yaml").read_text(encoding="utf-8")
    )
    assert fw["rules"]["inbound"] == []
    assert 9119 in fw["forbidden_public_ports"]
    assert 9120 in fw["forbidden_public_ports"]
    assert 22 in fw["forbidden_public_ports"]


def test_profile_ports_are_distinct() -> None:
    ja = yaml.safe_load(
        Path("config/hermes/profiles/jannek-assistant/config.yaml").read_text(
            encoding="utf-8"
        )
    )
    eng = yaml.safe_load(
        Path("config/hermes/profiles/cdb-engineer/config.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert ja["server"]["port"] == 9119
    assert eng["server"]["port"] == 9120
