-- Test Fixture: Seed Data for E2E Tests
-- Purpose: Provide deterministic, repeatable test data
-- Usage: Applied after reset to establish known DB state

-- Seed Portfolio Snapshot (Initial State: 100,000 USDT)
INSERT INTO portfolio_snapshots (
    id,
    timestamp,
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
    1,
    '2025-01-01 00:00:00+00'::timestamptz,
    100000.00,
    100000.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0.00,
    0,
    '{"deployment_mode": "test", "risk_profile": "conservative", "test_run": true}'::jsonb
);

-- Seed Signals (Test Scenarios)
INSERT INTO signals (
    id,
    symbol,
    signal_type,
    price,
    confidence,
    timestamp,
    source,
    metadata
) VALUES
    -- Signal 1: Strong BUY signal for BTC
    (1, 'BTCUSDT', 'buy', 42000.00, 0.95, '2025-01-01 10:00:00+00', 'test_strategy_001', '{"test_id": "sig_001", "reason": "strong_uptrend"}'::jsonb),
    -- Signal 2: Weak SELL signal for ETH
    (2, 'ETHUSDT', 'sell', 2200.00, 0.65, '2025-01-01 11:00:00+00', 'test_strategy_001', '{"test_id": "sig_002", "reason": "overbought"}'::jsonb),
    -- Signal 3: Medium BUY signal for BNB
    (3, 'BNBUSDT', 'buy', 310.00, 0.75, '2025-01-01 12:00:00+00', 'test_strategy_002', '{"test_id": "sig_003", "reason": "breakout"}'::jsonb);

-- Seed Orders (Risk-Validated)
INSERT INTO orders (
    id,
    signal_id,
    symbol,
    side,
    order_type,
    price,
    size,
    approved,
    rejection_reason,
    status,
    filled_size,
    avg_fill_price,
    created_at,
    submitted_at,
    filled_at,
    metadata
) VALUES
    -- Order 1: Approved BTC order (FILLED)
    (
        1,
        1,
        'BTCUSDT',
        'buy',
        'market',
        42000.00,
        0.5,
        true,
        null,
        'filled',
        0.5,
        42010.00,
        '2025-01-01 10:00:10+00',
        '2025-01-01 10:00:15+00',
        '2025-01-01 10:00:20+00',
        '{"test_id": "ord_001", "dry_run": true}'::jsonb
    ),
    -- Order 2: Rejected ETH order (insufficient balance)
    (
        2,
        2,
        'ETHUSDT',
        'sell',
        'market',
        2200.00,
        100.0,
        false,
        'Position size exceeds available balance',
        'rejected',
        0.0,
        null,
        '2025-01-01 11:00:10+00',
        null,
        null,
        '{"test_id": "ord_002", "dry_run": true}'::jsonb
    ),
    -- Order 3: Pending BNB order
    (
        3,
        3,
        'BNBUSDT',
        'buy',
        'limit',
        310.00,
        10.0,
        true,
        null,
        'pending',
        0.0,
        null,
        '2025-01-01 12:00:10+00',
        null,
        null,
        '{"test_id": "ord_003", "dry_run": true}'::jsonb
    );

-- Seed Trades (Executed Orders)
INSERT INTO trades (
    id,
    order_id,
    symbol,
    side,
    price,
    size,
    status,
    execution_price,
    slippage_bps,
    fees,
    timestamp,
    exchange,
    exchange_trade_id,
    metadata
) VALUES
    -- Trade 1: BTC filled order
    (
        1,
        1,
        'BTCUSDT',
        'buy',
        42000.00,
        0.5,
        'filled',
        42010.00,
        2.38,  -- 10 USD slippage on 42000 = 0.0238% = 2.38 bps
        21.00,  -- 0.05% taker fee
        '2025-01-01 10:00:20+00',
        'MEXC',
        'MEXC_TEST_TRADE_001',
        '{"test_id": "trd_001", "paper_trading": true}'::jsonb
    );

-- Seed Positions (Current Holdings)
INSERT INTO positions (
    id,
    symbol,
    side,
    size,
    entry_price,
    current_price,
    unrealized_pnl,
    realized_pnl,
    stop_loss_price,
    take_profit_price,
    liquidation_price,
    opened_at,
    updated_at,
    closed_at,
    metadata
) VALUES
    -- Position 1: Long BTC position (from Trade 1)
    (
        1,
        'BTCUSDT',
        'long',
        0.5,
        42010.00,
        42500.00,  -- Current price +490 USD
        245.00,     -- (42500 - 42010) * 0.5 = 245 USD unrealized PnL
        0.00,
        39000.00,   -- Stop loss at -7%
        45000.00,   -- Take profit at +7%
        null,        -- No liquidation price (spot trading)
        '2025-01-01 10:00:20+00',
        '2025-01-01 13:00:00+00',
        null,
        '{"test_id": "pos_001", "paper_trading": true}'::jsonb
    );

-- Reset sequences to continue from last seed value
SELECT setval('signals_id_seq', (SELECT MAX(id) FROM signals));
SELECT setval('orders_id_seq', (SELECT MAX(id) FROM orders));
SELECT setval('trades_id_seq', (SELECT MAX(id) FROM trades));
SELECT setval('positions_id_seq', (SELECT MAX(id) FROM positions));
SELECT setval('portfolio_snapshots_id_seq', (SELECT MAX(id) FROM portfolio_snapshots));

-- Verification: Count seeded rows
DO $$
DECLARE
    signals_count INTEGER;
    orders_count INTEGER;
    trades_count INTEGER;
    positions_count INTEGER;
    snapshots_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO signals_count FROM signals;
    SELECT COUNT(*) INTO orders_count FROM orders;
    SELECT COUNT(*) INTO trades_count FROM trades;
    SELECT COUNT(*) INTO positions_count FROM positions;
    SELECT COUNT(*) INTO snapshots_count FROM portfolio_snapshots;

    RAISE NOTICE 'Seed Data Applied:';
    RAISE NOTICE '  signals: %', signals_count;
    RAISE NOTICE '  orders: %', orders_count;
    RAISE NOTICE '  trades: %', trades_count;
    RAISE NOTICE '  positions: %', positions_count;
    RAISE NOTICE '  portfolio_snapshots: %', snapshots_count;

    IF signals_count != 3 OR orders_count != 3 OR trades_count != 1
       OR positions_count != 1 OR snapshots_count != 1 THEN
        RAISE EXCEPTION 'Seed data counts unexpected';
    END IF;
END $$;
