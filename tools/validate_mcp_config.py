#!/usr/bin/env python3
"""Validate the local mcp-config.toml for common schema and path issues."""

import argparse
from pathlib import PurePosixPath, PureWindowsPath
import sys
import tomllib

REQUIRED_AGENT_KEYS = [
    "agent_mode",
    "model",
    "project_root",
]

REQUIRED_CANONICAL_KEYS = [
    "allowed_root",
    "docs_hub_index",
    "knowledge_hub",
    "governance",
    "working_repo_index",
    "working_agents",
    "codex",
    "logs",
]


def load_config(path: str) -> dict:
    with open(path, "rb") as handle:
        return tomllib.load(handle)


def _is_absolute_path(path: str) -> bool:
    return PurePosixPath(path).is_absolute() or PureWindowsPath(path).is_absolute()


def validate_agent_section(config: dict) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_AGENT_KEYS:
        if key not in config:
            errors.append(f"missing required key '{key}' at root level")
        elif not isinstance(config[key], str):
            errors.append(f"'{key}' must be a string")
    project_root = config.get("project_root")
    if isinstance(project_root, str) and not _is_absolute_path(project_root):
        errors.append("project_root must be an absolute path (Windows or POSIX)")
    return errors


def validate_mcp_servers(config: dict) -> list[str]:
    errors: list[str] = []
    servers = config.get("mcp_servers")
    if not isinstance(servers, dict):
        return ["[mcp_servers] table is missing or malformed"]

    for name, section in servers.items():
        if not isinstance(section, dict):
            errors.append(f"[mcp_servers.{name}] must be a table")
            continue
        command = section.get("command")
        args = section.get("args")
        if not isinstance(command, str) or not command:
            errors.append(f"[mcp_servers.{name}] command must be a non-empty string")
        if not isinstance(args, list):
            errors.append(f"[mcp_servers.{name}] args must be a non-empty list of non-empty strings")
        elif not args or not all(isinstance(item, str) and item for item in args):
            errors.append(f"[mcp_servers.{name}] args must be a non-empty list of non-empty strings")
    return errors


def _validate_path_root(path_value: str, allowed_root: str, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(path_value, str):
        errors.append(f"{label} must be a string")
    elif allowed_root and not path_value.startswith(allowed_root):
        errors.append(f"{label} must start with allowed_root='{allowed_root}'")
    return errors


def validate_canonical_paths(config: dict) -> list[str]:
    errors: list[str] = []
    paths = config.get("canonical_paths")
    if not isinstance(paths, dict):
        return ["[canonical_paths] table is missing or malformed"]

    for key in REQUIRED_CANONICAL_KEYS:
        if key not in paths:
            errors.append(f"[canonical_paths] is missing '{key}'")

    allowed_root = paths.get("allowed_root")
    if not isinstance(allowed_root, str) or not allowed_root:
        errors.append("allowed_root must be a non-empty string")
        allowed_root = ""

    for key, value in paths.items():
        if key == "logs":
            if not isinstance(value, list) or not value:
                errors.append("[canonical_paths] logs must be a non-empty list of paths")
            else:
                for idx, entry in enumerate(value):
                    errors.extend(_validate_path_root(entry, allowed_root, f"logs[{idx}]"))
        elif key != "allowed_root":
            errors.extend(_validate_path_root(value, allowed_root, key))
    return errors


def summarize(errors: list[str]) -> int:
    if errors:
        print("❌ mcp-config.toml validation failed:")
        for issue in errors:
            print(f" - {issue}")
        return 1
    print("✅ mcp-config.toml looks consistent and ready")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        nargs="?",
        default="mcp-config.toml",
        help="Path to the configuration to validate",
    )
    args = parser.parse_args()

    errors: list[str] = []
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        errors.append(f"Configuration file not found: {args.config}")
        return summarize(errors)
    except tomllib.TOMLDecodeError as e:
        errors.append(f"Failed to parse TOML: {e}")
        return summarize(errors)
    errors.extend(validate_agent_section(config))
    errors.extend(validate_mcp_servers(config))
    errors.extend(validate_canonical_paths(config))

    return summarize(errors)


if __name__ == "__main__":
    sys.exit(main())
