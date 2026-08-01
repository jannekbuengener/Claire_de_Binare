"""Static contract checks for Hermes systemd units (#4289)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UNIT_PATH = (
    REPO_ROOT / "infrastructure" / "hermes" / "systemd" / "hermes-serve@.service"
)

REQUIRED_SNIPPETS = (
    "User=hermes",
    "HERMES_HOME=/var/lib/hermes/profiles/%i",
    "--host 127.0.0.1",
    "NoNewPrivileges=true",
    "MemoryMax=",
    "CPUQuota=",
    "ConditionPathExists=!/var/lib/hermes/profiles/%i/.DISABLED",
)

FORBIDDEN_SNIPPETS = (
    "0.0.0.0",
    "--insecure",
    "User=root",
)


def validate_unit(path: Path | None = None) -> list[str]:
    unit = path or UNIT_PATH
    errors: list[str] = []
    if not unit.is_file():
        return [f"missing unit file: {unit}"]
    text = unit.read_text(encoding="utf-8")
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"missing required snippet: {snippet}")
    for snippet in FORBIDDEN_SNIPPETS:
        if snippet in text:
            errors.append(f"forbidden snippet present: {snippet}")
    return errors
