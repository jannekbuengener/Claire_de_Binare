"""Provider factory registering mock + Cursor adapters (#4254)."""

from __future__ import annotations

from typing import Any

from tools.agent_control.errors import DispatchError
from tools.agent_control.provider import MockProvider, Provider
from tools.agent_control.providers.cursor_cli import CursorCliDriver
from tools.agent_control.providers.cursor_cloud_api import CursorCloudApiDriver
from tools.agent_control.providers.cursor_sdk import CursorSdkDriver

CURSOR_PROVIDER_IDS = frozenset({"cursor-sdk", "cursor-cli", "cursor-cloud-api"})
ALL_PROVIDER_IDS = frozenset({"mock"}) | CURSOR_PROVIDER_IDS


def registered_provider_ids() -> tuple[str, ...]:
    return tuple(sorted(ALL_PROVIDER_IDS))


def build_provider(
    provider_id: str,
    *,
    allow_live: bool = False,
    transports: dict[str, Any] | None = None,
) -> Provider:
    transports = transports or {}
    if provider_id == "mock":
        return MockProvider()
    if provider_id == "cursor-sdk":
        return CursorSdkDriver(
            client_factory=transports.get("sdk_client_factory"),
            allow_live=allow_live,
            model_catalog=transports.get("model_catalog"),
            runtime=transports.get("runtime", "local"),
        )
    if provider_id == "cursor-cli":
        return CursorCliDriver(
            runner=transports.get("process_runner"),
            binary=transports.get("binary", "agent"),
            allow_live=allow_live,
            allow_force=bool(transports.get("allow_force", False)),
        )
    if provider_id == "cursor-cloud-api":
        return CursorCloudApiDriver(
            http=transports.get("http"),
            sse=transports.get("sse"),
            allow_live=allow_live,
            model_catalog=transports.get("model_catalog"),
            human_go_live=bool(transports.get("human_go_live", False)),
        )
    if provider_id == "cursor":
        raise DispatchError(
            "PROVIDER_ID_AMBIGUOUS",
            "provider_id 'cursor' is a legacy profile placeholder; use cursor-sdk|cursor-cli|cursor-cloud-api",
        )
    raise DispatchError(
        "PROVIDER_UNKNOWN",
        f"unknown provider_id: {provider_id!r}",
    )
