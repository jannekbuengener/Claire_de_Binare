"""Legacy Claire context/brain path facade preserved for #18 parity.

This does **not** remove or replace existing Claire SurrealDB / MCP tooling.
It provides a stable, selectable handle so #13 can prove both paths exist.
"""

from __future__ import annotations

from typing import Any, Mapping

from tools.agent_brain.adapter import ConsumerResult
from tools.agent_brain.policy import assert_claire_consumer_policy, attach_claire_policy


class LegacyContextPath:
    """Minimal read-only facade over the in-repo Context Package v2 builder."""

    PATH_NAME = "legacy"

    def context_read(
        self,
        *,
        target_scope: str,
        artifacts: list[Mapping[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> ConsumerResult:
        policy = assert_claire_consumer_policy(target_scope=target_scope, tags=tags)
        from tools.surrealdb.context_package_v2 import (
            ContextPackageV2Request,
            build_context_package_v2,
        )

        package = build_context_package_v2(
            ContextPackageV2Request(
                target_scope=target_scope,
                artifacts=list(artifacts or ()),
            )
        )
        data = attach_claire_policy(
            {
                "package": package,
                "legacy_owner": "tools.surrealdb.context_package_v2",
            },
            policy,
        )
        return ConsumerResult(
            ok=True,
            operation="context_read",
            path=self.PATH_NAME,
            data=data,
            error=None,
            agent_brain_version=None,
            limitations=("legacy_claire_path",),
        )


__all__ = ["LegacyContextPath"]
