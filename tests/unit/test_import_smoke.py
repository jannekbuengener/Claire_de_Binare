"""Smoke import tests for critical services."""

import importlib

import pytest


@pytest.mark.unit
def test_import_risk_service_module():
    """Import risk service to catch fragile relative imports early."""
    importlib.import_module("services.risk.service")


@pytest.mark.unit
def test_import_signal_service_module():
    """Import signal service to catch fragile relative imports early."""
    importlib.import_module("services.signal.service")
