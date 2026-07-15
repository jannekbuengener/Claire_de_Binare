"""Validate the tracked repository root against the canonical root layout policy."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

DEFAULT_POLICY_PATH = Path("config/repository/root_layout.json")


class RootLayoutPolicyError(ValueError):
    """Raised when the root layout policy is malformed."""


@dataclass(frozen=True, order=True)
class RootLayoutViolation:
    kind: str
    path: str
    detail: str


def _string_set(policy: Mapping[str, Any], key: str) -> set[str]:
    value = policy.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RootLayoutPolicyError(f"{key} must be a list of strings")
    return set(value)


def load_policy(path: Path) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RootLayoutPolicyError(f"cannot read policy {path}: {exc}") from exc

    if not isinstance(policy, dict):
        raise RootLayoutPolicyError("policy root must be a JSON object")
    if policy.get("schema_version") != "root-layout.v1":
        raise RootLayoutPolicyError("unsupported or missing schema_version")

    for key in (
        "approved_directories",
        "approved_files",
        "required_directories",
        "required_files",
        "required_paths",
    ):
        _string_set(policy, key)

    retired = policy.get("retired_root_entries")
    if not isinstance(retired, list):
        raise RootLayoutPolicyError("retired_root_entries must be a list")
    for entry in retired:
        if not isinstance(entry, dict):
            raise RootLayoutPolicyError("retired_root_entries items must be objects")
        if not isinstance(entry.get("path"), str):
            raise RootLayoutPolicyError("retired entry path must be a string")
        if entry.get("kind") not in {"directory", "file"}:
            raise RootLayoutPolicyError("retired entry kind must be directory or file")
        if not isinstance(entry.get("disposition"), str):
            raise RootLayoutPolicyError("retired entry disposition must be a string")
    return policy


def classify_tracked_paths(paths: Iterable[str]) -> tuple[set[str], set[str]]:
    """Return tracked top-level directories and root files from git-style paths."""
    directories: set[str] = set()
    files: set[str] = set()
    for raw_path in paths:
        path = raw_path.strip().replace("\\", "/")
        if not path:
            continue
        top, separator, _ = path.partition("/")
        if separator:
            directories.add(top)
        else:
            files.add(top)
    return directories, files


def git_tracked_paths(repo_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            f"cannot enumerate tracked files in {repo_root}: {exc}"
        ) from exc
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def validate_layout(
    policy: Mapping[str, Any],
    directories: set[str],
    files: set[str],
    *,
    repo_root: Path | None = None,
) -> list[RootLayoutViolation]:
    approved_directories = _string_set(policy, "approved_directories")
    approved_files = _string_set(policy, "approved_files")
    required_directories = _string_set(policy, "required_directories")
    required_files = _string_set(policy, "required_files")
    required_paths = _string_set(policy, "required_paths")

    violations: list[RootLayoutViolation] = []
    for path in sorted(directories - approved_directories):
        violations.append(
            RootLayoutViolation(
                "unexpected directory", path, "not approved at repository root"
            )
        )
    for path in sorted(files - approved_files):
        violations.append(
            RootLayoutViolation(
                "unexpected file", path, "not approved at repository root"
            )
        )
    for path in sorted(required_directories - directories):
        violations.append(
            RootLayoutViolation(
                "missing directory", path, "required root directory is absent"
            )
        )
    for path in sorted(required_files - files):
        violations.append(
            RootLayoutViolation("missing file", path, "required root file is absent")
        )

    for entry in policy["retired_root_entries"]:
        path = entry["path"]
        present = path in directories if entry["kind"] == "directory" else path in files
        if present:
            violations.append(
                RootLayoutViolation("retired root entry", path, entry["disposition"])
            )

    if repo_root is not None:
        for path in sorted(required_paths):
            if not (repo_root / path).exists():
                violations.append(
                    RootLayoutViolation(
                        "missing canonical path", path, "required path is absent"
                    )
                )

    return sorted(violations)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (default: parent of tools/)",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="policy path, relative to repo root by default",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    policy_path = args.policy if args.policy.is_absolute() else repo_root / args.policy
    try:
        policy = load_policy(policy_path)
        directories, files = classify_tracked_paths(git_tracked_paths(repo_root))
        violations = validate_layout(policy, directories, files, repo_root=repo_root)
    except (RootLayoutPolicyError, RuntimeError) as exc:
        print(f"ROOT LAYOUT ERROR: {exc}")
        return 2

    if violations:
        print("ROOT LAYOUT FAIL")
        for violation in violations:
            print(f"- [{violation.kind}] {violation.path}: {violation.detail}")
        return 1

    print("ROOT LAYOUT PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
