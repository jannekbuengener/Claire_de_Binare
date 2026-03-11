# docs/ → knowledge/ Consolidation Mapping

**Created:** 2026-01-18
**Branch:** `docs/consolidate-docs-into-knowledge`
**Mission:** Integrate all `docs/` content into `knowledge/` without duplication or canon breaks

---

## Summary Statistics

| Category | Count | Action |
|----------|-------|--------|
| MOVE | 28 | Move files to new knowledge/ location |
| MERGE | 2 | Merge with existing knowledge/ files (docs version is newer/better) |
| REDUNDANT | 6 | Delete (identical duplicates already in knowledge/) |
| OBSOLETE | 2 | Archive as superseded/outdated |
| UNCERTAIN | 0 | **All resolved** ✅ |
| **TOTAL** | **38** | **Real files in docs/** |

---

## Detailed Mapping Table

| # | Source (docs/) | Target (knowledge/) | Category | Rationale | Kept File |
|---|----------------|---------------------|----------|-----------|-----------|
| 1 | `docs/AGENT_TOOLS.md` | `knowledge/archive/docs_legacy/AGENT_TOOLS.md` | OBSOLETE | Generic agent tools doc, likely superseded by agents/ structure | Archive |
| 2 | `docs/analysis/PROJECT_ANALYTICS.md` | `knowledge/analysis/PROJECT_ANALYTICS.md` | MOVE | Unique analysis content | knowledge/analysis/PROJECT_ANALYTICS.md |
| 3 | `docs/ci-cd/ci_checks.md` | `knowledge/operating_rules/ci_cd/ci_checks.md` | MOVE | CI checks documentation | knowledge/operating_rules/ci_cd/ci_checks.md |
| 4 | `docs/ci-cd/CI_PIPELINE_GUIDE.md` | `knowledge/operating_rules/ci_cd/CI_PIPELINE_GUIDE.md` | MERGE | docs version (6690b, 2025-12-28) is newer than knowledge version (1440b, 2025-12-19) | knowledge/operating_rules/ci_cd/CI_PIPELINE_GUIDE.md |
| 5 | `docs/ci-cd/TROUBLESHOOTING.md` | `knowledge/operating_rules/ci_cd/TROUBLESHOOTING.md` | MERGE | docs version (6676b) is much larger than knowledge version (1025b) | knowledge/operating_rules/ci_cd/TROUBLESHOOTING.md |
| 6 | `docs/contracts/market_data.schema.json` | `knowledge/contracts/market_data.schema.json` | MOVE | JSON schema for market data | knowledge/contracts/market_data.schema.json |
| 7 | `docs/contracts/market_data_invalid.json` | `knowledge/contracts/market_data_invalid.json` | MOVE | Test fixture (invalid example) | knowledge/contracts/market_data_invalid.json |
| 8 | `docs/contracts/market_data_valid.json` | `knowledge/contracts/market_data_valid.json` | MOVE | Test fixture (valid example) | knowledge/contracts/market_data_valid.json |
| 9 | `docs/contracts/MIGRATION.md` | `knowledge/contracts/MIGRATION.md` | MOVE | Contract migration guide | knowledge/contracts/MIGRATION.md |
| 10 | `docs/contracts/README.md` | `knowledge/contracts/README.md` | MOVE | Contracts overview | knowledge/contracts/README.md |
| 11 | `docs/contracts/REPLAY_CONTRACT.md` | `knowledge/contracts/REPLAY_CONTRACT.md` | MOVE | Replay contract specification | knowledge/contracts/REPLAY_CONTRACT.md |
| 12 | `docs/contracts/signal.schema.json` | `knowledge/contracts/signal.schema.json` | MOVE | JSON schema for signals | knowledge/contracts/signal.schema.json |
| 13 | `docs/contracts/signal_invalid.json` | `knowledge/contracts/signal_invalid.json` | MOVE | Test fixture (invalid example) | knowledge/contracts/signal_invalid.json |
| 14 | `docs/contracts/signal_valid.json` | `knowledge/contracts/signal_valid.json` | MOVE | Test fixture (valid example) | knowledge/contracts/signal_valid.json |
| 15 | `docs/general/CONTRACTS.md` | `knowledge/contracts/CONTRACTS.md` | MOVE | General contracts documentation | knowledge/contracts/CONTRACTS.md |
| 16 | `docs/general/EMERGENCY_STOP_SOP.md` | `knowledge/operating_rules/EMERGENCY_STOP_SOP.md` | MOVE | Emergency procedures runbook | knowledge/operating_rules/EMERGENCY_STOP_SOP.md |
| 17 | `docs/general/HANDOVERS_TO_TEAM_A.md` | `knowledge/content/HANDOVERS_TO_TEAM_A.md` | MOVE | Team handover documentation | knowledge/content/HANDOVERS_TO_TEAM_A.md |
| 18 | `docs/general/HEALTH_CONTRACT.md` | `knowledge/contracts/HEALTH_CONTRACT.md` | MOVE | Health check contract spec | knowledge/contracts/HEALTH_CONTRACT.md |
| 19 | `docs/general/HIGH_VOLTAGE_ANALYSIS_REPORT.md` | `knowledge/audits/HIGH_VOLTAGE_ANALYSIS_REPORT.md` | MOVE | Analysis report | knowledge/audits/HIGH_VOLTAGE_ANALYSIS_REPORT.md |
| 20 | `docs/general/HITL_METRICS_MAPPING.md` | DELETE | REDUNDANT | Identical (hash 32670e7) to knowledge/operating_rules/HITL_METRICS_MAPPING.md | knowledge/operating_rules/HITL_METRICS_MAPPING.md |
| 21 | `docs/general/HITL_RUNBOOK.md` | DELETE | REDUNDANT | Identical (hash fe98e57) to knowledge/operating_rules/HITL_RUNBOOK.md | knowledge/operating_rules/HITL_RUNBOOK.md |
| 22 | `docs/general/ONBOARDING_LINKS.md` | `knowledge/content/ONBOARDING_LINKS.md` | MOVE | Onboarding links collection | knowledge/content/ONBOARDING_LINKS.md |
| 23 | `docs/general/ONBOARDING_QUICK_START.md` | `knowledge/content/ONBOARDING_QUICK_START.md` | MOVE | Quick start guide | knowledge/content/ONBOARDING_QUICK_START.md |
| 24 | `docs/general/PATCHSET_PLAN_345.md` | `knowledge/roadmap/PATCHSET_PLAN_345.md` | MOVE | Historical patchset planning doc | knowledge/roadmap/PATCHSET_PLAN_345.md |
| 25 | `docs/general/runbook_papertrading.md` | DELETE | REDUNDANT | Identical (hash 49c1a6c) to knowledge/operating_rules/runbook_papertrading.md | knowledge/operating_rules/runbook_papertrading.md |
| 26 | `docs/general/SECURITY_HARDENING.md` | `knowledge/security/SECURITY_HARDENING.md` | MOVE | Security hardening guide | knowledge/security/SECURITY_HARDENING.md |
| 27 | `docs/general/SETUP_GUIDE.md` | `knowledge/archive/docs_legacy/SETUP_GUIDE.md` | OBSOLETE | Only 6 bytes (nearly empty), likely placeholder | Archive |
| 28 | `docs/general/STACK_LIFECYCLE.md` | `knowledge/systems/STACK_LIFECYCLE.md` | MOVE | Stack lifecycle documentation | knowledge/systems/STACK_LIFECYCLE.md |
| 29 | `docs/general/TESTNET_SETUP.md` | `knowledge/operations/TESTNET_SETUP.md` | MOVE | Testnet setup procedures | knowledge/operations/TESTNET_SETUP.md |
| 30 | `docs/general/TEST_HARNESS_V1.md` | `knowledge/testing/TEST_HARNESS_V1.md` | MOVE | Test harness documentation | knowledge/testing/TEST_HARNESS_V1.md |
| 31 | `docs/general/TRADING_MODES.md` | `knowledge/systems/TRADING_MODES.md` | MOVE | Trading modes specification | knowledge/systems/TRADING_MODES.md |
| 32 | `docs/k8s/README.md` | `knowledge/systems/K8S_OVERVIEW.md` | MOVE | Kubernetes overview (rename to avoid generic README) | knowledge/systems/K8S_OVERVIEW.md |
| 33 | `docs/onboarding/QUICK_START.md` | DELETE | REDUNDANT | Identical (hash 9aaca6f) to docs/general/ONBOARDING_QUICK_START.md | knowledge/content/ONBOARDING_QUICK_START.md |
| 34 | `docs/ops/MONTHLY_MAINTENANCE.md` | `knowledge/operations/MONTHLY_MAINTENANCE.md` | MOVE | Operations runbook | knowledge/operations/MONTHLY_MAINTENANCE.md |
| 35 | `docs/orchestrator/ORCHESTRATOR_PACK_144.md` | `knowledge/archive/legacy/ORCHESTRATOR_PACK_144.md` | MOVE | Legacy orchestrator doc (21KB), meta/legacy pointer exists | knowledge/archive/legacy/ORCHESTRATOR_PACK_144.md |
| 36 | `docs/planning/PATCHSET_PLAN_345.md` | DELETE | REDUNDANT | Identical (hash 16e1603) to docs/general/PATCHSET_PLAN_345.md | knowledge/roadmap/PATCHSET_PLAN_345.md |
| 37 | `docs/sdk/README.md` | `knowledge/systems/SDK_OVERVIEW.md` | MOVE | SDK documentation (rename to avoid generic README) | knowledge/systems/SDK_OVERVIEW.md |
| 38 | `docs/team/HANDOVERS_TO_TEAM_A.md` | DELETE | REDUNDANT | Identical (hash 14a69d7) to docs/general/HANDOVERS_TO_TEAM_A.md | knowledge/content/HANDOVERS_TO_TEAM_A.md |

---

## Symlink Entries (No Action Required)

The following are symlinks pointing to other locations - they will be removed when `docs/` is deleted:

- `docs/architecture` → (symlink)
- `docs/audit` → (symlink)
- `docs/ci` → (symlink)
- `docs/core` → (symlink)
- `docs/decisions` → (symlink)
- `docs/infra` → (symlink)
- `docs/observability` → (symlink)
- `docs/operations` → (symlink)
- `docs/security` → (symlink)
- `docs/services` → (symlink)
- `docs/testing` → (symlink)
- `docs/test_plans` → (symlink)
- `docs/tools` → (symlink)
- `docs/workflows` → (symlink)

---

## UNCERTAIN Items - All Resolved ✅

All initially uncertain items were resolved via hash comparison:

1. ✅ `docs/onboarding/QUICK_START.md` → **REDUNDANT** (identical to docs/general version)
2. ✅ `docs/orchestrator/ORCHESTRATOR_PACK_144.md` → **MOVE** to archive/legacy (already has pointer in meta/legacy)
3. ✅ `docs/planning/PATCHSET_PLAN_345.md` → **REDUNDANT** (identical to docs/general version)
4. ✅ `docs/team/HANDOVERS_TO_TEAM_A.md` → **REDUNDANT** (identical to docs/general version)

---

## New Directories to Create

The following directories will be created as needed:

- `knowledge/contracts/` - For contract specifications and schemas
- `knowledge/content/` - For onboarding and informational content (if doesn't exist)

---

## Next Steps (Phase 2)

1. **Resolve UNCERTAIN items** - Run hash checks on potential duplicates
2. **Validate mapping** - Get user approval on categorizations
3. **Proceed with Phase 3** - Execute MOVE/MERGE/REDUNDANT/OBSOLETE actions
4. **Phase 4** - Fix all references/links repo-wide
5. **Phase 5** - Clean up and verify

---

## Evidence Commands Used

```bash
# File size comparison
find docs -type f -name "*.md" -o -name "*.json" | while read f; do echo "$f $(wc -c < "$f")"; done

# Hash comparison for REDUNDANT items (knowledge/ duplicates)
git hash-object docs/general/HITL_METRICS_MAPPING.md knowledge/operating_rules/HITL_METRICS_MAPPING.md
# Result: 32670e7791c12061be927a6748406713fd5e0f13 (identical) ✅

git hash-object docs/general/HITL_RUNBOOK.md knowledge/operating_rules/HITL_RUNBOOK.md
# Result: fe98e575667f14697afb92a0ea799895cac2c317 (identical) ✅

git hash-object docs/general/runbook_papertrading.md knowledge/operating_rules/runbook_papertrading.md
# Result: 49c1a6cb7ee29bda14e6a9341b17837651b84a9d (identical) ✅

# Hash comparison for REDUNDANT items (docs/ internal duplicates)
git hash-object docs/onboarding/QUICK_START.md docs/general/ONBOARDING_QUICK_START.md
# Result: 9aaca6fd69d9c7170e20b3a659ee6842b743bcc0 (identical) ✅

git hash-object docs/planning/PATCHSET_PLAN_345.md docs/general/PATCHSET_PLAN_345.md
# Result: 16e1603ee0106d43bc17e42044169bf1d30ae5c8 (identical) ✅

git hash-object docs/team/HANDOVERS_TO_TEAM_A.md docs/general/HANDOVERS_TO_TEAM_A.md
# Result: 14a69d7ec06a9a901c635a08811fe54839058f66 (identical) ✅

# Size and hash check for ORCHESTRATOR_PACK_144.md
wc -c docs/orchestrator/ORCHESTRATOR_PACK_144.md meta/legacy/ORCHESTRATOR_PACK_144.md
# Result: 21039 vs 137 bytes (meta/legacy is just a pointer) ✅

# Content diff for MERGE candidates
diff -u knowledge/operating_rules/ci_cd/CI_PIPELINE_GUIDE.md docs/ci-cd/CI_PIPELINE_GUIDE.md
# Result: docs version is newer (2025-12-28) and more complete (6690b vs 1440b)

diff -u knowledge/operating_rules/ci_cd/TROUBLESHOOTING.md docs/ci-cd/TROUBLESHOOTING.md
# Result: docs version is much larger (6676b vs 1025b)
```
