-- Issue #4184: persistent reduce-only preparation/result contract.
--
-- This table is an execution safety ledger. It reserves the maximum executable
-- exit quantity before adapter submission and makes result application
-- idempotent across duplicate delivery and process restart.

CREATE TABLE IF NOT EXISTS reduce_only_executions (
    order_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    position_before DECIMAL(18, 8),
    requested_quantity DECIMAL(18, 8) NOT NULL,
    submitted_quantity DECIMAL(18, 8) NOT NULL DEFAULT 0,
    filled_quantity DECIMAL(18, 8) NOT NULL DEFAULT 0,
    position_after DECIMAL(18, 8),
    status VARCHAR(24) NOT NULL CHECK (
        status IN (
            'PREPARED',
            'BLOCKED',
            'FILLED',
            'PARTIALLY_FILLED',
            'REJECTED'
        )
    ),
    reason_code VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reduce_only_requested_non_negative CHECK (requested_quantity >= 0),
    CONSTRAINT reduce_only_submitted_non_negative CHECK (submitted_quantity >= 0),
    CONSTRAINT reduce_only_filled_non_negative CHECK (filled_quantity >= 0),
    CONSTRAINT reduce_only_filled_lte_submitted CHECK (
        filled_quantity <= submitted_quantity
    )
);

CREATE INDEX IF NOT EXISTS idx_reduce_only_executions_symbol_status
    ON reduce_only_executions(symbol, status);

COMMENT ON TABLE reduce_only_executions IS
    'Persistent execution-boundary ledger for reduce-only clamp and fill idempotency';

