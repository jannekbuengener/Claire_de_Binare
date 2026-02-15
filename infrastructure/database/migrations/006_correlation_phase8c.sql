-- Migration 006: Correlation IDs End-to-End (Phase 8C)
-- Date: 2026-02-15
-- Reason: End-to-end correlation tracking + eliminate silent blocks
-- Gordon Review: APPROVED (explicit GO in conversation)

-- ============================================================================
-- TABLE: correlation_ledger (append-only audit trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS correlation_ledger (
    id SERIAL PRIMARY KEY,
    event_pk CHAR(36) NOT NULL,              -- UUIDv5 idempotency key
    correlation_id CHAR(36) NOT NULL,        -- UUIDv5 chain root (from signal_id)
    signal_id VARCHAR(80),                   -- sig-{uuid} from Signal Service
    decision_id CHAR(36),                    -- Risk Service decision UUID
    order_id VARCHAR(100),                   -- paper_*/MOCK_* from Execution
    fill_id VARCHAR(100),                    -- Redis Stream Entry ID or exchange_trade_id
    event_type VARCHAR(20) NOT NULL,         -- SIGNAL, DECISION, ORDER, FILL
    symbol VARCHAR(20) NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB,

    CONSTRAINT uq_correlation_event_pk UNIQUE (event_pk)
);

-- Indexes for correlation_ledger
CREATE INDEX IF NOT EXISTS idx_correlation_id ON correlation_ledger(correlation_id);
CREATE INDEX IF NOT EXISTS idx_correlation_signal ON correlation_ledger(signal_id);
CREATE INDEX IF NOT EXISTS idx_correlation_decision ON correlation_ledger(decision_id);
CREATE INDEX IF NOT EXISTS idx_correlation_order ON correlation_ledger(order_id);
CREATE INDEX IF NOT EXISTS idx_correlation_timestamp ON correlation_ledger(timestamp_ms DESC);

COMMENT ON TABLE correlation_ledger IS 'Append-only audit trail for end-to-end correlation (Phase 8C)';
COMMENT ON COLUMN correlation_ledger.event_pk IS 'Deterministic idempotency key (UUIDv5)';
COMMENT ON COLUMN correlation_ledger.correlation_id IS 'Correlation chain root (UUIDv5 from signal_id)';

-- ============================================================================
-- TABLE: blocked_decisions (eliminates silent blocks)
-- ============================================================================

CREATE TABLE IF NOT EXISTS blocked_decisions (
    id SERIAL PRIMARY KEY,
    decision_pk CHAR(36) NOT NULL,           -- UUIDv5 (same algorithm as risk_events)
    signal_id VARCHAR(80) NOT NULL,          -- sig-{uuid} from Signal Service
    decision_id CHAR(36) NOT NULL,           -- Risk Service decision UUID
    symbol VARCHAR(20) NOT NULL,
    reason_code VARCHAR(20) NOT NULL,        -- RC_001, RC_002, etc.
    timestamp_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB,

    CONSTRAINT uq_blocked_decision_pk UNIQUE (decision_pk)
);

-- Indexes for blocked_decisions
CREATE INDEX IF NOT EXISTS idx_blocked_decisions_signal ON blocked_decisions(signal_id);
CREATE INDEX IF NOT EXISTS idx_blocked_decisions_symbol ON blocked_decisions(symbol);
CREATE INDEX IF NOT EXISTS idx_blocked_decisions_timestamp ON blocked_decisions(timestamp_ms DESC);

COMMENT ON TABLE blocked_decisions IS 'BLOCK decisions with full audit trail (Phase 8C)';
COMMENT ON COLUMN blocked_decisions.decision_pk IS 'Idempotency key (same algorithm as risk_events.decision_pk)';

-- ============================================================================
-- SCHEMA VERSION UPDATE
-- ============================================================================

INSERT INTO schema_version (version, description)
SELECT '1.0.5', 'Add correlation_ledger + blocked_decisions (Phase 8C)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.5');

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
BEGIN
    -- Verify correlation_ledger exists (with explicit schema)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'correlation_ledger'
    ) THEN
        RAISE EXCEPTION 'Migration failed: correlation_ledger table missing';
    END IF;

    -- Verify blocked_decisions exists (with explicit schema)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'blocked_decisions'
    ) THEN
        RAISE EXCEPTION 'Migration failed: blocked_decisions table missing';
    END IF;

    -- Verify unique constraints (with conrelid for precision)
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_correlation_event_pk'
          AND conrelid = 'public.correlation_ledger'::regclass
    ) THEN
        RAISE EXCEPTION 'Migration failed: uq_correlation_event_pk constraint missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_blocked_decision_pk'
          AND conrelid = 'public.blocked_decisions'::regclass
    ) THEN
        RAISE EXCEPTION 'Migration failed: uq_blocked_decision_pk constraint missing';
    END IF;

    -- Verify schema_version updated
    IF NOT EXISTS (
        SELECT 1 FROM schema_version WHERE version = '1.0.5'
    ) THEN
        RAISE EXCEPTION 'Migration failed: schema_version 1.0.5 not found';
    END IF;

    RAISE NOTICE 'Migration 006 successful: correlation_ledger + blocked_decisions created (Phase 8C)';
END $$;
