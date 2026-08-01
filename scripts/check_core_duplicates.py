#!/usr/bin/env python3
"""
CI-Guard: Prevents core duplicates, secrets.py sprawl, and exact script clones.

Rule 1: No services/*/core/** directories.
Rule 2: No additional secrets.py files (except core/domain/secrets.py and
        core/secrets.py).
Rule 3: No byte-identical git-tracked implementations under both scripts/ and
        infrastructure/scripts/ for the same relative path, unless an explicit
        wrapper/pointer exception applies.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

# Relative paths (posix) under scripts/ that may intentionally mirror
# infrastructure/scripts/ as thin wrappers/pointers. Identical full
# implementations are never allowlisted here — only explicit pointer markers.
WRAPPER_MARKERS = (
    "CDB_SCRIPT_WRAPPER",
    "CDB_SCRIPT_POINTER",
)


def _is_wrapper_or_pointer(path: Path) -> bool:
    """Return True when a file explicitly declares itself a wrapper/pointer."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return any(marker in text for marker in WRAPPER_MARKERS)


def _git_tracked_under(root_dir: Path, prefix: str) -> list[str]:
    """List git-tracked paths under prefix relative to root_dir.

    Returns an empty list when root_dir is not a git work tree. Untracked
    files and foreign worktrees are ignored by design.
    """
    result = subprocess.run(
        ["git", "-C", str(root_dir), "ls-files", "-z", "--", prefix],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    raw = result.stdout.split(b"\0")
    paths: list[str] = []
    for item in raw:
        if not item:
            continue
        paths.append(item.decode("utf-8", errors="replace"))
    return paths


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rel_under(prefix: str, tracked_path: str) -> str | None:
    prefix = prefix.rstrip("/") + "/"
    if not tracked_path.startswith(prefix):
        return None
    return tracked_path[len(prefix) :]


def check_script_surface_duplicates(root_dir: Path) -> list[str]:
    """Flag identical git-tracked files shared by scripts/ and infrastructure/scripts/."""
    violations: list[str] = []
    scripts_prefix = "scripts/"
    infra_prefix = "infrastructure/scripts/"

    scripts_tracked = _git_tracked_under(root_dir, scripts_prefix)
    infra_tracked = _git_tracked_under(root_dir, infra_prefix)

    scripts_map: dict[str, str] = {}
    for tracked in scripts_tracked:
        rel = _rel_under(scripts_prefix, tracked)
        if rel is None or not rel:
            continue
        scripts_map[rel] = tracked

    infra_map: dict[str, str] = {}
    for tracked in infra_tracked:
        rel = _rel_under(infra_prefix, tracked)
        if rel is None or not rel:
            continue
        # Legacy quarantine is reference-only; not an active scripts/ twin surface.
        if rel.startswith("legacy/"):
            continue
        infra_map[rel] = tracked

    for rel in sorted(set(scripts_map) & set(infra_map)):
        scripts_path = root_dir / scripts_map[rel]
        infra_path = root_dir / infra_map[rel]
        if not scripts_path.is_file() or not infra_path.is_file():
            continue
        if _is_wrapper_or_pointer(scripts_path) or _is_wrapper_or_pointer(infra_path):
            continue
        if _sha256_file(scripts_path) == _sha256_file(infra_path):
            violations.append(
                "FORBIDDEN: identical script implementation at "
                f"{scripts_map[rel]} and {infra_map[rel]}"
            )
    return violations


def check_duplicates() -> int:
    violations: list[str] = []
    root_dir = Path.cwd()

    # Rule 1: Check for services/*/core/**
    services_dir = root_dir / "services"
    if services_dir.exists():
        for service_path in services_dir.iterdir():
            if service_path.is_dir():
                core_path = service_path / "core"
                if core_path.exists():
                    violations.append(
                        "FORBIDDEN: core duplicate at "
                        f"{core_path.relative_to(root_dir).as_posix()}"
                    )

    # Rule 2: Check for secrets.py files (except allowlisted core paths)
    excluded_dirs = {".git", "__pycache__", ".worktrees_backup"}
    allowed_secrets = {Path("core/domain/secrets.py"), Path("core/secrets.py")}

    for secrets_file in root_dir.rglob("secrets.py"):
        if any(part in excluded_dirs for part in secrets_file.parts):
            continue
        rel_path = secrets_file.relative_to(root_dir)
        if rel_path not in allowed_secrets:
            violations.append(f"FORBIDDEN: secrets.py at {rel_path.as_posix()}")

    # Rule 3: Exact clones between scripts/ and infrastructure/scripts/
    violations.extend(check_script_surface_duplicates(root_dir))

    if violations:
        print("CI-Guard FAILED")
        for item in violations:
            print(f"  {item}")
        return 1

    print("CI-Guard PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(check_duplicates())
