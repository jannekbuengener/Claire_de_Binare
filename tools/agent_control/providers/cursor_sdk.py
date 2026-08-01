"""Cursor Python SDK driver (primary adapter surface, #4254)."""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Callable

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import ProviderRequest, ProviderResult
from tools.agent_control.providers.cursor_common import (
    build_provider_result,
    validate_router_selection,
)


@dataclass
class FakeSdkRun:
    run_id: str
    status: str = "RUNNING"
    text: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    busy: bool = False


@dataclass
class FakeSdkAgent:
    agent_id: str
    runtime: str
    runs: list[FakeSdkRun] = field(default_factory=list)
    archived: bool = False

    def send(self, prompt: str, *, idempotency_key: str | None = None) -> FakeSdkRun:
        del prompt, idempotency_key
        if self.archived:
            raise DispatchError("PROVIDER_ARCHIVED", "agent archived")
        if self.runs and self.runs[-1].status in {"CREATING", "RUNNING"}:
            raise DispatchError("PROVIDER_BUSY", "AgentBusyError")
        run = FakeSdkRun(
            run_id=f"{'bc' if self.runtime == 'cloud' else 'agent'}-run-{len(self.runs)+1}",
            status="FINISHED",
            text="ok",
            usage={
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
                "cost": None,
            },
        )
        self.runs.append(run)
        return run

    def cancel(self, run_id: str) -> FakeSdkRun:
        for run in self.runs:
            if run.run_id == run_id:
                run.status = "CANCELLED"
                return run
        raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", run_id)

    def archive(self) -> None:
        self.archived = True

    def unarchive(self) -> None:
        self.archived = False

    def get_usage(self) -> dict[str, Any]:
        if not self.runs:
            return {"cost": None}
        return dict(self.runs[-1].usage)


SdkClientFactory = Callable[..., Any]


class CursorSdkDriver:
    provider_id = "cursor-sdk"

    def __init__(
        self,
        *,
        client_factory: SdkClientFactory | None = None,
        allow_live: bool = False,
        model_catalog: dict[str, Any] | None = None,
        runtime: str = "local",
    ) -> None:
        self._client_factory = client_factory
        self._allow_live = allow_live
        self._catalog = model_catalog or {
            "model_ids": ["auto-smart", "composer-2"],
            "optimize_for": ["cost", "balanced", "intelligence"],
        }
        self._runtime = runtime
        self._agents: dict[str, FakeSdkAgent] = {}
        self._run_index: dict[str, str] = {}
        self.dispatch_calls = 0

    def _require_injected_or_block(self) -> None:
        if self._client_factory is None and not self._allow_live:
            raise DispatchError(
                "CURSOR_ENVIRONMENT_PROFILE_NOT_READY",
                "live cursor-sdk dispatch blocked until #4255 environment profile",
            )

    def package_version(self) -> str | None:
        try:
            return version("cursor-sdk")
        except PackageNotFoundError:
            return None

    def _lazy_import_probe(self) -> None:
        if self._client_factory is not None:
            return
        try:
            import_module("cursor_sdk")
        except ImportError as exc:
            raise DispatchError(
                "PROVIDER_SDK_MISSING",
                "cursor-sdk package is not installed",
            ) from exc

    def dispatch(self, request: ProviderRequest) -> ProviderResult:
        self.dispatch_calls += 1
        self._require_injected_or_block()
        if self._client_factory is None:
            self._lazy_import_probe()
            raise DispatchError(
                "CURSOR_ENVIRONMENT_PROFILE_NOT_READY",
                "live cursor-sdk execution is not enabled in #4254",
            )
        if not request.prompt_text:
            raise DispatchError(
                "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
                "cursor-sdk requires in-memory prompt text from verified work order",
            )
        optimize_for = (request.provider_profile or {}).get("optimize_for", "balanced")
        validate_router_selection(
            self._catalog,
            model_id=(request.provider_profile or {}).get("model_id", "auto-smart"),
            optimize_for=str(optimize_for),
        )
        agent = FakeSdkAgent(
            agent_id=f"{'bc' if self._runtime == 'cloud' else 'agent'}-{request.run_id[-12:]}",
            runtime=self._runtime,
        )
        run = agent.send(request.prompt_text, idempotency_key=request.idempotency_key)
        self._agents[agent.agent_id] = agent
        self._run_index[run.run_id] = agent.agent_id
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=run.run_id,
            raw_status=run.status,
            usage=run.usage,
            result_refs={
                "agent_id": agent.agent_id,
                "runtime": self._runtime,
                "sdk_version": self.package_version(),
            },
            delivery_receipt=request.delivery_receipt,
        )

    def watch(self, provider_run_id: str) -> ProviderResult:
        agent_id = self._run_index.get(provider_run_id)
        agent = self._agents.get(agent_id or "")
        if agent is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        run = next(r for r in agent.runs if r.run_id == provider_run_id)
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status=run.status,
            usage=run.usage,
            result_refs={"agent_id": agent.agent_id},
        )

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
        del reason
        agent_id = self._run_index.get(provider_run_id)
        agent = self._agents.get(agent_id or "")
        if agent is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        run = agent.cancel(provider_run_id)
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status=run.status,
            usage=run.usage,
            cancel_confirmed=True,
        )

    def follow_up(
        self, provider_run_id: str, request: ProviderRequest
    ) -> ProviderResult:
        agent_id = self._run_index.get(provider_run_id)
        agent = self._agents.get(agent_id or "")
        if agent is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        run = agent.send(
            request.prompt_text or "", idempotency_key=request.idempotency_key
        )
        self._run_index[run.run_id] = agent.agent_id
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=run.run_id,
            raw_status=run.status,
            usage=run.usage,
            result_refs={"agent_id": agent.agent_id, "follow_up": True},
        )

    def archive(self, provider_run_id: str) -> ProviderResult:
        agent_id = self._run_index.get(provider_run_id)
        agent = self._agents.get(agent_id or "")
        if agent is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        agent.archive()
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status="FINISHED",
            result_refs={"archived": True, "agent_id": agent.agent_id},
        )

    def unarchive(self, provider_run_id: str) -> ProviderResult:
        agent_id = self._run_index.get(provider_run_id)
        agent = self._agents.get(agent_id or "")
        if agent is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        agent.unarchive()
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status="FINISHED",
            result_refs={"archived": False, "agent_id": agent.agent_id},
        )

    def get_usage(self, provider_run_id: str) -> dict[str, Any]:
        agent_id = self._run_index.get(provider_run_id)
        agent = self._agents.get(agent_id or "")
        if agent is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        return agent.get_usage()
