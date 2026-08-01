"""Contract: BLUE/TLS mount migration 012 reduce-only ledger (#4261).

test_id: tc_blue_012_reduce_only_wiring_001
test_type: Datenbank-Test / Wissens-Test
cdb_area: infrastructure/compose + infrastructure/database
rule_ref: execution_reduce_only_v1 ledger must be initdb-reachable on BLUE
decision_ref: Issue #4261 residual BLUE-012 Upgrade/Wiring
issue_ref: #4261
security_relevant: true
live_relevant: false
profitability_relevant: false

Static YAML/SQL contracts only — no Docker runtime, no DB apply.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from tests.unit.infra._compose_stack_contract_helpers import (
    COMPOSE_DIR,
    REPO_ROOT,
    load_compose_yaml,
)

pytestmark = [pytest.mark.unit, pytest.mark.contract]

MIGRATION_012 = "012_reduce_only_execution_contract.sql"
MIGRATION_011 = "011_trade_realized_pnl.sql"
MIGRATION_013 = "013_candle_backfill_provenance.sql"
INITDB_PREFIX = "/docker-entrypoint-initdb.d/"
MIGRATION_DIR = "infrastructure/database/migrations/"


def _postgres_services(compose: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    services = compose.get("services") or {}
    if not isinstance(services, dict):
        return []
    found: list[tuple[str, dict[str, Any]]] = []
    for name, cfg in services.items():
        if not isinstance(cfg, dict):
            continue
        image = str(cfg.get("image") or "")
        volumes = cfg.get("volumes") or []
        has_initdb = any(isinstance(v, str) and INITDB_PREFIX in v for v in volumes)
        if "postgres" in image.lower() or has_initdb:
            found.append((name, cfg))
    return found


def _initdb_migration_mounts(service_cfg: dict[str, Any]) -> list[tuple[str, str]]:
    """Return (migration_filename, initdb_basename) for migration mounts."""
    mounts: list[tuple[str, str]] = []
    for volume in service_cfg.get("volumes") or []:
        if not isinstance(volume, str):
            continue
        if MIGRATION_DIR not in volume or INITDB_PREFIX not in volume:
            continue
        host_part, _, container_part = volume.partition(":")
        migration_name = Path(host_part).name
        initdb_name = Path(container_part.split(":")[0]).name
        mounts.append((migration_name, initdb_name))
    return mounts


def _mount_order_index(mounts: list[tuple[str, str]], migration_name: str) -> int:
    for idx, (name, _) in enumerate(mounts):
        if name == migration_name:
            return idx
    raise AssertionError(f"migration mount missing: {migration_name}")


@pytest.mark.parametrize("compose_file", ["compose.blue.yml", "tls.yml"])
def test_canonical_postgres_mounts_migration_012(compose_file: str) -> None:
    """
    test_id: tc_blue_012_reduce_only_wiring_001
    Protects: reduce_only_executions ledger reachable via BLUE/TLS initdb.
    """
    compose = load_compose_yaml(compose_file)
    pg_services = _postgres_services(compose)
    assert (
        pg_services
    ), f"{compose_file} must declare a Postgres service with initdb mounts"

    matched = False
    for _name, cfg in pg_services:
        mounts = _initdb_migration_mounts(cfg)
        names = [m[0] for m in mounts]
        if MIGRATION_012 not in names:
            continue
        matched = True
        host_paths = [
            v
            for v in (cfg.get("volumes") or [])
            if isinstance(v, str) and MIGRATION_012 in v
        ]
        assert host_paths, f"{compose_file} missing host path for {MIGRATION_012}"
        assert any(
            f"{MIGRATION_DIR}{MIGRATION_012}" in path for path in host_paths
        ), f"{compose_file} must mount exact path {MIGRATION_DIR}{MIGRATION_012}"
        assert any(
            f"{INITDB_PREFIX}12-migration-012.sql" in path for path in host_paths
        ), f"{compose_file} must use initdb basename 12-migration-012.sql"
    assert matched, (
        f"{compose_file} Postgres volumes must mount {MIGRATION_012} "
        f"(Issue #4261 BLUE-012 wiring)"
    )


def test_compose_blue_migration_order_011_012_013() -> None:
    """BLUE initdb order must be 011 → 012 → 013 so 012 is not skipped."""
    compose = load_compose_yaml("compose.blue.yml")
    pg_services = _postgres_services(compose)
    assert pg_services
    mounts = _initdb_migration_mounts(pg_services[0][1])
    idx_011 = _mount_order_index(mounts, MIGRATION_011)
    idx_012 = _mount_order_index(mounts, MIGRATION_012)
    idx_013 = _mount_order_index(mounts, MIGRATION_013)
    assert (
        idx_011 < idx_012 < idx_013
    ), f"expected 011→012→013 order, got {[m[0] for m in mounts]}"


def test_migration_012_is_idempotent_upgrade_safe() -> None:
    """SQL must be IF NOT EXISTS so existing volumes can apply via runner."""
    path = REPO_ROOT / "infrastructure" / "database" / "migrations" / MIGRATION_012
    text = path.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS reduce_only_executions" in text
    assert "CREATE INDEX IF NOT EXISTS idx_reduce_only_executions_symbol_status" in text
    assert (
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_trades_reduce_only_execution_order"
        in text
    )
    assert not re.search(r"\bDROP\s+TABLE\b", text, flags=re.IGNORECASE)


def test_execution_prepare_path_depends_on_reduce_only_ledger() -> None:
    """Wiring check: production prepare path references the ledger table."""
    database_py = (REPO_ROOT / "services" / "execution" / "database.py").read_text(
        encoding="utf-8"
    )
    assert "def prepare_reduce_only" in database_py
    assert "FROM reduce_only_executions" in database_py
    assert "INSERT INTO reduce_only_executions" in database_py


def test_compose_files_exist_for_blue_012_contract() -> None:
    assert (COMPOSE_DIR / "compose.blue.yml").is_file()
    assert (COMPOSE_DIR / "tls.yml").is_file()
    assert (
        REPO_ROOT / "infrastructure" / "database" / "migrations" / MIGRATION_012
    ).is_file()
