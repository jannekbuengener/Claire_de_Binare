#!/usr/bin/env python3
"""
CI-Guard: Prevents core duplicates and secrets.py files.
Rule 1: No services/*/core/** directories.
Rule 2: No additional secrets.py files (except core/domain/secrets.py).
"""

import sys
from pathlib import Path


def check_duplicates():
    violations = []
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

    # Rule 2: Check for secrets.py files (except core/domain/secrets.py)
    excluded_dirs = {".git", "__pycache__", ".worktrees_backup"}
    for secrets_file in root_dir.rglob("secrets.py"):
        if any(part in excluded_dirs for part in secrets_file.parts):
            continue
        rel_path = secrets_file.relative_to(root_dir)
        # Whitelist: core/domain/secrets.py is allowed
        if rel_path != Path("core/domain/secrets.py"):
            violations.append(
                f"FORBIDDEN: secrets.py at {rel_path.as_posix()}"
            )

    if violations:
        print("CI-Guard FAILED")
        for v in violations:
            print(f"  {v}")
        sys.exit(1)
    else:
        print("CI-Guard PASSED")
        sys.exit(0)


if __name__ == "__main__":
    check_duplicates()
