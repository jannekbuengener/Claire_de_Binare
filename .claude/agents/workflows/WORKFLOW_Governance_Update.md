# WORKFLOW_Governance_Update – Agenten & DECISION_LOG

## Ziel

Sicherstellen, dass:

- neue Agenten-Rollen, Capabilities und Workflows aus Brainstorming-Sessions
  sauber in `AGENTS.md` nachgeführt werden,
- der DECISION_LOG alle wichtigen Governance-Entscheidungen protokolliert.

---

## Preconditions

- User-Session, in der neue Rollen/Capabilities/Workflows besprochen wurden.
- MCP-Server aktiv: `agents-sync`, `filesystem`, `github-official`, `cdb-logger`.

---

## Phase A – Analyse

1. Session-Auswertung
   - Orchestrator extrahiert aus der aktuellen Unterhaltung:
     - neu definierte Rollen,
     - geänderte Verantwortlichkeiten,
     - neue oder angepasste Workflows.
2. Abgleich mit bestehender Governance
   - `filesystem.read_file("AGENTS.md")`.
   - Optional: weitere Governance-Dokumente (z. B. `governance/GOVERNANCE_AND_RIGHTS.md`).
3. Gap-Analyse
   - Welche Agenten sind neu und fehlen?
   - Welche Rollen haben neue Capabilities bekommen?
   - Welche Workflows müssen ergänzt/aktualisiert werden?
4. Logging
   - `cdb-logger.log_event` – `GOVERNANCE_ANALYSIS_COMPLETED`.
5. Output
   - Vorschlag, wie `AGENTS.md` und ggf. die verlinkten Rollen-/Workflow-Dateien angepasst werden sollen.

---

## Phase B – Delivery (nach Freigabe)

1. Branching
   - Branch-Name: `governance-update-YYYYMMDD`.
2. Governance-Dateien aktualisieren
   - `filesystem.write_file`:
     - Aktualisierung von `AGENTS.md` (Tabellen- / Link-Updates).
     - ggf. neue Dateien in `roles/` und `workflows/` anlegen.
3. DECISION_LOG pflegen
   - `cdb-logger.append_markdown`:
     - Governance-Entscheidung dokumentieren (Datum, Session-Kontext, Kurzinhalt).
4. Commit & PR
   - `github-official`:
     - Commit mit Message „Update agent governance & decision log“.
     - PR Richtung `main` mit:
       - Übersicht aller Governance-Änderungen,
       - Motivation und Risiken.

---

## Erfolgsindikatoren

- `AGENTS.md` spiegelt die real genutzten Agenten und Workflows korrekt wider.
- DECISION_LOG enthält nachvollziehbare Einträge zu Governance-Änderungen.
- Neue Rollen/Workflows sind referenziert und können von `agents-sync` sauber geladen werden.
