"""Live Hetzner Cloud capability preflight for Hermes (#4289).

Probes write surfaces and classifies whether server create is possible.
Never prints tokens. Creates ephemeral probe resources only when needed and
deletes them. Safe to run repeatedly.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

API = "https://api.hetzner.cloud/v1"


@dataclass
class ProbeResult:
    name: str
    http: int
    error_code: str | None = None
    message: str | None = None
    created_id: int | None = None


@dataclass
class HCloudPreflight:
    ok: bool
    classification: str
    auth_ok: bool
    server_create_ok: bool
    probes: list[ProbeResult] = field(default_factory=list)
    human_actions: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "classification": self.classification,
            "auth_ok": self.auth_ok,
            "server_create_ok": self.server_create_ok,
            "probes": [
                {
                    "name": p.name,
                    "http": p.http,
                    "error_code": p.error_code,
                    "message": p.message,
                    "created_id": p.created_id,
                }
                for p in self.probes
            ],
            "human_actions": self.human_actions,
            "details": self.details,
        }


def _call(
    token: str, method: str, path: str, body: dict[str, Any] | None = None
) -> tuple[int, dict[str, Any]]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read()
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            return int(resp.status), payload
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:400]}
        return int(exc.code), payload


def _err(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    err = payload.get("error") or {}
    if not isinstance(err, dict):
        return None, None
    return err.get("code"), err.get("message")


def run_hcloud_preflight(token: str | None = None) -> HCloudPreflight:
    """Classify whether this token can provision a Hermes VM."""
    if token is None:
        tok = (os.environ.get("HCLOUD_TOKEN") or "").strip()
    else:
        tok = token.strip()
    if not tok:
        return HCloudPreflight(
            ok=False,
            classification="MISSING_TOKEN",
            auth_ok=False,
            server_create_ok=False,
            human_actions=[
                "Set HCLOUD_TOKEN to a Hetzner Cloud API token (Read & Write)."
            ],
        )

    probes: list[ProbeResult] = []
    code, payload = _call(tok, "GET", "/servers")
    err_c, err_m = _err(payload)
    probes.append(ProbeResult("GET /servers", code, err_c, err_m))
    if code != 200:
        return HCloudPreflight(
            ok=False,
            classification="AUTH_FAILED",
            auth_ok=False,
            server_create_ok=False,
            probes=probes,
            human_actions=[
                "HCLOUD_TOKEN rejected for GET /servers — regenerate token in project Security → API Tokens."
            ],
        )

    stamp = int(time.time())
    # Free/meta write probe (proves token is not read-only).
    code, payload = _call(
        tok,
        "POST",
        "/firewalls",
        {"name": f"cdb-hermes-preflight-fw-{stamp}", "rules": []},
    )
    err_c, err_m = _err(payload)
    fw_id = (payload.get("firewall") or {}).get("id")
    probes.append(ProbeResult("POST /firewalls", code, err_c, err_m, fw_id))
    if fw_id:
        _call(tok, "DELETE", f"/firewalls/{fw_id}")

    # Server create probe (deleted immediately on success).
    code, payload = _call(
        tok,
        "POST",
        "/servers",
        {
            "name": f"cdb-hermes-preflight-{stamp}",
            "server_type": "cx23",
            "image": "ubuntu-24.04",
            "location": "fsn1",
            "start_after_create": True,
        },
    )
    err_c, err_m = _err(payload)
    srv_id = (payload.get("server") or {}).get("id")
    probes.append(ProbeResult("POST /servers", code, err_c, err_m, srv_id))
    if srv_id:
        _call(tok, "DELETE", f"/servers/{srv_id}")

    fw_ok = probes[1].http in (200, 201)
    srv_ok = probes[2].http in (200, 201)

    if srv_ok:
        return HCloudPreflight(
            ok=True,
            classification="SERVER_CREATE_OK",
            auth_ok=True,
            server_create_ok=True,
            probes=probes,
            details={"note": "ephemeral probe server deleted"},
        )

    if fw_ok and probes[2].http == 403:
        return HCloudPreflight(
            ok=False,
            classification="SERVER_CREATE_FORBIDDEN",
            auth_ok=True,
            server_create_ok=False,
            probes=probes,
            human_actions=[
                "Token is not read-only (firewall create works) but POST /servers returns 403 forbidden.",
                "In Hetzner Console: try creating a CX23 manually in the same project.",
                "If Console fails: complete Full-account / payment / client data; check project locks.",
                "If Console works: recreate API token as project Owner/Admin with Read & Write; replace HCLOUD_TOKEN.txt.",
                "Ensure project member role is Member or higher (Restricted cannot create servers).",
            ],
            details={
                "error_code": probes[2].error_code,
                "pattern": "meta_writes_ok_server_create_forbidden",
            },
        )

    if probes[2].error_code == "token_readonly" or (
        not fw_ok and probes[2].http == 403
    ):
        return HCloudPreflight(
            ok=False,
            classification="TOKEN_READONLY",
            auth_ok=True,
            server_create_ok=False,
            probes=probes,
            human_actions=[
                "Create a new API token with Read & Write and replace HCLOUD_TOKEN.txt."
            ],
        )

    return HCloudPreflight(
        ok=False,
        classification="SERVER_CREATE_FAILED",
        auth_ok=True,
        server_create_ok=False,
        probes=probes,
        human_actions=[
            f"Investigate POST /servers HTTP {probes[2].http} code={probes[2].error_code}."
        ],
        details={"error_code": probes[2].error_code, "message": probes[2].message},
    )
