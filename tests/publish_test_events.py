#!/usr/bin/env python3
"""
Redis Test Event Publisher - Claire de Binare
Publishes test events to Redis for db_writer validation
"""

import json
import os
import sys
import time
import redis
from json import JSONDecodeError
from pathlib import Path


def load_test_events():
    """Load test events from JSON file"""
    test_file = Path(__file__).parent / "test_events.json"

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)

    try:
        with open(test_file) as f:
            events = json.load(f)
    except JSONDecodeError as exc:
        print(f"❌ Failed to parse {test_file}: {exc}")
        sys.exit(1)

    required_keys = {
        "signals": ["symbol", "signal_type"],
        "orders": ["symbol", "side"],
        "order_results": ["symbol", "status"],
        "portfolio_snapshots": ["timestamp"],
    }

    for key, required_fields in required_keys.items():
        section = events.get(key)
        if section is None:
            print(f"❌ Missing required key '{key}' in test events")
            sys.exit(1)
        if not isinstance(section, list):
            print(f"❌ '{key}' must be a list in test_events.json")
            sys.exit(1)

        for idx, entry in enumerate(section, start=1):
            if not isinstance(entry, dict):
                print(f"❌ Entry {idx} in '{key}' must be an object")
                sys.exit(1)

            missing = [field for field in required_fields if field not in entry]
            if missing:
                print(
                    f"❌ Entry {idx} in '{key}' is missing required field(s): {', '.join(missing)}"
                )
                sys.exit(1)

    return events


def connect_redis():
    """Connect to Redis"""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_password = os.getenv("REDIS_PASSWORD", "")

    try:
        client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password or None,
            decode_responses=True,
        )
        client.ping()
        print(f"✅ Connected to Redis at {redis_host}:{redis_port}")
        return client
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        sys.exit(1)


def publish_events(redis_client, events_data):
    """Publish all test events to Redis"""

    # Channel mapping
    channels = {
        "signals": "signals",
        "orders": "orders",
        "order_results": "order_results",
        "portfolio_snapshots": "portfolio_snapshots",
    }

    total_published = 0

    for event_type, channel in channels.items():
        events = events_data.get(event_type, [])

        if not events:
            print(f"⏭️  No {event_type} to publish")
            continue

        print(f"\n📤 Publishing {len(events)} {event_type} to channel '{channel}'...")

        for i, event in enumerate(events, 1):
            try:
                # Publish to Redis
                message = json.dumps(event, ensure_ascii=False)
                redis_client.publish(channel, message)

                # Log
                symbol = event.get("symbol", "N/A")
                side = event.get("side", event.get("status", "N/A"))
                print(f"  ✅ [{i}/{len(events)}] Published: {symbol} {side}")

                total_published += 1

                # Small delay to avoid overwhelming the system
                time.sleep(0.1)

            except Exception as e:
                print(f"  ❌ Failed to publish event {i}: {e}")

    return total_published


def verify_db_writer_running(redis_client):
    """Check if db_writer is subscribed to channels"""
    print("\n🔍 Checking if db_writer is listening...")

    channels_to_check = ["signals", "orders", "order_results", "portfolio_snapshots"]

    for channel in channels_to_check:
        try:
            # Use PUBSUB NUMSUB to check subscribers
            result = redis_client.execute_command("PUBSUB", "NUMSUB", channel)
            num_subscribers = result[1] if len(result) > 1 else 0

            if num_subscribers > 0:
                print(f"  ✅ Channel '{channel}': {num_subscribers} subscriber(s)")
            else:
                print(f"  ⚠️  Channel '{channel}': No subscribers!")
        except Exception as e:
            print(f"  ❌ Failed to check channel '{channel}': {e}")


def main():
    """Main execution"""
    print("=" * 60)
    print("🧪 Claire de Binare - Test Event Publisher")
    print("=" * 60)

    # Load test events
    print("\n📂 Loading test events...")
    events_data = load_test_events()

    total_events = sum(len(events) for events in events_data.values())
    print(f"✅ Loaded {total_events} test events:")
    for event_type, events in events_data.items():
        print(f"   - {event_type}: {len(events)}")

    # Connect to Redis
    print("\n🔌 Connecting to Redis...")
    redis_client = connect_redis()

    # Verify db_writer is running
    verify_db_writer_running(redis_client)

    # Ask for confirmation (unless auto-publish is enabled)
    auto_publish = os.getenv("CDB_AUTO_PUBLISH")

    if auto_publish and auto_publish.lower() in ("1", "true", "yes", "y", "on"):
        print("\n" + "=" * 60)
        print(
            "📤 Auto-publish enabled via CDB_AUTO_PUBLISH; skipping confirmation prompt."
        )
    else:
        print("\n" + "=" * 60)
        try:
            response = input("📤 Publish events to Redis? [y/N]: ")
        except EOFError:
            print("❌ No input available and auto-publish not enabled; aborting.")
            sys.exit(1)

        if response.lower() != "y":
            print("❌ Aborted by user")
            sys.exit(0)

    # Publish events
    print("\n🚀 Publishing events...")
    total_published = publish_events(redis_client, events_data)

    # Summary
    print("\n" + "=" * 60)
    print(f"✅ Published {total_published}/{total_events} events successfully!")
    print("=" * 60)
    print("\n📊 Next steps:")
    print("1. Check db_writer logs:")
    print("   docker compose logs cdb_db_writer --tail=50")
    print("\n2. Validate in PostgreSQL:")
    print("   docker exec -it cdb_postgres psql -U claire_user -d claire_de_binare")
    print("   SELECT COUNT(*) FROM signals;")
    print("   SELECT COUNT(*) FROM orders;")
    print("   SELECT COUNT(*) FROM trades;")
    print("   SELECT COUNT(*) FROM portfolio_snapshots;")
    print("\n3. Run validation script:")
    print("   python tests/validate_persistence.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
