"""Static contract checks for the fixed Hermes tailnet transport."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSPORT_UNIT_PATH = (
    REPO_ROOT
    / "infrastructure"
    / "hermes"
    / "systemd"
    / "hermes-runs-tailnet-transport.service"
)


def validate_transport_unit(path: Path | None = None) -> list[str]:
    """Require a root-owned private TLS Serve frontend to the loopback gateway."""
    unit = path or TRANSPORT_UNIT_PATH
    if not unit.is_file():
        return [f"missing transport unit file: {unit}"]

    text = unit.read_text(encoding="utf-8")
    required = (
        "Type=oneshot",
        "RemainAfterExit=yes",
        "User=root",
        "Group=root",
        "EnvironmentFile=/etc/hermes/cdb-engineer.env",
        "Requires=tailscaled.service hermes-gateway-cdb-engineer.service",
        "ExecStartPre=-/usr/bin/tailscale serve --bg --yes --tcp=${API_SERVER_PORT} off",
        "ExecStart=/usr/bin/tailscale serve --bg --yes --https=${API_SERVER_PORT} "
        "http://127.0.0.1:${API_SERVER_PORT}",
        "ExecStop=/usr/bin/tailscale serve --bg --yes --https=${API_SERVER_PORT} off",
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
        "UMask=0077",
    )
    errors = [
        f"transport missing required snippet: {snippet}"
        for snippet in required
        if snippet not in text
    ]

    lower = text.lower()
    for forbidden in (
        "tailscale funnel",
        "0.0.0.0",
        "--http=",
        "ExecStart=/usr/bin/tailscale serve --bg --yes --tcp=",
        "--tls-terminated-tcp=",
        "environment=api_server_port=",
    ):
        if forbidden in lower:
            errors.append(f"transport forbidden snippet present: {forbidden}")
    return errors
