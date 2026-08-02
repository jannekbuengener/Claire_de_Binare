"""Systemd unit contract for Hermes dashboard (#4289)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.hermes_ops.systemd_contract import validate_unit

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_hermes_dashboard_unit_is_hardened_loopback() -> None:
    errors = validate_unit()
    assert errors == [], errors


def test_legacy_serve_unit_absent() -> None:
    legacy = Path("infrastructure/hermes/systemd/hermes-serve@.service")
    assert not legacy.exists()


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
