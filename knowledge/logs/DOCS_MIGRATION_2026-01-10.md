# DOCS_MIGRATION_2026-01-10.md
**Date:** 2026-01-10
**Migration:** Working Repo → Docs Hub
**Status:** Complete

---

## Summary

| Metric | Count |
|--------|-------|
| Files Moved (Kategorie B) | ~60 |
| Pointers Created (Kategorie C) | 1 |
| Unresolved (Kategorie E) | 5 |

---

## Moved Files (Kategorie B)

### Onboarding
| Source | Target |
|--------|--------|
| `docs/ONBOARDING_QUICK_START.md` | `docs/onboarding/QUICK_START.md` |

### Operations
| Source | Target |
|--------|--------|
| `docs/EMERGENCY_STOP_SOP.md` | `docs/operations/EMERGENCY_STOP_SOP.md` |
| `docs/STACK_LIFECYCLE.md` | `docs/operations/STACK_LIFECYCLE.md` |
| `docs/TRADING_MODES.md` | `docs/operations/TRADING_MODES.md` |
| `docs/TESTNET_SETUP.md` | `docs/operations/TESTNET_SETUP.md` |
| `docs/72H_SOAK_TEST_RUNBOOK.md` | `docs/operations/72H_SOAK_TEST_RUNBOOK.md` |
| `docs/MONTHLY_MAINTENANCE.md` | `docs/operations/MONTHLY_MAINTENANCE.md` |
| `docs/360-SYSTEMCHECK.md` | `docs/operations/360_SYSTEMCHECK.md` |

### Security
| Source | Target |
|--------|--------|
| `docs/SECURITY_HARDENING.md` | `docs/security/SECURITY_HARDENING.md` |
| `docs/security/CONTAINER_HARDENING.md` | `docs/security/CONTAINER_HARDENING.md` |
| `docs/security/SECURITY_BASELINE.md` | `docs/security/SECURITY_BASELINE.md` |
| `docs/security/POSTGRES_HARDENING.md` | `docs/security/POSTGRES_HARDENING.md` |
| `docs/security/AUDIT_TRAIL.md` | `docs/security/AUDIT_TRAIL.md` |

### Services
| Source | Target |
|--------|--------|
| `docs/services/WS_SERVICE_RUNBOOK.md` | `docs/services/WS_SERVICE_RUNBOOK.md` |
| `docs/services/PAPER_TRADING_ARCHITECTURE.md` | `docs/services/PAPER_TRADING_ARCHITECTURE.md` |
| `docs/services/MEXC_MARKET_DATA_SPECIFICATION.md` | `docs/services/MEXC_MARKET_DATA_SPECIFICATION.md` |
| `docs/services/EXECUTION_SERVICE_STATUS.md` | `docs/services/EXECUTION_SERVICE_STATUS.md` |

### Infrastructure
| Source | Target |
|--------|--------|
| `docs/infra/memory-backend-setup.md` | `docs/infra/memory-backend-setup.md` |
| `docs/infra/MONITORING_ALERTING.md` | `docs/infra/MONITORING_ALERTING.md` |
| `docs/infra/TLS_SETUP.md` | `docs/infra/TLS_SETUP.md` |
| `docs/infra/COMPOSE_LAYERS.md` | `docs/infra/COMPOSE_LAYERS.md` |

### Testing
| Source | Target |
|--------|--------|
| `docs/testing/markers.md` | `docs/testing/markers.md` |
| `docs/testing/test_baseline.md` | `docs/testing/test_baseline.md` |
| `docs/testing/FLAKY_LOG.md` | `docs/testing/FLAKY_LOG.md` |
| `docs/test_plans/issue_113_e2e_p0_test_plan.md` | `docs/test_plans/issue_113_e2e_p0_test_plan.md` |

### Knowledge
| Source | Target |
|--------|--------|
| `knowledge/ISSUE_BUNDLING_ANALYSIS.md` | `knowledge/analysis/ISSUE_BUNDLING_ANALYSIS.md` |
| `knowledge/ISSUE_WORK_BLOCKS.md` | `knowledge/operations/ISSUE_WORK_BLOCKS.md` |
| `knowledge/SYSTEM.CONTEXT.md` | `knowledge/SYSTEM_CONTEXT.md` |
| `knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md` | `knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md` |
| `knowledge/LIVE_TRADING_RUNBOOK.md` | `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` |

### Agent Briefings
| Source | Target |
|--------|--------|
| `.agent_briefings/*.md` | `knowledge/agent_briefings/` |

### GitHub
| Source | Target |
|--------|--------|
| `.github/ARCHITECTURE_ISSUE_144.md` | `knowledge/issues/ARCHITECTURE_ISSUE_144.md` |
| `.github/BRANCH_TRIAGE_2026-01-08.md` | `knowledge/issues/BRANCH_TRIAGE_2026-01-08.md` |
| `.github/pull_request_template.md` | `knowledge/templates/pull_request_template.md` |

### Tools
| Source | Target |
|--------|--------|
| `tools/README.md` | `docs/tools/README.md` |
| `tools/research/CDB_TOOL_INDEX.md` | `docs/tools/INDEX.md` |
| `tools/enforce-root-baseline.README.md` | `docs/tools/enforce-root-baseline.md` |

### Tests
| Source | Target |
|--------|--------|
| `tests/README.md` | `docs/testing/README.md` |
| `tests/e2e/README.md` | `docs/testing/e2e/README.md` |
| `tests/fixtures/README.md` | `docs/testing/fixtures/README.md` |

### Core/Services
| Source | Target |
|--------|--------|
| `core/README.md` | `docs/core/README.md` |
| `services/README.md` | `docs/services/README.md` |
| `services/signal/README.md` | `docs/services/signal/README.md` |
| `services/risk/README.md` | `docs/services/risk/README.md` |

---

## Pointers Created (Kategorie C)

| Source | Target | Action |
|--------|--------|--------|
| `knowledge/governance/SERVICE_CATALOG.md` | `knowledge/governance/SERVICE_CATALOG.md` | Pointer created, source replaced |

---

## Unresolved (Kategorie E)

| Datei | Grund | Status |
|-------|-------|--------|
| `.worktree-config.md` | Config, unclear | Decision required |
| `.worktree_backup_*.txt` | Backup, temporär | Decision required |
| `.pytest_cache/README.md` | Auto-generated | Decision required |
| `services/*/requirements.txt` | Code Dependencies | Keep in Working Repo |
| `infrastructure/scripts/discussion_pipeline/*.md` | Not found in source | Decision required |

---

## Working Repo Changes

### Files Removed
- All Kategorie B files moved to Docs Hub
- `knowledge/governance/SERVICE_CATALOG.md` replaced with pointer

### Files Added
- `mapping/DOCS_MIGRATION_MAP.md`
- `mapping/DOCS_MIGRATION_UNRESOLVED.md`

---

## References

- Work Order: `D:\Dev\Workspaces\Prompts\OPENCODE\OPENCODE_WORK_ORDER_DOCS_MIGRATION.md`
- Mapping: `mapping/DOCS_MIGRATION_MAP.md`
- Unresolved: `mapping/DOCS_MIGRATION_UNRESOLVED.md`
