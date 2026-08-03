"""Cursor Cloud Agents API v1 driver (#4254 / live pilot #4258)."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse

from tools.agent_control.cursor_preflight import extract_environment_identity
from tools.agent_control.delivery_verify import (
    claimed_delivery_from_git,
    truncate_run_result_text,
)
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
_BC_ID = re.compile(
    r"^bc-(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}|[A-Za-z0-9_-]+-[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)


@dataclass
class _CloudState:
    agent_id: str
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    archived: bool = False
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    last_event_ids: dict[str, str] = field(default_factory=dict)


def _stable_agent_id(request: ProviderRequest) -> str:
    """Client-supplied idempotent agent id (official ``bc-<uuid>`` shape)."""
    seed = f"{request.contract_digest}|{request.idempotency_key or request.run_id}"
    # uuid5 yields a parseable UUID; raw hex slices can fail API UUID validation.
    return f"bc-{uuid.uuid5(uuid.NAMESPACE_URL, seed)}"


class CursorCloudApiDriver:
    provider_id = "cursor-cloud-api"

    def __init__(
        self,
        *,
        http: HttpTransport | None = None,
        sse: SseTransport | None = None,
        allow_live: bool = False,
        model_catalog: dict[str, Any] | None = None,
        human_go_live: bool = False,
    ) -> None:
        self._http = http
        self._sse = sse
        self._allow_live = allow_live
        self._human_go_live = human_go_live
        self._catalog = model_catalog or {
            "model_ids": ["auto-smart"],
            "optimize_for": ["cost", "balanced", "intelligence"],
        }
        self._agents: dict[str, _CloudState] = {}
        self._run_to_agent: dict[str, str] = {}
        self.dispatch_calls = 0
        self.mutating_posts = 0
        if self._http is None and self._allow_live:
            from tools.agent_control.providers.live_http import (
                build_urllib_http_transport_compat,
            )

            self._http = build_urllib_http_transport_compat()

    def _gate(self) -> None:
        if self._http is None and not self._allow_live:
            raise DispatchError(
                "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                "live cursor-cloud-api dispatch is permanently fail-closed; "
                "use injected fake/recorded HTTP transport only",
            )

    def rehydrate(
        self,
        *,
        provider_run_id: str,
        agent_id: str,
        status: str = "RUNNING",
    ) -> None:
        """Restore in-memory maps after process restart (from RunStore refs)."""
        if not provider_run_id or not agent_id:
            raise DispatchError(
                "DISPATCH_PROVIDER_RUN_NOT_FOUND",
                "rehydrate requires provider_run_id and agent_id",
            )
        if not (_BC_ID.match(agent_id) or agent_id.startswith("bc-")):
            raise DispatchError("PROVIDER_AGENT_ID_INVALID", agent_id)
        state = self._agents.get(agent_id) or _CloudState(agent_id=agent_id)
        if provider_run_id not in state.runs:
            state.runs[provider_run_id] = {
                "status": status,
                "usage": {"cost": None},
            }
        self._agents[agent_id] = state
        self._run_to_agent[provider_run_id] = agent_id

    def _resolve_agent(
        self, provider_run_id: str, *, result_refs: dict[str, Any] | None = None
    ) -> tuple[str, _CloudState]:
        agent_id = self._run_to_agent.get(provider_run_id)
        if agent_id is None and result_refs and result_refs.get("agent_id"):
            self.rehydrate(
                provider_run_id=provider_run_id,
                agent_id=str(result_refs["agent_id"]),
            )
            agent_id = self._run_to_agent.get(provider_run_id)
        state = self._agents.get(agent_id or "")
        if state is None or agent_id is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        return agent_id, state

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
        route = dict(request.route or {})
        profile = request.provider_profile or {}
        human_go = bool(self._human_go_live or profile.get("human_go_live_cursor"))
        # autoCreatePR only when Human-GO live path explicitly sets it on profile.
        auto_create = bool(profile.get("autoCreatePR", False)) and human_go
        work_on = bool(profile.get("workOnCurrentBranch", False))
        pr_url = route.get("pr_url") or route.get("prUrl")
        repo_url = route.get("repo_url") or route.get("repository_url")
        if not repo_url:
            repo_url = "https://github.com/jannekbuengener/Claire_de_Binare"
        if work_on and not pr_url and route.get("target_pr"):
            pr_url = f"{str(repo_url).rstrip('/')}/pull/{int(route['target_pr'])}"
        guard_cloud_route_binding(
            auto_create_pr=auto_create,
            work_on_current_branch=work_on,
            pr_url=pr_url if isinstance(pr_url, str) else None,
            contract_target_pr=route.get("target_pr"),
            contract_target_branch=route.get("target_branch"),
            human_go_live=human_go,
        )
        agent_id_client = profile.get("agentId") or _stable_agent_id(request)
        if not _BC_ID.match(str(agent_id_client)) and not str(
            agent_id_client
        ).startswith("bc-"):
            raise DispatchError("PROVIDER_AGENT_ID_INVALID", str(agent_id_client))
        body: dict[str, Any] = {
            "prompt": {"text": request.prompt_text},
            "autoCreatePR": bool(auto_create),
            "workOnCurrentBranch": work_on,
            "agentId": agent_id_client,
        }
        starting_ref = route.get("starting_ref") or route.get("startingRef")
        if not starting_ref and auto_create:
            # Official API: omit or set startingRef; default to main for autoCreatePR.
            starting_ref = "main"
        # Named cloud environment XOR repos (official CreateAgentRequest).
        # Prefer explicit repos + versioned .cursor/environment.json for
        # dashboardless determinism. Optional named env via profile.
        env_req = profile.get("env") if isinstance(profile.get("env"), dict) else None
        use_named_env = bool(env_req and env_req.get("type") and env_req.get("name"))
        if use_named_env:
            body["env"] = {
                "type": str(env_req.get("type") or "cloud"),
                "name": str(env_req["name"]),
            }
        elif pr_url and repo_url:
            body["repos"] = [{"url": repo_url, "prUrl": pr_url}]
        elif repo_url:
            entry: dict[str, Any] = {"url": repo_url}
            if starting_ref:
                entry["startingRef"] = starting_ref
            body["repos"] = [entry]
        requested_env = {
            "binding_mode": (
                "named_cloud_env" if use_named_env else "repos_plus_repo_config"
            ),
            "env": body.get("env"),
            "repos": body.get("repos"),
        }
        git_meta: dict[str, Any] = {"branches": []}
        resolved_env: dict[str, Any] | None = None
        if self._http is not None:
            try:
                created = self._request("POST", "/v1/agents", json_body=body)
            except DispatchError as exc:
                if exc.code == "PROVIDER_BUSY" and "agent_id_conflict" in str(
                    exc.message
                ):
                    # Idempotent resume: fetch existing agent + latest run.
                    existing = self._request("GET", f"/v1/agents/{agent_id_client}")
                    agent_id = existing.get("id") or agent_id_client
                    run_id = existing.get("latestRunId") or existing.get(
                        "latest_run_id"
                    )
                    if not run_id:
                        raise
                    status = "RUNNING"
                    created = {
                        "agent": (
                            existing if isinstance(existing, dict) else {"id": agent_id}
                        ),
                        "run": {"id": run_id, "status": status},
                    }
                else:
                    raise
            else:
                agent_id = created["agent"]["id"]
                run_id = created["run"]["id"]
                status = created["run"].get("status", "CREATING")
            run_body = (
                created.get("run") if isinstance(created.get("run"), dict) else {}
            )
            agent_body = (
                created.get("agent") if isinstance(created.get("agent"), dict) else {}
            )
            resolved_env = extract_environment_identity(agent_body)
            if use_named_env:
                req_name = str(env_req.get("name"))
                got_name = resolved_env.get("name")
                # Fail closed when API returns a conflicting name. Missing name is
                # a public observability gap (PARTIAL) recorded in result_refs.
                if got_name is not None and got_name != req_name:
                    raise DispatchError(
                        "PROVIDER_ENVIRONMENT_MISMATCH",
                        f"requested env.name={req_name!r} resolved={got_name!r}",
                    )
            git_meta = (
                run_body.get("git") if isinstance(run_body.get("git"), dict) else {}
            )
            if not git_meta and isinstance(agent_body.get("git"), dict):
                git_meta = agent_body["git"]
        else:
            agent_id = agent_id_client
            run_id = f"run-{request.run_id[-12:]}"
            status = "FINISHED"
            resolved_env = {
                "type": "cloud",
                "name": (env_req or {}).get("name") if use_named_env else None,
                "environment_public_id": None,
                "environment_version_public_id": None,
            }
            if auto_create:
                git_meta = {
                    "branches": [
                        {
                            "repoUrl": (repo_url or "").replace("https://", ""),
                            "branch": f"cursor/pilot-{request.run_id[-8:]}",
                            "prUrl": "https://github.com/example/repo/pull/1",
                        }
                    ]
                }
        state = _CloudState(agent_id=agent_id)
        state.runs[run_id] = {
            "status": status,
            "usage": {"cost": None, "input_tokens": 2},
            "git": git_meta,
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
            result_refs={
                "agent_id": agent_id,
                "api": "v1",
                "git": git_meta,
                "claimed_delivery": claimed_delivery_from_git(git_meta),
                "delivery_verified": False,
                "raw_status": status,
                "environment_requested": requested_env,
                "environment_resolved": resolved_env,
            },
            delivery_receipt=request.delivery_receipt,
            error_code=(
                "PROVIDER_RUN_ERROR" if str(status).upper() == "ERROR" else None
            ),
        )

    def watch(self, provider_run_id: str) -> ProviderResult:
        agent_id, state = self._resolve_agent(provider_run_id)
        run_result_text: str | None = None
        duration_ms: int | None = None
        stream_error: dict[str, Any] | None = None
        if self._http is not None:
            body = self._request(
                "GET",
                f"/v1/agents/{agent_id}/runs/{provider_run_id}",
            )
            status = body.get("status", "RUNNING")
            state.runs.setdefault(provider_run_id, {"usage": {"cost": None}})
            state.runs[provider_run_id]["status"] = status
            if isinstance(body.get("git"), dict):
                state.runs[provider_run_id]["git"] = body["git"]
            if isinstance(body.get("result"), str):
                run_result_text = body["result"]
                state.runs[provider_run_id]["result"] = run_result_text
            if isinstance(body.get("durationMs"), int):
                duration_ms = body["durationMs"]
                state.runs[provider_run_id]["duration_ms"] = duration_ms
            # OpenAPI Run has no structured error field; capture if present anyway.
            if isinstance(body.get("error"), dict):
                state.runs[provider_run_id]["error"] = body["error"]
        status = state.runs[provider_run_id]["status"]
        git_meta = state.runs[provider_run_id].get("git") or {}
        if run_result_text is None and isinstance(
            state.runs[provider_run_id].get("result"), str
        ):
            run_result_text = state.runs[provider_run_id]["result"]
        if duration_ms is None and isinstance(
            state.runs[provider_run_id].get("duration_ms"), int
        ):
            duration_ms = state.runs[provider_run_id]["duration_ms"]
        err = state.runs[provider_run_id].get("error")
        claimed = claimed_delivery_from_git(
            git_meta if isinstance(git_meta, dict) else None
        )
        refs: dict[str, Any] = {
            "agent_id": agent_id,
            "api": "v1",
            "git": git_meta,
            "claimed_delivery": claimed,
            "delivery_verified": False,
            "raw_status": status,
        }
        truncated = truncate_run_result_text(run_result_text)
        if truncated is not None:
            refs["run_result_text"] = truncated
        if duration_ms is not None:
            refs["duration_ms"] = duration_ms
        if isinstance(err, dict):
            refs["run_error"] = {
                "code": err.get("code"),
                "message": err.get("message"),
            }
        if stream_error:
            refs["stream_error"] = stream_error
        error_code = None
        if str(status).upper() == "ERROR":
            error_code = (
                isinstance(err, dict) and err.get("code")
            ) or "PROVIDER_RUN_ERROR"
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status=status,
            usage=state.runs[provider_run_id].get("usage"),
            result_refs=refs,
            error_code=str(error_code) if error_code else None,
        )

    def read_stream_diagnostics(self, provider_run_id: str) -> dict[str, Any]:
        """Read-only SSE snapshot for an existing run (no follow-up / no create)."""
        agent_id, state = self._resolve_agent(provider_run_id)
        events = self.stream(provider_run_id)
        out: dict[str, Any] = {
            "agent_id": agent_id,
            "provider_run_id": provider_run_id,
            "events": [],
            "result_text": None,
            "stream_error": None,
            "git": None,
            "terminal_status": None,
        }
        for event in events:
            if not isinstance(event, dict):
                continue
            name = event.get("event")
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            compact = {"event": name}
            if name == "error":
                compact["code"] = data.get("code")
                compact["message"] = data.get("message")
                out["stream_error"] = {
                    "code": data.get("code"),
                    "message": data.get("message"),
                }
            elif name == "result":
                compact["status"] = data.get("status")
                out["terminal_status"] = data.get("status")
                if isinstance(data.get("text"), str):
                    out["result_text"] = truncate_run_result_text(data.get("text"))
                if isinstance(data.get("git"), dict):
                    out["git"] = data.get("git")
                    state.runs.setdefault(provider_run_id, {})["git"] = data["git"]
            elif name == "status":
                compact["status"] = data.get("status")
                out["terminal_status"] = data.get("status") or out["terminal_status"]
            out["events"].append(compact)
            if len(out["events"]) >= 50:
                break
        return out

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
        del reason
        agent_id, state = self._resolve_agent(provider_run_id)
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
        agent_id, state = self._resolve_agent(provider_run_id)
        del state
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
            # Official v1: {"run": {"id": "...", "status": "..."}}; accept legacy flat id.
            run_obj = body.get("run") if isinstance(body.get("run"), dict) else body
            new_run = str(run_obj.get("id") or body.get("id") or new_run)
            status = str(run_obj.get("status") or body.get("status") or "CREATING")
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
        # Documented v1 path is agent-scoped: GET /v1/agents/{id}/artifacts
        # (NOT /runs/{runId}/artifacts — that route 404s and is not evidence).
        if self._http is not None and agent_id:
            body = self._request("GET", f"/v1/agents/{agent_id}/artifacts")
            items = body.get("items") if isinstance(body, dict) else None
            if isinstance(items, list):
                state.artifacts = [
                    {
                        "path": item.get("path"),
                        "size": item.get("sizeBytes") or item.get("size"),
                        "digest": item.get("digest") or item.get("sha256"),
                    }
                    for item in items
                    if isinstance(item, dict) and item.get("path")
                ]
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
        # Documented v1 path is agent-scoped: GET /v1/agents/{id}/usage
        # Optional ?runId= filter. Run-scoped /runs/{id}/usage is NOT documented.
        if self._http is not None and agent_id:
            body = self._request(
                "GET",
                f"/v1/agents/{agent_id}/usage?runId={provider_run_id}",
            )
            usage: dict[str, Any] = {"cost": None}
            if isinstance(body, dict):
                runs = body.get("runs") if isinstance(body.get("runs"), list) else []
                matched = None
                for item in runs:
                    if isinstance(item, dict) and item.get("id") == provider_run_id:
                        matched = item
                        break
                if matched is None and runs:
                    matched = runs[0] if isinstance(runs[0], dict) else None
                if isinstance(matched, dict):
                    u = (
                        matched.get("usage")
                        if isinstance(matched.get("usage"), dict)
                        else {}
                    )
                    cost = (
                        matched.get("cost")
                        if isinstance(matched.get("cost"), dict)
                        else {}
                    )
                    usage = {
                        "cost": cost.get("chargedCents"),
                        "input_tokens": u.get("inputTokens"),
                        "output_tokens": u.get("outputTokens"),
                        "total_tokens": u.get("totalTokens"),
                        "usage_uuid": matched.get("usageUuid"),
                        "source_path": f"/v1/agents/{agent_id}/usage",
                    }
                elif isinstance(body.get("totalUsage"), dict):
                    tu = body["totalUsage"]
                    usage = {
                        "cost": (
                            (body.get("cost") or {}).get("chargedCents")
                            if isinstance(body.get("cost"), dict)
                            else None
                        ),
                        "input_tokens": tu.get("inputTokens"),
                        "output_tokens": tu.get("outputTokens"),
                        "total_tokens": tu.get("totalTokens"),
                        "source_path": f"/v1/agents/{agent_id}/usage",
                    }
            state.runs[provider_run_id]["usage"] = usage
            return dict(usage)
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
