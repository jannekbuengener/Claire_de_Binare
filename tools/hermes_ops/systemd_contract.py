"""Static contract checks for Hermes systemd units (#4289)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_PATH = (
    REPO_ROOT / "infrastructure" / "hermes" / "systemd" / "hermes-dashboard@.service"
)
LEGACY_SERVE_PATH = (
    REPO_ROOT / "infrastructure" / "hermes" / "systemd" / "hermes-serve@.service"
)

REQUIRED_SNIPPETS = (
    "User=hermes",
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
)

FORBIDDEN_SNIPPETS = (
    "0.0.0.0",
    "--insecure",
    "User=root",
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
    # Forbid dangerous binds / users anywhere; forbid legacy ExecStart command.
    for snippet in ("0.0.0.0", "--insecure", "User=root"):
        if snippet in text:
            errors.append(f"forbidden snippet present: {snippet}")
    for line in text.splitlines():
        if line.strip().startswith("ExecStart=") and "hermes serve" in line:
            errors.append("forbidden snippet present: hermes serve")
    return errors
