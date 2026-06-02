# Session 2026-06-02 — #2800 Evidence-aware decision replay v2

## Scope

Issue #2800 / PR #2814 — additive `build_decision_replay_v2` over v1; MCP `cdb_context_decision_replay` on `decision-replay-query/v2`; read-only/in-memory evidence enrichment; no DB/MCP mutations.

## Delivered

- `tools/surrealdb/decision_replay_builder.py` — `SCHEMA_VERSION_V2`, `build_decision_replay_v2` (evidence_links, resolved_evidence, unresolved_evidence_refs, evidence_resolution_status, evidence_warnings, decision_chain_hash, replay_explainability); v1 semantics unchanged
- `tools/mcp/context_decision_tools.py` — replay handler uses v2; optional `evidence_records` / `claim_records`
- `tests/unit/surrealdb/test_decision_replay_builder_v2.py` (8 tests) + Wave14/MCP contract updates
- `docs/surrealdb/decision_replay_query_contract.md` — v2 contract section
- Review fix `39c545ac` — `decision_chain_hash` hashes post-enrichment evidence resolution (Codex r3341036125)

## Validation

- `pytest -q tests/unit/surrealdb/test_decision_replay_builder_v1.py tests/unit/surrealdb/test_decision_replay_builder_v2.py tests/unit/surrealdb/test_decision_mcp_tools_v1.py`
- `ruff check tools/surrealdb/decision_replay_builder.py tools/mcp/context_decision_tools.py`
- PR #2814 required checks green; squash-merge `622fb17d0689fa89ba4429e1c371480810ac7b0f`

## GitHub

- PR [#2814](https://github.com/jannekbuengener/Claire_de_Binare/pull/2814) MERGED
- Issue [#2800](https://github.com/jannekbuengener/Claire_de_Binare/issues/2800) CLOSED
- Epic [#2778](https://github.com/jannekbuengener/Claire_de_Binare/issues/2778) progress comment posted

## Boundaries

- LR NO-GO; `PERSIST_ALLOWED=False` / `MUTATION_ALLOWED=False`; no productive DB writes; no live/Echtgeld scope
- #2798 / #2802 / #2803 / #2804 untouched

## Follow-ups

- #2778 remaining Phase-2 child slices (#2797–#2804; #2799/#2800 CLOSED)
