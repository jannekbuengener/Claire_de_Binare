"""
LR-021 Offline Replay Runner (Slice 1).

Reads JSONL input (envelope events), validates schema, computes
canonical hash per envelope, and writes output JSONL with event_hash
and optional chain_hash.

Usage:
    python scripts/replay/lr021_replay.py \\
        --input tests/fixtures/replay/lr021_sample_envelopes.jsonl \\
        --output artifacts/lr021_replay_output.jsonl

Pure file-to-file. No Redis, no service starts, no side effects.

relations:
  role: replay_runner
  domain: replay
  upstream:
    - core/replay/canonical_json.py
  downstream:
    - tests/unit/replay/test_lr021_replay.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import TextIO

# Allow running as standalone script: scripts/ has no __init__.py,
# so we add repo root to sys.path for `core.*` imports.
if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.replay.canonical_json import canonical_json_dumps, sha256_hex


REQUIRED_FIELDS = {"schema_version", "event_type", "event_id", "ts_ms", "payload"}
VALID_SCHEMA_VERSIONS = {"envelope.v1"}
VALID_EVENT_TYPES = {"DECISION", "ORDER", "FILL"}


def validate_envelope(obj: object, line_number: int) -> list[str]:
    """Validate envelope schema. Returns list of error messages (empty = valid)."""
    errors = []
    if not isinstance(obj, dict):
        errors.append(
            f"line {line_number}: envelope must be a JSON object, "
            f"got {type(obj).__name__}"
        )
        return errors
    missing = REQUIRED_FIELDS - set(obj.keys())
    if missing:
        errors.append(f"line {line_number}: missing fields: {sorted(missing)}")
    schema_version = obj.get("schema_version")
    if not schema_version or schema_version not in VALID_SCHEMA_VERSIONS:
        errors.append(
            f"line {line_number}: unsupported schema_version {schema_version!r}, "
            f"expected one of {sorted(VALID_SCHEMA_VERSIONS)}"
        )
    event_type = obj.get("event_type")
    if event_type and event_type not in VALID_EVENT_TYPES:
        errors.append(
            f"line {line_number}: invalid event_type '{event_type}', "
            f"expected one of {sorted(VALID_EVENT_TYPES)}"
        )
    if "ts_ms" in obj and not isinstance(obj["ts_ms"], int):
        errors.append(
            f"line {line_number}: ts_ms must be int, got {type(obj['ts_ms']).__name__}"
        )
    if "payload" in obj and not isinstance(obj["payload"], dict):
        errors.append(
            f"line {line_number}: payload must be dict, got {type(obj['payload']).__name__}"
        )
    return errors


def compute_event_hash(envelope_dict: dict) -> str:
    """Compute canonical SHA-256 hash of an envelope dict."""
    canonical = canonical_json_dumps(envelope_dict)
    return sha256_hex(canonical.encode("utf-8"))


def compute_chain_hash(prev_chain_hash: str, current_event_hash: str) -> str:
    """Compute chain hash: SHA-256(prev_chain_hash + ":" + current_event_hash)."""
    combined = (prev_chain_hash + ":" + current_event_hash).encode("utf-8")
    return sha256_hex(combined)


def replay(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    strict: bool = True,
    chain: bool = True,
) -> dict:
    """Run offline replay over JSONL input.

    Args:
        input_stream: Readable text stream of JSONL envelopes.
        output_stream: Writable text stream for output JSONL.
        strict: If True, abort on validation errors. If False, skip invalid lines.
        chain: If True, include chain_hash in output.

    Returns:
        Summary dict with counts and final hashes.
    """
    prev_chain_hash = "0" * 64  # Genesis hash
    processed = 0
    skipped = 0
    all_errors: list[str] = []

    for line_number, raw_line in enumerate(input_stream, start=1):
        line = raw_line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            msg = f"line {line_number}: invalid JSON: {e}"
            if strict:
                raise ValueError(msg) from e
            all_errors.append(msg)
            skipped += 1
            continue

        errors = validate_envelope(obj, line_number)
        if errors:
            if strict:
                raise ValueError("; ".join(errors))
            all_errors.extend(errors)
            skipped += 1
            continue

        event_hash = compute_event_hash(obj)

        output_obj = {**obj, "event_hash": event_hash}
        if chain:
            chain_hash_val = compute_chain_hash(prev_chain_hash, event_hash)
            output_obj["chain_hash"] = chain_hash_val
            prev_chain_hash = chain_hash_val

        output_line = canonical_json_dumps(output_obj)
        output_stream.write(output_line + "\n")
        processed += 1

    return {
        "processed": processed,
        "skipped": skipped,
        "errors": all_errors,
        "final_chain_hash": prev_chain_hash if chain else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LR-021 Offline Replay Runner (Slice 1)"
    )
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file path")
    parser.add_argument(
        "--output", "-o", help="Output JSONL file path (default: stdout)"
    )
    parser.add_argument(
        "--no-chain", action="store_true", help="Disable chain_hash computation"
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Skip invalid lines instead of aborting",
    )
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f_in:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f_out:
                summary = replay(
                    f_in, f_out, strict=not args.lenient, chain=not args.no_chain
                )
        else:
            summary = replay(
                f_in, sys.stdout, strict=not args.lenient, chain=not args.no_chain
            )

    print(json.dumps(summary, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
