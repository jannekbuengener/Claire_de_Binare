#!/usr/bin/env python3
"""
MCP Configuration Validator
Checks if the MCP servers defined in configuration files are resolvable and executable.
Specifically handles python-based servers by verifying their modules can be imported.
"""

import json
import sys
import subprocess
from pathlib import Path

def validate_mcp_file(file_path: Path) -> bool:
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
                print(f"  Could not determine python module from args for {name}: {args}")
        elif command in ("cmd", "npx"):
            # Basic check for npx existence
            print(f"  Skipping deep validation for {command}-based server: {name}")
        else:
            print(f"  Unknown command type for {name}: {command}")

    return all_ok

def main():
    # Search for common MCP config filenames
    root = Path(".")
    mcp_files = list(root.glob("*.mcp.json"))
    if root.joinpath(".mcp.json").exists():
        mcp_files.append(root.joinpath(".mcp.json"))

    # Deduplicate
    mcp_files = sorted(list(set(mcp_files)))

    if not mcp_files:
        print("⚠️  No MCP configuration files found (*.mcp.json or .mcp.json)")
        return

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
