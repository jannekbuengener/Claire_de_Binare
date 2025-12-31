#!/usr/bin/env python3
"""
Contract Validation CLI Tool
Validates Redis messages against JSON Schemas.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

try:
    from jsonschema import Draft7Validator
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    print("Missing dependency: jsonschema. Install with 'pip install jsonschema'.", file=sys.stderr)
    raise SystemExit(2) from exc

try:
    import redis  # type: ignore
except ImportError:
    redis = None


CONTRACTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "contracts"


def load_schema(schema_name: str) -> Dict[str, Any]:
    schema_path = CONTRACTS_DIR / f"{schema_name}.schema.json"
    if not schema_path.exists():
        print(f"Schema not found: {schema_path}", file=sys.stderr)
        raise SystemExit(1)
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def coerce_payload_types(payload: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    properties = schema.get("properties", {})
    for key, spec in properties.items():
        if key not in payload:
            continue
        value = payload[key]
        if not isinstance(value, str):
            continue
        expected = spec.get("type")
        if isinstance(expected, list):
            expected_types = expected
        else:
            expected_types = [expected]
        if "integer" in expected_types:
            try:
                payload[key] = int(value)
            except ValueError:
                pass
        elif "number" in expected_types:
            try:
                payload[key] = float(value)
            except ValueError:
                pass
    return payload


def load_payload_from_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_payload_from_stdin() -> Dict[str, Any]:
    return json.load(sys.stdin)


def load_payload_from_redis(
    stream: str,
    host: str,
    port: int,
    password: str | None,
    db: int,
) -> Dict[str, Any]:
    if redis is None:
        print("Missing dependency: redis. Install with 'pip install redis'.", file=sys.stderr)
        raise SystemExit(2)
    client = redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True)
    entries = client.xrevrange(stream, max="+", min="-", count=1)
    if not entries:
        print(f"No entries found in stream '{stream}'.", file=sys.stderr)
        raise SystemExit(1)
    _, payload = entries[0]
    return dict(payload)


def validate_payload(schema_name: str, payload: Dict[str, Any], schema: Dict[str, Any], verbose: bool) -> None:
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.path))
    if errors:
        print(f"Validation FAILED ({len(errors)} error(s))")
        for index, error in enumerate(errors, 1):
            path = ".".join(str(part) for part in error.path) or "<root>"
            print(f"\nError {index}:")
            print(f"  Path: {path}")
            print(f"  Message: {error.message}")
            if verbose:
                schema_path = ".".join(str(part) for part in error.schema_path)
                print(f"  Schema Path: {schema_path}")
        raise SystemExit(1)
    print("Validation PASSED")
    if verbose:
        print(f"  Schema: {schema_name}")
        print(f"  Version: {payload.get('schema_version', 'N/A')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Redis messages against contracts")
    parser.add_argument("schema", choices=["market_data", "signal"], help="Contract schema name")
    parser.add_argument("--file", "-f", help="JSON file to validate")
    parser.add_argument("--stdin", action="store_true", help="Read JSON payload from stdin")
    parser.add_argument("--redis-stream", help="Read latest entry from Redis stream")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")
    parser.add_argument("--redis-password", default=None, help="Redis password")
    parser.add_argument("--redis-db", type=int, default=0, help="Redis DB index")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    schema = load_schema(args.schema)

    if args.file:
        payload = load_payload_from_file(Path(args.file))
    elif args.stdin:
        payload = load_payload_from_stdin()
    elif args.redis_stream:
        payload = load_payload_from_redis(
            args.redis_stream, args.redis_host, args.redis_port, args.redis_password, args.redis_db
        )
        payload = coerce_payload_types(payload, schema)
    else:
        print("Provide one input source: --file, --stdin, or --redis-stream.", file=sys.stderr)
        raise SystemExit(1)

    validate_payload(args.schema, payload, schema, args.verbose)


if __name__ == "__main__":
    main()
