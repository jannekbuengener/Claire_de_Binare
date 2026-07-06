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
pytest -q tests/unit/tools/test_validate_skill_surface_mirror.py
pytest -q tests/unit -k "skill or surface or mirror or brain_evidence or bootloader"
python tools/validate_skill_surface_mirror.py
```

## Non-goals

- New skill content or surface adapters (mirror workflow unchanged).
- Context architecture or SurrealDB schema changes.
- Runtime / Docker / BLUE / RED changes.
