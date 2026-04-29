---
name: cdb-exchange-adapters
description: CDB exchange-adapter work in the current working repo. Use when Codex needs to implement or harden REST or websocket adapters, order or market-data normalization, rate-limit handling, reconnect logic, or idempotent exchange boundaries. Prefer current repo realities and active integrations; treat MEXC as the default exchange only when the repo context proves it, and keep all work in paper or testnet-safe scope.
---

# Exchange Adapters

## Canon first
- Use the working repo as canon. Do not reference the retired external docs repo.
- Read `CURRENT_STATUS.md` and local adapter code before assuming the active exchange scope.
- Stage `trade-capable` is not a license for live endpoints or live keys.

## Trigger phrases
- exchange adapter, REST client, websocket client
- MEXC, Binance, Crypto.com, market data, order schema
- rate limit, retry, backoff, reconnect, heartbeat
- idempotency, auth failure, timeout taxonomy

## Non-negotiables
- No real keys in code.
- No live endpoints by default; paper or testnet only when explicitly needed.
- Normalize to the repo's current internal schema instead of inventing a new one.
- Add tests for happy path plus failure taxonomy.
- Include one simulated failure case that proves retry or backoff behavior.

## Deliverables
- adapter module or boundary patch
- tests for success and failure paths
- short evidence snippet for the user or PR
