# Wave-18 Completion Gates

**Wave 18 — Knowledge Quality Scoring & Architect Signals**  
Anchor Issue: #2170  
Status: `draft` → update to `complete` when all gates pass  
Epic: #1976

---

## Completion Gate Checklist

### Gate 1: Core Services Implemented

- [x] `tools/surrealdb/quality_scoring.py` — Knowledge Quality Scoring Service v1 (#2171)
  - 8 scoring dimensions with weighted aggregation
  - Grade bands: blocking/watch/weak/good
  - Blocking downgrade rule (any blocking dim → overall capped at watch)
  - GUARDRAILS embedded in every result
  - `score_knowledge_quality_v1()` public API

- [x] `tools/surrealdb/architect_signals.py` — Architect Signal Service v1 (#2174)
  - 11 signal types
  - Severity levels: info / watch / blocking
  - Pure function, no auto-issue creation
  - `accepted_risk` / `false_positive` modellable per finding
  - `scan_architect_signals_v1()` public API

### Gate 2: CLI Implementations

- [x] `tools/surrealdb/quality_scoring_cli.py` — Quality Scoring CLI (#2172)
  - `score-knowledge` subcommand
  - `show-score --dimension` subcommand
  - `report-quality` subcommand
  - Exit codes: 0 (ok), 1 (weak), 2 (error), 3 (not found)
  - `--fail-on-weak` flag
  - `--format json|markdown`

### Gate 3: MCP Adapters

- [x] `tools/mcp/quality_scoring_tools.py` — Quality Score MCP tool (#2173)
  - Tool name: `cdb_context_quality_score`
  - Bundle-driven, read-only, fail-closed
  - `metadata.read_only = True` on every response

- [x] `tools/mcp/architect_signal_tools.py` — Architect Signals MCP tool (#2175)
  - Tool name: `cdb_context_architect_signals`
  - Bundle-driven, read-only, fail-closed
  - `metadata.read_only = True` on every response

### Gate 4: Registry & Bridge Integration

- [x] `tools/mcp/permission_guard.py` updated
  - `cdb_context_quality_score` in `INPUT_SCAN_EXEMPT_TOOLS`
  - `cdb_context_architect_signals` in `INPUT_SCAN_EXEMPT_TOOLS`

- [x] `tools/mcp/registry.py` updated
  - `cdb_context_quality_score` registered with `read_only=True`
  - `cdb_context_architect_signals` registered with `read_only=True`

- [x] `tools/mcp/context_bridge.py` updated
  - `cdb_context_quality_score_handler` defined and routed
  - `cdb_context_architect_signals_handler` defined and routed
  - Wave-18 handler map registered in `ContextBridge.__init__`

### Gate 5: Tests & Fixtures

- [x] `tests/unit/surrealdb/test_quality_scoring.py` (#2176)
  - All 8 dimensions produce scores
  - Grade threshold tests
  - Blocking downgrade rule
  - Empty bundle returns blocking coverage
  - Clean bundle returns good overall
  - Determinism tests
  - Error case tests

- [x] `tests/unit/tools/mcp/test_quality_scoring_tools.py` (#2176)
  - Permission guard exempt test
  - Registry read-only test
  - Bridge routing test
  - Missing/invalid bundle tests
  - Dimension / grade / limit filters
  - Guardrails in response

- [x] `tests/fixtures/surrealdb/quality_scoring/sample_bundle.json` (#2176)

### Gate 6: Documentation

- [x] `docs/surrealdb/quality-scoring-architect-signals-runbook.md` (#2177)
  - Score dimensions reference
  - Grade bands reference
  - CLI usage guide
  - MCP tool usage guide
  - Bundle format reference
  - Human escalation guide
  - Guardrails section

- [x] `docs/surrealdb/context-wave18-completion-gates.md` (#2178) — this file

---

## Open Issues to Close

When all gates above are checked and PRs are merged, close in this order:

1. #2171 — Quality Scoring Service v1
2. #2172 — Quality Scoring CLI
3. #2173 — Quality Score MCP tool
4. #2174 — Architect Signal Service v1
5. #2175 — Architect Signals MCP tool
6. #2176 — Tests & Fixtures
7. #2177 — Runbook
8. #2178 — Completion Gates (this issue)
9. #2170 — Wave-18 anchor (after all children closed)

---

## Governance Notes

- LR Status remains `NO-GO` for live trading.
- Board Stage `trade-capable` (ratified 2026-04-08) is orthogonal to LR NO-GO.
- No live capital, no Grafana gate, no strategy validation implied by Wave-18 completion.
- Quality Scoring and Architect Signals are **informational services** only.
- Human-GO is always required before any blocking signal leads to writes or capital changes.
