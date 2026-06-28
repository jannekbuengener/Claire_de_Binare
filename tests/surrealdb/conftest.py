"""Test fixtures for SurrealDB schema tests."""

from __future__ import annotations

from pathlib import Path

import pytest


SURQL_ORIGINAL = Path("infrastructure/surrealdb/context_intelligence_v0.surql")
SURQL_DEPLOY = Path("infrastructure/surrealdb/context_intelligence_v0_deploy.surql")
BASELINE_PATH = Path("infrastructure/surrealdb/schema_baseline.json")


@pytest.fixture(scope="session")
def surql_original_text() -> str:
    return SURQL_ORIGINAL.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def surql_deploy_text() -> str:
    return SURQL_DEPLOY.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def baseline_json() -> dict:
    import json
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
