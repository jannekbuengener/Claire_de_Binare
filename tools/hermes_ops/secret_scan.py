"""Secret / PII leak scanner for Hermes repo surfaces (#4289)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ci.publisher.redaction import redact_text

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCAN_ROOTS = (
    REPO_ROOT / "config" / "hermes",
    REPO_ROOT / "infrastructure" / "hermes",
    REPO_ROOT / "tools" / "hermes_ops",
    REPO_ROOT / "docs" / "runbooks" / "hermes_hetzner_operations.md",
    REPO_ROOT / "docs" / "security" / "hermes_hetzner_threat_model.md",
)

FORBIDDEN_BASENAMES = frozenset(
    {
        ".env",
        "auth.json",
        "state.db",
        "id_rsa",
        "id_ed25519",
    }
)
FORBIDDEN_SUFFIXES = (".pem", ".key")
# High-signal leak patterns (values, not key names).
LEAK_PATTERNS = (
    re.compile(r"(?i)gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"-----BEGIN[A-Z ]*PRIVATE KEY-----"),
    re.compile(
        r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]"
    ),
)
# Device / product identifiers that must not land in prompts/memory templates.
PII_PATTERNS = (
    re.compile(r"(?i)device[_-]?id\s*[:=]\s*\S+"),
    re.compile(r"(?i)product[_-]?id\s*[:=]\s*\S+"),
    re.compile(r"(?i)windows\s*product\s*key\s*[:=]\s*\S+"),
)

TEXT_SUFFIXES = {
    ".md",
    ".yml",
    ".yaml",
    ".py",
    ".sh",
    ".ps1",
    ".service",
    ".EXAMPLE",
    ".json",
    ".toml",
    ".txt",
}


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    detail: str


def _iter_files(roots: tuple[Path, ...]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file():
                files.append(path)
    return files


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def scan_paths(roots: tuple[Path, ...] | None = None) -> list[Finding]:
    roots = roots or DEFAULT_SCAN_ROOTS
    findings: list[Finding] = []
    for path in _iter_files(roots):
        name = path.name
        if (
            name in FORBIDDEN_BASENAMES
            or name.startswith(".env.")
            and name != ".env.EXAMPLE"
        ):
            if name != ".env.EXAMPLE":
                findings.append(
                    Finding(_display_path(path), "forbidden_basename", name)
                )
        if name.endswith(FORBIDDEN_SUFFIXES):
            findings.append(Finding(_display_path(path), "forbidden_suffix", name))
        if path.suffix not in TEXT_SUFFIXES and path.name not in {
            ".gitignore",
            ".env.EXAMPLE",
        }:
            # Still scan extensionless text-ish files under profiles.
            if "profiles" not in path.parts:
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in LEAK_PATTERNS:
            if pattern.search(text):
                findings.append(
                    Finding(
                        _display_path(path),
                        "secret_pattern",
                        redact_text(pattern.pattern),
                    )
                )
                break
        for pattern in PII_PATTERNS:
            if pattern.search(text):
                findings.append(
                    Finding(
                        _display_path(path),
                        "pii_pattern",
                        pattern.pattern,
                    )
                )
                break
    return findings


def scan_ok(roots: tuple[Path, ...] | None = None) -> bool:
    return not scan_paths(roots)
