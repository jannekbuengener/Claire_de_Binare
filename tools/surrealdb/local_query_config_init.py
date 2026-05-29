"""Initialize the local-only Context Query config from the checked-in example.

No secrets are generated or read here. The target file is operator-local and
must remain untracked.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from tools.surrealdb.context_query import load_config

DEFAULT_EXAMPLE = Path("infrastructure/config/surrealdb/context_query.local.example.yaml")
DEFAULT_TARGET = Path("infrastructure/config/surrealdb/context_query.local.yaml")


def init_local_query_config(
    *,
    repo_root: Path,
    example_rel: Path = DEFAULT_EXAMPLE,
    target_rel: Path = DEFAULT_TARGET,
) -> str:
    """Copy the checked-in example to the operator-local config path if missing."""

    example_path = repo_root / example_rel
    target_path = repo_root / target_rel

    if not example_path.is_file():
        raise FileNotFoundError(f"example config not found: {example_rel}")

    # Validate before copying so a broken example cannot become local operator config.
    load_config(example_path)

    if target_path.exists():
        load_config(target_path)
        return f"exists: {target_rel}"

    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(example_path, target_path)
    load_config(target_path)
    return f"created: {target_rel}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create local context_query.local.yaml from the checked-in example."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    args = parser.parse_args(argv)

    try:
        result = init_local_query_config(repo_root=args.repo_root)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"[OK] {result}")
    print("NOTE: local query config is gitignored and must not contain secrets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
