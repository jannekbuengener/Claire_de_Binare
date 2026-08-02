"""Path helpers for agent-control tooling."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "docs" / "contracts" / "cdb_agent_registry.v1.schema.json"
DEFAULT_CONFIG_ROOT = REPO_ROOT / "config" / "agent-control"
