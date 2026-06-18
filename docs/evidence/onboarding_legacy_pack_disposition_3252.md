# Legacy Onboarding Pack Disposition (#3252)

Status: Evidence / Decision
Issue: #3252
Parent: #3246
Date: 2026-06-16

## Executive Summary

The two legacy onboarding packs `knowledge/content/ONBOARDING_QUICK_START.md` and
`knowledge/content/ONBOARDING_LINKS.md` were deleted. Their historical context is
preserved in existing evidence, migration, and audit documents. No unique useful
content was lost.

## Disposition Decision: DELETE

### Files affected

| File | Disposition | Rationale |
|---|---|---|
| `knowledge/content/ONBOARDING_QUICK_START.md` | **DELETE** | Self-declared legacy; all content is stale/missing-path references; active replacements captured in `DOCS_TO_KNOWLEDGE_MAPPING.md`; broken-path inventory captured in `onboarding_readme_navigation_audit_3227.md` |
| `knowledge/content/ONBOARDING_LINKS.md` | **DELETE** | Same as above; additionally listed incorrectly as a "canonical runtime reference" in `knowledge/CDB_DOCKER_STACK_INVENTORY.md` |

### Why not archive?

- Both files already carried a `Legacy / Historical — Pointer Only` header redirecting to the active chain
- The broken-path inventory is fully documented in `docs/evidence/onboarding_readme_navigation_audit_3227.md`
- The migration history is captured in `knowledge/migrations/DOCS_TO_KNOWLEDGE_MAPPING.md`
- The lifecycle inventory note is in `knowledge/governance/TODO_LIFECYCLE_INVENTORY_2026-03-22.md`
- Moving to `docs/archive/` would add no new evidence value and would create a new stale surface

### Why not pointer-only?

Keeping pointer-only files in `knowledge/content/` was the worst option because:
- `knowledge/content/` is a live knowledge directory; any file there acts as implicit active truth
- Both files already had pointer-only headers, yet `knowledge/CDB_DOCKER_STACK_INVENTORY.md` still referenced `ONBOARDING_LINKS.md` as a "canonical runtime reference"
- Agent tooling discovery surfaces could pick them up as knowledge entries

## Reference cleanup

| File | Change | Reason |
|---|---|---|
| `knowledge/CDB_DOCKER_STACK_INVENTORY.md:9` | Removed `knowledge/content/ONBOARDING_LINKS.md` from canonical runtime references | Was never a runtime reference; stale onboarding doc miscategorised |
| `knowledge/staging/CDB_DOCKER_STACK_INVENTORY.md:12` | Removed `knowledge/content/ONBOARDING_LINKS.md` from "Use instead" list | Non-canonical staging copy mirrored the stale reference |

### References intentionally left unchanged

| File | Reason |
|---|---|
| `knowledge/migrations/DOCS_TO_KNOWLEDGE_MAPPING.md` | Historical migration metadata; records the MOVE from `docs/general/` to `knowledge/content/` |
| `knowledge/governance/TODO_LIFECYCLE_INVENTORY_2026-03-22.md` | Historical archive-candidate inventory |
| `docs/evidence/onboarding_readme_navigation_audit_3227.md` | Evidence document; correctly records the legacy state at audit time |
| `tools/validate_onboarding_docs.py` | `LEGACY_PACK_NAMES` list preserved as negative-test fixtures |
| `tests/unit/tools/test_validate_onboarding_docs.py` | Test fixtures for legacy name detection |
| `docs/archive/docs_hub_snapshot/` | Historical archive (not touched) |

## Active onboarding truth (unchanged)

- `README.md`
- `docs/index.md`
- `DEVELOPER_ONBOARDING.md`
- `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`
- `docs/onboarding/fresh_clone_rehearsal.md`
- `docs/onboarding/first_issue_sandbox.md`
- `docs/onboarding/cdb_glossary.md`
- `docs/onboarding/repo_brain_context_intelligence.md`
- `docs/onboarding/examples/`
- `docs/onboarding/templates/`
- `docs/surrealdb/README.md`
- `tools/README.md`
- `tests/README.md`
- `services/README.md`

## Validation

- `python -m tools.validate_onboarding_docs` → PASS
- `pytest -q tests/unit/tools/test_validate_onboarding_docs.py` → PASS
- `pytest -q tests/unit/test_onboarding_tour.py` → PASS
- `pytest -q tests/unit/test_onboarding_doctor.py` → PASS
- `rg` dedupe: zero active-surface hits for `ONBOARDING_QUICK_START` or `ONBOARDING_LINKS` outside archive/evidence/migration/test surfaces

## Safety Boundaries

- LR: NO-GO
- Board-Stage `trade-capable` is not Live-Go
- No runtime, Docker, trading, DB, or MCP changes
- Onboarding validator not weakened (`LEGACY_PACK_NAMES` preserved)
- No secrets touched

## Restunsicherheiten

- `docs/archive/docs_hub_snapshot/` contains historical navpack artifacts (graph JSON, taxonomy) that reference these legacy filenames; these are immutable archive artifacts and were not modified
- The `knowledge/content/` directory still exists and may contain other legacy or stale files not evaluated in this issue
