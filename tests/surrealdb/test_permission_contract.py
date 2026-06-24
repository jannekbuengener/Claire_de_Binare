"""Tests for SurrealDB readonly agent permission contract.

All tests are static file analysis — no DB connection needed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.surrealdb.conftest import SURQL_ORIGINAL, SURQL_DEPLOY
from tests.surrealdb.test_context_intelligence_v0_surql import EXPECTED_TABLES

PERMISSION_CONTRACT = Path(
    "infrastructure/surrealdb/context_intelligence_readonly_agent_permissions.surql"
)
PERMISSION_MATRIX_DOC = Path(
    "docs/surrealdb/context-intelligence-permission-matrix-v0.md"
)
PERMISSION_GUARD = Path("tools/mcp/permission_guard.py")
FORBIDDEN_TABLES: tuple[str, ...] = (
    "order",
    "fill",
    "position",
    "risk_state",
    "position_state",
    "trade",
)

# ---------------------------------------------------------------------------
# Existence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_permission_contract_file_exists() -> None:
    assert (
        PERMISSION_CONTRACT.exists()
    ), f"Permission contract missing: {PERMISSION_CONTRACT}"


@pytest.mark.unit
def test_permission_matrix_doc_exists() -> None:
    assert (
        PERMISSION_MATRIX_DOC.exists()
    ), f"Permission matrix doc missing: {PERMISSION_MATRIX_DOC}"


# ---------------------------------------------------------------------------
# Secret / credential guardrails
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_concrete_password_string() -> None:
    """PASSWORD must NOT appear with a concrete quoted value in the contract."""
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    # Allow PASSHASH placeholder, but disallow PASSWORD '...' or PASSWORD "..."
    # We look for PASSWORD followed by a quote character
    violations = re.findall(
        r"PASSWORD\s+['\"]",
        text,
        re.IGNORECASE,
    )
    assert not violations, (
        f"Found concrete PASSWORD value in contract: {violations}. "
        "Use PASSHASH with ${...} placeholder instead."
    )


@pytest.mark.unit
def test_passhash_uses_placeholder_format() -> None:
    """PASSHASH must use ${VAR_NAME} placeholder format.

    Only check the actual DEFINE USER statement, not comment lines
    that explain PASSHASH semantics.
    """
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    # Find the DEFINE USER block (may span multiple lines)
    lines = text.splitlines()
    define_user_block: list[str] = []
    in_block = False
    for line in lines:
        if "DEFINE USER" in line.upper():
            in_block = True
        if in_block:
            define_user_block.append(line)
            if line.strip().endswith(";"):
                break
    assert define_user_block, "No DEFINE USER statement found in permission contract"
    block_text = " ".join(define_user_block)
    assert (
        "PASSHASH" in block_text.upper()
    ), "DEFINE USER must use PASSHASH, got block: " + " ".join(define_user_block)
    passhash_line = next(
        (ln for ln in define_user_block if "PASSHASH" in ln.upper()), ""
    )
    assert (
        "${" in passhash_line and "}" in passhash_line
    ), f"PASSHASH must use ${{...}} placeholder, got: {passhash_line.strip()}"


@pytest.mark.unit
def test_no_concrete_jwt_or_root_token() -> None:
    """No JWT or root-token definitions in the contract."""
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    # Check for JWT key material or token definitions (comments about JWT are ok)
    jwt_definition = re.findall(
        r"DEFINE\s+ACCESS.*TYPE\s+JWT",
        text,
        re.IGNORECASE,
    )
    assert not jwt_definition, (
        f"Found JWT access definition in contract: {jwt_definition}. "
        "System-user RBAC with PASSHASH is sufficient."
    )


@pytest.mark.unit
def test_no_definable_secrets_in_doc_or_surql() -> None:
    """No real secrets, passwords, or API keys committed in contract or doc."""
    for path in (PERMISSION_CONTRACT, PERMISSION_MATRIX_DOC):
        text = path.read_text(encoding="utf-8")
        # Concrete JWT-looking tokens (long base64/base64url strings)
        # This regex catches plausible JWT values (header.payload.signature)
        jwt_values = re.findall(
            r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
            text,
        )
        assert not jwt_values, f"Found potential JWT value in {path.name}: {jwt_values}"


# ---------------------------------------------------------------------------
# Role guardrails
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_readonly_agent_uses_viewer_role() -> None:
    """cdb_context_agent must use ROLES VIEWER, not OWNER or EDITOR."""
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    assert "ROLES VIEWER" in text.upper(), "Readonly agent must use ROLES VIEWER"
    owner_match = re.search(r"ROLES\s+OWNER", text, re.IGNORECASE)
    assert not owner_match, "ROLES OWNER not permitted for read-only agent"
    editor_match = re.search(r"ROLES\s+EDITOR", text, re.IGNORECASE)
    assert not editor_match, "ROLES EDITOR not permitted for read-only agent"


# ---------------------------------------------------------------------------
# Deprecated / forbidden SurrealQL statements
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_define_token() -> None:
    """DEFINE TOKEN is deprecated (removed in SurrealDB 3.0).

    Only check actual SurrealQL statements, not explanatory comments.
    """
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    # Only consider non-comment lines for statement checking
    code_lines = [
        line for line in text.splitlines() if not line.strip().startswith("--")
    ]
    for line in code_lines:
        assert "DEFINE TOKEN" not in line.upper(), (
            f"DEFINE TOKEN is deprecated and must not be used. "
            f"Found in: {line.strip()}"
        )


@pytest.mark.unit
def test_no_define_capabilities() -> None:
    """DEFINE CAPABILITIES is not a SurrealQL statement.

    Capabilities are server-level CLI flags (--deny-all, --deny-scripting, etc.).
    Only check actual SurrealQL statements, not explanatory comments.
    """
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    # Only consider non-comment lines for statement checking
    code_lines = [
        line for line in text.splitlines() if not line.strip().startswith("--")
    ]
    code_text = "\n".join(code_lines)
    define_cap = re.findall(
        r"DEFINE\s+CAPABILITIES",
        code_text,
        re.IGNORECASE,
    )
    assert not define_cap, (
        f"Found DEFINE CAPABILITIES in contract: {define_cap}. "
        "Capabilities are server-level CLI configuration, not SurrealQL."
    )


@pytest.mark.unit
def test_no_unnecessary_define_access() -> None:
    """DEFINE ACCESS is not needed when using system-user RBAC.

    The contract uses DEFINE USER with ROLES VIEWER, which is the correct
    SurrealDB system-user approach.  DEFINE ACCESS is for record/JWT/bearer
    user types that require table-level PERMISSIONS instead.
    Only check actual SurrealQL statements, not explanatory comments.
    """
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    # Only consider non-comment lines for statement checking
    code_lines = [
        line for line in text.splitlines() if not line.strip().startswith("--")
    ]
    code_text = "\n".join(code_lines)
    define_access = re.findall(
        r"DEFINE\s+ACCESS",
        code_text,
        re.IGNORECASE,
    )
    assert not define_access, (
        f"Found DEFINE ACCESS in contract: {define_access}. "
        "System-user RBAC (DEFINE USER ... ROLES VIEWER) is sufficient."
    )


# ---------------------------------------------------------------------------
# Table scope
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_all_context_tables_in_permission_matrix_doc() -> None:
    """All known context intelligence tables must be listed in the matrix doc."""
    text = PERMISSION_MATRIX_DOC.read_text(encoding="utf-8")
    for table in EXPECTED_TABLES:
        assert table in text, f"Table {table} missing from permission matrix doc"


@pytest.mark.unit
def test_no_trading_state_tables_in_scope() -> None:
    """Permission matrix must NOT include trading-state tables."""
    text = PERMISSION_MATRIX_DOC.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_TABLES:
        define_matches = re.findall(
            r"(`?\b" + re.escape(forbidden) + r"\b`?)\s*\|",
            text,
            re.IGNORECASE,
        )
        assert (
            not define_matches
        ), f"Forbidden trading table found in permission scope: {forbidden}"


# ---------------------------------------------------------------------------
# Tool-level permission guard unchanged
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_permission_guard_py_not_modified() -> None:
    """tools/mcp/permission_guard.py must NOT be modified by this issue."""
    assert PERMISSION_GUARD.exists(), f"Permission guard missing: {PERMISSION_GUARD}"
    text = PERMISSION_GUARD.read_text(encoding="utf-8")
    assert (
        "Issue #3426" not in text
    ), "permission_guard.py must not reference #3426 — it is not modified"


# ---------------------------------------------------------------------------
# Operation semantics in doc
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_select_allowed_in_doc() -> None:
    """Doc must document SELECT as allowed."""
    text = PERMISSION_MATRIX_DOC.read_text(encoding="utf-8")
    assert (
        "SELECT" in text
    ), "Permission matrix doc must document that SELECT is allowed"


@pytest.mark.unit
def test_create_update_delete_define_forbidden_in_doc() -> None:
    """Doc must document CREATE/UPDATE/DELETE/DEFINE as forbidden."""
    text = PERMISSION_MATRIX_DOC.read_text(encoding="utf-8")
    for op in ("CREATE", "UPDATE", "DELETE", "DEFINE"):
        assert op in text, f"Permission matrix doc must document that {op} is forbidden"


# ---------------------------------------------------------------------------
# Capabilities documented as server-level in doc
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_capabilities_documented_as_server_level() -> None:
    """Doc must explain that CAPABILITIES are server-level CLI flags."""
    text = PERMISSION_MATRIX_DOC.read_text(encoding="utf-8")
    assert "server-level" in text.lower() or "CLI" in text, (
        "Permission matrix doc must document that CAPABILITIES are "
        "server-level CLI configuration"
    )


# ---------------------------------------------------------------------------
# DEFINE USER pattern correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_permission_contract_defines_user_on_database() -> None:
    """DEFINE USER must be ON DATABASE level (not ROOT or NAMESPACE)."""
    text = PERMISSION_CONTRACT.read_text(encoding="utf-8")
    matches = re.findall(
        r"DEFINE\s+USER.*ON\s+(ROOT|NAMESPACE|DATABASE)",
        text,
        re.IGNORECASE,
    )
    assert matches, "No DEFINE USER ON ... found"
    for level in matches:
        assert (
            level.upper() == "DATABASE"
        ), f"DEFINE USER must be ON DATABASE, got ON {level}"


@pytest.mark.unit
def test_no_root_token_creation_in_doc() -> None:
    """Permission matrix doc must not describe or advocate root tokens."""
    text = PERMISSION_MATRIX_DOC.read_text(encoding="utf-8")
    root_token_pattern = re.findall(
        r"DEFINE\s+(TOKEN|ACCESS)\s+.*ON\s+ROOT",
        text,
        re.IGNORECASE,
    )
    assert (
        not root_token_pattern
    ), f"Root token definition found in doc: {root_token_pattern}"
