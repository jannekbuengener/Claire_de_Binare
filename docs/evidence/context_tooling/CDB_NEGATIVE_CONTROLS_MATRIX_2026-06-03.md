# Negative-control matrix — write-intent and mutation blockades

**Issue:** [#2854](https://github.com/jannekbuengener/Claire_de_Binare/issues/2854)  
**Parent:** [#2847](https://github.com/jannekbuengener/Claire_de_Binare/issues/2847)  
**Date:** 2026-06-03

## Scope

Regression-only. No productive SurrealDB writes, no MCP mutations, no runtime BLUE/RED
changes, no Security-alert scope (#2860–#2869).

## Safety defaults (must stay off in CI)

| Flag | Expected | Module |
|------|----------|--------|
| `PERSIST_ALLOWED` | `False` | `tools/surrealdb/memory_write_gate.py` |
| `MUTATION_ALLOWED` | `False` | `tools/mcp/memory_write_intent_tools.py` |

## Matrix categories

| Category | Intent |
|----------|--------|
| `safety_defaults` | Module constants remain default-off |
| `write_intent` | `cdb_context_memory_write_intent` dry-run vs refused modes |
| `mutation_gate` | Mutation flags / SQL injection blocked |
| `productive_persist` | `approved_for_persist` false without `CDB_PERSIST_ALLOWED=1` |
| `fake_db_evidence` | Caller `brain_source` without records → `invalid_fake_db` |
| `scope_drift` | `unauthorized_write_intent` without `human_go_token` |
| `harness_classification` | Bridge **PASS** vs MCP **BLOCKED_SAFETY** |

## Harness verdict semantics

| Verdict | Meaning |
|---------|---------|
| **PASS** | Expected fail-closed refusal or dry-run gate (bridge write-intent) |
| **BLOCKED_SAFETY** | MCP Smart Mode / policy blocked the call (not a handler FAIL) |
| **FAIL** | Unexpected activation or missing block |

Bridge `cdb_context_memory_write_intent` with `operation_mode=agent_memory_write`
must classify as **PASS** (`status=refused`, `agent_memory_write_not_activated`).

MCP-only Smart Mode blocks classify as **BLOCKED_SAFETY** (accepted boundary per
benchmark #2849 evidence).

## Rerun focused tests

```bash
make context-negative-controls
```

Or:

```bash
pytest -q tests/unit/surrealdb/test_negative_controls_regression.py -m unit
pytest -q tests/unit/tools/mcp/test_memory_write_intent_tool.py -m unit
pytest -q tests/unit/surrealdb/test_memory_write_gate.py -m unit
```

Include in broader context regression:

```bash
make context-live-invoke
```

Machine-readable matrix index is embedded in harness JSON evidence under
`negative_controls` (`tools/surrealdb/negative_controls.py`).

## Non-goals

- Enabling `PERSIST_ALLOWED` / `MUTATION_ALLOWED` in CI
- Live MCP stdio mutation proofs
- Security workflow changes
- Operator trust scoring (#2856) or senses docs (#2855)
