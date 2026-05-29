"""#2719 unit contracts for claim evidence proof runtime CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.surrealdb.claim_evidence_proof_runtime import (
    CLAIM_PROOF_RUNTIME_SCHEMA,
    check_claim_evidence_proof_preconditions,
)

_CLI = Path(__file__).parents[3] / "tools" / "surrealdb" / "claim_evidence_proof_cli.py"
_RUNTIME = (
    Path(__file__).parents[3]
    / "tools"
    / "surrealdb"
    / "claim_evidence_proof_runtime.py"
)


@pytest.mark.unit
def test_claim_runtime_and_cli_modules_exist() -> None:
    assert _CLI.is_file()
    assert _RUNTIME.is_file()


@pytest.mark.unit
def test_claim_preflight_reuses_memory_preflight_schema() -> None:
    with patch(
        "tools.surrealdb.claim_evidence_proof_runtime.check_memory_db_proof_preconditions",
        return_value={"ok": True, "limitations": []},
    ):
        result = check_claim_evidence_proof_preconditions(confirm=True)
    assert result["schema_version"] == CLAIM_PROOF_RUNTIME_SCHEMA
    assert result["ok"] is True


@pytest.mark.unit
def test_claim_cli_run_proof_success_prints_json() -> None:
    from tools.surrealdb.claim_evidence_proof_cli import EXIT_OK, main

    payload = {"schema_version": CLAIM_PROOF_RUNTIME_SCHEMA, "status": "ok"}
    with patch(
        "tools.surrealdb.claim_evidence_proof_cli.run_claim_evidence_proof_cycle",
        return_value=payload,
    ):
        with patch("builtins.print") as mock_print:
            code = main(["run-proof", "--confirm"])
    assert code == EXIT_OK
    parsed = json.loads(mock_print.call_args[0][0])
    assert parsed["status"] == "ok"
