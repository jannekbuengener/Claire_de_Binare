-- DATABASE_SCHEMA.sql - Claire de Binare
-- PostgreSQL Schema für Trading-System
-- Erstellt: 2025-11-19
-- Version: 1.0.2
--
-- Dieses Schema wird automatisch geladen beim ersten Start von cdb_postgres
-- via docker-compose.yml → docker-entrypoint-initdb.d/01-schema.sql

-- ============================================================================
-- DROP existing tables (für sauberes Re-Deploy)
-- ============================================================================

DROP TABLE IF EXISTS portfolio_snapshots CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS signals CASCADE;
DROP TABLE IF EXISTS candles_1m CASCADE;

-- ============================================================================
-- SIGNALS - Trading-Signale vom Signal-Engine
-- ============================================================================

CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('buy', 'sell')),
    price DECIMAL(18, 8) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) DEFAULT 'momentum_strategy',
    metadata JSONB,

    -- Indexes
    CONSTRAINT signals_symbol_check CHECK (LENGTH(symbol) >= 3)
);

CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_timestamp ON signals(timestamp DESC);
CREATE INDEX idx_signals_signal_type ON signals(signal_type);

COMMENT ON TABLE signals IS 'Trading-Signale generiert vom Signal-Engine';
COMMENT ON COLUMN signals.confidence IS 'Signal-Konfidenz zwischen 0.0 und 1.0';
COMMENT ON COLUMN signals.metadata IS 'Zusätzliche Signal-Metadaten als JSON';

-- ============================================================================
-- ORDERS - Validierte Orders vom Risk-Manager
-- ============================================================================

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) UNIQUE,
    signal_id INTEGER REFERENCES signals(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell', 'long', 'short')),
    order_type VARCHAR(20) NOT NULL DEFAULT 'market' CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    price DECIMAL(18, 8),
    size DECIMAL(18, 8) NOT NULL,

    -- Risk-Validation
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    rejection_reason TEXT,

    -- Execution-Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'filled', 'partial', 'cancelled', 'rejected')),
    filled_size DECIMAL(18, 8) DEFAULT 0.0,
    avg_fill_price DECIMAL(18, 8),

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,

    -- Additional metadata
    metadata JSONB,

    -- Constraints
    CONSTRAINT orders_size_positive CHECK (size > 0),
    CONSTRAINT orders_filled_size_valid CHECK (filled_size >= 0 AND filled_size <= size)
);

CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_order_id ON orders(order_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX idx_orders_signal_id ON orders(signal_id);

COMMENT ON TABLE orders IS 'Validierte Trading-Orders vom Risk-Manager';
COMMENT ON COLUMN orders.order_id IS 'Execution Service Order ID (unique identifier for order tracking)';
COMMENT ON COLUMN orders.price IS 'Limit-Preis (NULL für Market-Orders ohne Limit)';
COMMENT ON COLUMN orders.approved IS 'Risk-Validation bestanden?';
COMMENT ON COLUMN orders.rejection_reason IS 'Grund für Ablehnung (falls approved=false)';

-- ============================================================================
-- TRADES - Ausgeführte Trades vom Execution-Service
-- ============================================================================

CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    price DECIMAL(18, 8) NOT NULL,
    size DECIMAL(18, 8) NOT NULL,

    -- Execution-Details
    status VARCHAR(20) NOT NULL DEFAULT 'filled' CHECK (status IN ('filled', 'partial', 'cancelled')),
    execution_price DECIMAL(18, 8) NOT NULL,
    slippage_bps DECIMAL(10, 2), -- Slippage in Basis Points
    fees DECIMAL(18, 8) DEFAULT 0.0,
    realized_pnl DECIMAL(18, 8),

    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Exchange-Informationen (für Paper-Trading Mock)
    exchange VARCHAR(20) DEFAULT 'MEXC',
    exchange_trade_id VARCHAR(100),

    -- Additional metadata
    metadata JSONB,

    -- Constraints
    CONSTRAINT trades_size_positive CHECK (size > 0),
    CONSTRAINT trades_price_positive CHECK (price > 0),
    CONSTRAINT trades_execution_price_positive CHECK (execution_price > 0)
);

CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_timestamp ON trades(timestamp DESC);
CREATE INDEX idx_trades_order_id ON trades(order_id);
CREATE INDEX idx_trades_status ON trades(status);

COMMENT ON TABLE trades IS 'Ausgeführte Trades vom Execution-Service';
COMMENT ON COLUMN trades.slippage_bps IS 'Slippage in Basis Points (1 bps = 0.01%)';
COMMENT ON COLUMN trades.exchange_trade_id IS 'Trade-ID von MEXC Exchange (im Live-Modus)';
COMMENT ON COLUMN trades.realized_pnl IS 'Realisierter PnL für Exit-Executions; NULL solange der Trade-Row keinen abgeschlossenen Outcome trägt';

-- ============================================================================
-- POSITIONS - Aktuelle Positionen (Aggregiert aus Trades)
-- ============================================================================

CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,

    -- Position-Details
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short', 'none')),
    size DECIMAL(18, 8) NOT NULL DEFAULT 0.0,
    entry_price DECIMAL(18, 8),
    current_price DECIMAL(18, 8),

    -- PnL
    unrealized_pnl DECIMAL(18, 8) DEFAULT 0.0,
    realized_pnl DECIMAL(18, 8) DEFAULT 0.0,

    -- Risk-Metriken
    stop_loss_price DECIMAL(18, 8),
    take_profit_price DECIMAL(18, 8),
    liquidation_price DECIMAL(18, 8), -- Für Perpetual Futures

    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE,

    -- Additional metadata
    metadata JSONB,

    -- Constraints
    CONSTRAINT positions_size_non_negative CHECK (size >= 0)
);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_side ON positions(side);
CREATE INDEX idx_positions_updated_at ON positions(updated_at DESC);

COMMENT ON TABLE positions IS 'Aktuelle Positionen (aggregiert aus Trades)';
COMMENT ON COLUMN positions.unrealized_pnl IS 'Noch nicht realisierter Gewinn/Verlust';
COMMENT ON COLUMN positions.realized_pnl IS 'Realisierter Gewinn/Verlust (nach Schließung)';
COMMENT ON COLUMN positions.liquidation_price IS 'Liquidations-Preis für Perpetual Futures (MEXC)';

-- ============================================================================
-- PORTFOLIO_SNAPSHOTS - Portfolio-Snapshots für Performance-Tracking
-- ============================================================================

CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Portfolio-Metriken
    total_equity DECIMAL(18, 8) NOT NULL,
    available_balance DECIMAL(18, 8) NOT NULL,
    margin_used DECIMAL(18, 8) DEFAULT 0.0,

    -- PnL
    daily_pnl DECIMAL(18, 8) DEFAULT 0.0,
    total_unrealized_pnl DECIMAL(18, 8) DEFAULT 0.0,
    total_realized_pnl DECIMAL(18, 8) DEFAULT 0.0,

    -- Risk-Metriken
    total_exposure_pct DECIMAL(5, 4) DEFAULT 0.0, -- Prozent von Equity
    max_drawdown_pct DECIMAL(5, 4) DEFAULT 0.0,

    -- Positions-Anzahl
    open_positions INTEGER DEFAULT 0,

    -- Additional metadata
    metadata JSONB,

    -- Constraints
    CONSTRAINT portfolio_snapshots_equity_positive CHECK (total_equity > 0),
    CONSTRAINT portfolio_snapshots_balance_non_negative CHECK (available_balance >= 0),
    CONSTRAINT portfolio_snapshots_exposure_valid CHECK (total_exposure_pct >= 0 AND total_exposure_pct <= 1)
);

CREATE INDEX idx_portfolio_snapshots_timestamp ON portfolio_snapshots(timestamp DESC);

COMMENT ON TABLE portfolio_snapshots IS 'Portfolio-Snapshots für Performance-Tracking und Backtesting';
COMMENT ON COLUMN portfolio_snapshots.total_exposure_pct IS 'Gesamt-Exposure als % von Equity (0.0-1.0)';
COMMENT ON COLUMN portfolio_snapshots.max_drawdown_pct IS 'Maximaler Drawdown seit Snapshot-Start';

-- ============================================================================
-- CANDLES_1M - Persistente 1-Minuten-OHLCV-Candles für ARVP Replay-Input
-- ============================================================================
-- Persistenz-Vorbedingung für DB-backed Replay-Inputs (Issue #1855).
-- Candles entstehen in cdb_candles und fliessen ephemer durch stream.candles_1m
-- in Redis. Dieses Table speichert sie dauerhaft, damit DBBackedDatasetProvider
-- (#1841) sie deterministisch als historisches Window abfragen kann.
-- ============================================================================

CREATE TABLE candles_1m (
    id          BIGSERIAL                NOT NULL,
    symbol      VARCHAR(20)              NOT NULL,
    ts_ms       BIGINT                   NOT NULL,
    open        DECIMAL(18, 8)           NOT NULL,
    high        DECIMAL(18, 8)           NOT NULL,
    low         DECIMAL(18, 8)           NOT NULL,
    close       DECIMAL(18, 8)           NOT NULL,
    volume      DECIMAL(18, 8)           NOT NULL DEFAULT 0.0,
    trade_count INTEGER                  NOT NULL DEFAULT 0,
    regime_id   SMALLINT,
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT candles_1m_pkey          PRIMARY KEY (id),
    CONSTRAINT candles_1m_ts_positive   CHECK (ts_ms > 0),
    CONSTRAINT candles_1m_open_positive CHECK (open > 0),
    CONSTRAINT candles_1m_high_positive CHECK (high > 0),
    CONSTRAINT candles_1m_low_positive  CHECK (low > 0),
    CONSTRAINT candles_1m_close_positive CHECK (close > 0),
    CONSTRAINT candles_1m_high_gte_low  CHECK (high >= low),
    CONSTRAINT candles_1m_volume_nonneg CHECK (volume >= 0),
    CONSTRAINT candles_1m_trades_nonneg CHECK (trade_count >= 0),
    CONSTRAINT candles_1m_unique        UNIQUE (symbol, ts_ms)
    -- UNIQUE (symbol, ts_ms) implicitly creates the B-tree index needed for
    -- deterministic window queries: WHERE symbol=? AND ts_ms BETWEEN ? AND ?
);

COMMENT ON TABLE candles_1m IS 'Persistente 1m-OHLCV-Candles aus stream.candles_1m fuer ARVP DB-backed Replay-Input (#1855)';
COMMENT ON COLUMN candles_1m.ts_ms IS 'Candle-Startzeit als Unix-Millisekunden (UTC). Primary sort key fuer historische Fensterabfragen.';
COMMENT ON COLUMN candles_1m.regime_id IS 'Marktregime zum Emissionszeitpunkt (NULL = kein Signal vorhanden). Nicht im Candle-Stream; reserviert fuer spaetere Anreicherung.';
COMMENT ON COLUMN candles_1m.ingested_at IS 'DB-Eingangszeit (Audit). Kein Replay-Feld.';

-- ============================================================================
-- CANDLE_BACKFILL_IMPORTS - Provenance fuer echte historische Candle-Backfills
-- ============================================================================

CREATE TABLE IF NOT EXISTS candle_backfill_imports (
    import_id              UUID PRIMARY KEY,
    source                 TEXT                     NOT NULL,
    source_url             TEXT                     NOT NULL,
    import_command         TEXT                     NOT NULL,
    imported_at            TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol                 VARCHAR(20)              NOT NULL,
    start_ts_ms            BIGINT                   NOT NULL,
    end_ts_ms              BIGINT                   NOT NULL,
    row_count              INTEGER                  NOT NULL,
    inserted_count         INTEGER                  NOT NULL,
    skipped_existing_count INTEGER                  NOT NULL,
    checksum_sha256        CHAR(64)                 NOT NULL,
    payload                JSONB                    NOT NULL,

    CONSTRAINT candle_backfill_window_valid CHECK (start_ts_ms <= end_ts_ms),
    CONSTRAINT candle_backfill_counts_nonneg CHECK (
        row_count >= 0 AND inserted_count >= 0 AND skipped_existing_count >= 0
    ),
    CONSTRAINT candle_backfill_checksum_hex CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE INDEX IF NOT EXISTS idx_candle_backfill_symbol_window
    ON candle_backfill_imports(symbol, start_ts_ms, end_ts_ms);

COMMENT ON TABLE candle_backfill_imports IS 'Provenance records for real-source candle backfills into public.candles_1m (#1906).';
COMMENT ON COLUMN candle_backfill_imports.source IS 'Real historical source identifier, e.g. binance_spot_api_v3_klines. No mock source allowed.';
COMMENT ON COLUMN candle_backfill_imports.checksum_sha256 IS 'SHA-256 over canonical imported candle rows.';
COMMENT ON COLUMN candle_backfill_imports.payload IS 'Full import manifest including source query/URL, command, row counts, and stable row payloads.';

-- ============================================================================
-- GRANTS - Permissions für claire_user
-- ============================================================================

-- Stell sicher dass claire_user alle Rechte hat
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO claire_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO claire_user;

-- ============================================================================
-- INITIAL DATA - Beispiel-Portfolio (optional, für Tests)
-- ============================================================================

-- Initial Portfolio-Snapshot (100,000 USDT Startkapital)
INSERT INTO portfolio_snapshots (
    total_equity,
    available_balance,
    margin_used,
    daily_pnl,
    total_unrealized_pnl,
    total_realized_pnl,
    total_exposure_pct,
    max_drawdown_pct,
    open_positions,
    metadata
) VALUES (
    100000.00,  -- total_equity
    100000.00,  -- available_balance
    0.00,       -- margin_used
    0.00,       -- daily_pnl
    0.00,       -- total_unrealized_pnl
    0.00,       -- total_realized_pnl
    0.00,       -- total_exposure_pct
    0.00,       -- max_drawdown_pct
    0,          -- open_positions
    '{"deployment_mode": "paper", "risk_profile": "conservative"}'::jsonb
);

-- ============================================================================
-- SCHEMA VERSION - Für Migrations-Tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(20) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES
    ('1.0.10', 'Initial schema with orders.price nullable, orders.order_id, and trades.realized_pnl'),
    ('1.1.0', 'Add candles_1m table for ARVP DB-backed replay persistence (Issue #1855)'),
    ('1.1.1', 'Add candle backfill provenance table for ARVP replay data continuity (Issue #1906)');

-- ============================================================================
-- VACUUM & ANALYZE - Optimiere nach Schema-Erstellung
-- ============================================================================

VACUUM ANALYZE;

-- ============================================================================
-- SCHEMA-ERSTELLUNG ABGESCHLOSSEN
-- ============================================================================
-- Tabellen: signals, orders, trades, positions, portfolio_snapshots, candles_1m, candle_backfill_imports
-- User: claire_user (mit vollen Rechten)
-- Initial Equity: 100,000 USDT
-- Status: ✅ Ready for Paper Trading
