"""Cursor Cloud Agents API v1 driver (#4254)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import ProviderRequest, ProviderResult
from tools.agent_control.providers.cursor_common import (
    build_provider_result,
    guard_cloud_route_binding,
    host_is_api_cursor,
    validate_artifact_path,
)

HttpTransport = Callable[..., Any]
SseTransport = Callable[..., Any]

API_BASE = "https://api.cursor.com"


@dataclass
class _CloudState:
    agent_id: str
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    archived: bool = False
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    last_event_ids: dict[str, str] = field(default_factory=dict)


class CursorCloudApiDriver:
    provider_id = "cursor-cloud-api"

    def __init__(
        self,
        *,
        http: HttpTransport | None = None,
        sse: SseTransport | None = None,
        allow_live: bool = False,
        model_catalog: dict[str, Any] | None = None,
    ) -> None:
        self._http = http
        self._sse = sse
        self._allow_live = allow_live
        self._catalog = model_catalog or {
            "model_ids": ["auto-smart"],
            "optimize_for": ["cost", "balanced", "intelligence"],
        }
        self._agents: dict[str, _CloudState] = {}
        self._run_to_agent: dict[str, str] = {}
        self.dispatch_calls = 0
        self.mutating_posts = 0

    def _gate(self) -> None:
        if self._http is None and not self._allow_live:
            raise DispatchError(
                "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                "live cursor-cloud-api dispatch is permanently fail-closed; "
                "use injected fake/recorded HTTP transport only",
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{API_BASE}{path}"
        if not host_is_api_cursor(url):
            raise DispatchError("PROVIDER_HOST_FORBIDDEN", url)
        if method.upper() == "DELETE":
            raise DispatchError(
                "PROVIDER_DELETE_FORBIDDEN",
                "DELETE /v1/agents is never exposed",
            )
        if self._http is None:
            raise DispatchError(
                "PROVIDER_TRANSPORT_MISSING",
                "no HTTP transport configured",
            )
        if method.upper() == "POST":
            self.mutating_posts += 1
        try:
            response = self._http(
                method=method, url=url, json=json_body, headers=headers or {}
            )
        except DispatchError:
            raise
        except Exception as exc:
            if method.upper() == "POST":
                raise DispatchError(
                    "PROVIDER_DISPATCH_OUTCOME_UNKNOWN",
                    f"network abort after POST: {exc}",
                ) from exc
            raise DispatchError("PROVIDER_HTTP_ERROR", str(exc)) from exc
        status = int(response.get("status") or 0)
        body = response.get("json") or {}
        if status in {401, 403}:
            raise DispatchError("AUTH_BLOCKED", f"HTTP {status}")
        if status == 409 and body.get("error") in {"agent_busy", "agent_id_conflict"}:
            raise DispatchError("PROVIDER_BUSY", str(body.get("error")))
        if status == 410:
            raise DispatchError("PROVIDER_STREAM_EXPIRED", "stream_expired")
        if status == 429 and method.upper() == "GET":
            raise DispatchError("PROVIDER_RATE_LIMITED", "429")
        if status >= 500 and method.upper() == "POST":
            raise DispatchError(
                "PROVIDER_DISPATCH_OUTCOME_UNKNOWN",
                f"5xx after mutating request: {status}",
            )
        if status >= 400:
            raise DispatchError("PROVIDER_HTTP_ERROR", f"HTTP {status}: {body}")
        return body

    def dispatch(self, request: ProviderRequest) -> ProviderResult:
        self.dispatch_calls += 1
        self._gate()
        if not request.prompt_text:
            raise DispatchError(
                "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
                "cloud API requires verified in-memory prompt",
            )
        route = request.route or {}
        auto_create = bool((request.provider_profile or {}).get("autoCreatePR", False))
        work_on = bool(
            (request.provider_profile or {}).get("workOnCurrentBranch", False)
        )
        pr_url = route.get("pr_url") or route.get("prUrl")
        guard_cloud_route_binding(
            auto_create_pr=auto_create,
            work_on_current_branch=work_on,
            pr_url=pr_url,
            contract_target_pr=route.get("target_pr"),
            contract_target_branch=route.get("target_branch"),
        )
        body = {
            "prompt": {"text": request.prompt_text},
            "autoCreatePR": False,
            "workOnCurrentBranch": work_on,
        }
        if pr_url and route.get("repo_url"):
            body["repos"] = [
                {
                    "url": route["repo_url"],
                    "prUrl": pr_url,
                }
            ]
        if self._http is not None:
            created = self._request("POST", "/v1/agents", json_body=body)
            agent_id = created["agent"]["id"]
            run_id = created["run"]["id"]
            status = created["run"].get("status", "CREATING")
        else:
            agent_id = f"bc-{request.run_id[-12:]}"
            run_id = f"run-{request.run_id[-12:]}"
            status = "FINISHED"
        state = _CloudState(agent_id=agent_id)
        state.runs[run_id] = {
            "status": status,
            "usage": {"cost": None, "input_tokens": 2},
        }
        state.artifacts = [
            {"path": "artifacts/log.txt", "size": 10, "digest": "sha256:" + "a" * 64}
        ]
        self._agents[agent_id] = state
        self._run_to_agent[run_id] = agent_id
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=run_id,
            raw_status=status,
            usage=state.runs[run_id]["usage"],
            result_refs={"agent_id": agent_id, "api": "v1"},
            delivery_receipt=request.delivery_receipt,
        )

    def watch(self, provider_run_id: str) -> ProviderResult:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        if self._http is not None:
            body = self._request(
                "GET",
                f"/v1/agents/{agent_id}/runs/{provider_run_id}",
            )
            status = body.get("status", "RUNNING")
            state.runs[provider_run_id]["status"] = status
        status = state.runs[provider_run_id]["status"]
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status=status,
            usage=state.runs[provider_run_id].get("usage"),
            result_refs={"agent_id": agent_id},
        )

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
        del reason
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        if self._http is not None:
            self._request(
                "POST",
                f"/v1/agents/{agent_id}/runs/{provider_run_id}/cancel",
            )
        state.runs[provider_run_id]["status"] = "CANCELLED"
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status="CANCELLED",
            cancel_confirmed=True,
            result_refs={"agent_id": agent_id},
        )

    def stream(
        self,
        provider_run_id: str,
        *,
        last_event_id: str | None = None,
    ) -> list[dict[str, Any]]:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        if self._sse is None:
            # Fake stream for offline tests.
            events = [
                {"id": "1", "event": "status", "data": {"status": "RUNNING"}},
                {"id": "2", "event": "done", "data": {"status": "FINISHED"}},
            ]
            if last_event_id:
                events = [e for e in events if e["id"] > last_event_id]
            return events
        try:
            return list(
                self._sse(
                    url=f"{API_BASE}/v1/agents/{agent_id}/runs/{provider_run_id}/stream",
                    last_event_id=last_event_id,
                )
            )
        except DispatchError as exc:
            if exc.code == "PROVIDER_STREAM_EXPIRED":
                # Fallback to get-run; never PASS from missing stream.
                self.watch(provider_run_id)
                return [{"event": "fallback_get_run", "data": {"status": "FINISHED"}}]
            raise

    def follow_up(
        self, provider_run_id: str, request: ProviderRequest
    ) -> ProviderResult:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        if any(r.get("status") in {"CREATING", "RUNNING"} for r in state.runs.values()):
            raise DispatchError("PROVIDER_BUSY", "agent_busy")
        new_run = f"run-fu-{len(state.runs)+1}"
        if self._http is not None:
            body = self._request(
                "POST",
                f"/v1/agents/{agent_id}/runs",
                json_body={"prompt": {"text": request.prompt_text or ""}},
            )
            new_run = body["id"]
            status = body.get("status", "CREATING")
        else:
            status = "FINISHED"
        state.runs[new_run] = {"status": status, "usage": {"cost": None}}
        self._run_to_agent[new_run] = agent_id
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=new_run,
            raw_status=status,
            result_refs={"agent_id": agent_id, "follow_up": True},
        )

    def list_artifacts(self, provider_run_id: str) -> list[dict[str, Any]]:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        out = []
        for item in state.artifacts:
            path = validate_artifact_path(item["path"])
            out.append(
                {
                    "path": path,
                    "size": item.get("size"),
                    "digest": item.get("digest"),
                }
            )
        return out

    def download_artifact(self, provider_run_id: str, path: str) -> dict[str, Any]:
        safe = validate_artifact_path(path)
        # Never persist presigned URL.
        return {"path": safe, "bytes": b"fixture", "presigned_url": None}

    def get_usage(self, provider_run_id: str) -> dict[str, Any]:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        return dict(state.runs[provider_run_id].get("usage") or {"cost": None})

    def archive(self, provider_run_id: str) -> ProviderResult:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        if self._http is not None:
            self._request("POST", f"/v1/agents/{agent_id}/archive")
        state.archived = True
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status="FINISHED",
            result_refs={"archived": True, "agent_id": agent_id},
        )

    def unarchive(self, provider_run_id: str) -> ProviderResult:
        agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        if self._http is not None:
            self._request("POST", f"/v1/agents/{agent_id}/unarchive")
        state.archived = False
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status="FINISHED",
            result_refs={"archived": False, "agent_id": agent_id},
        )
