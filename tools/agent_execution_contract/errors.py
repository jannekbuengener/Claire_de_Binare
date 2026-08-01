"""Typed errors for Agent Execution Contract validation."""

from __future__ import annotations


class ContractValidationError(ValueError):
    """Fail-closed contract validation or attenuation error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
