# PR08_PAPER_TRADING_SCHEMA

Date: 2025-12-19
Scope: Database schema plan for paper trading
Repo: Claire_de_Binare (Working Repo)

## Proposed tables
- paper_orders
- paper_fills
- paper_positions
- paper_pnl_snapshots

## Migration plan
- infrastructure/database/migrations/003_paper_trading_schema.sql
- infrastructure/database/migrations/003_paper_trading_schema_rollback.sql

## Indexes
- paper_orders: symbol, created_at desc, status
- paper_pnl_snapshots: snapshot_time desc

## Verification
- Apply migration in local Postgres
- Verify tables and indexes
- Insert sample rows
- Rollback works

## Notes
- This plan mirrors Issue #142 SQL skeleton.
