"""Fail-closed MCP SDK preflight for unit-test collection."""

from __future__ import annotations

import importlib.metadata
import time
from pathlib import Path

from ci.lib.evidence import StageResult, utc_now
from ci.stages._common import StageContext

MCP_SDK_VERSION_MISMATCH = "MCP_SDK_VERSION_MISMATCH"
MCP_SERVER_LIST_TOOLS_UNAVAILABLE = "MCP_SERVER_LIST_TOOLS_UNAVAILABLE"
MCP_REQUIREMENTS_PIN_MISSING = "MCP_REQUIREMENTS_PIN_MISSING"


def _pinned_mcp_version(repo_root: Path) -> str:
    requirements = repo_root / "requirements-mcp.txt"
    for line in requirements.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("mcp=="):
            return stripped.split("==", maxsplit=1)[1].strip()
    raise ValueError(f"{MCP_REQUIREMENTS_PIN_MISSING}: mcp== pin not found")


def _validate_mcp_sdk(repo_root: Path) -> tuple[str, str]:
    expected = _pinned_mcp_version(repo_root)
    try:
        active = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError as exc:
        raise ValueError(
            f"{MCP_SDK_VERSION_MISMATCH}: active mcp package is missing"
        ) from exc
    if active != expected:
        raise ValueError(
            f"{MCP_SDK_VERSION_MISMATCH}: active mcp {active} does not match pin {expected}"
        )
    from mcp.server import Server

    if not hasattr(Server, "list_tools"):
        raise ValueError(
            f"{MCP_SERVER_LIST_TOOLS_UNAVAILABLE}: mcp {active} Server.list_tools is unavailable"
        )
    return expected, active


def run(ctx: StageContext) -> StageResult:
    """Record MCP SDK closure before pytest can import MCP server modules."""
    started = utc_now()
    wall_start = time.perf_counter()
    log_path = ctx.logs_dir / "mcp_dependency_closure.log"
    try:
        expected, active = _validate_mcp_sdk(ctx.repo_root)
    except (OSError, ValueError) as exc:
        message = str(exc)
        reason_code = next(
            (
                code
                for code in (
                    MCP_REQUIREMENTS_PIN_MISSING,
                    MCP_SDK_VERSION_MISMATCH,
                    MCP_SERVER_LIST_TOOLS_UNAVAILABLE,
                )
                if message.startswith(code)
            ),
            MCP_SDK_VERSION_MISMATCH,
        )
        log_path.write_text(message + "\n", encoding="utf-8")
        return StageResult(
            name="mcp_dependency_closure",
            status="FAIL",
            exit_code=1,
            started_at_utc=started,
            ended_at_utc=utc_now(),
            duration_seconds=round(time.perf_counter() - wall_start, 3),
            command_summary=[
                "validate requirements-mcp.txt active mcp SDK",
                f"reason_code={reason_code}",
            ],
            log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
            artifacts=[],
            skip_reason=None,
            required=True,
            reason_code=reason_code,
        )

    log_path.write_text(
        f"mcp_pin={expected}\nactive_mcp={active}\nServer.list_tools=available\n",
        encoding="utf-8",
    )
    return StageResult(
        name="mcp_dependency_closure",
        status="PASS",
        exit_code=0,
        started_at_utc=started,
        ended_at_utc=utc_now(),
        duration_seconds=round(time.perf_counter() - wall_start, 3),
        command_summary=["validate requirements-mcp.txt active mcp SDK"],
        log_path=str(log_path.relative_to(ctx.run_dir).as_posix()),
        artifacts=[],
        skip_reason=None,
        required=True,
        reason_code=None,
    )
