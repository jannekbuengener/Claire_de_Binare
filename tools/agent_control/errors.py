"""Typed errors for Agent Control Plane tooling (registry + dispatcher)."""

from __future__ import annotations


class AgentControlError(ValueError):
    """Fail-closed agent-control error with stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class RegistryError(AgentControlError):
    """Fail-closed registry or reconciler error."""


class DispatchError(AgentControlError):
    """Fail-closed dispatcher / lifecycle / provider error."""
