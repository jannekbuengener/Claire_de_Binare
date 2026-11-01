"""Exact Agent Brain pin for the Claire consumer cutover (#13 / #17 / #19).

Canonical pin forms (Consumer Contract #17):
- ``agent-brain==0.2.1`` when the package is published to an index
- ``agent-brain @ git+https://github.com/jannekbuengener/agent-brain.git@v0.2.1``

Moving refs (``main``, branches, ``latest``, local paths) are forbidden.
"""

from __future__ import annotations

from importlib import metadata

from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode

# AGENT_BRAIN_CUTOVER_VERSION — immutable release including #12 + #19 genericity.
PINNED_AGENT_BRAIN_VERSION = "0.2.1"
PINNED_GIT_TAG = f"v{PINNED_AGENT_BRAIN_VERSION}"
PINNED_REQUIREMENT = (
    "agent-brain @ "
    f"git+https://github.com/jannekbuengener/agent-brain.git@{PINNED_GIT_TAG}"
)
PACKAGE_NAME = "agent-brain"


def installed_version() -> str:
    """Return the installed package version or raise a structured mismatch error."""
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError as exc:
        raise ConsumerError(
            ConsumerErrorCode.CONTRACT_VERSION_MISMATCH,
            "agent-brain package is not installed",
            details={"expected": PINNED_AGENT_BRAIN_VERSION},
        ) from exc


def verify_runtime_pin(
    *,
    expected: str = PINNED_AGENT_BRAIN_VERSION,
) -> str:
    """Fail closed when runtime version != expected pin."""
    runtime = installed_version()
    if runtime != expected:
        raise ConsumerError(
            ConsumerErrorCode.CONTRACT_VERSION_MISMATCH,
            "agent-brain runtime version does not match Claire pin",
            details={"expected": expected, "runtime": runtime},
        )
    return runtime


__all__ = [
    "PACKAGE_NAME",
    "PINNED_AGENT_BRAIN_VERSION",
    "PINNED_GIT_TAG",
    "PINNED_REQUIREMENT",
    "installed_version",
    "verify_runtime_pin",
]
