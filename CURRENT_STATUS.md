# Current Status

**Status Class**: Working Repo / Engineering Status
**Authority**: Current repo/main/test/dependency snapshot; not the canonical live-readiness or Echtgeld Go/No-Go source.
**Operational Canon**: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
**Last Updated**: 2026-04-04
**Latest Main Commit**: d530a7ea — evidence(p5): committed P5-Core-Artefaktsatz mit LR-040 PASS (#1421) (#1432)
**Previous**: 55734fcd — chore(session): close session #24 — #1426 market healthcheck start_period (#1430)

---

## Repo / Engineering Status (2026-04-04)

- **main**: green
- **Open PRs (relevant/current focus)**:
  - #1431: chore(session): close session #24 — #1426 market healthcheck (likely superseded by #1430; to close after merge)
  - #1429: fix(soak): treat docker disk evidence as valid fallback (#1427)
  - #1375: docs: close #1374 #1373 #1372 (noch OPEN, faktisch supersediert)
  - #1285: fix(soak-monitor): use df -P (#1282)
  - #1237: LR-040 runtime env prep (BLOCKIERT)
  - #1217: fix(digest): auto-close weekly digest
  - #1207: feat(market): V3 shadow mode
  - **Merged (Session 3, 2026-03-22)**: #1226 P5 prestart normalization (df169f4)
  - **Merged (Session 4, 2026-03-22)**: #1257 fix(lr031): liveness floor min=1 (a407838)
  - **Merged (Session 5+6, 2026-03-24)**: #1270/#1271 (soak env_interruption/timeline), #1273 (batch soak+alerting fixes, af0f21e), #1274 (docs, ee29e99)
  - **Merged (Session 7, 2026-03-26)**: #1266/#1267 — execErrState: KeepLast fix (216d0eb), geschlossen 2026-03-27; #1282/#1283 disk-check + pointer robustness (08f7e7b), geschlossen 2026-03-27.
  - **Merged (Session 11, 2026-03-27)**: #1290 — .gitignore Δ1–Δ4 (5a50700), #1234 geschlossen.
  - **Merged (Session 12, 2026-03-29)**: #1359/#1360/#1361/#1362/#1363 — Sessions-README, Signal-Alerts-Claim, Monitoring-Terminologie, INV-006 `min_qty_sum`, historische Governance-Artefakte markiert.
  - **Merged (Session 13, 2026-03-30)**: #1370 — LR-007-Canon auf 72h-Validierungsfenster ausgerichtet (93daac4).
  - **Merged (Session 14, 2026-03-30)**: #1382/#1383/#1384/#1386 — BLUE+RED-Startup-Canon, Solo-Maintainer-SOPs, LR-BLACK-Stack-Terminologie und aktive Infra-Canon-Doku bereinigt.
  - **Merged (Session 15, 2026-03-30)**: #1389 — aktive Governance-/Risk-Terminologie auf `Risk Service` / `cdb_risk` vereinheitlicht (e48add6).
  - **Merged (Session 17, 2026-03-31)**: #1408 — Batch #1403–#1407: knowledge link drift + secrets helper legacy + contributor docs + test-pack entrypoints (c6a51cd). Issues #1403–#1407 geschlossen.
  - **Merged (Session 18, 2026-03-31)**: #1410 — Aktive Runbooks/Playbooks/Templates auf BLUE+RED Runtime-Canon bereinigt. 24 Dateien. PR #1415 (04b91d4b). Issue #1410 geschlossen.
  - **Merged (Session 19, 2026-03-31)**: #1411 — Aktive Secrets-/Runbook-/Evidence-Doku auf SECRETS_PATH-Canon gezogen. 21 Dateien. PR #1415 (04b91d4b). Issue #1411 geschlossen.
  - **Merged (Session 20, 2026-03-31)**: #1413 — Legacy-Ops-/Secrets-Pointer aus aktiven Discovery-Surfaces entfernt. 9 Dateien. PR #1415 (04b91d4b). Issue #1413 geschlossen.
  - **Merged (Session 21+22, 2026-03-31/04-01)**: #1412 — LR-AUDIT-STATUS / CURRENT_STATUS SSOT-Trennung bereinigt. Operative Phasentabelle aus CURRENT_STATUS.md entfernt; Rueckkopplung in LR-AUDIT-STATUS beseitigt; P-Phasen-Inline-Status aus AGENTS.md entfernt. PR #1414 (bb0c42c0). Issue #1412 geschlossen.
  - **Merged (Session 22, 2026-04-01)**: Git-Divergenz aufgeloest; PR-Batch #1414+#1415 durchgezogen; Issues #1410/#1411/#1412/#1413 geschlossen. PR #1416 (9f92651c).
  - **Merged (Session 23, 2026-04-01)**: #1409 — ARCHITECTURE_MAP + SERVICE_CATALOG gegen BLUE/RED-Runtime reconciled; Logging Overlay als separates Overlay klassifiziert; CDB_DOCKER_STACK_INVENTORY ergaenzt. PR #1416 (9f92651c). Issue #1409 geschlossen.
  - **Merged (Session 24, 2026-04-04)**: #1426 — cdb_market healthcheck start_period auf 30s. PR #1430 (55734fcd).
  - **Merged (Session 25, 2026-04-04)**: #1421/#1422 — P5-Core-Artefaktsatz mit LR-040 PASS + Live-Captures. PR #1432 (d530a7ea). Human Gate GRANTED. #1421 + #1422 geschlossen. #1423 freigestellt.

---

## Live-Readiness

Operatives Go/No-Go-Verdikt: **NO-GO** — Phasenstatus und Verdikt-Quelle ausschliesslich unter [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md). Diese Datei ist nicht die operative SSOT fuer Live-Readiness.

---

## Wesentliche Aenderungen seit 2026-02-21

### Live-Readiness
- LR-010: Evidence-Status auf PASS hochgestuft (PR #1223)
- LR-020: IMPLEMENTED / DONE — Tier-2 paper-trade flow mit FILLED-State, Decimal-qty-Fix, TRACE_CONTRACT_V1 (PR #1190)
- LR-007: Spezifikation/Status auf das kanonische 72h-Validierungsfenster ausgerichtet; alte 30d-Draft-Wording entfernt (PR #1370)
- LR-031: Threshold neu kalibriert auf min=1 (liveness floor, PR #1257 a407838); lean Run 23407946292 vollstaendig PASS (soak_gate + comparison + canonical package)
- LR-041: Deterministischer Redis/Postgres-Recovery-Drill hinzugefuegt (PR #1130)

### Operatives / Infra
- Kill-Switch: Shared State + E2E Smoke Test (PR #1198)
- Regime-Heartbeat: Verhindert stale regime_id -> RC_001-Block (PR #1218)
- cdb_market: Write-Ownership fuer market_state uebertragen, Service in BLUE Stack (PR #1203)
- Alerting: Circuit-Breaker-Alert-Chain repariert (#1220); neue Regeln High Error Rate + Orders Rejected (#1249, #1250)
- Makefile: docker-* Targets auf kanonischen BLUE/RED Pfad migriert (#1219)
- Backup: Automatisierungs-Runbook + SurrealDB-Drill (#1175, #1130)
- Governance: TODO/Placeholder-Lifecycle formalisiert (#1239)
- Aktive Runtime-Doku verweist jetzt konsistent auf `compose.blue.yml` + `compose.red.yml`; unqualifiziertes `docker compose up -d` und base/dev-Canon aus aktiven Artefakten entfernt (#1382, #1386)
- Incident-/Emergency-/CI-Dokumente auf Solo-Maintainer-Realitaet umgestellt; Mehrpersonen-Eskalationsketten aus aktiven SOPs entfernt (#1383)
- Obsolete `BLACK`-Terminologie aus aktiven Live-Readiness- und Governance-Artefakten entfernt; aktive Domain-Bezeichnung jetzt `Risk Service` / `cdb_risk` (#1384, #1389)

### Soak-Monitor + Alerting (2026-03-24, Session 6)

6 Issues in PR #1273 geschlossen:

- **#1268** (Regression-Tests): Bash-Octal-Parsing-Bug bei `%H`-Stunden 08/09 dokumentiert; 18 neue Tests in `TestOctalSafeScheduleChecks` (`test_soak_monitor_timeline.py`)
- **#1263** (Service-Health): SUT_SERVICES-Liste auf exakt 12 Services erweitert (BLUE core 8 + postgres/redis + ws/signal); `grep -qx` statt Broad-Filter
- **#1264** (Disk-Evidence): Check 5 nutzt `/repo` (mounted) statt `/var/lib/docker` (nicht gemountet) + `docker system df`; schreibt Disk-Evidence-Artifact pro Checkpoint
- **#1265** (Circuit-Breaker-Alert): `type: gte` → `type: gt`, `params: [1]` → `params: [0]` (binary metric semantisch äquivalent; `gte` war ungültiger Grafana-Operator → DatasourceError)
- **#1266** (Orders-Rejected-Alert): `execErrState: Error` → `execErrState: KeepLastState` (noisy DatasourceError-Mails während Prometheus-Restart unterdrückt)
- **#1267** (High-Error-Rate-Alert): `execErrState: Error` → `execErrState: KeepLastState` (gleicher Root Cause wie #1266)

Neue Testdatei: `tests/unit/scripts/test_grafana_alerting_provisioning.py` (21 Tests, 4 Klassen)
`test_soak_monitor_timeline.py`: 71 Tests total (+46 in dieser Session)

**Geschlossen**: #1269 (midnight-rollover UTC→MESZ) — Live-Evidence aus `soak_test_20260325_121250` bestätigt: beide UTC-Mitternachts-Grenzen (Hour 11 + Hour 35) ohne Fragmentierung oder Schedule-Misfire passiert. #1278 Pointer-Mechanismus wirksam (2026-03-27).

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

1. **#1277 (soak restart scope):** Gemerged (PR #1279, `b5486c9`). Check 1 auf 12 SUT-Services eingeschränkt; Non-SUT-Restarts nur INFO.
2. **#1278 (validation mode):** Gemerged (PR #1280, `ac6ab87`). Separater Artifact-Namespace, Pointer, `run_intent.txt`, Gate-Evaluator `NOT_APPLICABLE` für Validation Runs.
3. **LR-040 72h-Run abgeschlossen — PASS:** `artifacts/soak_test_20260401_114850/lr040_soak_gate_eval.json` — 72.19h, alle 8 Gate-Checks bestanden. Committed unter `reports/p5_canary/2026-04-04/lr040/`. PR #1432 gemergt (d530a7ea).
4. **#1282/#1283 (Disk-Check + generischer Pointer):** Gefixt (08f7e7b, 2026-03-26). `_write_active_run_path()` in `soak_monitor.sh` schreibt jetzt auch `soak_active_run_path.txt` für lr040 Runs; Validation-Runs unberührt. Disk-Check unterscheidet Command-Failure von Parse-Failure, schreibt Reason + Raw-Output in disk_evidence. +6 neue Regressionstests (4 Pointer-Sync, 2 Disk-Check).
5. **#1266/#1267 (Grafana execErrState):** Gefixt (216d0eb, 2026-03-26), geschlossen 2026-03-27. Root Cause: `KeepLastState` war nie ein gültiger Unified-Alerting-Wert; korrekt ist `KeepLast` (Grafana 10.4+/11.0+). Kein Image-Upgrade nötig. Beide Alert-Regeln und Tests aktualisiert.
6. **#1269 (midnight-rollover):** Geschlossen (2026-03-27). Live-Evidence aus `soak_test_20260325_121250`: beide UTC-Mitternachts-Grenzen (Hour 11 @ 2026-03-26 00:00, Hour 35 @ 2026-03-27 00:00) ohne Fragmentierung passiert. #1278 Pointer-Mechanismus bestätigt wirksam. Hour-29-Lücke = bekannte Umgebungsunterbrechung (2026-03-26 18:00 UTC). Formales Gate-Ergebnis: INCONCLUSIVE (s. Eintrag 3).
7. **Grafana circuit_breaker alert aktiv:** Sendet gerade Alerts (laut Log), da circuit_breaker_active evaluiert wird. Normal — kein Blocker.
8. **LR-011:** State-machine-Test-Coverage noch offen (Issue #780).
9. **Human Gate:** GRANTED (2026-04-04). GO fuer naechsten kontrollierten P5-Shadow-/Stabilitaetsschritt. Keine Live-Aktivierung, keine Produktionsfreigabe.
10. **#1375:** Offene Sammel-PR ist durch die Einzelmerges #1383/#1384/#1386 fachlich ueberholt; entscheiden, ob schliessen oder sauber neu ausrichten.

---

## Postmortem / Session Logs

- `knowledge/logs/sessions/` — aktuelle Session-Logs
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — operativer Live-Readiness-Verdict (letzte Reconciliation 2026-03-29, #1306)
