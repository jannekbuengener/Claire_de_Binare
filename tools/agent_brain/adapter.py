"""Thin Claire adapter over ``agent_brain.protocol`` (public surface only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from tools.agent_brain.errors import (
    ConsumerError,
    ConsumerErrorCode,
    map_protocol_error_code,
)
from tools.agent_brain.pin import PINNED_AGENT_BRAIN_VERSION, verify_runtime_pin
from tools.agent_brain.policy import assert_claire_consumer_policy, attach_claire_policy

# Public-surface-only imports. Do not import agent_brain.core / surrealdb internals.
InvokeFn = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ConsumerResult:
    ok: bool
    operation: str
    path: str
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    agent_brain_version: str | None = None
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "operation": self.operation,
            "path": self.path,
            "data": self.data,
            "error": self.error,
            "agent_brain_version": self.agent_brain_version,
            "limitations": list(self.limitations),
        }


class AgentBrainAdapter:
    """Translate Claire inputs ↔ Agent Brain public protocol responses."""

    PATH_NAME = "agent_brain"

    def __init__(
        self,
        *,
        invoke_fn: InvokeFn | None = None,
        expected_version: str = PINNED_AGENT_BRAIN_VERSION,
        verify_pin: bool = True,
    ) -> None:
        self._expected_version = expected_version
        self._verify_pin = verify_pin
        if invoke_fn is not None:
            self._invoke = invoke_fn
        else:
            from agent_brain.protocol import invoke as protocol_invoke

            self._invoke = protocol_invoke

    def verify_pin(self) -> str:
        if not self._verify_pin:
            return self._expected_version
        return verify_runtime_pin(expected=self._expected_version)

    def health(self) -> ConsumerResult:
        self.verify_pin()
        return self._call("health", {})

    def capabilities(self) -> ConsumerResult:
        self.verify_pin()
        return self._call("capabilities", {})

    def require_capability(self, capability: str) -> None:
        report = self.capabilities()
        if not report.ok or report.data is None:
            raise ConsumerError(
                ConsumerErrorCode.CAPABILITY_UNAVAILABLE,
                "capabilities readback failed",
                details={"capability": capability, "error": report.error},
            )
        items = report.data.get("capabilities") or []
        match = next(
            (
                item
                for item in items
                if isinstance(item, Mapping) and item.get("capability") == capability
            ),
            None,
        )
        if match is None or match.get("state") != "available":
            raise ConsumerError(
                ConsumerErrorCode.CAPABILITY_UNAVAILABLE,
                f"required capability unavailable: {capability}",
                details={"capability": capability, "state": (match or {}).get("state")},
            )

    def context_read(
        self,
        *,
        target_scope: str,
        artifacts: list[Mapping[str, Any]] | None = None,
        mode: str = "package",
        tags: list[str] | None = None,
        generated_at_or_as_of: str = "2026-10-31T12:00:00Z",
    ) -> ConsumerResult:
        policy = assert_claire_consumer_policy(target_scope=target_scope, tags=tags)
        self.verify_pin()
        self.require_capability("context_read")
        payload = {
            "mode": mode,
            "target_scope": target_scope,
            "source_priority": {
                "ordered_sources": [
                    "github_live",
                    "repo_live",
                    "verified_context_db_mcp_evidence",
                    "canonical_governance_files",
                    "ledger_files",
                    "memory",
                ]
            },
            "artifacts": list(artifacts or []),
            "generated_at_or_as_of": generated_at_or_as_of,
        }
        result = self._call("context_read", payload)
        if result.ok and result.data is not None:
            return ConsumerResult(
                ok=True,
                operation=result.operation,
                path=result.path,
                data=attach_claire_policy(result.data, policy),
                error=None,
                agent_brain_version=result.agent_brain_version,
                limitations=result.limitations,
            )
        return result

    def _call(self, operation: str, payload: Mapping[str, Any]) -> ConsumerResult:
        response = self._invoke(operation, dict(payload))
        version = self._expected_version
        # ProtocolResponse is a dataclass with .ok / .data / .error / .limitations
        ok = bool(getattr(response, "ok", False))
        limitations = tuple(getattr(response, "limitations", ()) or ())
        if ok:
            data = getattr(response, "data", None)
            return ConsumerResult(
                ok=True,
                operation=operation,
                path=self.PATH_NAME,
                data=dict(data) if isinstance(data, Mapping) else {"value": data},
                error=None,
                agent_brain_version=version,
                limitations=tuple(str(x) for x in limitations),
            )

        err = getattr(response, "error", None)
        if err is None:
            mapped = ConsumerError(
                ConsumerErrorCode.INTERNAL_FAILURE,
                "protocol response not ok without structured error",
            )
        else:
            code = map_protocol_error_code(getattr(err, "code", None))
            # Never reinterpret unavailable as empty success — already failure path.
            mapped = ConsumerError(
                code,
                str(getattr(err, "message", "protocol error")),
                details=dict(getattr(err, "details", None) or {}),
            )
        return ConsumerResult(
            ok=False,
            operation=operation,
            path=self.PATH_NAME,
            data=None,
            error=mapped.to_dict(),
            agent_brain_version=version,
            limitations=tuple(str(x) for x in limitations),
        )


__all__ = ["AgentBrainAdapter", "ConsumerResult"]
