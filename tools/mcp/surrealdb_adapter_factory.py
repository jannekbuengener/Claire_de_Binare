"""Adapter factory for DB-backed context MCP tools.

Issue #2461 — Wire core context MCP tools to local SurrealDB read-only adapters.
Parent: #1976

Provides a single entry-point ``build_adapter_from_params`` that reads an
optional ``adapter_config_path`` MCP parameter and returns either:

* a ``NoopQueryAdapter`` (no network, ``source="in_memory"``) — the safe
  default when no adapter config is supplied, or
* a ``SurrealDBLocalQueryAdapter`` restricted to localhost-only HTTP access.

All callers must check ``isinstance(result, dict)`` before destructuring the
return value; a dict return means an error-response that should be forwarded
directly to the MCP client.

Guardrails:
    - No writes.  ``SurrealDBLocalQueryAdapter`` enforces read-only at
      statement-classification level independently of this module.
    - Localhost-only.  ``load_config`` and ``SurrealDBLocalQueryAdapter``
      both reject non-local URLs.
    - Soft DB failures.  ``hard_mode=False`` means an unreachable DB returns
      empty results and sets ``adapter.status = "surrealdb-local-unavailable"``
      rather than raising.
    - LR remains NO-GO.  This surface is context/read-only and does not
      authorize live capital, trading actions, or strategy changes.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Mapping

from tools.surrealdb.context_query import (
    ConfigValidationError,
    ContextQueryConfig,
    InputNotFoundError,
    NoopQueryAdapter,
    QueryAdapter,
    SurrealDBLocalQueryAdapter,
    _load_query_credentials,
    load_config,
)

logger = logging.getLogger(__name__)

_IN_MEMORY_SOURCE = "in_memory"
_ALLOWED_MCP_SOURCES = frozenset(
    {
        _IN_MEMORY_SOURCE,
        "surrealdb-local",
        "surrealdb-local-unavailable",
    }
)


def _make_adapter_error(tool_name: str, message: str) -> dict[str, Any]:
    """Build a well-formed MCP error-response dict for adapter config failures."""
    return {
        "tool": tool_name,
        "status": "error",
        "error": {
            "code": "adapter_config_error",
            "message": message,
        },
        "metadata": {
            "query_time_ms": 0,
            "source": _IN_MEMORY_SOURCE,
            "read_only": True,
        },
    }


def adapter_source(adapter: QueryAdapter) -> str:
    """Map ``adapter.status`` to the MCP ``metadata.source`` label.

    ``NoopQueryAdapter.status`` is ``"noop-no-network"``; all callers expect
    the label ``"in_memory"`` on the MCP surface.
    ``SurrealDBLocalQueryAdapter.status`` is already ``"surrealdb-local"`` or
    ``"surrealdb-local-unavailable"`` — returned unchanged.
    """
    status = adapter.status
    if status == "noop-no-network":
        return _IN_MEMORY_SOURCE
    return status


def derive_guarded_source_label(
    params: Mapping[str, Any] | None = None,
    *,
    adapter: QueryAdapter | None = None,
) -> str:
    """Derive ``metadata.source`` strictly from adapter evidence.

    Caller-provided request fields such as ``source``, ``brain_source``,
    ``brain_status``, or nested ``metadata.source`` are intentionally ignored.
    Without a real adapter object this helper always fail-closes to
    ``"in_memory"``.
    """
    _ = params
    if adapter is None:
        return _IN_MEMORY_SOURCE

    source = adapter_source(adapter)
    if source not in _ALLOWED_MCP_SOURCES:
        logger.warning("unexpected adapter source label %r; fail-closing", source)
        return _IN_MEMORY_SOURCE
    return source


def build_adapter_from_params(
    params: Mapping[str, Any],
    tool_name: str,
) -> tuple[QueryAdapter, ContextQueryConfig | None] | dict[str, Any]:
    """Return ``(adapter, config_or_none)`` or an error-response dict.

    When ``adapter_config_path`` is absent from *params*, returns a
    ``(NoopQueryAdapter(), None)`` pair — the safe, non-DB default.

    When ``adapter_config_path`` is present:

    1. Loads and validates the YAML config via ``load_config()``.
    2. Resolves credentials via ``_load_query_credentials()``.
    3. Instantiates ``SurrealDBLocalQueryAdapter`` with ``hard_mode=False``
       (soft fallback — DB unreachable → empty results, never fatal for the
       MCP surface).

    Secrets path resolution order:
        1. ``params["secrets_path"]``
        2. Env var ``CDB_CONTEXT_SECRETS_PATH``
        3. ``None`` (works for ``auth_mode="none"``)

    Returns an error-response dict on any config or credential failure.
    Callers must check ``isinstance(result, dict)`` before destructuring.
    """
    raw_path = params.get("adapter_config_path")
    if raw_path is None:
        return NoopQueryAdapter(), None

    config_path = Path(str(raw_path))
    try:
        config = load_config(config_path)
    except (ConfigValidationError, InputNotFoundError) as exc:
        logger.warning("adapter config load failed (%s): %s", tool_name, exc)
        return _make_adapter_error(tool_name, str(exc))
    except Exception as exc:
        logger.error(
            "unexpected error loading adapter config (%s): %s",
            tool_name,
            exc,
            exc_info=True,
        )
        return _make_adapter_error(tool_name, f"unexpected config error: {exc}")

    raw_secrets = params.get("secrets_path") or os.environ.get(
        "CDB_CONTEXT_SECRETS_PATH"
    )
    secrets_path = Path(str(raw_secrets)) if raw_secrets else None

    try:
        user, password = _load_query_credentials(config, secrets_path)
    except (ConfigValidationError, InputNotFoundError) as exc:
        logger.warning("credentials load failed (%s): %s", tool_name, exc)
        return _make_adapter_error(tool_name, str(exc))

    adapter = SurrealDBLocalQueryAdapter(
        surreal_url=config.surreal_url,
        namespace=config.namespace,
        database=config.database,
        user=user,
        password=password,
        timeout=config.timeout,
        hard_mode=False,
        config=config,
    )
    return adapter, config
