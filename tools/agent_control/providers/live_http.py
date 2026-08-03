"""Stdlib HTTP transport for Cursor Cloud Agents API (live path only)."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any


def _auth_header_from_env(environ: dict[str, str] | None = None) -> dict[str, str]:
    env = environ if environ is not None else os.environ
    key = env.get("CURSOR_API_KEY", "").strip()
    if not key:
        return {}
    token = base64.b64encode(f"{key}:".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def build_urllib_http_transport(
    *,
    environ: dict[str, str] | None = None,
    timeout_seconds: float = 60.0,
):
    """Return an HttpTransport callable using urllib.

    Auth header is attached per-request from env and never returned in the
    response body. Callers must not log headers.
    """

    def _http(
        *,
        method: str,
        url: str,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        # Compat: some call sites use ``json=`` keyword.
        body = json_body
        req_headers = {
            "Accept": "application/json",
            "User-Agent": "cdb-agent-control/1",
        }
        req_headers.update(_auth_header_from_env(environ))
        if headers:
            # Never allow caller to override Authorization with a logged value;
            # only merge non-auth headers.
            for k, v in headers.items():
                if k.lower() == "authorization":
                    continue
                req_headers[k] = v
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, data=data, headers=req_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:
                raw = resp.read()
                status = int(getattr(resp, "status", 200) or 200)
                parsed: Any = {}
                if raw:
                    try:
                        parsed = json.loads(raw.decode("utf-8"))
                    except json.JSONDecodeError:
                        parsed = {"raw_text": "[non-json]"}
                return {
                    "status": status,
                    "json": parsed if isinstance(parsed, dict) else {},
                }
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            parsed = {}
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    parsed = {}
            return {
                "status": int(exc.code),
                "json": parsed if isinstance(parsed, dict) else {},
            }
        except urllib.error.URLError as exc:
            raise ConnectionError(
                str(exc.reason if hasattr(exc, "reason") else exc)
            ) from exc

    return _http


def build_urllib_http_transport_compat():
    """Wrapper accepting ``json=`` as used by CursorCloudApiDriver._request."""

    inner = build_urllib_http_transport()

    def _http(*, method: str, url: str, json=None, headers=None):  # noqa: A002
        return inner(method=method, url=url, json_body=json, headers=headers)

    return _http
