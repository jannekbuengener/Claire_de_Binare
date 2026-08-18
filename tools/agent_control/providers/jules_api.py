"""Official Jules REST v1alpha provider adapter for the CDB ACP (#4461)."""

from __future__ import annotations

import re
from typing import Any, Callable

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import ProviderRequest, ProviderResult
from tools.agent_control.providers.jules_common import (
    build_jules_provider_result,
    host_is_jules,
    normalize_activities,
    normalize_pull_requests,
)

HttpTransport = Callable[..., Any]
API_BASE = "https://jules.googleapis.com"
DEFAULT_CDB_SOURCE = "sources/github/jannekbuengener/Claire_de_Binare"
_SESSION_NAME = re.compile(r"^sessions/[A-Za-z0-9_-]+$")
_SOURCE_NAME = re.compile(r"^sources/[A-Za-z0-9_./-]+$")


class JulesApiDriver:
    """CDB provider adapter over documented Jules v1alpha operations only.

    The common ChatGPT/MCP Jules gateway remains the preferred coarse dispatch
    path where it is sufficient. This adapter exists for CDB-specific governed
    lifecycle operations: explicit plan approval, structured activities,
    follow-up, and result/PR handoff.
    """

    provider_id = "jules-api"

    def __init__(
        self,
        *,
        http: HttpTransport | None = None,
        allow_live: bool = False,
    ) -> None:
        self._http = http
        self._allow_live = allow_live
        self.dispatch_calls = 0
        self.mutating_posts = 0
        if self._http is None and allow_live:
            from tools.agent_control.providers.jules_live_http import (
                build_jules_urllib_http_transport,
            )

            self._http = build_jules_urllib_http_transport()

    def _gate(self) -> None:
        if self._http is None:
            raise DispatchError(
                "PROVIDER_LIVE_DISPATCH_FORBIDDEN",
                "jules-api requires an injected fake/recorded HTTP transport or explicit live enable",
            )

    @staticmethod
    def _session_name(value: str) -> str:
        text = str(value).strip()
        if not _SESSION_NAME.fullmatch(text):
            raise DispatchError("PROVIDER_RUN_ID_INVALID", "invalid Jules session name")
        return text

    @staticmethod
    def _source_name(value: str) -> str:
        text = str(value).strip()
        if not _SOURCE_NAME.fullmatch(text) or ".." in text.split("/"):
            raise DispatchError("PROVIDER_SOURCE_INVALID", "invalid Jules source name")
        return text

    @staticmethod
    def _assert_network_policy(request: ProviderRequest) -> None:
        policy = (request.budget or {}).get("network_policy") or {}
        domains = set(policy.get("allowed_domains") or [])
        if policy.get("mode") != "allowlist" or "jules.googleapis.com" not in domains:
            raise DispatchError(
                "PROVIDER_NETWORK_POLICY_BLOCKED",
                "Jules dispatch requires contract allowlist for jules.googleapis.com",
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._gate()
        url = f"{API_BASE}{path}"
        if not host_is_jules(url):
            raise DispatchError("PROVIDER_HOST_FORBIDDEN", url)
        method_u = method.upper()
        if method_u == "DELETE":
            raise DispatchError(
                "PROVIDER_DELETE_FORBIDDEN",
                "Jules v1alpha DELETE is not a documented CDB provider operation",
            )
        if method_u == "POST":
            self.mutating_posts += 1
        assert self._http is not None
        try:
            response = self._http(
                method=method_u,
                url=url,
                json=json_body,
                headers={},
            )
        except DispatchError:
            raise
        except Exception as exc:
            if method_u == "POST":
                raise DispatchError(
                    "PROVIDER_DISPATCH_OUTCOME_UNKNOWN",
                    f"network abort after Jules POST: {type(exc).__name__}",
                ) from exc
            raise DispatchError("PROVIDER_HTTP_ERROR", type(exc).__name__) from exc
        status = int(response.get("status") or 0)
        body = response.get("json") or {}
        if status in {401, 403}:
            raise DispatchError("AUTH_BLOCKED", f"HTTP {status}")
        if status == 429:
            raise DispatchError("PROVIDER_RATE_LIMITED", "HTTP 429")
        if status >= 500 and method_u == "POST":
            raise DispatchError(
                "PROVIDER_DISPATCH_OUTCOME_UNKNOWN",
                f"5xx after Jules mutating request: {status}",
            )
        if status >= 400:
            raise DispatchError("PROVIDER_HTTP_ERROR", f"HTTP {status}")
        if not isinstance(body, dict):
            raise DispatchError(
                "PROVIDER_MALFORMED_RESPONSE", "Jules response is not an object"
            )
        return body

    def dispatch(self, request: ProviderRequest) -> ProviderResult:
        self.dispatch_calls += 1
        self._gate()
        self._assert_network_policy(request)
        if not request.prompt_text:
            raise DispatchError(
                "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
                "jules-api requires verified in-memory prompt text",
            )
        profile = dict(request.provider_profile or {})
        route = dict(request.route or {})
        source = self._source_name(
            str(
                profile.get("source") or route.get("jules_source") or DEFAULT_CDB_SOURCE
            )
        )
        starting_branch = str(
            route.get("starting_ref") or profile.get("starting_branch") or "main"
        ).strip()
        if not starting_branch or any(ch in starting_branch for ch in "\r\n\x00"):
            raise DispatchError(
                "PROVIDER_ROUTE_BINDING_MISSING", "invalid Jules starting branch"
            )

        require_plan_approval = bool(profile.get("require_plan_approval", True))
        auto_pr_requested = bool(profile.get("auto_create_pr", True))
        open_pr_allowed = bool((request.effective_permissions or {}).get("open_pr"))
        body: dict[str, Any] = {
            "prompt": request.prompt_text,
            "sourceContext": {
                "source": source,
                "githubRepoContext": {"startingBranch": starting_branch},
            },
            "requirePlanApproval": require_plan_approval,
            "title": str(profile.get("title") or f"CDB {request.contract_id}")[:120],
        }
        if auto_pr_requested and open_pr_allowed:
            body["automationMode"] = "AUTO_CREATE_PR"

        created = self._request("POST", "/v1alpha/sessions", json_body=body)
        session_name = self._session_name(str(created.get("name") or ""))
        raw_state = str(created.get("state") or "STATE_UNSPECIFIED")
        refs = {
            "api": "v1alpha",
            "session_name": session_name,
            "session_id": created.get("id"),
            "session_url": created.get("url"),
            "raw_state": raw_state,
            "require_plan_approval": require_plan_approval,
            "awaiting_plan_approval": raw_state == "AWAITING_PLAN_APPROVAL",
            "auto_create_pr_requested": auto_pr_requested,
            "auto_create_pr_effective": bool(
                body.get("automationMode") == "AUTO_CREATE_PR"
            ),
            "pull_requests": normalize_pull_requests(created.get("outputs")),
        }
        return build_jules_provider_result(
            provider_run_id=session_name,
            raw_status=raw_state,
            result_refs=refs,
        )

    def list_sessions(self, *, page_size: int = 30) -> dict[str, Any]:
        """List safe Session metadata without prompts or provider-authored text."""
        if (
            not isinstance(page_size, int)
            or isinstance(page_size, bool)
            or not 1 <= page_size <= 100
        ):
            raise DispatchError(
                "PROVIDER_LIST_PAGE_SIZE_INVALID",
                "Jules sessions page_size must be an integer from 1 to 100",
            )
        payload = self._request("GET", f"/v1alpha/sessions?pageSize={page_size}")
        rows = (
            payload.get("sessions") if isinstance(payload.get("sessions"), list) else []
        )
        sessions: list[dict[str, Any]] = []
        for item in rows[:page_size]:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            try:
                safe_name = self._session_name(name)
            except DispatchError:
                continue
            sessions.append(
                {
                    "name": safe_name,
                    "id": item.get("id"),
                    "state": item.get("state"),
                    "url": item.get("url"),
                    "pull_requests": normalize_pull_requests(item.get("outputs")),
                }
            )
        return {
            "sessions": sessions,
            "count": len(sessions),
            "next_page_token_present": bool(payload.get("nextPageToken")),
        }

    def list_activities(self, provider_run_id: str) -> dict[str, Any]:
        session = self._session_name(provider_run_id)
        payload = self._request(
            "GET",
            f"/v1alpha/{session}/activities?pageSize=100",
        )
        return normalize_activities(payload)

    def watch(self, provider_run_id: str) -> ProviderResult:
        session = self._session_name(provider_run_id)
        current = self._request("GET", f"/v1alpha/{session}")
        raw_state = str(current.get("state") or "STATE_UNSPECIFIED")
        activities = self.list_activities(session)
        refs = {
            "api": "v1alpha",
            "session_name": session,
            "session_id": current.get("id"),
            "session_url": current.get("url"),
            "raw_state": raw_state,
            "awaiting_plan_approval": raw_state == "AWAITING_PLAN_APPROVAL",
            "awaiting_user_feedback": raw_state == "AWAITING_USER_FEEDBACK",
            "paused": raw_state == "PAUSED",
            "activities": activities,
            "pull_requests": normalize_pull_requests(current.get("outputs")),
        }
        return build_jules_provider_result(
            provider_run_id=session,
            raw_status=raw_state,
            result_refs=refs,
        )

    def approve_plan(self, provider_run_id: str) -> ProviderResult:
        session = self._session_name(provider_run_id)
        current = self._request("GET", f"/v1alpha/{session}")
        if str(current.get("state")) != "AWAITING_PLAN_APPROVAL":
            raise DispatchError(
                "PROVIDER_PLAN_APPROVAL_INVALID_STATE",
                "Jules plan approval requires AWAITING_PLAN_APPROVAL",
            )
        self._request("POST", f"/v1alpha/{session}:approvePlan", json_body={})
        return self.watch(session)

    def follow_up(
        self, provider_run_id: str, request: ProviderRequest
    ) -> ProviderResult:
        session = self._session_name(provider_run_id)
        if not request.prompt_text:
            raise DispatchError(
                "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
                "Jules follow-up requires verified in-memory prompt text",
            )
        current = self._request("GET", f"/v1alpha/{session}")
        if str(current.get("state") or "STATE_UNSPECIFIED") in {
            "FAILED",
            "STATE_UNSPECIFIED",
        }:
            raise DispatchError(
                "PROVIDER_FOLLOW_UP_INVALID_STATE",
                "Jules follow-up blocked for failed/unknown session",
            )
        self._request(
            "POST",
            f"/v1alpha/{session}:sendMessage",
            json_body={"prompt": request.prompt_text},
        )
        return self.watch(session)

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
        """Fail closed: the documented Jules v1alpha surface has no cancel RPC."""
        del reason
        session = self._session_name(provider_run_id)
        return build_jules_provider_result(
            provider_run_id=session,
            raw_status="STATE_UNSPECIFIED",
            result_refs={
                "api": "v1alpha",
                "session_name": session,
                "cancel_supported": False,
            },
            error_code="PROVIDER_CANCEL_UNSUPPORTED",
            cancel_confirmed=False,
        )
