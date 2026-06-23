# CDB Testing Knowledge

Status: active local index

This folder contains CDB testing guidance and planning maps. It is knowledge,
not executable test code.

## Current Entries

| File | Purpose |
|---|---|
| `TEST_HARNESS_V1.md` | Historical test execution guide and local command map. |
| `PAPER_TRADING_TEST_REQUIREMENTS.md` | Early P0 paper-trading scenario requirements. |
| `PERFORMANCE_BASELINES.md` | Draft latency and throughput baseline targets. |
| `MOCKEXCHANGE_CDB_TEST_MAP.md` | Active map for turning MockExchange reference patterns into CDB-native tests. |
| `TEST_FIRST_PROCESSING_CONTRACT.md` | Active contract: test metadata standard, 15 test types, SurrealDB knowledge model, processing pipeline. |
| `SKILL_VALLEY_TEST_UPGRADE_PLAN.md` | Active plan: 8 skill rules agents must learn before scaling tests. |

## Guardrail

Testing knowledge does not authorize runtime, Docker, exchange, database, or
live-capital actions. LR remains NO-GO unless the canonical live-readiness SSOT
states otherwise.
