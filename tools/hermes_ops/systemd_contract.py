"""Static contract checks for Hermes systemd units (#4289)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_PATH = (
    REPO_ROOT / "infrastructure" / "hermes" / "systemd" / "hermes-dashboard@.service"
)
BROKER_UNIT_PATH = (
    REPO_ROOT / "infrastructure" / "hermes" / "systemd" / "hermes-github-token.service"
)
LEGACY_SERVE_PATH = (
    REPO_ROOT / "infrastructure" / "hermes" / "systemd" / "hermes-serve@.service"
)

REQUIRED_SNIPPETS = (
    "User=hermes-%i",
    "Group=hermes-%i",
    "HERMES_HOME=/var/lib/hermes/profiles/%i",
    "--host 127.0.0.1",
    "hermes dashboard",
    "${HERMES_PORT}",
    "--isolated",
    "NoNewPrivileges=true",
    "MemoryMax=",
    "CPUQuota=",
    "ConditionPathExists=!/var/lib/hermes/profiles/%i/.DISABLED",
    "EnvironmentFile=/etc/hermes/%i.env",
    "ReadWritePaths=/var/lib/hermes/profiles/%i /var/log/hermes/%i",
)

FORBIDDEN_SNIPPETS = (
    "0.0.0.0",
    "--insecure",
    "hermes serve",
)


def validate_unit(path: Path | None = None) -> list[str]:
    unit = path or UNIT_PATH
    errors: list[str] = []
    if LEGACY_SERVE_PATH.is_file():
        errors.append(
            "legacy hermes-serve@.service must be removed "
            "(official entrypoint is hermes dashboard)"
        )
    if not unit.is_file():
        return errors + [f"missing unit file: {unit}"]
    text = unit.read_text(encoding="utf-8")
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"missing required snippet: {snippet}")
    for snippet in ("0.0.0.0", "--insecure"):
        if snippet in text:
            errors.append(f"forbidden snippet present: {snippet}")
    # Shared User=hermes (without %i) is forbidden — both profiles would share UID.
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {"User=hermes", "Group=hermes"}:
            errors.append(
                "forbidden shared identity: "
                f"{stripped} (require User=hermes-%i / Group=hermes-%i)"
            )
        if stripped.startswith("User=root"):
            errors.append("forbidden snippet present: User=root on dashboard unit")
        if stripped.startswith("ExecStart=") and "hermes serve" in stripped:
            errors.append("forbidden snippet present: hermes serve")
    return errors


def validate_broker_unit(path: Path | None = None) -> list[str]:
    """Broker is root oneshot; PEM root-only; token RuntimeDirectory isolated."""
    unit = path or BROKER_UNIT_PATH
    errors: list[str] = []
    if not unit.is_file():
        return [f"missing broker unit file: {unit}"]
    text = unit.read_text(encoding="utf-8")
    required = (
        "Type=oneshot",
        "RemainAfterExit=yes",
        "User=root",
        "RuntimeDirectory=hermes/cdb-engineer",
        "RuntimeDirectoryMode=0700",
        "cdb-hermes-engineer.pem",
        "hermes-cdb-engineer",
        "mint-token",
        "--profile cdb-engineer",
        "ExecStopPost=+/bin/rm -f /run/hermes/cdb-engineer/token",
        "ExecStartPost=+/bin/chown -R hermes-cdb-engineer:hermes-cdb-engineer",
    )
    for snippet in required:
        if snippet not in text:
            errors.append(f"broker missing required snippet: {snippet}")
    forbidden = (
        "User=hermes\n",
        "User=hermes-jannek-assistant",
        "Group=hermes\n",
        "/var/lib/hermes/profiles",
    )
    for snippet in forbidden:
        if snippet in text:
            errors.append(f"broker forbidden snippet present: {snippet!r}")
    return errors
