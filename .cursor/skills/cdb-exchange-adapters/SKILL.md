<!--
Canonical Skill Source: docs/skills/cdb-exchange-adapters/SKILL.md
Surface: cursor
Sync Status: mirrored-from-canon
Last Verified: 2026-07-01
Drift Policy: Surface-Adapter duerfen nur mit dokumentierter Begruendung abweichen.
-->
---
name: cdb-exchange-adapters
description: CDB exchange-adapter work in the current Claire de Binare repository. Use when Codex needs to implement or harden REST or websocket adapters, order or market-data normalization, rate-limit handling, reconnect logic, or idempotent exchange boundaries. Prefer current repo realities and active integrations; treat MEXC as the default exchange only when the repo context proves it, and keep all work in paper or testnet-safe scope.
disable-model-invocation: true
---

# Exchange Adapters

## Canon first
- Use the Claire de Binare repository as canon. Do not reference the retired external docs repo.
- Read `CURRENT_STATUS.md` and local adapter code before assuming the active exchange scope.
- Stage `trade-capable` is not a license for live endpoints or live keys.

## Trigger phrases
- exchange adapter, REST client, websocket client
- MEXC, Binance, Crypto.com, market data, order schema
- rate limit, retry, backoff, reconnect, heartbeat
- idempotency, auth failure, timeout taxonomy

## Non-negotiables
- No real keys in code.
- Default-safe scope is paper/mock only.
- Testnet is allowed only with explicit user GO and an explicit reason.
- Live endpoints / real keys are never the default; do not derive any live-trading authorization from this skill text.
- Normalize to the repo's current internal schema instead of inventing a new one.
- Add tests for happy path plus failure taxonomy.
- Include one simulated failure case that proves retry or backoff behavior.

## External Documentation Lookup

This skill touches exchange APIs, WebSocket protocols, and Protobuf schemas:
- Load `cdb-external-docs` before implementation.
- Look up `docs/external-docs/index.md` → Exchange / Market Data section.
- Relevant: MEXC Spot V3 API, MEXC Contract API, Protocol Buffers, websockets Python.
- Read official docs before writing adapter code.
- If no internet is available, report `EXTERNAL_DOCS_UNVERIFIED` instead of guessing API behavior.

## Deliverables
- adapter module or boundary patch
- tests for success and failure paths
- short evidence snippet for the user or PR
