-- Migration 005: Add idempotency to risk_events
-- Date: 2026-02-15
-- Reason: Phase 8B - Deterministic persistence with replay-safe PK
-- Historical note: Phase 8B review artifact (reports/GORDON_P8B_BRIEF.md); Gordon gate decommissioned (#2689). Human-GO + repo evidence only.

-- Add idempotency columns
ALTER TABLE risk_events ADD COLUMN IF NOT EXISTS decision_pk VARCHAR(36);
ALTER TABLE risk_events ADD COLUMN IF NOT EXISTS input_snapshot_hash VARCHAR(64);

-- Create unique constraint on decision_pk (idempotency key)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_risk_events_decision_pk'
    ) THEN
        ALTER TABLE risk_events ADD CONSTRAINT uq_risk_events_decision_pk UNIQUE (decision_pk);
    END IF;
END $$;

-- Add index on reason_code
CREATE INDEX IF NOT EXISTS idx_risk_events_reason_code ON risk_events(reason_code);

-- Update schema version (idempotent)
INSERT INTO schema_version (version, description)
SELECT '1.0.4', 'Add idempotency to risk_events (Phase 8B)'
WHERE NOT EXISTS (SELECT 1 FROM schema_version WHERE version = '1.0.4');

-- Verification
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'risk_events' AND column_name = 'decision_pk'
    ) THEN
        RAISE EXCEPTION 'Migration failed: decision_pk column missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_risk_events_decision_pk'
    ) THEN
        RAISE EXCEPTION 'Migration failed: uq_risk_events_decision_pk constraint missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'risk_events' AND indexname = 'idx_risk_events_reason_code'
    ) THEN
        RAISE EXCEPTION 'Migration failed: idx_risk_events_reason_code index missing';
    END IF;

    RAISE NOTICE 'Migration 005 successful: idempotency added to risk_events';
END $$;
