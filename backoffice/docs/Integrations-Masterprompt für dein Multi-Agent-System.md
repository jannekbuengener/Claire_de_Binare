# PROMPT 5 – MCP- / CDB-STACK INTEGRATION (AKTUELLE VERSION)

Ziel dieses Dokuments:
- Definiert den Betriebsmodus, in dem der Claire-de-Binare-Docker-Stack und der MCP-Gateway parallel laufen.
- Legt einen einfachen Start-Flow fest (zwei Hauptschritte), nach denen die Umgebung für Agenten und Workflows nutzbar ist.
- Beschreibt drei selbstoptimierende Workflows (WF1–WF3), abgestimmt auf die aktuelle CDB-Governance, -Workflows und -Architektur.

Dieses Dokument ist Teil der technischen und operativen Basis von Claire de Binare und gehört in `backoffice/docs`.

---

## 1. Scope & Rahmenbedingungen

### 1.1 Systemkontext (Stand aktuell)

Die Beschreibung orientiert sich an den kanonischen Grundlagen in `CDB_FOUNDATION.md`, `CDB_GOVERNANCE.md` und `CDB_WORKFLOWS.md`:

- Architektur: Event-getriebener Trading-Stack mit Microservices, Redis-Pub/Sub und PostgreSQL.
- Betrieb: Lokales Setup unter Windows 10/11 mit Docker Desktop (WSL2 Backend). 
- Governance: Session Lead orchestriert alle Workflows; klare Trennung von Analyse- und Delivery-Mode.
- Cleanroom-Prinzip: Canonical Docs liegen unter `backoffice/docs`.

### 1.2 Ziele von Prompt 5 (aktualisiert)

1. Parallelbetrieb von:
   - **CDB-Docker-Stack** (Trading-Infrastruktur)
   - **MCP-Gateway + MCP-Servern** (Agenten- und Tool-Zugriff)
2. Klare Startsequenz:
   - Schritt 1: CDB-Stack hochfahren
   - Schritt 2: MCP-Gateway starten
3. Definition von drei **selbstoptimierenden Workflows**:
   - WF1: „AKTUELLER_STAND Auto-Refresh“
   - WF2: „Handelsfrequenz & Signalqualität-Tuning“
   - WF3: „Agenten-Governance & DECISION_LOG Pflege“
4. Einbettung in die **Supervisor- und Governance-Protokolle** aus `CDB_WORKFLOWS.md` und `CDB_GOVERNANCE.md`.

---

## 2. Betriebsmodi und Komponenten

### 2.1 CDB-Stack (Trading-Infrastruktur)

Services (gemäß technischer Grundlage):

- `cdb_redis` – Message Bus / Cache
- `cdb_postgres` – Persistence für Orders/Trades/Events
- `cdb_ws` – Daten-Ingestion (WebSocket)
- `cdb_core` – Signal Engine
- `cdb_risk` – Risk Engine
- `cdb_execution` – Execution (Paper-Mode in Phase N1)
- `cdb_prometheus` – Metrics
- `cdb_grafana` – Dashboards

Legacy-/Ghost-Services (`cdb_rest`, `cdb_signal_gen`) gelten explizit als **deaktiviert** bzw. zu bereinigen und sind in diesem Prompt nicht mehr Teil des Sollzustands.

### 2.2 MCP-Stack (Tool- und Agenten-Zugriff)

MCP-Server (Docker-basiert, Beispielkonfiguration):

- `filesystem`  
  - Zugriff auf Repo und Backoffice-Dokumente, u. a.  
    - `C:\Users\janne\Documents\Claire_de_Binare`
    - `C:\Users\janne\mcp_servers\logs`
- `github-official`  
  - Zugriff auf Branches, PRs, Dateien (GitHub API)
- `playwright`  
  - Browser-Automation für:
    - Prometheus: `http://localhost:19090` bzw. `http://localhost:9090`
    - Grafana: `http://localhost:3000`
- `agents-sync`  
  - Zugriff auf Agenten- und Workflow-Metadaten aus `AGENTS.md` und weiteren Governance-/Workflow-Dateien.
- `cdb-logger`  
  - Domänenspezifische Log-Events (Agents, Repo, Trading, Governance).

### 2.3 Rollenmodell (Abgleich mit Governance)

- **Level 0 – User**: Letzte Entscheidungsinstanz, definiert Ziele, gibt Freigaben.
- **Level 1 – Session Lead**:  
  - Single Voice zum User, Orchestrator für Workflows.  
  - Aktiviert Supervisor Protocol aus `CDB_WORKFLOWS.md`.  
  - Darf Agenten-Rollen (Level 3) annehmen und Peer-Modelle konsultieren.
- **Level 2 – Peer Models**: Gemini, Copilot, Codex etc. – liefern Analysen, aber keine direkten Aktionen.
- **Level 3 – Agents**: Spezialisierte Rollen aus `AGENTS.md` (z. B. `system-architect`, `risk-architect`, `project-visionary`).

Prompt 5 definiert **keinen eigenen Governance-Layer**, sondern nutzt die bestehende Verfassung (`CDB_GOVERNANCE.md`) und ordnet CDB-/MCP-Stack und Workflows dort ein.

---

## 3. Start-Flow der Gesamtsysteme

### 3.1 Schritt 1 – CDB-Stack starten

In PowerShell im Projektordner:

```powershell
cd C:\Users\janne\Documents\Claire_de_Binare

# Full Trading-Stack hochfahren (Phase N1 – Paper Trading)
docker compose up -d
```

Healthcheck (Option, nicht Pflicht):

```powershell
curl http://localhost:8000/health    # cdb_ws
curl http://localhost:8001/health    # cdb_core
curl http://localhost:8002/health    # cdb_risk
curl http://localhost:8003/health    # cdb_execution
```

Monitoring-URLs (wichtig für MCP/Playwright):

- Prometheus: `http://localhost:19090` oder `http://localhost:9090`
- Grafana: `http://localhost:3000`

### 3.2 Schritt 2 – MCP-Stack aktivieren

Voraussetzung:  
- MCP-Server sind im Docker-MCP-Toolkit definiert und aktiviert.
- Gateway-Konfiguration liegt vor (inkl. Server-Liste, Policies).

Kurz-Check der verfügbaren Server:

```powershell
docker mcp server list
```

Erwartete Server (Mindestsatz):
- `filesystem`
- `github-official`
- `playwright`
- `agents-sync`
- `cdb-logger`

Gateway starten (Beispiel):

```powershell
docker mcp gateway run `
  --log-calls `
  --verify-signatures `
  --block-secrets
```

Ab diesem Zeitpunkt gilt:

- Der Trading-Stack ist betriebsbereit (Paper-Modus).
- Der MCP-Gateway stellt Tools/Server für alle Clients bereit.
- IDEs / Chat-Clients (ChatGPT, Claude, Cursor, etc.) sprechen **nur** mit dem MCP-Gateway.

---

## 4. Selbstoptimierende Workflows (WF1–WF3)

Diese Workflows sind **Agenten-getriebene Automationen**, die in das Supervisor-Protocol aus `CDB_WORKFLOWS.md` eingebettet sind:

- Start: immer **Analysis Mode**
- Plan: Analyse-Report + Vorschlag
- Gate: explizite User-Freigabe (Decision Gate)
- Delivery: nach „mach den Job fertig“ / „go“ durch Session Lead

### 4.1 WF1 – „AKTUELLER_STAND Auto-Refresh“

**Zweck**  
`AKTUELLER_STAND.md` spiegelt den realen Systemzustand wider: laufende Services, Health, offene Blocker, Roadmap.  
WF1 hält dieses Dokument synchron mit:

- Docker-/Service-Health,
- Metriken aus Prometheus/Grafana,
- relevanten Backoffice-Dokumenten (Analysen, Governance).

**Phase A – Daten sammeln (Analysis Mode)**

1. Session Lead aktiviert Workflow „Status_Update“ (z. B. via `agents-sync`).
2. Nutzung von MCP-Tools:
   - `filesystem.read_file`:
     - `backoffice/docs/AKTUELLER_STAND.md` (Soll-Zustand)
     - `backoffice/docs/CDB_FOUNDATION.md`
     - `backoffice/docs/CDB_INSIGHTS.md`
   - `playwright`:
     - Öffnet Grafana-Dashboards und erstellt Screenshots.
     - Optional: Zugriff auf Prometheus-Metriken.
3. Agent (z. B. `AGENT_Project_Stability_Guardian`) extrahiert:
   - Laufende Container / Services (`cdb_*`)
   - Relevante Metriken (z. B. Trades/Tag, Alerts)
   - Offene Blocker aus bestehenden Docs/Issues.
4. `cdb-logger.log_event`: `STATUS_REFRESH_ANALYSIS_STARTED`.

**Phase B – Aktualisierung (Delivery Mode nach Freigabe)**

1. Session Lead präsentiert Analyse & geplante Updates an User (Decision Gate).
2. Nach Freigabe:
   - Neue Version von `AKTUELLER_STAND.md` wird erzeugt (Diff-bewusst).
   - `filesystem.write_file` aktualisiert Datei unter `backoffice/docs`.
   - `github-official`:
     - Branch `status-auto-refresh-YYYYMMDD` von `main`.
     - Commit „Update AKTUELLER_STAND via MCP Agent“.
     - PR mit Kurzbeschreibung, Changelog, optional Links auf Grafana-Panels.
   - `cdb-logger.log_event`: `STATUS_REFRESH_DELIVERED` inkl. PR-URL.

**Ergebnis**  
Ein reproduzierbarer, Agenten-getriebener Workflow, der den Projektstatus konsistent mit der realen Systemlage hält.

---

### 4.2 WF2 – „Handelsfrequenz & Signalqualität-Tuning“

**Zweck**  
Bestehende Strategie/Parameter sollen so optimiert werden, dass:

- Handelsfrequenz erhöht oder strukturiert angepasst wird,
- Signalqualität (z. B. Winrate) nicht inakzeptabel sinkt,
- Risiko-Grenzen aus `.env` / Konfiguration eingehalten werden.

**Phase A – Analyse & Vorschlag (Analysis Mode)**

1. Session Lead aktiviert Rolle `Strategy Engineer` / `Signal Optimizer` aus `AGENTS.md`.
2. `filesystem.read_file` für:
   - `services/signal_engine/config.py` (oder äquivalente Konfigurationsdatei)
   - Relevante Analyse-Dokumente (z. B. `backoffice/docs/Handelsfrequenz_und_Signalqualität.md` oder äquivalent).
3. Optional: Zugriff auf Analytics-/Backtest-Skripte:
   - z. B. `backoffice/scripts/query_analytics.py` zur Ermittlung von Winrate, Trades/Tag, Drawdown.
4. Agent analysiert:
   - Welche Parameter aktuell zu konservativ sind.
   - Welche Parameterkombination sinnvoll zur Frequenzsteigerung ist (z. B. Threshold, RSI-Filter, Trendfilter).
5. `cdb-logger.log_event`: `SIGNAL_TUNING_PROPOSAL_CREATED` (inkl. Vorschlags-Parameter).

Der Session Lead liefert einen **strukturierten Vorschlag** (Analysis Report Format):

- Ist-Konfiguration
- Soll-Konfiguration
- Erwartete Effekte (Trades/Tag, Winrate, Drawdown)
- Rollback-Plan

**Phase B – Umsetzung im Repo (Delivery Mode nach GO)**

Nach expliziter Freigabe durch den User:

1. Branch `signal-tuning-YYYYMMDD` von `main`.
2. `filesystem.write_file`:
   - Anpassung von `config.py` oder der relevanten Konfigurationsquelle.
   - Optional: Update von `backoffice/docs/Risikomanagement_Logic.md` o. ä.
3. `github-official`:
   - Commit „Signal Engine parameter tuning: increase trade frequency under controlled risk“.
   - PR mit Parametervarianten und kurzer Begründung.
4. `cdb-logger.log_event`: `SIGNAL_TUNING_PR_CREATED` inkl. Diff/PR-Referenz.

**Phase C – Beobachtung & Iteration**

Später (Paper-/Live-Betrieb):

- Agenten (z. B. `Project_Visualizer` + `Stability_Guardian`) werten neue Metriken aus:
  - neue Winrate
  - neue Trades/Tag
  - Drawdown
- Ergebnisse werden im PR-Thread oder in `DECISION_LOG.md` dokumentiert.
- Nächste Iteration wird als eigener Workflow-Lauf (Iteration 2, 3, …) behandelt.

---

### 4.3 WF3 – „Agenten-Governance & DECISION_LOG Pflege“

**Zweck**  
Sicherstellen, dass:

- `AGENTS.md` die real genutzten Agenten-/Workflow-Definitionen widerspiegelt.
- `DECISION_LOG.md` alle wichtigen Entscheidungen und Änderungen enthält.
- Brainstorming-Sessions nicht im Chat „verpuffen“, sondern in Governance und Artefakte überführt werden.

**Trigger**

- Immer wenn im Chat / in einer Session neue Agentenrollen, Capabilities oder Workflows definiert werden.
- Insbesondere bei Formulierungen wie „mach den Job fertig“, „der Agent ist jetzt offiziell dafür zuständig“ etc.

**Ablauf (Analysis → Delivery)**

1. Session Lead erkennt neue oder geänderte Agenten-/Workflow-Definitionen im Chat-Protokoll.
2. `agents-sync`:
   - Lädt aktuelle Agenten-Definitionen/Workflows (z. B. aus `AGENTS.md`).
3. `filesystem.read_file("backoffice/docs/governance/AGENTS.md")` (oder äquivalenter Pfad).
4. Agent `AGENT_Project_Visionary`:
   - Formuliert formale Definition der neuen/angepassten Rolle inkl.:
     - Name, Zweck, Verantwortlichkeiten
     - Eingabe-/Ausgabeformate
     - Zugehörige Workflows
5. Session Lead präsentiert Änderungsvorschlag (Decision Gate).

Nach Freigabe (Delivery Mode):

6. `filesystem.write_file` aktualisiert `AGENTS.md` (kanonische Governance-Version).
7. `cdb-logger.append_markdown`:
   - Fügt Eintrag in `DECISION_LOG.md` hinzu:
     - Was wurde geändert/eingeführt?
     - Datum/Uhrzeit
     - Session-/Kontext-Referenz
8. `github-official`:
   - Je nach Policy:
     - Direkt-Commit auf `main` (Governance fast-track) oder
     - Branch + PR (z. B. `governance-update-YYYYMMDD`).

Optional: `cdb-logger.log_event` mit Kategorie `agents`, Typ `GOVERNANCE_UPDATED`.

**Ergebnis**  
Deine Governance-Dokumente bleiben synchron mit den tatsächlichen Projektentscheidungen, ohne dass du händisch nachpflegen musst.

---

## 5. Rolle der Clients („Kollektoren“)

- IDEs & Chat-Apps (ChatGPT, Claude, Cursor, etc.) sind **nur Oberflächen**.
- Der tatsächliche Workflow läuft über:
  - Session Lead (Supervisor/Orchestrator)
  - MCP-Gateway
  - CDB-Stack

Regel:

1. Du definierst Ziel/Workflow im Chat (WF1–WF3 oder Kombination).
2. Wenn du sagst „mach den Job fertig“ / „Delivery starten“:
   - Session Lead wechselt von Analysis Mode zu Delivery Mode im Sinne von `CDB_WORKFLOWS.md`.
   - Der Workflow wird so lange durchgezogen, bis:
     - PR(s) erstellt sind,
     - `AKTUELLER_STAND.md`, `AGENTS.md`, `DECISION_LOG.md` etc. aktualisiert wurden,
     - ein klarer Abschlussbericht vorliegt.
3. Alle Schritte sind:
   - protokolliert (`cdb-logger`),
   - auditierbar,
   - rückführbar auf eine explizite User-Entscheidung.

---

## 6. Zusammenfassung (aktualisierte Kernaussagen)

1. CDB-Stack und MCP-Stack laufen parallel und getrennt:  
   - CDB für Trading-Infrastruktur  
   - MCP für Tools, Governance-Workflows und Automations
2. Start-Flow bleibt zweistufig, ist aber an **Windows 10/11 + Docker Desktop + Governance-Protokolle** angepasst.
3. WF1–WF3 sind explizit mit den Rollen und Protokollen aus `CDB_GOVERNANCE.md` und `CDB_WORKFLOWS.md` verzahnt.
4. Projekt-Gehirn (Project_Visionary, Project_Visualizer, Stability_Guardian) fungiert als intellektueller Layer über diesen Workflows:
   - WF1: Status & Roadmap
   - WF2: Strategie- und Parametertuning
   - WF3: Governance- & Entscheidungslog-Pflege
5. Dieses Dokument ist die operative Brücke zwischen:
   - technischer Basis (`CDB_FOUNDATION.md`),
   - Governance/Verfassung (`CDB_GOVERNANCE.md`),
   - Workflows (`CDB_WORKFLOWS.md`),
   - und deinem tatsächlichen Agenten-/MCP-Betrieb.
