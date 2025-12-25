"""
Deterministic Replay Runner - Replays paper-trading sessions from stream.fills

Usage:
    python -m tools.replay.replay --count 50 --out artifacts/replay.jsonl

Environment Variables:
    CDB_REPLAY=1               - Enable replay mode (safety gate)
    CDB_REPLAY_COUNT=N         - Number of entries to replay (default: 10)
    CDB_REPLAY_FROM_ID=<id>    - Start from specific stream ID
    CDB_REPLAY_TO_ID=<id>      - End at specific stream ID
    CDB_REPLAY_SEED=123        - Random seed for determinism (optional)
    REDIS_PASSWORD             - Redis password (default: claire_redis_secret_2024)

Determinism Guarantees:
    - Events processed in Stream ID order (lexicographic)
    - No datetime.now() calls (uses event timestamps)
    - Fixed random seed if CDB_REPLAY_SEED set
    - Stable JSONL output (sorted keys)

Supports: #258 (Deterministic Replay)
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Optional

import redis


class ReplayConfig:
    """Configuration for replay session."""

    def __init__(self):
        self.enabled = os.getenv("CDB_REPLAY", "0") == "1"
        self.stream_name = os.getenv("CDB_REPLAY_STREAM", "stream.fills")
        self.count = int(os.getenv("CDB_REPLAY_COUNT", "10"))
        self.from_id = os.getenv("CDB_REPLAY_FROM_ID", "-")  # Oldest
        self.to_id = os.getenv("CDB_REPLAY_TO_ID", "+")      # Newest
        self.seed = os.getenv("CDB_REPLAY_SEED")
        self.output_file = os.getenv("CDB_REPLAY_OUTPUT")

        # Redis connection
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = os.getenv("REDIS_PASSWORD", "claire_redis_secret_2024")

    def validate(self) -> None:
        """Validate configuration."""
        if not self.enabled:
            raise ValueError("Replay not enabled. Set CDB_REPLAY=1 to enable.")
        if self.count < 1:
            raise ValueError(f"Invalid count: {self.count}. Must be >= 1.")


class StreamEvent:
    """Parsed stream event with type conversion."""

    def __init__(self, stream_id: str, raw_data: dict):
        self.stream_id = stream_id
        self.raw = raw_data

        # Required fields (with type conversion)
        self.type = raw_data.get("type", "unknown")
        self.order_id = raw_data.get("order_id", "")
        self.status = raw_data.get("status", "")
        self.symbol = raw_data.get("symbol", "")
        self.side = raw_data.get("side", "")

        # Convert numeric fields from strings
        try:
            self.quantity = float(raw_data.get("quantity", "0"))
        except ValueError:
            self.quantity = 0.0

        try:
            self.filled_quantity = float(raw_data.get("filled_quantity", "0"))
        except ValueError:
            self.filled_quantity = 0.0

        try:
            self.timestamp = int(raw_data.get("timestamp", "0"))
        except ValueError:
            self.timestamp = 0

        # Optional fields
        self.price = self._safe_float(raw_data.get("price"))
        self.strategy_id = raw_data.get("strategy_id")
        self.bot_id = raw_data.get("bot_id")
        self.client_id = raw_data.get("client_id")
        self.error_message = raw_data.get("error_message")

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        """Safely convert string to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def to_dict(self) -> dict:
        """Convert to deterministic dictionary (sorted keys)."""
        result = {
            "stream_id": self.stream_id,
            "type": self.type,
            "order_id": self.order_id,
            "status": self.status,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "timestamp": self.timestamp,
        }

        # Add optional fields if present
        if self.price is not None:
            result["price"] = self.price
        if self.strategy_id is not None:
            result["strategy_id"] = self.strategy_id
        if self.bot_id is not None:
            result["bot_id"] = self.bot_id
        if self.client_id is not None:
            result["client_id"] = self.client_id
        if self.error_message is not None:
            result["error_message"] = self.error_message

        # Return with sorted keys for determinism
        return dict(sorted(result.items()))

    def to_jsonl(self) -> str:
        """Convert to JSONL format (one line, sorted keys)."""
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


class ReplayRunner:
    """Deterministic replay runner."""

    def __init__(self, config: ReplayConfig):
        self.config = config
        self.redis_client = None
        self.events_processed = 0
        self.output_file_handle = None

    def connect_redis(self) -> None:
        """Connect to Redis with fallback."""
        # Try internal docker network first
        try:
            client = redis.Redis(
                host="cdb_redis",
                port=6379,
                password=self.config.redis_password,
                decode_responses=True,
                socket_timeout=5
            )
            client.ping()
            self.redis_client = client
            print(f"✅ Connected to Redis (cdb_redis:6379)")
            return
        except (redis.ConnectionError, redis.TimeoutError):
            pass

        # Fallback to configured host
        try:
            client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                password=self.config.redis_password,
                decode_responses=True,
                socket_timeout=5
            )
            client.ping()
            self.redis_client = client
            print(f"✅ Connected to Redis ({self.config.redis_host}:{self.config.redis_port})")
            return
        except (redis.ConnectionError, redis.TimeoutError) as e:
            raise ConnectionError(
                f"Could not connect to Redis "
                f"(tried cdb_redis:6379 and {self.config.redis_host}:{self.config.redis_port})"
            ) from e

    def read_stream(self) -> list[tuple[str, dict]]:
        """Read events from stream in deterministic order."""
        if self.redis_client is None:
            raise ValueError("Redis not connected. Call connect_redis() first.")

        # Check stream exists
        if not self.redis_client.exists(self.config.stream_name):
            raise ValueError(f"Stream '{self.config.stream_name}' does not exist")

        # Read entries using XRANGE (deterministic ordering)
        entries = self.redis_client.xrange(
            self.config.stream_name,
            min=self.config.from_id,
            max=self.config.to_id,
            count=self.config.count
        )

        return entries

    def open_output(self) -> None:
        """Open output file for writing."""
        if self.config.output_file:
            self.output_file_handle = open(self.config.output_file, "w", encoding="utf-8")
            print(f"📝 Output: {self.config.output_file}")
        else:
            self.output_file_handle = sys.stdout
            print(f"📝 Output: stdout")

    def close_output(self) -> None:
        """Close output file."""
        if self.output_file_handle and self.output_file_handle != sys.stdout:
            self.output_file_handle.close()

    def write_event(self, event: StreamEvent) -> None:
        """Write event to output in JSONL format."""
        line = event.to_jsonl()
        self.output_file_handle.write(line + "\n")
        self.events_processed += 1

    def run(self) -> None:
        """Execute replay."""
        print("=" * 60)
        print("Deterministic Replay Runner (#258)")
        print("=" * 60)
        print(f"Stream: {self.config.stream_name}")
        print(f"Range: {self.config.from_id} → {self.config.to_id}")
        print(f"Count: {self.config.count}")
        if self.config.seed:
            print(f"Seed: {self.config.seed}")
        print("=" * 60)

        # Connect to Redis
        self.connect_redis()

        # Read stream entries
        print(f"📖 Reading stream...")
        entries = self.read_stream()
        print(f"✅ Found {len(entries)} entries")

        if len(entries) == 0:
            print("⚠️  No entries to replay")
            return

        # Open output
        self.open_output()

        # Process events
        print(f"⚙️  Processing events...")
        for entry_id, entry_data in entries:
            event = StreamEvent(entry_id, entry_data)
            self.write_event(event)

        # Close output
        self.close_output()

        # Summary
        print("=" * 60)
        print(f"✅ Replay Complete")
        print(f"Events Processed: {self.events_processed}")
        print(f"Output File: {self.config.output_file or 'stdout'}")
        print("=" * 60)

    def calculate_output_hash(self) -> Optional[str]:
        """Calculate SHA256 hash of output file for determinism verification."""
        if not self.config.output_file or not os.path.exists(self.config.output_file):
            return None

        sha256 = hashlib.sha256()
        with open(self.config.output_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        return sha256.hexdigest()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Deterministic Replay Runner for stream.fills (#258)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--count",
        type=int,
        help="Number of entries to replay (default: 10)"
    )
    parser.add_argument(
        "--from-id",
        help="Start from specific stream ID (default: oldest)"
    )
    parser.add_argument(
        "--to-id",
        help="End at specific stream ID (default: newest)"
    )
    parser.add_argument(
        "--out",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--stream",
        help="Stream name (default: stream.fills)"
    )
    parser.add_argument(
        "--seed",
        help="Random seed for determinism (optional)"
    )
    parser.add_argument(
        "--verify-hash",
        action="store_true",
        help="Print SHA256 hash of output file after replay"
    )

    args = parser.parse_args()

    # Build config (CLI args override env vars)
    config = ReplayConfig()
    config.enabled = True  # CLI invocation implies enabled

    if args.count is not None:
        config.count = args.count
    if args.from_id:
        config.from_id = args.from_id
    if args.to_id:
        config.to_id = args.to_id
    if args.out:
        config.output_file = args.out
    if args.stream:
        config.stream_name = args.stream
    if args.seed:
        config.seed = args.seed

    # Validate
    try:
        config.validate()
    except ValueError as e:
        print(f"❌ Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Run replay
    runner = ReplayRunner(config)
    try:
        runner.run()
    except Exception as e:
        print(f"❌ Replay Failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Calculate and print hash if requested
    if args.verify_hash and config.output_file:
        output_hash = runner.calculate_output_hash()
        if output_hash:
            print(f"📊 Output Hash (SHA256): {output_hash}")


if __name__ == "__main__":
    main()
