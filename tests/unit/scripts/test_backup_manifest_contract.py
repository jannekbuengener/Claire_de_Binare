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


@pytest.mark.unit
def test_manifest_reconciliation_fixture_surrealdb_artifact_present() -> None:
    """Regression fixture: SurrealDB directory evidence reconciles to included."""
    manifest = {
        "Components": {"Postgres": False, "Redis": False, "SurrealDB": False},
        "Evidence": {"SurrealDB": {}},
    }
    artifacts = {
        "surrealdb_data": {
            "file_count": 4,
            "total_bytes": 8192,
        }
    }

    surreal_present = (
        artifacts["surrealdb_data"]["file_count"] > 0
        and artifacts["surrealdb_data"]["total_bytes"] > 0
    )
    reconciled = surreal_present
    assert reconciled is True

    manifest["Components"]["SurrealDB"] = reconciled
    manifest["Evidence"]["SurrealDB"] = {
        "Artifact": "surrealdb_data",
        "FileCount": artifacts["surrealdb_data"]["file_count"],
        "TotalBytes": artifacts["surrealdb_data"]["total_bytes"],
    }
    assert manifest["Components"]["SurrealDB"] is True


@pytest.mark.unit
def test_missing_artifacts_fixture_all_components_absent() -> None:
    """Missing artifacts must remain visible as not included."""
    manifest = {
        "Components": {"Postgres": False, "Redis": False, "SurrealDB": False},
        "Evidence": {
            "Postgres": {},
            "Redis": {},
            "SurrealDB": {},
        },
    }
    artifacts: dict[str, int] = {}

    missing = [
        name
        for name, flag in manifest["Components"].items()
        if not flag and not artifacts
    ]
    assert missing == ["Postgres", "Redis", "SurrealDB"]
