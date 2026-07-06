# Agent OS Contract Tests

Status: active (Issue #3864 child slices)
Scope: Agent OS / Skills / Evidence — test-only guards, no runtime change

## Purpose

These contract tests protect **agent-facing rules**, not trading runtime code.
They answer: can a fresh agent read CDB governance, mirror skills correctly,
and emit honest Brain Evidence without inventing DB-backed claims?

| Issue | Test module | Rule protected |
|---|---|---|
| #3865 | `tests/unit/agents/test_agent_read_order_bootloader_contract.py` | Bootloader Read Order, status surfaces, LR vs Board stage |
| #3866 | `tests/unit/agents/test_skill_surface_adapter_drift_contract.py` | Skill SSOT mirrors (`docs/skills/` → surface adapters) |
| #3866 | `tests/unit/tools/test_validate_skill_surface_mirror.py` | Drift guard implementation (#3643) |
| #3867 | `tests/unit/agents/test_brain_evidence_agent_os_regression_contract.py` | Brain Evidence block + final report shape |
| #3867 | `tests/unit/agents/test_brain_evidence_block_contract.py` | MCP briefing Brain Evidence gate (#3774) |
| #3868 | `tests/unit/agents/test_onboarding_fresh_agent_contract.py` | Fresh-agent read-only default, setup GO gate, simulation modes |
| #3868 | `tests/smoke/test_onboarding_orchestrator.py` | Orchestrator CLI smoke (no mutations) |
| #3868 | `tests/smoke/test_onboarding_cross_agent_surfaces.py` | Cross-surface onboarding routing |
| #3869 | `tests/unit/agents/test_agent_role_consistency_contract.py` | Agent role LR/Live/MCP/write/onboarding consistency |
| #3870 | `tests/unit/agents/test_mcp_capability_resolution_contract.py` | MCP capability resolution: config, inventory, dispatch, fallback semantics |
| #3870 | `tests/unit/tools/test_context_tool_inventory.py` | Tool inventory / exposure truth (#3493) |
| #3871 | `tests/unit/agents/test_agent_knowledge_skill_map_contract.py` | Skill registry, onboarding map, docs/knowledge, archive guards |
| #3871 | `tools/validate_onboarding_docs.py` | Active onboarding surface integrity (#3233) |

Shared helpers: `tests/unit/agents/_bootloader_read_order_helpers.py`,
`tests/unit/agents/_agent_os_contract_helpers.py`.

## Why contract tests here

- **Testart:** Wissens-Test / Contract-Test (see `TEST_FIRST_PROCESSING_CONTRACT.md`).
- **Fail-closed:** Missing canon files, skill drift, or misclassified Brain Evidence
  fail CI before agents rely on stale mirrors or fake DB claims.
- **No DB/MCP writes:** Fixtures and repo reads only; LR remains NO-GO.

## Validation commands

```bash
pytest -q tests/unit/agents/test_skill_surface_adapter_drift_contract.py
pytest -q tests/unit/agents/test_brain_evidence_agent_os_regression_contract.py
pytest -q tests/unit/agents/test_onboarding_fresh_agent_contract.py
pytest -q tests/unit/agents/test_agent_role_consistency_contract.py
pytest -q tests/unit/agents/test_mcp_capability_resolution_contract.py
pytest -q tests/unit/agents/test_agent_knowledge_skill_map_contract.py
pytest -q tests/unit/tools/test_context_tool_inventory.py
pytest -q tests/unit/tools/test_validate_skill_surface_mirror.py
pytest -q tests/unit -k "onboarding or agent or role or guardrail or brain_evidence"
pytest -q tests/smoke -k "onboarding"
python tools/validate_skill_surface_mirror.py
```

## Non-goals

- New skill content or surface adapters (mirror workflow unchanged).
- Context architecture or SurrealDB schema changes.
- Runtime / Docker / BLUE / RED changes.
