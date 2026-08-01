"""Systemd unit contract for Hermes serve (#4289)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.hermes_ops.systemd_contract import validate_unit

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def test_hermes_serve_unit_is_hardened_loopback() -> None:
    errors = validate_unit()
    assert errors == [], errors


def test_version_pin_schema_present() -> None:
    pin = yaml.safe_load(
        Path("infrastructure/hermes/VERSION_PIN.yaml").read_text(encoding="utf-8")
    )
    assert pin["schema_version"] == "cdb.hermes.version_pin/v1"
    assert pin["hermes"]["install_url"].startswith("https://")
    # Empty pin is intentional until operator fills it; bootstrap refuses empty.
    assert pin["hermes"]["git_ref"] == ""
    assert pin["hetzner"]["backups"] is True


def test_firewall_forbids_public_hermes_ports() -> None:
    fw = yaml.safe_load(
        Path("infrastructure/hermes/hetzner/firewall.yaml").read_text(encoding="utf-8")
    )
    assert fw["rules"]["inbound"] == []
    assert 9119 in fw["forbidden_public_ports"]
    assert 22 in fw["forbidden_public_ports"]
