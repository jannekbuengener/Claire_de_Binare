-- =============================================================================
-- Claire de Binaire - Event Store Database Schema
-- =============================================================================
-- Purpose: Immutable event log for deterministic replay and full audit trail
-- Version: 1.0.0
-- Database: PostgreSQL 15+
-- =============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- EVENTS TABLE - Core Event Store
-- =============================================================================

CREATE TABLE IF NOT EXISTS events (
    -- Primary identifiers
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,

    -- Logical ordering (CRITICAL for determinism)
    sequence_number BIGSERIAL UNIQUE NOT NULL,

    -- Timestamps
    timestamp_utc TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    timestamp_logical BIGINT NOT NULL,

    -- Event relationships (causation chain)
    causation_id UUID REFERENCES events(event_id),
    correlation_id UUID NOT NULL,

    -- Metadata (audit trail)
    metadata JSONB NOT NULL,

    -- Event-specific payload
    payload JSONB NOT NULL,

    -- Constraints
    CONSTRAINT events_sequence_positive CHECK (sequence_number > 0),
    CONSTRAINT events_logical_timestamp_positive CHECK (timestamp_logical >= 0)
);

-- Indexes for efficient querying
CREATE INDEX idx_events_sequence ON events(sequence_number);
CREATE INDEX idx_events_timestamp_utc ON events(timestamp_utc);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_correlation_id ON events(correlation_id);
CREATE INDEX idx_events_causation_id ON events(causation_id) WHERE causation_id IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX idx_events_type_timestamp ON events(event_type, timestamp_utc);
CREATE INDEX idx_events_correlation_timestamp ON events(correlation_id, timestamp_utc);

-- JSONB indexes for payload queries
CREATE INDEX idx_events_payload_symbol ON events((payload->>'symbol')) WHERE payload ? 'symbol';
CREATE INDEX idx_events_metadata_service ON events((metadata->>'service'));

COMMENT ON TABLE events IS 'Immutable event log for deterministic replay and audit trail';
COMMENT ON COLUMN events.sequence_number IS 'Monotonically increasing logical clock (guarantees ordering)';
COMMENT ON COLUMN events.timestamp_utc IS 'Wall-clock time for humans (NOT used for ordering)';
COMMENT ON COLUMN events.timestamp_logical IS 'Bot-internal logical timestamp (ms since start)';
COMMENT ON COLUMN events.causation_id IS 'Event that caused this event (for tracing)';
COMMENT ON COLUMN events.correlation_id IS 'Session/Trade ID to group related events';

-- =============================================================================
-- STATE SNAPSHOTS TABLE - For Faster Replay
-- =============================================================================

CREATE TABLE IF NOT EXISTS state_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sequence_number BIGINT NOT NULL REFERENCES events(sequence_number),
    snapshot_type VARCHAR(50) NOT NULL,
    state_data JSONB NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    CONSTRAINT snapshots_sequence_positive CHECK (sequence_number > 0)
);

CREATE INDEX idx_snapshots_sequence ON state_snapshots(sequence_number DESC);
CREATE INDEX idx_snapshots_type ON state_snapshots(snapshot_type);

COMMENT ON TABLE state_snapshots IS 'Periodic state snapshots for faster replay from checkpoints';
COMMENT ON COLUMN state_snapshots.checksum IS 'SHA256 checksum for integrity validation';

-- =============================================================================
-- AUDIT QUERIES VIEW - For Easy Querying
-- =============================================================================

CREATE OR REPLACE VIEW v_audit_trail AS
SELECT
    e.event_id,
    e.event_type,
    e.sequence_number,
    e.timestamp_utc,
    e.correlation_id,
    e.causation_id,
    e.metadata->>'service' AS service,
    e.metadata->>'environment' AS environment,
    e.payload
FROM events e
ORDER BY e.sequence_number;

COMMENT ON VIEW v_audit_trail IS 'Simplified view for audit trail queries';

-- =============================================================================
-- RISK DECISIONS VIEW - For Risk Analysis
-- =============================================================================

CREATE OR REPLACE VIEW v_risk_decisions AS
SELECT
    e.event_id,
    e.sequence_number,
    e.timestamp_utc,
    e.correlation_id,
    e.payload->>'signal_id' AS signal_id,
    (e.payload->>'approved')::boolean AS approved,
    e.payload->>'reason' AS reason,
    e.payload->>'symbol' AS symbol,
    e.payload->>'side' AS side,
    (e.payload->>'approved_size')::numeric AS approved_size,
    e.payload->'risk_state' AS risk_state,
    e.payload->'risk_checks' AS risk_checks
FROM events e
WHERE e.event_type = 'risk_decision'
ORDER BY e.sequence_number;

COMMENT ON VIEW v_risk_decisions IS 'All risk manager decisions with extracted fields';

-- =============================================================================
-- SIGNALS VIEW - For Strategy Analysis
-- =============================================================================

CREATE OR REPLACE VIEW v_signals AS
SELECT
    e.event_id,
    e.sequence_number,
    e.timestamp_utc,
    e.correlation_id,
    e.causation_id,
    e.payload->>'symbol' AS symbol,
    e.payload->>'side' AS side,
    (e.payload->>'confidence')::numeric AS confidence,
    e.payload->>'reason' AS reason,
    (e.payload->>'price')::numeric AS price,
    e.payload->'strategy_params' AS strategy_params
FROM events e
WHERE e.event_type = 'signal_generated'
ORDER BY e.sequence_number;

COMMENT ON VIEW v_signals IS 'All generated trading signals with extracted fields';

-- =============================================================================
-- ORDERS VIEW - For Execution Analysis
-- =============================================================================

CREATE OR REPLACE VIEW v_orders AS
SELECT
    e.event_id,
    e.sequence_number,
    e.timestamp_utc,
    e.correlation_id,
    e.payload->>'order_id' AS order_id,
    e.payload->>'symbol' AS symbol,
    e.payload->>'side' AS side,
    e.payload->>'status' AS status,
    (e.payload->>'filled_quantity')::numeric AS filled_quantity,
    (e.payload->>'fill_price')::numeric AS fill_price,
    (e.payload->>'fees')::numeric AS fees,
    (e.payload->>'slippage')::numeric AS slippage
FROM events e
WHERE e.event_type = 'order_result'
ORDER BY e.sequence_number;

COMMENT ON VIEW v_orders IS 'All order execution results with extracted fields';

-- =============================================================================
-- CAUSATION CHAIN FUNCTION - For Audit Trail
-- =============================================================================

CREATE OR REPLACE FUNCTION get_causation_chain(target_event_id UUID)
RETURNS TABLE (
    level INT,
    event_id UUID,
    event_type VARCHAR,
    sequence_number BIGINT,
    timestamp_utc TIMESTAMP WITH TIME ZONE,
    causation_id UUID
) AS $$
WITH RECURSIVE chain AS (
    -- Base case: target event
    SELECT
        0 AS level,
        e.event_id,
        e.event_type,
        e.sequence_number,
        e.timestamp_utc,
        e.causation_id
    FROM events e
    WHERE e.event_id = target_event_id

    UNION ALL

    -- Recursive case: follow causation links
    SELECT
        c.level + 1,
        e.event_id,
        e.event_type,
        e.sequence_number,
        e.timestamp_utc,
        e.causation_id
    FROM events e
    INNER JOIN chain c ON e.event_id = c.causation_id
)
SELECT * FROM chain
ORDER BY level DESC;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_causation_chain IS 'Trace causation chain backwards from any event';

-- =============================================================================
-- CORRELATION EVENTS FUNCTION - For Trade Analysis
-- =============================================================================

CREATE OR REPLACE FUNCTION get_correlation_events(target_correlation_id UUID)
RETURNS TABLE (
    event_id UUID,
    event_type VARCHAR,
    sequence_number BIGINT,
    timestamp_utc TIMESTAMP WITH TIME ZONE,
    causation_id UUID,
    payload JSONB
) AS $$
SELECT
    e.event_id,
    e.event_type,
    e.sequence_number,
    e.timestamp_utc,
    e.causation_id,
    e.payload
FROM events e
WHERE e.correlation_id = target_correlation_id
ORDER BY e.sequence_number;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_correlation_events IS 'Get all events for a specific trade/session';

-- =============================================================================
-- EVENT COUNT BY TYPE FUNCTION - For Monitoring
-- =============================================================================

CREATE OR REPLACE FUNCTION get_event_stats(
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '24 hours',
    end_time TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
RETURNS TABLE (
    event_type VARCHAR,
    event_count BIGINT,
    first_event TIMESTAMP WITH TIME ZONE,
    last_event TIMESTAMP WITH TIME ZONE
) AS $$
SELECT
    e.event_type,
    COUNT(*) AS event_count,
    MIN(e.timestamp_utc) AS first_event,
    MAX(e.timestamp_utc) AS last_event
FROM events e
WHERE e.timestamp_utc BETWEEN start_time AND end_time
GROUP BY e.event_type
ORDER BY event_count DESC;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_event_stats IS 'Event statistics for monitoring and health checks';

-- =============================================================================
-- EXPLAIN DECISION FUNCTION - For Audit Trail
-- =============================================================================

CREATE OR REPLACE FUNCTION explain_decision(decision_event_id UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    WITH decision AS (
        SELECT * FROM events WHERE event_id = decision_event_id
    ),
    signal AS (
        SELECT * FROM events
        WHERE event_id = (SELECT causation_id FROM decision)
    ),
    market_data AS (
        SELECT * FROM events
        WHERE event_id = (SELECT causation_id FROM signal)
    )
    SELECT jsonb_build_object(
        'decision', (SELECT row_to_json(decision.*) FROM decision),
        'signal', (SELECT row_to_json(signal.*) FROM signal),
        'market_data', (SELECT row_to_json(market_data.*) FROM market_data),
        'causation_chain', (
            SELECT jsonb_agg(row_to_json(c.*))
            FROM get_causation_chain(decision_event_id) c
        )
    ) INTO result;

    RETURN result;
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION explain_decision IS 'Full audit trail for any decision event';

-- =============================================================================
-- IMMUTABILITY TRIGGER - Prevent Event Modification
-- =============================================================================

CREATE OR REPLACE FUNCTION prevent_event_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Events are immutable and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER events_immutable_update
BEFORE UPDATE ON events
FOR EACH ROW
EXECUTE FUNCTION prevent_event_modification();

CREATE TRIGGER events_immutable_delete
BEFORE DELETE ON events
FOR EACH ROW
EXECUTE FUNCTION prevent_event_modification();

COMMENT ON TRIGGER events_immutable_update ON events IS 'Enforce event immutability (no updates)';
COMMENT ON TRIGGER events_immutable_delete ON events IS 'Enforce event immutability (no deletes)';

-- =============================================================================
-- PARTITIONING (Optional - for large event logs)
-- =============================================================================

-- Uncomment below for time-based partitioning (recommended for production)
/*
ALTER TABLE events RENAME TO events_template;

CREATE TABLE events (
    LIKE events_template INCLUDING ALL
) PARTITION BY RANGE (timestamp_utc);

-- Create partitions for each month
CREATE TABLE events_2025_01 PARTITION OF events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE events_2025_02 PARTITION OF events
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Add more partitions as needed...

-- Create index on parent table
CREATE INDEX idx_events_partitioned_sequence ON events(sequence_number);
*/

-- =============================================================================
-- GRANTS (Security)
-- =============================================================================

-- Event writer role (append-only)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'event_writer') THEN
        CREATE ROLE event_writer;
    END IF;
END $$;

GRANT INSERT ON events TO event_writer;
GRANT SELECT ON events TO event_writer;
GRANT USAGE ON SEQUENCE events_sequence_number_seq TO event_writer;

-- Event reader role (read-only)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'event_reader') THEN
        CREATE ROLE event_reader;
    END IF;
END $$;

GRANT SELECT ON events, state_snapshots TO event_reader;
GRANT SELECT ON v_audit_trail, v_risk_decisions, v_signals, v_orders TO event_reader;

-- Replay engine role (read + snapshot creation)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replay_engine') THEN
        CREATE ROLE replay_engine;
    END IF;
END $$;

GRANT SELECT ON events TO replay_engine;
GRANT INSERT, SELECT ON state_snapshots TO replay_engine;

COMMENT ON ROLE event_writer IS 'Can append new events (but not modify/delete)';
COMMENT ON ROLE event_reader IS 'Can read events for querying and analysis';
COMMENT ON ROLE replay_engine IS 'Can read events and create state snapshots';

-- =============================================================================
-- SAMPLE QUERIES (Documentation)
-- =============================================================================

/*
-- Get all events for a specific trade
SELECT * FROM get_correlation_events('YOUR-CORRELATION-UUID-HERE');

-- Trace causation chain backwards from decision
SELECT * FROM get_causation_chain('YOUR-EVENT-UUID-HERE');

-- Explain why a decision was made
SELECT explain_decision('YOUR-DECISION-EVENT-UUID-HERE');

-- Get event statistics for last 24 hours
SELECT * FROM get_event_stats();

-- Find all rejected signals
SELECT * FROM v_risk_decisions WHERE approved = FALSE;

-- Find all BTC signals with high confidence
SELECT * FROM v_signals WHERE symbol = 'BTCUSDT' AND confidence > 0.8;

-- Get latest state snapshot
SELECT * FROM state_snapshots ORDER BY sequence_number DESC LIMIT 1;

-- Count events by type
SELECT event_type, COUNT(*) FROM events GROUP BY event_type;

-- Find all events in specific time range
SELECT * FROM events
WHERE timestamp_utc BETWEEN '2025-02-10 13:00:00' AND '2025-02-10 14:00:00'
ORDER BY sequence_number;
*/
