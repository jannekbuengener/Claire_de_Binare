# WORKFLOW_Status_Update – AKTUELLER_STAND Auto-Refresh

## Ziel

Halte `AKTUELLER_STAND.md` konsistent mit:

- der real laufenden Infrastruktur (Docker-Services),
- den Monitoring-Daten (Prometheus/Grafana),
- den Backoffice-Dokumenten (Architektur, Risiko, Analysen).

Dieser Workflow wird vom Codex Orchestrator gesteuert und läuft in zwei Phasen: Analyse → Delivery.

---

## Preconditions

- CDB-Docker-Stack läuft (Postgres, Redis, Services, Prometheus, Grafana).
- Docker MCP Gateway aktiv mit:
  - `filesystem`
  - `playwright`
  - `agents-sync`
  - `github-official`
  - `cdb-logger`

---

## Phase A – Analyse (read-only)

1. Governance & Template laden
   - `agents-sync.get_workflow("Status_Update")` (optional, meta).
   - `filesystem.read_file`:  
     - `AKTUELLER_STAND.md`  
     - `PROJEKT_BESCHREIBUNG.md`  
     - ggf. weitere relevante Backoffice-Dokumente.
2. Monitoring & Metriken
   - `playwright`:
     - öffnet Grafana (`http://localhost:3000`),
     - liest/analysiert relevante Panels (System Health, Trading Performance, Risk).
   - Optional: Prometheus-Metriken (`http://localhost:9090`) als Textquelle.
3. Gap-Analyse
   - Orchestrator identifiziert:
     - veraltete Einträge,
     - fehlende Services/Metriken,
     - Diskrepanzen zwischen Doku und aktuellem Zustand.
4. Logging
   - `cdb-logger.log_event` – `STATUS_UPDATE_ANALYSIS_STARTED` / `..._COMPLETED`.
5. Output
   - Analyse-Report im Standardformat mit:
     - Ist-Zustand (Doku),
     - Ist-Zustand (real),
     - Abweichungen,
     - geplanter Update-Plan (Change-Plan).

---

## Phase B – Delivery (nach Freigabe)

1. Branching
   - Branch-Namen: `status-update-YYYYMMDD`.
   - `github-official` – Branch von `main` erstellen.
2. Änderungen anwenden
   - `filesystem.write_file`:
     - Aktualisierung von `AKTUELLER_STAND.md` gemäß Change-Plan.
   - Optional: weitere Doku-Files (z. B. Ergänzungen in PROJEKT_BESCHREIBUNG).
3. Commit & PR
   - `github-official`:
     - Commit mit klarer Message (z. B. „Update AKTUELLER_STAND via MCP Status Workflow“).
     - PR Richtung `main` mit:
       - Kurzbeschreibung,
       - Referenz auf Analyse-Report,
       - Risiken/Offene Punkte.
4. Logging
   - `cdb-logger.log_event` – `STATUS_UPDATE_PR_CREATED` + PR-URL.

---

## Erfolgsindikatoren

- `AKTUELLER_STAND.md` spiegelt Services, Tests, Monitoring realistisch wider.
- PR ist sauber strukturiert und referenziert Analyse-Report.
- DECISION_LOG beinhaltet Eintrag zum Status-Update.
