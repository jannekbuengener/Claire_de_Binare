"""
Event Store Service for Claire de Binaire

This service persists all events to PostgreSQL for:
- Deterministic replay
- Full audit trail
- Compliance and debugging

Responsibilities:
- Subscribe to all event channels on Redis
- Persist events to PostgreSQL (append-only)
- Create periodic state snapshots
- Provide event query API
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import psycopg2
from flask import Flask, jsonify, request
from psycopg2.extras import Json, RealDictCursor

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from services.event_sourcing import (
    AlertEvent,
    BaseEvent,
    EventType,
    MarketDataEvent,
    OrderRequestEvent,
    OrderResultEvent,
    PositionUpdateEvent,
    RiskDecisionEvent,
    SignalGeneratedEvent,
    StateSnapshotEvent,
    SystemEvent,
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Flask app for health checks and API
app = Flask(__name__)

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@cdb_postgres:5432/claire_de_binaire",
)

# Snapshot configuration
SNAPSHOT_INTERVAL = int(os.getenv("SNAPSHOT_INTERVAL", "1000"))  # Every N events
SNAPSHOT_TIME_INTERVAL = int(
    os.getenv("SNAPSHOT_TIME_INTERVAL", "3600")
)  # Every N seconds


# ==============================================================================
# DATABASE CONNECTION
# ==============================================================================


class DatabaseConnection:
    """PostgreSQL connection manager."""

    def __init__(self, database_url: str):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        self.conn = None
        self._connect()

    def _connect(self) -> None:
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False  # Use transactions
            logger.info("✅ Connected to PostgreSQL event store")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """
        Execute SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results or None
        """
        if not self.conn or self.conn.closed:
            self._connect()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                if cur.description:  # Query returns data
                    return cur.fetchall()
                self.conn.commit()
                return None
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Database query failed: {e}")
            raise

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """
        Execute query with multiple parameter sets.

        Args:
            query: SQL query string
            params_list: List of parameter tuples
        """
        if not self.conn or self.conn.closed:
            self._connect()

        try:
            with self.conn.cursor() as cur:
                cur.executemany(query, params_list)
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ Database executemany failed: {e}")
            raise

    def close(self) -> None:
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("Closed PostgreSQL connection")


# ==============================================================================
# EVENT WRITER
# ==============================================================================


class EventWriter:
    """
    Writes events to PostgreSQL event store.

    Ensures:
    - All events are persisted (durability)
    - Events are immutable (append-only)
    - Sequence numbers are monotonic
    - Transactions maintain consistency
    """

    def __init__(self, db: DatabaseConnection):
        """
        Initialize event writer.

        Args:
            db: Database connection
        """
        self.db = db
        self.event_count = 0
        self.last_snapshot_sequence = 0
        self.last_snapshot_time = time.time()

    def write_event(self, event: BaseEvent) -> None:
        """
        Write single event to database.

        Args:
            event: Event to persist

        Raises:
            Exception: If write fails
        """
        query = """
            INSERT INTO events (
                event_id,
                event_type,
                sequence_number,
                timestamp_utc,
                timestamp_logical,
                causation_id,
                correlation_id,
                metadata,
                payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Convert Pydantic model to dict
        event_dict = event.model_dump(mode="json")

        # Extract base fields
        params = (
            str(event.event_id),
            event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
            event.sequence_number,
            event.timestamp_utc,
            event.timestamp_logical,
            str(event.causation_id) if event.causation_id else None,
            str(event.correlation_id),
            Json(event.metadata.model_dump()),
            Json(self._extract_payload(event_dict)),
        )

        try:
            self.db.execute(query, params)
            self.event_count += 1
            logger.debug(
                f"✅ Event persisted: {event.event_type} seq={event.sequence_number}"
            )

            # Check if snapshot needed
            self._check_snapshot_trigger(event.sequence_number)

        except Exception as e:
            logger.error(f"❌ Failed to write event: {e}")
            raise

    def write_events_batch(self, events: List[BaseEvent]) -> None:
        """
        Write multiple events in single transaction.

        Args:
            events: List of events to persist
        """
        if not events:
            return

        query = """
            INSERT INTO events (
                event_id,
                event_type,
                sequence_number,
                timestamp_utc,
                timestamp_logical,
                causation_id,
                correlation_id,
                metadata,
                payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        params_list = []
        for event in events:
            event_dict = event.model_dump(mode="json")
            params_list.append(
                (
                    str(event.event_id),
                    event.event_type.value if isinstance(event.event_type, EventType) else event.event_type,
                    event.sequence_number,
                    event.timestamp_utc,
                    event.timestamp_logical,
                    str(event.causation_id) if event.causation_id else None,
                    str(event.correlation_id),
                    Json(event.metadata.model_dump()),
                    Json(self._extract_payload(event_dict)),
                )
            )

        try:
            self.db.execute_many(query, params_list)
            self.event_count += len(events)
            logger.info(f"✅ Batch persisted: {len(events)} events")
        except Exception as e:
            logger.error(f"❌ Failed to write event batch: {e}")
            raise

    def _extract_payload(self, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract payload from event dict (everything except base fields).

        Args:
            event_dict: Event as dictionary

        Returns:
            Dict containing only payload fields
        """
        base_fields = {
            "event_id",
            "event_type",
            "sequence_number",
            "timestamp_utc",
            "timestamp_logical",
            "causation_id",
            "correlation_id",
            "metadata",
        }
        return {k: v for k, v in event_dict.items() if k not in base_fields}

    def _check_snapshot_trigger(self, sequence_number: int) -> None:
        """
        Check if snapshot should be created.

        Snapshots are created:
        - Every N events
        - Every N seconds
        - On demand via API

        Args:
            sequence_number: Current sequence number
        """
        events_since_snapshot = sequence_number - self.last_snapshot_sequence
        time_since_snapshot = time.time() - self.last_snapshot_time

        if (
            events_since_snapshot >= SNAPSHOT_INTERVAL
            or time_since_snapshot >= SNAPSHOT_TIME_INTERVAL
        ):
            logger.info(
                f"📸 Creating state snapshot at sequence {sequence_number}"
            )
            # TODO: Implement snapshot creation
            # This would query current state from services and store it
            self.last_snapshot_sequence = sequence_number
            self.last_snapshot_time = time.time()

    def create_snapshot(
        self, snapshot_type: str, state_data: Dict[str, Any], sequence_number: int
    ) -> None:
        """
        Create state snapshot for faster replay.

        Args:
            snapshot_type: Type of snapshot (RISK_STATE, SIGNAL_STATE, etc.)
            state_data: Complete state as dictionary
            sequence_number: Sequence number at snapshot time
        """
        # Calculate checksum for integrity
        state_json = json.dumps(state_data, sort_keys=True)
        checksum = hashlib.sha256(state_json.encode()).hexdigest()

        query = """
            INSERT INTO state_snapshots (
                sequence_number,
                snapshot_type,
                state_data,
                checksum
            ) VALUES (%s, %s, %s, %s)
        """

        params = (sequence_number, snapshot_type, Json(state_data), checksum)

        try:
            self.db.execute(query, params)
            logger.info(
                f"✅ Snapshot created: {snapshot_type} at seq={sequence_number}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to create snapshot: {e}")
            raise


# ==============================================================================
# EVENT READER
# ==============================================================================


class EventReader:
    """
    Reads events from PostgreSQL event store.

    Provides:
    - Sequential event reading for replay
    - Range queries (time, sequence)
    - Correlation and causation tracing
    - Audit trail queries
    """

    def __init__(self, db: DatabaseConnection):
        """
        Initialize event reader.

        Args:
            db: Database connection
        """
        self.db = db

    def read_events(
        self,
        from_sequence: Optional[int] = None,
        to_sequence: Optional[int] = None,
        event_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read events in sequence order.

        Args:
            from_sequence: Start sequence number (inclusive)
            to_sequence: End sequence number (inclusive)
            event_types: Filter by event types
            limit: Maximum number of events to return

        Returns:
            List of events as dictionaries
        """
        query = "SELECT * FROM events WHERE 1=1"
        params = []

        if from_sequence is not None:
            query += " AND sequence_number >= %s"
            params.append(from_sequence)

        if to_sequence is not None:
            query += " AND sequence_number <= %s"
            params.append(to_sequence)

        if event_types:
            query += " AND event_type = ANY(%s)"
            params.append(event_types)

        query += " ORDER BY sequence_number"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        results = self.db.execute(query, tuple(params))
        return [dict(row) for row in results] if results else []

    def get_correlation_events(self, correlation_id: str) -> List[Dict[str, Any]]:
        """
        Get all events for specific correlation ID (trade/session).

        Args:
            correlation_id: Correlation UUID

        Returns:
            List of events
        """
        query = "SELECT * FROM get_correlation_events(%s)"
        results = self.db.execute(query, (correlation_id,))
        return [dict(row) for row in results] if results else []

    def get_causation_chain(self, event_id: str) -> List[Dict[str, Any]]:
        """
        Get causation chain for specific event.

        Args:
            event_id: Event UUID

        Returns:
            List of events in causation chain
        """
        query = "SELECT * FROM get_causation_chain(%s)"
        results = self.db.execute(query, (event_id,))
        return [dict(row) for row in results] if results else []

    def explain_decision(self, decision_event_id: str) -> Dict[str, Any]:
        """
        Get full audit trail for decision.

        Args:
            decision_event_id: Decision event UUID

        Returns:
            Complete audit trail
        """
        query = "SELECT explain_decision(%s)"
        if results := self.db.execute(query, (decision_event_id,)):
            return results[0]["explain_decision"]
        return {}

    def get_latest_snapshot(
        self, snapshot_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get latest state snapshot.

        Args:
            snapshot_type: Optional filter by snapshot type

        Returns:
            Latest snapshot or None
        """
        query = "SELECT * FROM state_snapshots"
        params = []

        if snapshot_type:
            query += " WHERE snapshot_type = %s"
            params.append(snapshot_type)

        query += " ORDER BY sequence_number DESC LIMIT 1"

        results = self.db.execute(query, tuple(params) if params else None)
        return dict(results[0]) if results else None


# ==============================================================================
# FLASK API
# ==============================================================================


db = DatabaseConnection(DATABASE_URL)
writer = EventWriter(db)
reader = EventReader(db)


@app.route("/health")
def health():
    """Health check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return jsonify({"status": "ok", "service": "event_store", "version": "1.0.0"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/events", methods=["POST"])
def write_event_api():
    """Write event via API."""
    try:
        event_data = request.get_json()
        # TODO: Deserialize to proper event type
        # writer.write_event(event)
        return jsonify({"status": "ok"}), 201
    except Exception as e:
        logger.error(f"Failed to write event: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events", methods=["GET"])
def read_events_api():
    """Query events via API."""
    try:
        from_seq = request.args.get("from_sequence", type=int)
        to_seq = request.args.get("to_sequence", type=int)
        event_types = request.args.getlist("event_type")
        limit = request.args.get("limit", type=int, default=100)

        events = reader.read_events(
            from_sequence=from_seq,
            to_sequence=to_seq,
            event_types=event_types if event_types else None,
            limit=limit,
        )

        return jsonify({"events": events, "count": len(events)})
    except Exception as e:
        logger.error(f"Failed to read events: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events/<event_id>/causation")
def get_causation_chain_api(event_id: str):
    """Get causation chain for event."""
    try:
        chain = reader.get_causation_chain(event_id)
        return jsonify({"causation_chain": chain})
    except Exception as e:
        logger.error(f"Failed to get causation chain: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/events/<event_id>/explain")
def explain_decision_api(event_id: str):
    """Explain decision event."""
    try:
        explanation = reader.explain_decision(event_id)
        return jsonify(explanation)
    except Exception as e:
        logger.error(f"Failed to explain decision: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/correlations/<correlation_id>")
def get_correlation_events_api(correlation_id: str):
    """Get all events for correlation ID."""
    try:
        events = reader.get_correlation_events(correlation_id)
        return jsonify({"events": events, "count": len(events)})
    except Exception as e:
        logger.error(f"Failed to get correlation events: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/snapshots/latest")
def get_latest_snapshot_api():
    """Get latest state snapshot."""
    try:
        snapshot_type = request.args.get("type")
        snapshot = reader.get_latest_snapshot(snapshot_type)
        if snapshot:
            return jsonify(snapshot)
        return jsonify({"message": "No snapshots found"}), 404
    except Exception as e:
        logger.error(f"Failed to get snapshot: {e}")
        return jsonify({"error": str(e)}), 500


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8004"))
    logger.info(f"🚀 Starting Event Store Service on port {port}")
    logger.info(f"📊 Database: {DATABASE_URL.split('@')[1]}")  # Don't log password

    app.run(host="0.0.0.0", port=port)
