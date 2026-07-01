"""Cross-platform contract tests for backup manifest drift behavior."""

from __future__ import annotations

import json

import pytest


@pytest.mark.unit
def test_manifest_drift_fixture_documents_redis_false_with_artifact() -> None:
    """Regression fixture for #3614 observed ZIP/manifest mismatch."""
    manifest = {
        "Components": {"Postgres": True, "Redis": False, "SurrealDB": False},
        "ComponentSelection": {"Postgres": True, "Redis": True, "SurrealDB": False},
        "Evidence": {
            "Postgres": {"Artifact": "postgres_dump.sql", "SizeBytes": 1039873045},
            "Redis": {},
        },
    }
    artifacts = {
        "postgres_dump.sql": 1039873045,
        "redis_dump.rdb": 10957629,
    }

    assert manifest["Components"]["Redis"] is False
    assert artifacts["redis_dump.rdb"] > 0
    assert manifest["ComponentSelection"]["Redis"] is True

    reconciled_redis = artifacts.get("redis_dump.rdb", 0) > 0
    assert reconciled_redis is True

    payload = json.dumps(manifest)
    assert '"Redis":  false' in payload or '"Redis": false' in payload
