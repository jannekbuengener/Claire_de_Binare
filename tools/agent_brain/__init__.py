"""Claire consumer surface for the pinned Agent Brain package (#13).

Architecture::

    Claire de Binare
          ↓
    tools.agent_brain (adapter / path selection / Claire policy)
          ↓
    agent_brain.protocol (public surface from #12)
          ↓
    Agent Brain core

This package must not import Agent Brain private/internal modules.
Claire-specific trading, live, and safety policy stays here.
Legacy Claire context paths remain available for #18 parity.
"""

from __future__ import annotations

from tools.agent_brain.adapter import AgentBrainAdapter, ConsumerResult
from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.parity import ParityClass, run_dual_suite
from tools.agent_brain.path_selection import (
    ConsumerPath,
    resolve_consumer_path,
    select_consumer_path,
)
from tools.agent_brain.pin import (
    PINNED_AGENT_BRAIN_VERSION,
    PINNED_REQUIREMENT,
    verify_runtime_pin,
)

__all__ = [
    "PINNED_AGENT_BRAIN_VERSION",
    "PINNED_REQUIREMENT",
    "AgentBrainAdapter",
    "ConsumerError",
    "ConsumerErrorCode",
    "ConsumerPath",
    "ConsumerResult",
    "ParityClass",
    "resolve_consumer_path",
    "run_dual_suite",
    "select_consumer_path",
    "verify_runtime_pin",
]
