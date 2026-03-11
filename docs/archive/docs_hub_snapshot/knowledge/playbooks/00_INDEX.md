# Claire de Binare — Playbooks Index
Stand: 2025-12-25

## Zielbild
Diese Playbooks sind die **kannonische Betriebs- und Debug-Dokumentation** für reproduzierbare “Green States” (Golden Path) im Projekt **Claire de Binare**.

**Design Goals**
- In **< 10 Minuten** von “Repo geklont” zu “Stack läuft / Problem isoliert”.
- **Evidence-first**: Wire/Logs/DB-Beweise statt Bauchgefühl.
- **Copy/Paste Commands**: PowerShell-First (Windows 11).
- **Rollback immer**: Jeder Fix hat einen Rückweg.
- **DoD = Doku**: P0/P1-Änderungen aktualisieren mindestens ein Playbook.

## Inhalte
1. [01_STACK_GOLDEN_PATH.md](01_STACK_GOLDEN_PATH.md) — Canonical Start/Stop, Health Checks, Debug Tree
2. [02_SECURITY_BASELINE_AND_SCANS.md](02_SECURITY_BASELINE_AND_SCANS.md) — Baseline, Scans, Allowlist/Accept Risk
3. [03_DB_MIGRATIONS_AND_INIT.md](03_DB_MIGRATIONS_AND_INIT.md) — Postgres Init-Skripte, Migrations, Recovery, Drift-Prevention
4. [04_REDIS_WIRE_LEVEL_DEBUG.md](04_REDIS_WIRE_LEVEL_DEBUG.md) — Pub/Sub vs Keys, Streams, Proof Commands
5. [05_E2E_REGRESSION_SHIELD.md](05_E2E_REGRESSION_SHIELD.md) — #255: Teststrategie, CI-Integration, Failure Diagnostics
6. [99_PLAYBOOK_TEMPLATE.md](../templates/99_PLAYBOOK_TEMPLATE.md) — Vorlage für neue Playbooks

## Minimal-SLO (lokal)
**Green** bedeutet:
- `docker ps` zeigt Kernservices stabil (keine Crashloops)
- `order_results` ist Wire-level nachweisbar (Subscriber sieht Message)
- DB: `orders/trades` vorhanden und Inserts möglich (nach #254/#256)
- Security: Baseline dokumentiert, Scans laufen (keine NEW High/Critical in Custom Images)

## Konventionen
- **Golden State Referenz:** Commit-Hash + PR Link im Playbook/Issue.
- **Beweise:** immer mit Commands + erwarteten Outputs.
- **Schadensbegrenzung:** “Dev Reset” vs “Prod Apply” strikt trennen.
# CDB Runbooks Pack (2025-12-25)

## TL;DR
Dieses Paket friert den aktuellen **Green State** und die **kanonischen Operating Procedures** ein, damit wir bei langem Chat / Context-Compression sauber bleiben.

## Inhalt
1. `00_INDEX.md`
2. `01_CANONICAL_GOLDEN_STATE.md`
3. `02_STACK_GOLDEN_PATH_WINDOWS.md`
4. `03_DB_SCHEMA_INIT_AND_MIGRATIONS.md`
5. `04_E2E_SHIELD_AND_CI.md`
6. `05_REDIS_WIRE_LEVEL_DEBUG.md`
7. `06_DETERMINISTIC_REPLAY.md`
8. `07_RISK_GUARDS_DRAWDOWN_BREAKER.md`
9. `08_ISSUE_TRIAGE_BACKLOG_HYGIENE.md`
10. `09_BRANCHING_RELEASE_ROLLBACK.md`
11. `10_AUTOPILOT_AGENT_OPERATIONS.md`
12. `11_VERIFICATION_REPORT_230_226.md` (Snapshot aus deinem Report)

## Empfohlene Ablage (Repo)
- Code-Repo: `docs/runbooks/` (neu anlegen) **oder** `docs/playbooks/` (wenn das eure Konvention ist)
- Docs-Repo: `knowledge/playbooks/`

## Quick Install (PowerShell)
```powershell
# im Repo-Root
mkdir docs\runbooks -Force
# Inhalt dieses Packs nach docs\runbooks kopieren
git add -A
git commit -m "Docs: add runbooks pack (2025-12-25)"
git push
```
