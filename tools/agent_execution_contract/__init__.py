"""cdb.agent_execution.v1 — provider-neutral Agent Execution Contract tools."""

from __future__ import annotations

from tools.agent_execution_contract.errors import ContractValidationError
from tools.agent_execution_contract.hashing import (
    DIGEST_PREFIX,
    attach_digest,
    compute_digest,
    verify_digest,
)
from tools.agent_execution_contract.jcs import canonicalize
from tools.agent_execution_contract.validate import validate_contract

__all__ = [
    "ContractValidationError",
    "DIGEST_PREFIX",
    "attach_digest",
    "canonicalize",
    "compute_digest",
    "validate_contract",
    "verify_digest",
]

SCHEMA_ID = "cdb.agent_execution.v1"
SCHEMA_VERSION = "1.0.0"
