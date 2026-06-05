#!/usr/bin/env python3
"""
example.py - Example automation script for cdb-control-intake

Usage:
    python example.py <input> [--verbose]

Exit Codes:
    0  - Success
    1  - General failure
    2  - Invalid arguments
"""

import argparse
import sys
from pathlib import Path


def process(input_path: Path, verbose: bool = False) -> bool:
    """TODO: Implement processing logic."""
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return False

    if verbose:
        print(f"Processing: {input_path}")

    # TODO: Add processing logic
    return True


def main():
    parser = argparse.ArgumentParser(description="Example script for cdb-control-intake")
    parser.add_argument("input", type=Path, help="Input file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    success = process(args.input, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
