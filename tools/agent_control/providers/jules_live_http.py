"""Stdlib HTTP transport for the official Jules REST API (#4461)."""

from __future__ import annotations

import json as jsonlib
import os
import urllib.error
import urllib.request
from typing import Any


def _api_key_header_from_env(environ: dict[str, str] | None = None) -> dict[str, str]:
    env = environ if environ is not None else os.environ
    key = env.get("JULES_API_KEY", "").strip()
    if not key:
        return {}
    return {"X-Goog-Api-Key": key}


def build_jules_urllib_http_transport(
    *,
    environ: dict[str, str] | None = None,
    timeout_seconds: float = 60.0,
):
    """Return a Jules HttpTransport that injects the key only at request time.

    The secret value and request headers are never included in the returned
    response object. Callers cannot override the authentication header.
    """

    def _http(
        *,
        method: str,
        url: str,
        json: dict[str, Any] | None = None,  # noqa: A002
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        req_headers = {
            "Accept": "application/json",
            "User-Agent": "cdb-agent-control/1",
        }
        req_headers.update(_api_key_header_from_env(environ))
        if headers:
            for key, value in headers.items():
                if key.lower() in {"x-goog-api-key", "authorization"}:
                    continue
                req_headers[key] = value
        data = None
        if json is not None:
            data = jsonlib.dumps(json).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url, data=data, headers=req_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200) or 200)
                parsed: Any = {}
                if raw:
                    try:
                        parsed = jsonlib.loads(raw.decode("utf-8"))
                    except jsonlib.JSONDecodeError:
                        parsed = {"raw_text": "[non-json]"}
                return {
                    "status": status,
                    "json": parsed if isinstance(parsed, dict) else {},
                }
        except urllib.error.HTTPError as exc:
            raw = exc.read() if hasattr(exc, "read") else b""
            parsed: Any = {}
            if raw:
                try:
                    parsed = jsonlib.loads(raw.decode("utf-8"))
                except jsonlib.JSONDecodeError:
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
