# DOCS_MIGRATION_UNRESOLVED.md
**Created:** 2026-01-10
**Status:** Unresolved - Decision Required

---

## Unresolved Files (Kategorie E)

| Datei | Grund | Empfehlung |
|-------|-------|------------|
| `.worktree-config.md` | Config-Datei, unclear ob Doku | Behalten im Working Repo |
| `.worktree_backup_*.txt` | Temporäre Backup-Dateien | Löschen (gitignored) |
| `.pytest_cache/README.md` | Auto-generated Cache | Löschen (gitignored) |
| `services/*/requirements.txt` | Python Dependencies (Code) | Behalten im Working Repo |
| `services/*/README.md` (nicht gefunden) | Dateien existieren nicht im Source | Überspringen |

---

## Nicht gefundene Dateien (aus Mapping)

| Aus Mapping | Status |
|-------------|--------|
| `docs/analysis/HIGH_VOLTAGE_ANALYSIS_REPORT.md` | ✅ Kopiert |
| `docs/analysis/PROJECT_ANALYTICS.md` | ✅ Kopiert |
| `docs/services/WS_SERVICE_RUNBOOK.md` | ✅ Kopiert |
| `docs/services/PAPER_TRADING_ARCHITECTURE.md` | ✅ Kopiert |
| `docs/services/MEXC_MARKET_DATA_SPECIFICATION.md` | ✅ Kopiert |
| `docs/services/EXECUTION_SERVICE_STATUS.md` | ✅ Kopiert |
| `docs/decisions/K8S_BUDGET_DECISION.md` | ✅ Kopiert |
| `docs/decisions/MEXC_WEBSOCKET_V3_MIGRATION_DECISION.md` | ✅ Kopiert |
| `docs/infra/memory-backend-setup.md` | ✅ Kopiert |
| `docs/infra/MONITORING_ALERTING.md` | ✅ Kopiert |
| `docs/infra/TLS_SETUP.md` | ✅ Kopiert |
| `docs/infra/COMPOSE_LAYERS.md` | ✅ Kopiert |
| `docs/infra/TEST_OVERLAY_README.md` | ✅ Kopiert |
| `docs/security/INCIDENT_RESPONSE_PLAYBOOK.md` | ✅ Kopiert |
| `docs/security/PENETRATION_TEST_REPORT.md` | ✅ Kopiert |
| `docs/security/OWASP_TOP10_AUDIT.md` | ✅ Kopiert |
| `docs/testing/PERFORMANCE_BASELINES.md` | ✅ Kopiert |
| `docs/testing/FLAKY_LOG.md` | ✅ Kopiert |
| `docs/test_plans/issue_113_e2e_p0_test_plan.md` | ✅ Kopiert |
| `docs/ops/MONTHLY_MAINTENANCE.md` | ✅ Kopiert |
| `docs/audit/DETERMINISM_EVENT_ID_CONTRACT.md` | ✅ Kopiert |
| `docs/HANDOVERS_TO_TEAM_A.md` | ✅ Kopiert |
| `docs/PATCHSET_PLAN_345.md` | ✅ Kopiert |
| `docs/TEST_HARNESS_V1.md` | ✅ Kopiert |
| `knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md` | ✅ Kopiert |
| `knowledge/LIVE_TRADING_RUNBOOK.md` | ✅ Kopiert |
| `.agent_briefings/*.md` | ✅ Kopiert |
| `.github/ARCHITECTURE_ISSUE_144.md` | ✅ Kopiert |
| `.github/BRANCH_TRIAGE_2026-01-08.md` | ✅ Kopiert |
| `.github/pull_request_template.md` | ✅ Kopiert |
| `tools/README.md` | ✅ Kopiert |
| `tools/research/CDB_TOOL_INDEX.md` | ✅ Kopiert |
| `tools/enforce-root-baseline.README.md` | ✅ Kopiert |
| `infrastructure/scripts/discussion_pipeline/*.md` | ❌ Nicht im Source gefunden |
| `tests/README.md` | ✅ Kopiert |
| `tests/e2e/README.md` | ✅ Kopiert |
| `tests/fixtures/README.md` | ✅ Kopiert |
| `core/README.md` | ✅ Kopiert |
| `services/README.md` | ✅ Kopiert |
| `services/signal/README.md` | ✅ Kopiert |
| `services/risk/README.md` | ✅ Kopiert |
| `infrastructure/compose/README.md` | ✅ Kopiert |

---

## Entscheidung erforderlich

1. **`.worktree-config.md`** - Soll diese Config-Datei migriert werden oder im Working Repo bleiben?
2. **`services/*/requirements.txt`** - Diese sind Dependencies (Code), nicht Docs. Korrekt im Working Repo.
3. **`infrastructure/scripts/discussion_pipeline/*.md`** - Diese Dateien wurden nicht im Source gefunden. Existieren sie noch?
