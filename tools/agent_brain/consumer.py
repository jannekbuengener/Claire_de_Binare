"""Path-aware Claire consumer entry for legacy vs Agent Brain."""

from __future__ import annotations

from typing import Any, Mapping

from tools.agent_brain.adapter import AgentBrainAdapter, ConsumerResult
from tools.agent_brain.errors import ConsumerError, ConsumerErrorCode
from tools.agent_brain.legacy import LegacyContextPath
from tools.agent_brain.path_selection import ConsumerPath, resolve_consumer_path


def read_context(
    *,
    target_scope: str,
    artifacts: list[Mapping[str, Any]] | None = None,
    path: str | ConsumerPath | None = None,
    adapter: AgentBrainAdapter | None = None,
    legacy: LegacyContextPath | None = None,
) -> ConsumerResult:
    """Dispatch context_read to the selected consumer path."""
    selected = resolve_consumer_path(explicit=path)
    if selected is ConsumerPath.LEGACY:
        facade = legacy or LegacyContextPath()
        return facade.context_read(target_scope=target_scope, artifacts=artifacts)
    if selected is ConsumerPath.AGENT_BRAIN:
        brain = adapter or AgentBrainAdapter()
        return brain.context_read(target_scope=target_scope, artifacts=artifacts)
    raise ConsumerError(
        ConsumerErrorCode.UNSUPPORTED_PATH,
        f"unsupported consumer path: {selected}",
    )


def rollback_to_legacy() -> ConsumerPath:
    """Explicit rollback handle: select legacy without code revert."""
    return resolve_consumer_path(explicit=ConsumerPath.LEGACY)


__all__ = ["read_context", "rollback_to_legacy"]
