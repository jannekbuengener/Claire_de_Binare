# AGENTS – CLAIRE-DE-BINARE

Single Source of Truth für:

- Rollen (Agents / Orchestrator / Sub-Agenten)
- globale Regeln (Governance)
- Workflows
- dazugehörige Prompt-Dateien

Dieses Dokument beschreibt **wer was darf** – der konkrete Prompt-Text steht in den verlinkten Dateien.

---

## 1. Globale Regeln

1. **Single Orchestrator**  
   - Nur der Orchestrator spricht direkt mit dem User.  
   - Sub-Agenten werden ausschließlich durch den Orchestrator gesteuert.

2. **Analyse vs. Delivery**  
   - Analyse-Phase:
     - nur Lesen (Repo, Doku, Metriken),
     - keine Dateiänderungen, keine PRs.
   - Delivery-Phase:
     - nur nach expliziter Freigabe,
     - Änderungen immer über Branch + PR, nie direkt auf `main`.

3. **Risk & Production**  
   - Kein Live-Trading ohne expliziten Risk-Workflow und Freigabe.  
   - Änderungen mit potenziellen Risikoauswirkungen werden separat dokumentiert.

4. **Dokumentation & Logs**  
   - Wichtige Entscheidungen landen im DECISION_LOG und relevanten Backoffice-Dokumenten.  
   - Aktionen werden über `cdb-logger` protokolliert (JSONL + Markdown).

5. **MCP-Tooling**  
   - Alle Tools laufen über den Docker MCP Gateway.  
   - Erlaubte Server:
     - `agents-sync`
     - `filesystem`
     - `github-official`
     - `playwright`
     - `cdb-logger`
6. **Project-Gehirn als Pflichtweg**  
   - Fachagenten arbeiten grundsätzlich auf Work-Items, die über `AGENT_Project_Visionary` und `AGENT_Project_Visualizer` vorbereitet wurden.  
   - CI/CD-, Security- und Repo-Hygiene-Signale werden über `AGENT_Stability_Guardian` in Issues übersetzt, bevor Fachagenten handeln.  
   - Direkte User-Interaktion durch Fachagenten ist nicht erlaubt; alle User-Kontakte laufen über ORCHESTRATOR_Codex.


---

## 2. Rollen – Übersicht

| Rolle                 | Typ          | Beschreibung                                     | Definition                        |
|-----------------------|-------------|--------------------------------------------------|-----------------------------------|
| ORCHESTRATOR_Codex    | Orchestrator| Single Entry Point für User, steuert alle Agenten| `roles/ORCHESTRATOR_Codex.md`     |
| Repository Auditor    | Sub-Agent    | Repo-Struktur, Doku-Konsistenz                   | `roles/REPO_Auditor.md` (optional)|
| Documentation Engineer| Sub-Agent    | Doku schreiben/aktualisieren                     | `roles/DOC_Engineer.md` (optional)|
| Refactoring Engineer  | Sub-Agent    | Strukturelle Code-Verbesserungen                 | `roles/Refactor_Engineer.md` (opt)|
| Risk Architect        | Sub-Agent    | Risiko- und Signalkonfiguration                  | `roles/Risk_Architect.md` (opt)   |
| weitere               | Sub-Agent    | spätere Spezialisierungen                        | tbd                               |

*(Rollen-Dateien, die noch nicht existieren, können schrittweise ergänzt werden.)*

### 2.1 Orchestration-Layer & Routing

- **Layer 1 – ORCHESTRATOR_Codex**  
  Single Entry Point für den User. Steuert Agenten und MCP-Tools gemäß `DECISION_MCP_STACK_BASELINE.md`.

- **Layer 2 – Projekt-Gehirn**  
  - `AGENT_Project_Visionary`: Eingang und Bewertung aller Work-Items (Issues, MRs, Research-, Sentiment-, Risk-, DevOps- oder Architektur-Signale).  
  - `AGENT_Project_Visualizer`: baut daraus Epics, Boards, Timelines und Cluster.  
  - `AGENT_Stability_Guardian`: übersetzt CI/CD-, Security- und Repo-Signale in saubere Stabilitäts- und Qualitäts-Tickets.

- **Layer 3 – Fachagenten**  
  System-, Daten-, Risk-, Test-, Doku-, DevOps-, Research- und Trading-Rollen arbeiten grundsätzlich auf Basis von Work-Items, die über das Projekt-Gehirn (Visionary/Visualizer/Stability) strukturiert wurden.

**Routing-Regeln (Kernprinzipien)**

1. Alle neuen Signals (Issues, MRs, Research, Sentiment, technische Findings)  
   → `AGENT_Project_Visionary` (Analyse, Label, Impact, Links).

2. Projektplanung und -sichtbarkeit (Epics, Boards, Timelines)  
   → `AGENT_Project_Visualizer`.

3. CI/CD-, Security- und Repo-Hygiene-Rauschen  
   → `AGENT_Stability_Guardian`.

4. Fachagenten (Architektur, Daten, Risk, Tests, Doku, DevOps, Trading, Research)  
   - erhalten ihre Aufgaben als vorbereitete Work-Items aus dem Projekt-Gehirn,  
   - melden Ergebnisse/Fundings zurück, die wieder durch `AGENT_Project_Visionary` und `AGENT_Project_Visualizer` ins Systembild integriert werden.


---

## 3. Workflows – Übersicht

| Workflow                        | Zweck                                          | Definition                                      |
|---------------------------------|-----------------------------------------------|-------------------------------------------------|
| Status_Update                   | AKTUELLER_STAND Auto-Refresh                  | `workflows/WORKFLOW_Status_Update.md`           |
| Signal_Tuning                   | Handelsfrequenz & Signalqualität anpassen     | `workflows/WORKFLOW_Signal_Tuning.md`           |
| Governance_Update               | Agenten-Governance + DECISION_LOG pflegen     | `workflows/WORKFLOW_Governance_Update.md`       |
| Repo_Audit                      | Repo- und Doku-Konsistenz prüfen              | `workflows/WORKFLOW_Repo_Audit.md` (optional)   |
| Feature_Implementation          | Feature-Umsetzung über PR-Workflow            | `workflows/WORKFLOW_Feature_Implementation.md`  |

---

## 4. Prompts – Übersicht

| Name                           | Typ        | Beschreibung                                  | Datei                                        |
|--------------------------------|-----------|-----------------------------------------------|---------------------------------------------|
| PROMPT_MAIN_Codex_Orchestrator| System    | Hauptprompt für ORCHESTRATOR_Codex            | `prompts/PROMPT_MAIN_Codex_Orchestrator.md` |
| PROMPT_Task_Brief_Template    | Template  | Task-Brief-Struktur                           | `prompts/PROMPT_Task_Brief_Template.md`     |
| PROMPT_Analysis_Report_Format | Template  | Strukturierter Analyse-Report                  | `prompts/PROMPT_Analysis_Report_Format.md`  |

---

## 5. Nutzung

1. **Meta-Ebene (Governance)**  
   - Dieses Dokument wird gelesen, nicht direkt „ausgeführt“.  
   - Anpassungen an Rollen/Workflows müssen PR-gestützt erfolgen.

2. **Runtime-Ebene (LLM)**  
   - Der Orchestrator erhält:
     - seine Rolle aus `roles/ORCHESTRATOR_Codex.md`,  
     - sein Systemprompt aus `prompts/PROMPT_MAIN_Codex_Orchestrator.md`.  
   - Sub-Agenten folgen ihren jeweiligen Rollendefinitionen.

3. **Keine Task-Prompts direkt hier**  
   - Spezifische Arbeits-Prompts gehören in `prompts/…`.  
   - `AGENTS.md` bleibt clean als Governance-/Index-Schicht.


