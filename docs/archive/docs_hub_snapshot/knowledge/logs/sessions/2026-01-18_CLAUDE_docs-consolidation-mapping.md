# Session Log: docs/ Consolidation Mapping

**Date:** 2026-01-18
**Agent:** Claude (Session Lead)
**Branch:** `docs/consolidate-docs-into-knowledge`
**Phase:** Phase 1 - Mapping & Planning
**Status:** ✅ COMPLETE - Awaiting User Approval

---

## Context

Consolidating the entire `docs/` directory into `knowledge/` to eliminate:
- Path duplication (docs/ vs knowledge/)
- Content duplication (identical files in both locations)
- Reference inconsistency (some links point to docs/, others to knowledge/)

**Governance Constraints:**
- No changes to `knowledge/governance/**` or `agents/**`
- No content loss - uncertain items archived with rationale
- Every deletion requires documented justification

---

## Inventory References

- **Source:** `.cdb_docs_inventory.txt` (66 entries)
- **Target:** `.cdb_knowledge_inventory.txt` (488 entries)
- **Real files:** 38 (excluding 14 symlinks in docs/)

---

## Decisions

### MUST (Completed)

1. ✅ **Create comprehensive mapping** - All 38 files categorized
2. ✅ **Resolve duplicates via hash comparison** - 6 REDUNDANT items identified
3. ✅ **Identify MERGE candidates** - 2 files where docs/ version is newer/better
4. ✅ **Resolve all UNCERTAIN items** - 4 items resolved via evidence
5. ✅ **Document evidence** - All hash comparisons and diffs recorded

### SHOULD (Next Phase)

1. ⏳ Execute MOVE operations (28 files)
2. ⏳ Execute MERGE operations (2 files)
3. ⏳ Delete REDUNDANT files (6 files)
4. ⏳ Archive OBSOLETE files (2 files)
5. ⏳ Update meta/legacy pointer for ORCHESTRATOR_PACK_144.md

### NICE (Phase 4+)

1. ⏳ Fix all internal links/references
2. ⏳ Verify no broken links remain
3. ⏳ Remove empty `docs/` directory

---

## Files Analysis

### By Category

| Category | Count | Examples |
|----------|-------|----------|
| **MOVE** | 28 | contracts/*, analysis/*, ci-cd/ci_checks.md, k8s/README.md |
| **MERGE** | 2 | CI_PIPELINE_GUIDE.md, TROUBLESHOOTING.md (docs version newer) |
| **REDUNDANT** | 6 | HITL_METRICS_MAPPING.md, HITL_RUNBOOK.md, runbook_papertrading.md, + 3 internal docs/ dupes |
| **OBSOLETE** | 2 | AGENT_TOOLS.md (generic), SETUP_GUIDE.md (6 bytes, empty) |
| **TOTAL** | 38 | |

### By Target Domain

| Target Domain | File Count | Notes |
|---------------|------------|-------|
| `knowledge/contracts/` | 11 | All contract specs, schemas, and examples |
| `knowledge/operating_rules/` | 3 | Emergency SOP, ci_cd/* |
| `knowledge/content/` | 4 | Onboarding, handovers |
| `knowledge/operations/` | 3 | Monthly maintenance, testnet setup |
| `knowledge/systems/` | 4 | Stack lifecycle, trading modes, K8S, SDK |
| `knowledge/security/` | 1 | Security hardening |
| `knowledge/testing/` | 1 | Test harness |
| `knowledge/audits/` | 1 | High voltage analysis |
| `knowledge/roadmap/` | 1 | Patchset plan |
| `knowledge/analysis/` | 1 | Project analytics |
| `knowledge/archive/legacy/` | 2 | Obsolete files + orchestrator pack |
| **DELETE** | 6 | Redundant duplicates |

---

## Key Findings

### Exact Duplicates Identified

1. **knowledge/ duplicates (3 files):**
   - `docs/general/HITL_METRICS_MAPPING.md` = `knowledge/operating_rules/HITL_METRICS_MAPPING.md`
   - `docs/general/HITL_RUNBOOK.md` = `knowledge/operating_rules/HITL_RUNBOOK.md`
   - `docs/general/runbook_papertrading.md` = `knowledge/operating_rules/runbook_papertrading.md`

2. **Internal docs/ duplicates (3 files):**
   - `docs/onboarding/QUICK_START.md` = `docs/general/ONBOARDING_QUICK_START.md`
   - `docs/planning/PATCHSET_PLAN_345.md` = `docs/general/PATCHSET_PLAN_345.md`
   - `docs/team/HANDOVERS_TO_TEAM_A.md` = `docs/general/HANDOVERS_TO_TEAM_A.md`

### MERGE Cases (docs/ version is better)

1. **CI_PIPELINE_GUIDE.md:**
   - `docs/ci-cd/` version: 6690 bytes, dated 2025-12-28, comprehensive
   - `knowledge/operating_rules/ci_cd/` version: 1440 bytes, dated 2025-12-19, basic overview
   - **Decision:** Use docs/ version

2. **TROUBLESHOOTING.md:**
   - `docs/ci-cd/` version: 6676 bytes
   - `knowledge/operating_rules/ci_cd/` version: 1025 bytes
   - **Decision:** Use docs/ version

### Special Cases

1. **ORCHESTRATOR_PACK_144.md:**
   - Real file (21KB) in `docs/orchestrator/`
   - Pointer file (137 bytes) in `meta/legacy/` pointing to docs location
   - **Decision:** Move to `knowledge/archive/legacy/`, update pointer

2. **contracts/ directory:**
   - 9 new files from docs/contracts/
   - Creates new `knowledge/contracts/` domain
   - Includes schemas, examples, and specs

---

## Evidence Trail

All decisions backed by:
- ✅ File size comparisons
- ✅ Git hash-object comparisons (SHA-1)
- ✅ Content diffs for MERGE candidates
- ✅ Existence checks in knowledge/ and meta/

**Mapping Document:** `knowledge/migrations/DOCS_TO_KNOWLEDGE_MAPPING.md`

---

## Next Steps

### Immediate (Awaiting Approval)

1. **User reviews mapping plan** - Categories and targets
2. **User approves or requests changes**
3. **Proceed to Phase 2** - Duplicate/Obsolete verification (minimal, mostly done)

### Phase 3 (Execution)

1. Create required directories (`knowledge/contracts/`, `knowledge/content/` if missing)
2. Execute MOVE operations (28 files) using `git mv`
3. Execute MERGE operations (2 files) - replace knowledge/ versions
4. Delete REDUNDANT files (6 files)
5. Move OBSOLETE files to archive with headers
6. Update meta/legacy/ORCHESTRATOR_PACK_144.md pointer

### Phase 4 (Link Fixes)

1. Find all references: `grep -r "docs/" --include="*.md"`
2. Replace systematically:
   - `docs/ci-cd/` → `knowledge/operating_rules/ci_cd/`
   - `docs/contracts/` → `knowledge/contracts/`
   - `docs/general/` → various (per mapping)
3. Verify no broken links

### Phase 5 (Cleanup)

1. Remove empty `docs/` directory
2. Remove `.cdb_*_inventory.txt` files
3. Verify `git status` is clean
4. Create PR

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Broken internal links | Phase 4 systematic link fixes + verification |
| Lost content | All UNCERTAIN resolved, nothing deleted without rationale |
| Merge conflicts | Using `git mv` to preserve history, MERGE only 2 files |
| Canon breaks | No changes to governance/** or agents/** per hard rules |

---

## Session Output

**Created Files:**
- `knowledge/migrations/DOCS_TO_KNOWLEDGE_MAPPING.md` (comprehensive mapping table)
- `knowledge/logs/sessions/2026-01-18_CLAUDE_docs-consolidation-mapping.md` (this file)

**Branch State:**
- Clean working directory (only untracked inventories)
- No uncommitted changes
- Ready for Phase 3 execution upon approval

---

**Status:** ⏸️ PAUSED - Awaiting user approval of mapping plan
