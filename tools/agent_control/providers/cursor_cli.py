"""Cursor headless CLI driver (#4254)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import ProviderRequest, ProviderResult
from tools.agent_control.providers.cursor_common import build_provider_result

ProcessRunner = Callable[..., Any]


@dataclass
class _CliRun:
    session_id: str
    status: str
    events: list[dict[str, Any]] = field(default_factory=list)
    exit_code: int = 0


def parse_stream_json_lines(
    lines: list[str],
) -> tuple[str | None, str, list[dict[str, Any]]]:
    """Parse NDJSON stream-json. Only terminal result/subtype=success => SUCCEEDED."""
    events: list[dict[str, Any]] = []
    session_id: str | None = None
    saw_success = False
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            event = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DispatchError(
                "PROVIDER_CLI_MALFORMED_JSON",
                f"malformed NDJSON: {exc}",
            ) from exc
        if not isinstance(event, dict):
            raise DispatchError("PROVIDER_CLI_MALFORMED_JSON", "event must be object")
        # Skip duplicate partial flush events.
        if event.get("type") == "assistant":
            if "model_call_id" in event:
                continue
            if "timestamp_ms" not in event and event.get("message"):
                # final flush duplicate
                continue
        events.append(event)
        if isinstance(event.get("session_id"), str):
            session_id = event["session_id"]
        if event.get("type") == "result" and event.get("subtype") == "success":
            saw_success = True
            session_id = event.get("session_id") or session_id
    if saw_success:
        return session_id, "FINISHED", events
    return session_id, "ERROR", events


class CursorCliDriver:
    provider_id = "cursor-cli"

    def __init__(
        self,
        *,
        runner: ProcessRunner | None = None,
        binary: str = "agent",
        allow_live: bool = False,
        allow_force: bool = False,
    ) -> None:
        self._runner = runner
        self._binary = binary
        self._allow_live = allow_live
        self._allow_force = allow_force
        self._runs: dict[str, _CliRun] = {}
        self.dispatch_calls = 0

    def _blocked_live(self) -> None:
        if self._runner is None and not self._allow_live:
            raise DispatchError(
                "CURSOR_ENVIRONMENT_PROFILE_NOT_READY",
                "live cursor-cli dispatch blocked until #4255 environment profile",
            )

    def _build_argv(
        self, request: ProviderRequest, *, force: bool = False
    ) -> list[str]:
        workspace = (request.route or {}).get("workspace") or "."
        workspace_path = Path(workspace).resolve()
        argv = [
            self._binary,
            "--print",
            "--output-format",
            "stream-json",
            "--workspace",
            str(workspace_path),
        ]
        if force:
            if not self._allow_force:
                raise DispatchError(
                    "PROVIDER_CLI_FORCE_FORBIDDEN",
                    "--force/--yolo forbidden without governed environment profile",
                )
            argv.append("--force")
        # Never put prompt in argv.
        return argv

    def dispatch(self, request: ProviderRequest) -> ProviderResult:
        self.dispatch_calls += 1
        self._blocked_live()
        if not request.prompt_text:
            raise DispatchError(
                "CONTRACT_PROVIDER_WORK_ORDER_MISSING",
                "cursor-cli requires verified in-memory prompt",
            )
        # Write permissions imply force would be needed; block until #4255.
        perms = request.effective_permissions or {}
        if perms.get("write_code") or perms.get("write_docs"):
            raise DispatchError(
                "CURSOR_ENVIRONMENT_PROFILE_NOT_READY",
                "cursor-cli write execution blocked until #4255",
            )
        argv = self._build_argv(request)
        if self._runner is None:
            raise DispatchError(
                "PROVIDER_CLI_BINARY_MISSING",
                "no process runner configured and live CLI blocked",
            )
        completed = self._runner(
            argv,
            input_text=request.prompt_text,
            env={"CURSOR_API_KEY": "[UNRESOLVED]"},
        )
        stdout = completed.get("stdout") or ""
        exit_code = int(completed.get("exit_code") or 0)
        lines = stdout.splitlines()
        session_id, raw_status, events = parse_stream_json_lines(lines)
        if exit_code != 0 or raw_status != "FINISHED" or not session_id:
            raise DispatchError(
                "PROVIDER_CLI_FAILED",
                "CLI non-zero exit or missing terminal success event",
            )
        tool_calls = sum(1 for e in events if e.get("type") == "tool_call")
        self._runs[session_id] = _CliRun(
            session_id=session_id,
            status=raw_status,
            events=events,
            exit_code=exit_code,
        )
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=session_id,
            raw_status=raw_status,
            usage={"iterations": 1, "tool_calls": tool_calls},
            result_refs={"events": len(events)},
            delivery_receipt=request.delivery_receipt,
        )

    def watch(self, provider_run_id: str) -> ProviderResult:
        run = self._runs.get(provider_run_id)
        if run is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status=run.status,
            usage={"iterations": 1, "tool_calls": 0},
        )

    def cancel(self, provider_run_id: str, reason: str) -> ProviderResult:
        del reason
        run = self._runs.get(provider_run_id)
        if run is None:
            raise DispatchError("DISPATCH_PROVIDER_RUN_NOT_FOUND", provider_run_id)
        run.status = "CANCELLED"
        return build_provider_result(
            provider_id=self.provider_id,
            provider_run_id=provider_run_id,
            raw_status="CANCELLED",
            cancel_confirmed=True,
        )
