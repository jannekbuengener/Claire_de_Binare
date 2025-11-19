#!/usr/bin/env python3
"""
Claire de Binaire - Command Line Interface

Commands:
    replay      Replay events from event log
    explain     Explain specific trading decision
    trace       Trace all events for correlation ID
    stats       Show event statistics
    snapshot    Create or restore state snapshot
    validate    Validate determinism

Examples:
    # Replay events from date range
    python claire_cli.py replay --from 2025-02-10 --to 2025-02-15

    # Replay specific sequence range
    python claire_cli.py replay --sequence 1000 2000

    # Explain decision
    python claire_cli.py explain <event-id>

    # Trace trade
    python claire_cli.py trace <correlation-id>

    # Validate determinism
    python claire_cli.py validate --sequence 1 1000
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

# Add services directory to path
sys.path.insert(0, os.path.dirname(__file__))

from backoffice.services.event_store.service import DatabaseConnection, EventReader
from services.replay_engine import ReplayEngine

# ==============================================================================
# CONFIGURATION
# ==============================================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/claire_de_binaire",
)

# ==============================================================================
# COMMAND IMPLEMENTATIONS
# ==============================================================================


def replay_command(args):
    """
    Replay events from event log.

    Args:
        args: Parsed arguments
    """
    logger.info("🎬 Starting replay...")

    # Connect to database
    db = DatabaseConnection(DATABASE_URL)
    reader = EventReader(db)
    engine = ReplayEngine(reader)

    # Determine replay range
    from_sequence = None
    to_sequence = None

    if args.sequence:
        from_sequence, to_sequence = args.sequence

    # TODO: Parse date strings to sequence numbers
    # if args.from_date or args.to_date:
    #     from_sequence = date_to_sequence(args.from_date)
    #     to_sequence = date_to_sequence(args.to_date)

    # Run replay
    try:
        stats = engine.replay_range(
            from_sequence=from_sequence,
            to_sequence=to_sequence,
            use_snapshot=not args.no_snapshot,
        )

        print("\n" + "=" * 60)
        print("REPLAY COMPLETE")
        print("=" * 60)
        print(f"Events loaded: {stats.get('events_loaded', 0)}")
        print(f"From sequence: {stats['replay_range']['from_sequence']}")
        print(f"To sequence: {stats['replay_range']['to_sequence']}")
        print("\nFinal State:")
        print(json.dumps(stats["final_state"], indent=2))

    except Exception as e:
        logger.error(f"❌ Replay failed: {e}")
        sys.exit(1)
    finally:
        db.close()


def explain_command(args):
    """
    Explain specific trading decision.

    Args:
        args: Parsed arguments
    """
    logger.info(f"🔍 Explaining decision {args.event_id}...")

    db = DatabaseConnection(DATABASE_URL)
    reader = EventReader(db)

    try:
        explanation = reader.explain_decision(args.event_id)

        if not explanation:
            print(f"❌ No decision found for event ID: {args.event_id}")
            sys.exit(1)

        print("\n" + "=" * 60)
        print(f"DECISION EXPLANATION: {args.event_id}")
        print("=" * 60)

        # Decision details
        if "decision" in explanation:
            decision = explanation["decision"]
            print(f"\n📊 Decision:")
            print(f"  Event Type: {decision.get('event_type')}")
            print(f"  Sequence: {decision.get('sequence_number')}")
            print(f"  Timestamp: {decision.get('timestamp_utc')}")
            print(f"  Approved: {decision.get('payload', {}).get('approved')}")
            print(f"  Reason: {decision.get('payload', {}).get('reason')}")

        # Signal details
        if "signal" in explanation and explanation["signal"]:
            signal = explanation["signal"]
            print(f"\n📡 Signal:")
            print(f"  Symbol: {signal.get('payload', {}).get('symbol')}")
            print(f"  Side: {signal.get('payload', {}).get('side')}")
            print(f"  Confidence: {signal.get('payload', {}).get('confidence')}")
            print(f"  Reason: {signal.get('payload', {}).get('reason')}")

        # Market data details
        if "market_data" in explanation and explanation["market_data"]:
            market_data = explanation["market_data"]
            print(f"\n📈 Market Data:")
            print(f"  Symbol: {market_data.get('payload', {}).get('symbol')}")
            print(f"  Price: {market_data.get('payload', {}).get('price')}")
            print(f"  Volume: {market_data.get('payload', {}).get('volume')}")

        # Causation chain
        if "causation_chain" in explanation:
            print(f"\n🔗 Causation Chain:")
            for event in explanation["causation_chain"]:
                print(f"  → {event.get('event_type')} (seq {event.get('sequence_number')})")

        print("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"❌ Explain failed: {e}")
        sys.exit(1)
    finally:
        db.close()


def trace_command(args):
    """
    Trace all events for correlation ID.

    Args:
        args: Parsed arguments
    """
    logger.info(f"🔍 Tracing correlation {args.correlation_id}...")

    db = DatabaseConnection(DATABASE_URL)
    reader = EventReader(db)

    try:
        events = reader.get_correlation_events(args.correlation_id)

        if not events:
            print(f"❌ No events found for correlation ID: {args.correlation_id}")
            sys.exit(1)

        print("\n" + "=" * 60)
        print(f"TRADE/SESSION TRACE: {args.correlation_id}")
        print("=" * 60)
        print(f"Total events: {len(events)}\n")

        for i, event in enumerate(events, 1):
            print(f"{i}. {event.get('event_type')} (seq {event.get('sequence_number')})")
            print(f"   Timestamp: {event.get('timestamp_utc')}")
            payload = event.get("payload", {})

            # Print relevant payload fields
            if event.get("event_type") == "market_data":
                print(f"   Symbol: {payload.get('symbol')}, Price: {payload.get('price')}")
            elif event.get("event_type") == "signal_generated":
                print(
                    f"   {payload.get('side')} {payload.get('symbol')} @ {payload.get('confidence')} confidence"
                )
            elif event.get("event_type") == "risk_decision":
                print(
                    f"   Approved: {payload.get('approved')}, Reason: {payload.get('reason')}"
                )
            elif event.get("event_type") == "order_result":
                print(
                    f"   Status: {payload.get('status')}, Filled: {payload.get('filled_quantity')}"
                )

            print()

    except Exception as e:
        logger.error(f"❌ Trace failed: {e}")
        sys.exit(1)
    finally:
        db.close()


def stats_command(args):
    """
    Show event statistics.

    Args:
        args: Parsed arguments
    """
    logger.info("📊 Fetching event statistics...")

    db = DatabaseConnection(DATABASE_URL)

    try:
        # Get event stats (last 24h by default)
        query = "SELECT * FROM get_event_stats()"
        results = db.execute(query)

        if not results:
            print("No events found")
            sys.exit(0)

        print("\n" + "=" * 60)
        print("EVENT STATISTICS (Last 24 hours)")
        print("=" * 60)
        print(
            f"{'Event Type':<25} {'Count':<10} {'First Event':<20} {'Last Event':<20}"
        )
        print("-" * 60)

        for row in results:
            print(
                f"{row['event_type']:<25} {row['event_count']:<10} {str(row['first_event']):<20} {str(row['last_event']):<20}"
            )

        print("\n" + "=" * 60)

    except Exception as e:
        logger.error(f"❌ Stats failed: {e}")
        sys.exit(1)
    finally:
        db.close()


def validate_command(args):
    """
    Validate determinism by replaying twice.

    Args:
        args: Parsed arguments
    """
    logger.info("🔍 Validating determinism...")

    if not args.sequence or len(args.sequence) != 2:
        print("❌ Error: --sequence requires two values (from to)")
        sys.exit(1)

    from_sequence, to_sequence = args.sequence

    db = DatabaseConnection(DATABASE_URL)
    reader = EventReader(db)
    engine = ReplayEngine(reader)

    try:
        result = engine.validate_determinism(
            from_sequence=from_sequence, to_sequence=to_sequence
        )

        print("\n" + "=" * 60)
        print("DETERMINISM VALIDATION")
        print("=" * 60)
        print(f"Range: {from_sequence} → {to_sequence}")
        print(f"Deterministic: {'✅ YES' if result['deterministic'] else '❌ NO'}")

        if not result["deterministic"]:
            print("\n⚠️  STATE DIFFERENCES DETECTED:")
            print(json.dumps(result["state_diff"], indent=2))

        print("\n" + "=" * 60)

        sys.exit(0 if result["deterministic"] else 1)

    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        sys.exit(1)
    finally:
        db.close()


# ==============================================================================
# MAIN CLI
# ==============================================================================


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Claire de Binaire - Deterministic Replay & Audit CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -------------------------------------------------------------------------
    # REPLAY command
    # -------------------------------------------------------------------------
    replay_parser = subparsers.add_parser("replay", help="Replay events from log")

    replay_parser.add_argument(
        "--from",
        dest="from_date",
        type=str,
        help="Start date (YYYY-MM-DD)",
    )

    replay_parser.add_argument(
        "--to",
        dest="to_date",
        type=str,
        help="End date (YYYY-MM-DD)",
    )

    replay_parser.add_argument(
        "--sequence",
        type=int,
        nargs=2,
        metavar=("FROM", "TO"),
        help="Replay specific sequence range",
    )

    replay_parser.add_argument(
        "--no-snapshot",
        action="store_true",
        help="Don't use state snapshots (full replay)",
    )

    # -------------------------------------------------------------------------
    # EXPLAIN command
    # -------------------------------------------------------------------------
    explain_parser = subparsers.add_parser("explain", help="Explain trading decision")

    explain_parser.add_argument("event_id", type=str, help="Event ID (UUID)")

    # -------------------------------------------------------------------------
    # TRACE command
    # -------------------------------------------------------------------------
    trace_parser = subparsers.add_parser(
        "trace", help="Trace all events for trade/session"
    )

    trace_parser.add_argument("correlation_id", type=str, help="Correlation ID (UUID)")

    # -------------------------------------------------------------------------
    # STATS command
    # -------------------------------------------------------------------------
    stats_parser = subparsers.add_parser("stats", help="Show event statistics")

    # -------------------------------------------------------------------------
    # VALIDATE command
    # -------------------------------------------------------------------------
    validate_parser = subparsers.add_parser("validate", help="Validate determinism")

    validate_parser.add_argument(
        "--sequence",
        type=int,
        nargs=2,
        metavar=("FROM", "TO"),
        required=True,
        help="Sequence range to validate",
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Dispatch to command handler
    commands = {
        "replay": replay_command,
        "explain": explain_command,
        "trace": trace_command,
        "stats": stats_command,
        "validate": validate_command,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"❌ Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
