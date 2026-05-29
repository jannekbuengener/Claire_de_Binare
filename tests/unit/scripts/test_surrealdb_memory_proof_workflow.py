"""Surface guard for optional SurrealDB memory proof workflow (#2721).

Protects against drift between the workflow and canonical Makefile proof targets
for #2603/#2606 local operator paths.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "surrealdb-memory-proof.yml"
MAKEFILE_PATH = REPO_ROOT / "Makefile"

PROOF_TARGETS = (
    "context-memory-db-proof",
    "context-claim-evidence-proof",
    "context-memory-rediscovery-proof",
)


def _load_workflow() -> dict:
    assert WORKFLOW_PATH.exists(), f"Workflow not found: {WORKFLOW_PATH}"
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_surrealdb_memory_proof_workflow_has_workflow_dispatch() -> None:
    workflow = _load_workflow()
    on_triggers = workflow.get("on") or workflow.get(True) or {}
    assert "workflow_dispatch" in on_triggers, (
        "surrealdb-memory-proof.yml must declare workflow_dispatch (#2721)."
    )


@pytest.mark.unit
def test_surrealdb_memory_proof_workflow_minimal_permissions() -> None:
    workflow = _load_workflow()
    permissions = workflow.get("permissions") or {}
    assert permissions.get("contents") == "read", (
        "surrealdb-memory-proof.yml must use contents: read only (#2721)."
    )


@pytest.mark.unit
def test_surrealdb_memory_proof_workflow_uses_self_hosted_docker() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "runs-on: [self-hosted, cdb, docker]" in content


@pytest.mark.unit
def test_surrealdb_memory_proof_workflow_is_non_blocking() -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "continue-on-error: true" in content


@pytest.mark.unit
@pytest.mark.parametrize("target", PROOF_TARGETS)
def test_makefile_has_memory_proof_target(target: str) -> None:
    content = MAKEFILE_PATH.read_text(encoding="utf-8")
    assert re.search(rf"^{target}:", content, re.MULTILINE), (
        f"Makefile missing target {target!r} required by #2721 workflow."
    )


@pytest.mark.unit
@pytest.mark.parametrize("target", PROOF_TARGETS)
def test_surrealdb_memory_proof_workflow_invokes_make_target(target: str) -> None:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert f"make {target}" in content, (
        f"surrealdb-memory-proof.yml must invoke make {target} (#2721 coupling)."
    )
