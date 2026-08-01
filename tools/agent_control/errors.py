"""Typed errors for Agent Registry validation and reconcile."""

from __future__ import annotations


class RegistryError(ValueError):
    """Fail-closed registry or reconciler error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
