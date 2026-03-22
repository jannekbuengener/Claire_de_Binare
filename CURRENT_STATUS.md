# Current Status

**Status Class**: Working Repo / Engineering Status
**Authority**: Current repo/main/test/dependency snapshot; not the canonical live-readiness or Echtgeld Go/No-Go source.
**Operational Canon**: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
**Last Updated**: 2026-03-22 (Session 3)
**Latest Commit**: df169f4

---

## Repo / Engineering Status (2026-03-22)

- **main**: green, 4 open PRs
- **Commits seit letztem Update (2026-02-21)**: ~246
- **Open PRs**:
  - #1237: LR-040 runtime env prep (verdict anchor)
  - #1217: fix(digest): auto-close weekly digest
  - #1207: feat(market): V3 shadow mode — cdb_market write path
  - #1180: deps: ruff 0.15.6 bump
- **Merged (Session 3, 2026-03-22)**: #1226 P5 prestart normalization (df169f4)

---

## Live-Readiness Phase Status (Stand 2026-03-22)

| Phase | LR-Tasks | Status | Aenderung seit 2026-02-21 |
|---|---|---|---|
| P0 Preconditions | LR-001..003 | DONE | unveraendert |
| P1 Deterministic Tests | LR-010, LR-011, LR-012 | PARTIAL | LR-010 PASS evidenced (#1223); LR-012 execution hardened (#1247) |
| P2 E2E + Replay | LR-020, LR-021 | DONE | LR-020 STATE.yaml = DONE (#1190); Tier-2 FILLED, Decimal qty fix |
| P3 Shadow Mode | LR-030, LR-031 | PARTIAL | LR-031 IMPLEMENTED nach kalibriertem PASS (#1186); LR-030 evidence gehaertet (#1129) |
| P4 Soak + Chaos | LR-040, LR-041, LR-042 | PARTIAL | LR-041 redis/postgres drill added (#1130); LR-042 metric fix (#1131); LR-040 gate evaluator + evidence docs (#1133) — LR-040 runtime-Prep PR #1237 offen |
| P5 Canary Echtgeld | LR-050 | OPEN | Prestart-Normalisierung PR #1226 offen; Human Gate noch nicht erteilt |

**Operative Gesamtverdikt: NO-GO** (unveraendert — P1/P3/P4 noch nicht vollstaendig, P5 Human Gate ausstehend)

---

## Wesentliche Aenderungen seit 2026-02-21

### Live-Readiness
- LR-010: Evidence-Status auf PASS hochgestuft (PR #1223)
- LR-020: IMPLEMENTED / DONE — Tier-2 paper-trade flow mit FILLED-State, Decimal-qty-Fix, TRACE_CONTRACT_V1 (PR #1190)
- LR-031: Kalibrierung nach erstem Lean-Dry-Run, IMPLEMENTED-Status promoviert (PR #1186)
- LR-041: Deterministischer Redis/Postgres-Recovery-Drill hinzugefuegt (PR #1130)

### Operatives / Infra
- Kill-Switch: Shared State + E2E Smoke Test (PR #1198)
- Regime-Heartbeat: Verhindert stale regime_id -> RC_001-Block (PR #1218)
- cdb_market: Write-Ownership fuer market_state uebertragen, Service in BLUE Stack (PR #1203)
- Alerting: Circuit-Breaker-Alert-Chain repariert (#1220); neue Regeln High Error Rate + Orders Rejected (#1249, #1250)
- Makefile: docker-* Targets auf kanonischen BLUE/RED Pfad migriert (#1219)
- Backup: Automatisierungs-Runbook + SurrealDB-Drill (#1175, #1130)
- Governance: TODO/Placeholder-Lifecycle formalisiert (#1239)

### Observability / Grafana (2026-03-22)
- Dashboard-Footprint: 15 → 2 Dashboards (#1251, Commit 6bb4532)
  - entfernt: 13 ARCHIVED + 1 Platzhalter-Huelle (cdb_money_result_owner_v1)
  - verbleibend: `cdb_system_health_owner_v1` (Prometheus, nicht bereinigt), `cdb_trading_performance_v1` (neu, minimal)
- `cdb_trading_performance_v1.json`: Prometheus (system health, circuit breaker, kill switch, trade pipeline) + PostgreSQL (equity, daily PnL, realized PnL, equity curve)
- Publish-Kette geschlossen (#1255, Commit c26b08d): `paper_runner` publiziert jetzt stündlich (konfigurierbar) Portfolio-Snapshots auf Redis-Channel `portfolio_snapshots` → `db_writer` → PostgreSQL → Grafana
- CLAUDE.md im Repo-Root angelegt (Commit 1116275)
- Restunsicherheiten Observability:
  - `max_drawdown_pct` im Snapshot aktuell Platzhalter (0.0)
  - `cdb_system_health_owner_v1.json`: 43 Panels, viele Platzhalter — kein eigener Cleanup-Issue
  - `infrastructure/monitoring/grafana/DASHBOARD_IMPORT.md` veraltet

---

## Known Blockers / Next Actions

1. **LR-040 Verdict**: PR #1237 (Linux/WSL runtime prep) muss gemergt werden; dann deterministischer 72h-Soak-Lauf ausfuehren
2. **P5 Prestart**: PR #1226 reviewen/mergen (artifact contract normalization)
3. **LR-011**: State-machine-Test-Coverage noch offen (Issue #780)
4. **Human Gate**: Fuer P5/Canary explizit erforderlich — noch nicht erteilt

---

## Postmortem / Session Logs

- `knowledge/logs/sessions/` — aktuelle Session-Logs
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — operativer Live-Readiness-Verdict (letzte Reconciliation 2026-03-15)
