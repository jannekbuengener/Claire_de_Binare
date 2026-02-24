"""
LR-021 Redis Stream -> envelope.v1 JSONL Exporter (Slice 3).

Reads DECISION / ORDER / FILL events from a Redis Stream (read-only)
and writes deterministic envelope.v1 JSONL suitable for lr021_replay strict
validation.

Default output: raw envelope.v1 lines (no event_hash / chain_hash).
The downstream lr021_replay computes those hashes deterministically.
Use --include-hashes to opt-in to event_hash + optional chain_hash.

Read-only: uses XRANGE only. No writes, no consumer-group mutations,
no XACK. Safe for production streams.

Streaming: entries are read in batches and written immediately -- the
exporter never collects the full stream into memory.

Usage:
    python scripts/replay/lr021_export_redis.py \\
        --redis-url redis://localhost:6379 \\
        --stream lr021:events \\
        --out artifacts/exported_envelopes.jsonl

    # Filter by event type:
    python scripts/replay/lr021_export_redis.py \\
        --redis-url redis://localhost:6379 \\
        --stream lr021:events \\
        --type DECISION --type ORDER \\
        --out artifacts/decisions_orders.jsonl

    # With hashes (opt-in):
    python scripts/replay/lr021_export_redis.py \\
        --redis-url redis://localhost:6379 \\
        --stream lr021:events \\
        --include-hashes --compute-chain-hash \\
        --out artifacts/with_chain.jsonl

relations:
  role: redis_stream_exporter
  domain: replay
  upstream:
    - core/replay/canonical_json.py
    - scripts/replay/lr021_replay.py
  downstream:
    - tests/unit/replay/test_lr021_export_redis.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Dict, Generator, Optional, TextIO, Tuple

# Allow running as standalone script.
if __name__ == "__main__":
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.replay.canonical_json import canonical_json_dumps

# Re-use hashing from the replay runner -- single source of truth.
from scripts.replay.lr021_replay import compute_chain_hash, compute_event_hash

logger = logging.getLogger("lr021.export_redis")

VALID_EVENT_TYPES = {"DECISION", "ORDER", "FILL"}
GENESIS_HASH = "0" * 64

# Default batch size for XRANGE reads.
XRANGE_BATCH_SIZE = 1000


def parse_stream_entry(entry_id: str, fields: Dict[str, str]) -> Optional[dict]:
    """Parse a Redis Stream entry into an envelope dict.

    Redis Stream entries store field-value pairs as strings.
    We expect either:
      (a) A single 'envelope' field containing a JSON-encoded envelope, or
      (b) A 'data' field containing a JSON-encoded envelope, or
      (c) Individual fields matching envelope schema (schema_version,
          event_type, event_id, ts_ms, payload, ...).

    Returns None if the entry cannot be parsed as an envelope.
    """
    # Strategy (a)/(b): JSON blob in a known field
    for key in ("envelope", "data"):
        raw = fields.get(key)
        if raw is not None:
            try:
                obj = json.loads(raw)
                if isinstance(obj, dict) and "schema_version" in obj:
                    return obj
            except (json.JSONDecodeError, TypeError):
                pass

    # Strategy (c): flat fields
    if "schema_version" in fields and "event_type" in fields:
        payload_raw = fields.get("payload")
        payload: Any
        if payload_raw is not None:
            try:
                payload = json.loads(payload_raw)
            except (json.JSONDecodeError, TypeError):
                payload = payload_raw
        else:
            payload = {}

        ts_ms_raw = fields.get("ts_ms", "0")
        try:
            ts_ms = int(ts_ms_raw)
        except (ValueError, TypeError):
            ts_ms = 0

        envelope: dict[str, Any] = {
            "schema_version": fields["schema_version"],
            "event_type": fields["event_type"],
            "event_id": fields.get("event_id", entry_id),
            "ts_ms": ts_ms,
            "payload": payload if isinstance(payload, dict) else {},
        }
        # Optional policy fields
        for opt_key in ("policy_id", "policy_hash", "input_hash", "output_hash"):
            val = fields.get(opt_key)
            if val is not None:
                envelope[opt_key] = val

        return envelope

    logger.warning("Skipping unparseable stream entry %s", entry_id)
    return None


def iter_stream_entries(
    redis_client: Any,
    stream: str,
    start_id: str = "-",
    end_id: str = "+",
    limit: Optional[int] = None,
    batch_size: int = XRANGE_BATCH_SIZE,
) -> Generator[Tuple[str, Dict[str, str]], None, None]:
    """Yield entries from a Redis Stream via XRANGE (read-only).

    Reads in batches and yields immediately -- never collects the full
    stream into memory.  Entries arrive in Redis ID order (deterministic).

    Args:
        redis_client: A redis.Redis (or compatible) client instance.
        stream: Redis stream key name.
        start_id: Start ID (inclusive). Default '-' = beginning.
        end_id: End ID (inclusive). Default '+' = end.
        limit: Maximum total entries to yield. None = all.
        batch_size: Entries per XRANGE call.

    Yields:
        (entry_id, fields_dict) tuples in ID order.
    """
    current_start = start_id
    yielded = 0

    while True:
        count = batch_size
        if limit is not None:
            remaining = limit - yielded
            if remaining <= 0:
                return
            count = min(batch_size, remaining)

        entries = redis_client.xrange(
            stream, min=current_start, max=end_id, count=count,
        )

        if not entries:
            return

        last_id: Optional[str] = None

        for raw_entry in entries:
            entry_id = (
                raw_entry[0]
                if isinstance(raw_entry[0], str)
                else raw_entry[0].decode("utf-8")
            )
            raw_fields = raw_entry[1]
            fields: Dict[str, str] = {}
            for k, v in raw_fields.items():
                key = k if isinstance(k, str) else k.decode("utf-8")
                val = v if isinstance(v, str) else v.decode("utf-8")
                fields[key] = val

            yield (entry_id, fields)
            yielded += 1
            last_id = entry_id

            if limit is not None and yielded >= limit:
                return

        if len(entries) < count:
            # Stream exhausted
            return

        # Next batch starts after last entry ID
        assert last_id is not None
        parts = last_id.split("-")
        if len(parts) == 2:
            current_start = f"{parts[0]}-{int(parts[1]) + 1}"
        else:
            return


def export_envelopes(
    entries: Generator[Tuple[str, Dict[str, str]], None, None],
    output_stream: TextIO,
    *,
    type_filter: Optional[set] = None,
    include_hashes: bool = False,
    compute_chain: bool = False,
) -> dict:
    """Convert Redis Stream entries to envelope.v1 JSONL.

    Default: writes raw envelope dicts (no event_hash / chain_hash).
    The downstream lr021_replay computes those deterministically.

    Args:
        entries: Iterable of (entry_id, fields_dict) -- typically from
                 iter_stream_entries.
        output_stream: Writable text stream for JSONL output.
        type_filter: If set, only include envelopes with event_type in
                     this set.
        include_hashes: If True, compute and include event_hash.
        compute_chain: If True (requires include_hashes), also include
                       chain_hash.  Ignored when include_hashes is False.

    Returns:
        Summary dict with counts and final hashes.
    """
    prev_chain_hash = GENESIS_HASH
    exported = 0
    skipped = 0
    parse_errors = 0

    for entry_id, fields in entries:
        envelope = parse_stream_entry(entry_id, fields)
        if envelope is None:
            parse_errors += 1
            continue

        # Apply type filter
        if type_filter and envelope.get("event_type") not in type_filter:
            skipped += 1
            continue

        if include_hashes:
            event_hash = compute_event_hash(envelope)
            output_obj = {**envelope, "event_hash": event_hash}

            if compute_chain:
                chain_hash_val = compute_chain_hash(prev_chain_hash, event_hash)
                output_obj["chain_hash"] = chain_hash_val
                prev_chain_hash = chain_hash_val
        else:
            output_obj = envelope

        line = canonical_json_dumps(output_obj)
        output_stream.write(line + "\n")
        exported += 1

    summary: dict[str, Any] = {
        "exported": exported,
        "skipped_by_filter": skipped,
        "parse_errors": parse_errors,
    }
    if include_hashes and compute_chain:
        summary["final_chain_hash"] = prev_chain_hash
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="LR-021 Redis Stream -> envelope.v1 JSONL Exporter (Slice 3). "
        "Read-only: no writes, no consumer groups, no XACK."
    )
    parser.add_argument(
        "--redis-url",
        default="redis://localhost:6379",
        help="Redis connection URL (default: redis://localhost:6379)",
    )
    parser.add_argument(
        "--stream",
        required=True,
        help="Redis stream key to read from",
    )
    parser.add_argument(
        "--out", "-o",
        help="Output JSONL file path (default: stdout)",
    )
    parser.add_argument(
        "--start-id",
        default="-",
        help="Start stream ID inclusive (default: - = beginning)",
    )
    parser.add_argument(
        "--end-id",
        default="+",
        help="End stream ID inclusive (default: + = end)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of stream entries to read",
    )
    parser.add_argument(
        "--type",
        action="append",
        dest="types",
        choices=["DECISION", "ORDER", "FILL"],
        help="Filter by event type (repeatable, e.g. --type DECISION --type ORDER)",
    )
    parser.add_argument(
        "--include-hashes",
        action="store_true",
        help="Compute and include event_hash in output (default: raw envelopes)",
    )
    parser.add_argument(
        "--compute-chain-hash",
        action="store_true",
        help="Also compute chain_hash (implies --include-hashes)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=XRANGE_BATCH_SIZE,
        help=f"XRANGE batch size (default: {XRANGE_BATCH_SIZE})",
    )
    return parser


def main(argv: Optional[list] = None) -> None:
    """CLI entry point."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    # --compute-chain-hash implies --include-hashes
    include_hashes = args.include_hashes or args.compute_chain_hash

    # Lazy import: redis is only needed for actual CLI usage, not for
    # library usage or unit tests with mocked clients.
    try:
        import redis
    except ImportError:
        print(
            "ERROR: 'redis' package not installed. "
            "Install with: pip install redis",
            file=sys.stderr,
        )
        sys.exit(1)

    client = redis.Redis.from_url(args.redis_url, decode_responses=True)

    logger.info(
        "Reading stream %s [%s .. %s] limit=%s",
        args.stream,
        args.start_id,
        args.end_id,
        args.limit,
    )

    entry_iter = iter_stream_entries(
        redis_client=client,
        stream=args.stream,
        start_id=args.start_id,
        end_id=args.end_id,
        limit=args.limit,
        batch_size=args.batch_size,
    )

    type_filter = set(args.types) if args.types else None

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f_out:
            summary = export_envelopes(
                entry_iter,
                f_out,
                type_filter=type_filter,
                include_hashes=include_hashes,
                compute_chain=args.compute_chain_hash,
            )
    else:
        summary = export_envelopes(
            entry_iter,
            sys.stdout,
            type_filter=type_filter,
            include_hashes=include_hashes,
            compute_chain=args.compute_chain_hash,
        )

    print(json.dumps(summary, indent=2), file=sys.stderr)


if __name__ == "__main__":
    main()
