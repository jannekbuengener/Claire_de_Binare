"""#2603 unit contracts for local context runtime Makefile targets.

Verifies Makefile target presence and local_schema_check hard vs soft behavior
(mocked HTTP). No live DB, no Docker.

Issue: #2603
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

_MAKEFILE = Path(__file__).parents[3] / "Makefile"


def _read_makefile() -> str:
    assert _MAKEFILE.exists(), "Makefile not found"
    return _MAKEFILE.read_text(encoding="utf-8")


def _lines_for_target(content: str, target: str) -> list[str]:
    lines = content.splitlines()
    in_target = False
    recipe: list[str] = []
    for line in lines:
        if line.startswith(f"{target}:"):
            in_target = True
            continue
        if in_target:
            if line.startswith("\t"):
                recipe.append(line)
            elif (
                line.startswith("ifeq ")
                or line.startswith("else")
                or line.startswith("endif")
            ):
                recipe.append(line)
            elif line.strip() == "" or line.startswith("#"):
                continue
            elif line and not line.startswith("\t") and ":" in line.split()[0]:
                break
            else:
                break
    return recipe


@pytest.mark.unit
def test_makefile_context_up_target_exists() -> None:
    content = _read_makefile()
    assert "context-up:" in content


@pytest.mark.unit
def test_makefile_context_smoke_db_target_exists() -> None:
    content = _read_makefile()
    assert "context-smoke-db:" in content


@pytest.mark.unit
def test_makefile_context_memory_db_proof_in_phony() -> None:
    content = _read_makefile()
    phony_lines = [line for line in content.splitlines() if line.startswith(".PHONY:")]
    phony_text = " ".join(phony_lines)
    assert "context-memory-db-proof" in phony_text


@pytest.mark.unit
def test_makefile_context_memory_db_proof_uses_hard_schema_check() -> None:
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-memory-db-proof")
    recipe_text = "\n".join(recipe)
    assert "local_schema_check.py" in recipe_text
    assert "--hard-mode" in recipe_text


@pytest.mark.unit
def test_makefile_context_memory_db_proof_invokes_cli() -> None:
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-memory-db-proof")
    recipe_text = "\n".join(recipe)
    assert "memory_db_proof_cli" in recipe_text
    assert "run-proof" in recipe_text
    assert "--confirm" in recipe_text


@pytest.mark.unit
def test_makefile_context_claim_evidence_proof_in_phony() -> None:
    content = _read_makefile()
    phony_lines = [line for line in content.splitlines() if line.startswith(".PHONY:")]
    phony_text = " ".join(phony_lines)
    assert "context-claim-evidence-proof" in phony_text


@pytest.mark.unit
def test_makefile_context_claim_evidence_proof_invokes_cli() -> None:
    content = _read_makefile()
    recipe = _lines_for_target(content, "context-claim-evidence-proof")
    recipe_text = "\n".join(recipe)
    assert "claim_evidence_proof_cli" in recipe_text
    assert "run-proof" in recipe_text
    assert "--confirm" in recipe_text


@pytest.mark.unit
def test_local_schema_check_hard_mode_exits_nonzero_if_offline() -> None:
    from tools.surrealdb import local_schema_check

    with (
        patch.object(local_schema_check, "_health_check", return_value=False),
        patch("sys.argv", ["local_schema_check.py", "--hard-mode"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        local_schema_check.main()

    assert exc_info.value.code == 1


@pytest.mark.unit
def test_local_schema_check_soft_mode_exits_zero_if_offline() -> None:
    from tools.surrealdb import local_schema_check

    with (
        patch.object(local_schema_check, "_health_check", return_value=False),
        patch("sys.argv", ["local_schema_check.py"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        local_schema_check.main()

    assert exc_info.value.code == 0
