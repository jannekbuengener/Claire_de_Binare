"""Shared helpers for the Dockerfile pip pin security contract (#4095).

Static Dockerfile parsing only — no image build, no registry access, no runtime
mutation.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Path segments that must never contribute Dockerfiles to the security inventory,
# even if somehow present in the git index (local worktrees, vendor trees, venvs).
_DISCOVERY_EXCLUDED_PATH_SEGMENTS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        ".worktrees",
        ".worktrees_backup",
        "third_party",
    }
)

# Advisory SSOT for the pinned floor:
#   CVE-2026-8643 / GHSA-wf93-45jw-7689 / PYSEC-2026-196 -> fixed in pip 26.1.2
# Earlier pip advisories that this floor also covers:
#   CVE-2025-8869 (25.3), CVE-2026-1703 (26.0), CVE-2026-3219 (26.1),
#   CVE-2026-6357 (26.1)
SAFE_PIP_VERSION = "26.1.2"
PIP_ADVISORY_FLOORS: dict[str, str] = {
    "CVE-2025-8869": "25.3",
    "CVE-2026-1703": "26.0",
    "CVE-2026-3219": "26.1",
    "CVE-2026-6357": "26.1",
    "CVE-2026-8643": "26.1.2",
}

# Image surfaces that ship pip into a productive service image. `services/*` are
# the BLUE/RED stack images; `tools/paper_trading` is the BLUE paper runner.
PRODUCTIVE_IMAGE_DOCKERFILES: tuple[str, ...] = (
    "services/allocation/Dockerfile",
    "services/candles/Dockerfile",
    "services/db_writer/Dockerfile",
    "services/execution/Dockerfile",
    "services/market/Dockerfile",
    "services/regime/Dockerfile",
    "services/reports/Dockerfile",
    "services/risk/Dockerfile",
    "services/signal/Dockerfile",
    "services/ws/Dockerfile",
    "tools/paper_trading/Dockerfile",
)

# Non-productive build surfaces. They are still scanned, but they are CI/test
# labs rather than deployed service images and are allowed to float pip.
# `infrastructure/actions-runner` installs the distro `python3-pip` and carries
# no PyPI pip pin; self-hosted runners are decommissioned from active CI (#3575).
NON_PRODUCTIVE_DOCKERFILES: tuple[str, ...] = (
    "ci/Dockerfile",
    "infrastructure/actions-runner/Dockerfile",
    "infrastructure/compose/Dockerfile.test",
)

# `services/execution` builds a venv that is copied into the runtime image, so
# both the venv pip and the global runtime pip are production image paths.
EXECUTION_DOCKERFILE = "services/execution/Dockerfile"
EXPECTED_EXECUTION_PIN_COUNT = 2

TRIVYIGNORE_FILE = ".trivyignore"

PINNED_PIP_PATTERN = re.compile(
    r"pip\s+install[^\n]*?\bpip==(?P<version>[0-9][0-9A-Za-z.\-_]*)"
)
UNPINNED_PIP_UPGRADE_PATTERN = re.compile(
    r"pip\s+install\s+(?:--[\w-]+\s+)*--upgrade\s+pip(?:\s|\\|$)"
)


@dataclass(frozen=True)
class PipPin:
    dockerfile: str
    line_number: int
    version: str


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def parse_version(version: str) -> tuple[int, ...]:
    """Parse a numeric-only pip version into a comparable tuple."""
    parts = version.split(".")
    if not all(part.isdigit() for part in parts):
        raise ValueError(f"non-numeric pip version pin: {version!r}")
    return tuple(int(part) for part in parts)


def collect_pip_pins(relative_path: str) -> list[PipPin]:
    pins: list[PipPin] = []
    for line_number, line in enumerate(_read(relative_path).splitlines(), start=1):
        match = PINNED_PIP_PATTERN.search(line)
        if match:
            pins.append(
                PipPin(
                    dockerfile=relative_path,
                    line_number=line_number,
                    version=match.group("version"),
                )
            )
    return pins


def collect_all_productive_pins() -> list[PipPin]:
    pins: list[PipPin] = []
    for dockerfile in PRODUCTIVE_IMAGE_DOCKERFILES:
        pins.extend(collect_pip_pins(dockerfile))
    return pins


def has_unpinned_pip_upgrade(relative_path: str) -> bool:
    for line in _read(relative_path).splitlines():
        if PINNED_PIP_PATTERN.search(line):
            continue
        if UNPINNED_PIP_UPGRADE_PATTERN.search(line):
            return True
    return False


def _is_excluded_discovery_path(relative_posix: str) -> bool:
    """Return True when any path segment is a known non-canon discovery surface."""
    return any(
        part in _DISCOVERY_EXCLUDED_PATH_SEGMENTS for part in Path(relative_posix).parts
    )


def _is_dockerfile_basename(relative_posix: str) -> bool:
    """Match Dockerfile / Dockerfile.* basenames (same semantics as Path.rglob)."""
    return Path(relative_posix).name.startswith("Dockerfile")


def discover_dockerfiles(repo_root: Path | None = None) -> list[str]:
    """Every git-tracked Dockerfile* under *repo_root*, as repo-relative POSIX paths.

    Discovery is intentionally bound to ``git ls-files`` so nested worktrees,
    backups, vendor copies, and untracked local files cannot pollute the
    productive/non-productive classification contract (#4237).

    Fail-closed: if git evidence cannot be collected, raise rather than silently
    returning a filesystem subset.
    """
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--",
                "*Dockerfile*",
                "*/Dockerfile*",
            ],
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise RuntimeError(
            f"cannot enumerate tracked Dockerfiles in {root}: git unavailable ({exc})"
        ) from exc

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        detail = f": {stderr}" if stderr else ""
        raise RuntimeError(
            f"cannot enumerate tracked Dockerfiles in {root} "
            f"(git ls-files exit {result.returncode}{detail})"
        )

    found: list[str] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8").replace("\\", "/")
        if not _is_dockerfile_basename(relative):
            continue
        if _is_excluded_discovery_path(relative):
            continue
        found.append(relative)
    return sorted(found)


def trivyignore_entries() -> list[str]:
    raw = _read(TRIVYIGNORE_FILE)
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
