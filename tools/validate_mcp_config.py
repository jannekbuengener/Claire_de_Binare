#!/usr/bin/env python3
"""
MCP Configuration Validator
Checks if the MCP servers defined in configuration files are resolvable and executable.
Specifically handles python-based servers by verifying their modules can be imported.
"""

import json
import sys
import os
import subprocess
import argparse
from pathlib import Path

def validate_mcp_file(file_path: Path) -> bool:
    if not file_path.exists():
        print(f"❌ Config file not found: {file_path}")
        return False

    print(f"🔎 Validating {file_path}...")
    try:
        with open(file_path, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse {file_path}: {e}")
        return False

    servers = config.get("mcpServers", {})
    if not servers:
        print(f"⚠️  No mcpServers found in {file_path}")
        return True

    all_ok = True
    for name, server in servers.items():
        command = server.get("command")
        args = server.get("args", [])

        if command == "python" or (command == "cmd" and "python" in args):
            # Try to find the module name in args
            module_name = None
            if "-m" in args:
                idx = args.index("-m")
                if idx + 1 < len(args):
                    module_name = args[idx+1]

            if module_name:
                print(f"  Checking python module: {module_name}...", end=" ", flush=True)
                try:
                    subprocess.run(
                        [sys.executable, "-c", f"import {module_name}"],
                        check=True,
                        capture_output=True
                    )
                    print("✅")
                except subprocess.CalledProcessError:
                    print(f"❌ (Module '{module_name}' not found)")
                    all_ok = False
            else:
                print(f"  Could NOT determine python module from args for {name}: {args}")
        elif command in ("cmd", "npx"):
            # Basic check for npx existence
            print(f"  Skipping deep validation for {command}-based server: {name}")
        else:
            print(f"  Unknown command type for {name}: {command}")

    return all_ok

def main():
    parser = argparse.ArgumentParser(description="Validate MCP configuration files.")
    parser.add_argument("paths", nargs="*", help="Paths to MCP config files (can be comma-separated).")
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail if no configuration files are found.")
    args = parser.parse_args()

    raw_paths = []

    # 1. Add paths from arguments (handle comma-separated strings)
    for p in args.paths:
        if "," in p:
            raw_paths.extend(p.split(","))
        else:
            raw_paths.append(p)

    # 2. Add paths from environment variable
    env_paths = os.getenv("MCP_CONFIG_PATHS")
    if env_paths:
        raw_paths.extend(env_paths.split(","))

    mcp_files = []
    for p in raw_paths:
        p_strip = p.strip()
        if p_strip:
            mcp_files.append(Path(p_strip))

    # 3. Default search if no paths provided via args or ENV
    if not mcp_files:
        root = Path(".")
        mcp_files.extend(list(root.glob("*.mcp.json")))
        if root.joinpath(".mcp.json").exists():
            mcp_files.append(root.joinpath(".mcp.json"))

    # Deduplicate and sort
    mcp_files = sorted(list(set(mcp_files)))

    if not mcp_files:
        if args.allow_empty:
            print("⚠️  No MCP configuration files found to validate (allowed by --allow-empty).")
            return
        else:
            print("❌ Error: No MCP configuration files found to validate.")
            print("To fix this, provide paths via arguments, MCP_CONFIG_PATHS environment variable,")
            print("or ensure .mcp.json or *.mcp.json files exist in the current directory.")
            sys.exit(1)

    success = True
    for mcp_file in mcp_files:
        if not validate_mcp_file(mcp_file):
            success = False

    if not success:
        print("\n❌ MCP Configuration Validation FAILED")
        sys.exit(1)

    print("\n✅ MCP Configuration Validation PASSED")

if __name__ == "__main__":
    main()
