# OPENCODE_WORK_ORDER — Docs-Migration (Working Repo → Doku-Repo) v2

**Datum:** 2026-01-10  
**Basis:** `DOCS_MIGRATION_MAP.md` (Mapping ist SOT für diese Migration)

## Ziel
Alle Doku-Artefakte aus `D:\Dev\Workspaces\Repos\Claire_de_Binare` ins Doku-Repo `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs` überführen. Working Repo bleibt „code-first“.

## Vorgehen (konkret)
1) **Mapping anwenden (ohne Kreativität):**
   - **Kategorie B:** Move nach Zielpfad (Docs Repo)
   - **Kategorie C:** Canon existiert → **Pointer im Working Repo**, Quelle entfernen
   - **Kategorie D:** bleibt im Working Repo
   - **Kategorie E:** nicht anfassen → als „unresolved“ loggen

2) **Moves sauber versionieren:**
   - Commit im **Docs Repo**: `docs: import documentation from working repo`
   - Commit im **Working Repo**: `chore(docs): remove migrated docs; add pointers`

3) **Pointer-Template (Working Repo)**
```md
# <Titel>
**Moved:** Canon liegt im Doku-Repo: `../Claire_de_Binare_Docs/<zielpfad>`
```

4) **Link-Fix**
- Nach dem Move: relative Links in Docs Repo reparieren (`git grep -n "](" -- "*.md"`)

5) **Evidence**
- `knowledge/logs/DOCS_MIGRATION_2026-01-10.md` im Docs Repo:
  - moved (src→dst)
  - pointers (src→canon)
  - unresolved (E) + Grund

## Mapping (SOT)
# DOCS_MIGRATION_MAP.md
**Created:** 2026-01-10
**Source:** `D:\Dev\Workspaces\Repos\Claire_de_Binare`
**Target:** `D:\Dev\Workspaces\Repos\Claire_de_Binare_Docs`

---

## Kategorisierung

### KATEGORIE A: bereits migriert (Pointer im Working Repo)

| Working Repo | Docs Repo Ziel | Status |
|--------------|----------------|--------|
| `AGENTS.md` | `agents/AGENTS.md` | Pointer |
| `knowledge/CURRENT_STATUS.md` | `knowledge/CURRENT_STATUS.md` | Canon |

---

### KATEGORIE B: Migrieren (Move zu Docs Repo)

| Quelle (Working) | Ziel (Docs Repo) | Begründung |
|------------------|------------------|------------|
| `docs/ONBOARDING_QUICK_START.md` | `docs/onboarding/QUICK_START.md` | Onboarding |
| `docs/ONBOARDING_LINKS.md` | `docs/onboarding/LINKS.md` | Onboarding |
| `docs/SETUP_GUIDE.md` | `docs/onboarding/SETUP_GUIDE.md` | Onboarding |
| `docs/CONTRACTS.md` | `docs/contracts/CONTRACTS.md` | Contracts |
| `docs/contracts/README.md` | `docs/contracts/README.md` | Contracts |
| `docs/contracts/MIGRATION.md` | `docs/contracts/MIGRATION.md` | Contracts |
| `docs/contracts/REPLAY_CONTRACT.md` | `docs/contracts/REPLAY_CONTRACT.md` | Contracts |
| `docs/HEALTH_CONTRACT.md` | `docs/contracts/HEALTH_CONTRACT.md` | Contracts |
| `docs/EMERGENCY_STOP_SOP.md` | `docs/operations/EMERGENCY_STOP_SOP.md` | Operations |
| `docs/STACK_LIFECYCLE.md` | `docs/operations/STACK_LIFECYCLE.md` | Operations |
| `docs/TRADING_MODES.md` | `docs/operations/TRADING_MODES.md` | Operations |
| `docs/runbook_papertrading.md` | `knowledge/operating_rules/runbook_papertrading.md` | Ops/Runbook |
| `docs/HITL_RUNBOOK.md` | `knowledge/operating_rules/HITL_RUNBOOK.md` | Ops/Runbook |
| `docs/HITL_METRICS_MAPPING.md` | `knowledge/operating_rules/HITL_METRICS_MAPPING.md` | Ops |
| `docs/TESTNET_SETUP.md` | `docs/operations/TESTNET_SETUP.md` | Operations |
| `docs/72H_SOAK_TEST_RUNBOOK.md` | `docs/operations/72H_SOAK_TEST_RUNBOOK.md` | Ops/Runbook |
| `docs/SECURITY_HARDENING.md` | `docs/security/SECURITY_HARDENING.md` | Security |
| `docs/security/CONTAINER_HARDENING.md` | `docs/security/CONTAINER_HARDENING.md` | Security |
| `docs/security/SECURITY_BASELINE.md` | `docs/security/SECURITY_BASELINE.md` | Security |
| `docs/security/POSTGRES_HARDENING.md` | `docs/security/POSTGRES_HARDENING.md` | Security |
| `docs/security/INCIDENT_RESPONSE_PLAYBOOK.md` | `knowledge/operating_rules/security/INCIDENT_RESPONSE_PLAYBOOK.md` | Security/Runbook |
| `docs/security/AUDIT_TRAIL.md` | `docs/security/AUDIT_TRAIL.md` | Security |
| `docs/security/PENETRATION_TEST_REPORT.md` | `docs/security/PENETRATION_TEST_REPORT.md` | Security |
| `docs/security/OWASP_TOP10_AUDIT.md` | `docs/security/OWASP_TOP10_AUDIT.md` | Security |
| `docs/HIGH_VOLTAGE_ANALYSIS_REPORT.md` | `docs/analysis/HIGH_VOLTAGE_ANALYSIS_REPORT.md` | Analysis |
| `docs/PROJECT_ANALYTICS.md` | `docs/analysis/PROJECT_ANALYTICS.md` | Analysis |
| `docs/observability/GRAFANA_DASHBOARDS.md` | `docs/observability/GRAFANA_DASHBOARDS.md` | Observability |
| `docs/infra/MONITORING_ALERTING.md` | `docs/infra/MONITORING_ALERTING.md` | Infra |
| `docs/infra/memory-backend-setup.md` | `docs/infra/memory-backend-setup.md` | Infra |
| `docs/infrastructure/tls/TLS_SETUP.md` | `docs/infra/TLS_SETUP.md` | Infra |
| `docs/infrastructure/compose/COMPOSE_LAYERS.md` | `docs/infra/COMPOSE_LAYERS.md` | Infra |
| `docs/infrastructure/compose/TEST_OVERLAY_README.md` | `docs/infra/TEST_OVERLAY_README.md` | Infra |
| `docs/services/WS_SERVICE_RUNBOOK.md` | `docs/services/WS_SERVICE_RUNBOOK.md` | Services |
| `docs/services/PAPER_TRADING_ARCHITECTURE.md` | `docs/services/PAPER_TRADING_ARCHITECTURE.md` | Services |
| `docs/services/MEXC_MARKET_DATA_SPECIFICATION.md` | `docs/services/MEXC_MARKET_DATA_SPECIFICATION.md` | Services |
| `docs/services/EXECUTION_SERVICE_STATUS.md` | `docs/services/EXECUTION_SERVICE_STATUS.md` | Services |
| `docs/decisions/K8S_BUDGET_DECISION.md` | `knowledge/decisions/K8S_BUDGET_DECISION.md` | Decisions |
| `docs/decisions/MEXC_WEBSOCKET_V3_MIGRATION_DECISION.md` | `knowledge/decisions/MEXC_WEBSOCKET_V3_MIGRATION_DECISION.md` | Decisions |
| `docs/testing/markers.md` | `docs/testing/markers.md` | Testing |
| `docs/testing/test_baseline.md` | `docs/testing/test_baseline.md` | Testing |
| `docs/testing/PERFORMANCE_BASELINES.md` | `knowledge/testing/PERFORMANCE_BASELINES.md` | Testing |
| `docs/testing/FLAKY_LOG.md` | `docs/testing/FLAKY_LOG.md` | Testing |
| `docs/test_plans/issue_113_e2e_p0_test_plan.md` | `docs/test_plans/issue_113_e2e_p0_test_plan.md` | Testing |
| `docs/workflows/FEATURE_WORKFLOW.md` | `docs/workflows/FEATURE_WORKFLOW.md` | Workflows |
| `docs/workflows/ISSUE_GENERATION_RULES.md` | `docs/workflows/ISSUE_GENERATION_RULES.md` | Workflows |
| `docs/ops/MONTHLY_MAINTENANCE.md` | `docs/operations/MONTHLY_MAINTENANCE.md` | Operations |
| `docs/audit/DETERMINISM_EVENT_ID_CONTRACT.md` | `docs/audit/DETERMINISM_EVENT_ID_CONTRACT.md` | Audit |
| `docs/HANDOVERS_TO_TEAM_A.md` | `docs/team/HANDOVERS_TO_TEAM_A.md` | Team |
| `docs/PATCHSET_PLAN_345.md` | `docs/planning/PATCHSET_PLAN_345.md` | Planning |
| `docs/TEST_HARNESS_V1.md` | `docs/testing/TEST_HARNESS_V1.md` | Testing |
| `docs/CI_CHECKS.md` | `docs/ci/CI_CHECKS.md` | CI |
| `docs/360-SYSTEMCHECK.md` | `docs/operations/360_SYSTEMCHECK.md` | Operations |
| `docs/ORCHESTRATOR_PACK_144.md` | `docs/orchestrator/ORCHESTRATOR_PACK_144.md` | Orchestrator |
| `knowledge/ISSUE_BUNDLING_ANALYSIS.md` | `knowledge/analysis/ISSUE_BUNDLING_ANALYSIS.md` | Analysis |
| `knowledge/ISSUE_WORK_BLOCKS.md` | `knowledge/operations/ISSUE_WORK_BLOCKS.md` | Operations |
| `knowledge/SYSTEM.CONTEXT.md` | `knowledge/SYSTEM_CONTEXT.md` | System |
| `knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md` | `knowledge/roadmap/EXPANDED_ECOSYSTEM_ROADMAP.md` | Roadmap |
| `knowledge/LIVE_TRADING_RUNBOOK.md` | `knowledge/operating_rules/LIVE_TRADING_RUNBOOK.md` | Runbook |
| `.agent_briefings/*.md` | `knowledge/agent_briefings/` | Agent Briefings |
| `.github/ARCHITECTURE_ISSUE_144.md` | `knowledge/issues/ARCHITECTURE_ISSUE_144.md` | Issues |
| `.github/BRANCH_TRIAGE_2026-01-08.md` | `knowledge/issues/BRANCH_TRIAGE_2026-01-08.md` | Issues |
| `.github/pull_request_template.md` | `knowledge/templates/pull_request_template.md` | Templates |
| `tools/README.md` | `docs/tools/README.md` | Tools |
| `tools/research/CDB_TOOL_INDEX.md` | `docs/tools/INDEX.md` | Tools |
| `tools/enforce-root-baseline.README.md` | `docs/tools/enforce-root-baseline.md` | Tools |
| `infrastructure/scripts/discussion_pipeline/*.md` | `knowledge/discussion_pipeline/` | Discussion Pipeline |
| `tests/README.md` | `docs/testing/README.md` | Testing |
| `tests/e2e/README.md` | `docs/testing/e2e/README.md` | Testing |
| `tests/fixtures/README.md` | `docs/testing/fixtures/README.md` | Testing |
| `core/README.md` | `docs/core/README.md` | Core |
| `services/README.md` | `docs/services/README.md` | Services |
| `services/signal/README.md` | `docs/services/signal/README.md` | Services |
| `services/risk/README.md` | `docs/services/risk/README.md` | Services |
| `services/ws/README.md` | `docs/services/ws/README.md` | Services |
| `services/execution/README.md` | `docs/services/execution/README.md` | Services |
| `services/regime/README.md` | `docs/services/regime/README.md` | Services |
| `services/allocation/README.md` | `docs/services/allocation/README.md` | Services |
| `services/candles/README.md` | `docs/services/candles/README.md` | Services |
| `services/market/README.md` | `docs/services/market/README.md` | Services |
| `infrastructure/compose/README.md` | `docs/infra/compose/README.md` | Infra |
| `k8s/README.md` | `docs/k8s/README.md` | K8s |
| `cdb_agent_sdk/README.md` | `docs/sdk/README.md` | SDK |

---

### KATEGORIE C: Pointer (Canon existiert bereits)

| Working Repo | Docs Repo Canon | Aktion |
|--------------|-----------------|--------|
| `knowledge/governance/SERVICE_CATALOG.md` | `knowledge/governance/SERVICE_CATALOG.md` | Pointer + remove source |

---

### KATEGORIE D: Im Working Repo behalten (Code-bezogen)

| Grund |
|-------|
| `README.md` - Projekt-Root-Readme (bleibt) |
| `CODE_OF_CONDUCT.md` - Projekt-Standard |
| `CONTRIBUTING.md` - Projekt-Standard |
| `governance/SECRETS_POLICY.md` - Out-of-Scope (Canon-ähnlich) |
| `LICENSE` - Projekt-Standard |

---

### KATEGORIE E: Unklar / Nicht eindeutig (Entscheidung nötig)

| Datei | Grund |
|-------|-------|
| `.worktree-config.md` | Config, nicht sicher |
| `.worktree_backup_*.txt` | Backup, temporär |
| `.pytest_cache/README.md` | Auto-generated |
| `services/*/requirements.txt` | Code-Dependencies |

---

## Zusammenfassung

| Kategorie | Anzahl |
|-----------|--------|
| Kategorie B (Migrieren) | ~75 |
| Kategorie C (Pointer) | ~1 |
| Kategorie D (Behalten) | ~5 |
| Kategorie E (Entscheidung nötig) | ~5 |

---

## Nächste Schritte

1. **Genehmigung:** Mapping prüfen und freigeben
2. **Move:** Kategorie B migrieren
3. **Pointer:** Kategorie C als Pointer ersetzen
4. **Cleanup:** Kategorie E klären

