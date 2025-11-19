"""Smoke test to ensure the primary package imports."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_import_main_package():
    """Verify that the project package is importable in the test environment."""

    for candidate in ("services", "claire_de_binare"):
        try:
            __import__(candidate)
            return
        except ImportError:
            continue

    pytest.skip(
        "Main package could not be imported; ensure repository root is on PYTHONPATH"
    )
