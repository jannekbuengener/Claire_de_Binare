# CDB Gemini Bootloader

1. **Tool-first Pflicht**
   - Zu Beginn jeder CDB-Aufgabe verfügbare Skills, Agents, MCP-Tools, Extensions und lokale Tools inventarisieren.
   - Wenn die Aufgabe GitHub-/Repo-Wahrheit braucht, sind MCP oder `gh`/`git` Pflicht.
   - Web-Fetch ist kein Ersatz für MCP/`gh`/`git` bei PR-/Issue-/Repo-Hygiene.

2. **Kanonische Read-Order**
   - `agents/GEMINI.md`
   - `agents/AGENTS.md`
   - `knowledge/governance/CDB_CONSTITUTION.md`
   - `knowledge/governance/CDB_GOVERNANCE.md`
   - `knowledge/governance/CDB_AGENT_POLICY.md`
   - `knowledge/governance/SYSTEM_INVARIANTS.md`
   - `docs/runbooks/CONTROL_REGISTER.md`
   - `CURRENT_STATUS.md` (nur als Repo-/Engineering-Ledger)
   - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`

3. **Live-Wahrheit**
   - PR-/Issue-/Branch-/CI-Fragen müssen live per MCP oder `gh`/`git` geprüft werden.
   - `CURRENT_STATUS.md`, Memory, alte Snapshots und Web-HTML reichen dafür nicht.
   - Wenn Live-Tools fehlen: fail-closed stoppen.

4. **Plan-Mode-Regel**
   - Wenn Plan Mode keine Live-Kommandos oder Dateiänderungen erlaubt, darf Gemini keine operative Repo-/PR-Hygiene, keine GitHub-Writes und keine Docs-Änderungen simulieren.
   - Dann stoppen statt Plan-Dateien schreiben.

5. **Antwort-Standard**
   Jede CDB-Antwort beginnt mit:
   - Tool-/Skill-/Agent-/MCP-/Extensions-Check
   - Gelesene Canon-Dateien
   - Live-Wahrheit geprüft: ja/nein
   - Stop-Grund, falls nein

---

# Gemini Agent Context (Bootstrap)

Diese Datei dient als primärer Einstiegspunkt für den Gemini-Agenten im Working Repo.

## 1. Kanonische Charter & Mandat
Die verbindlichen Regeln für Rolle, Mandat und Arbeitsweise sind hier definiert:
👉 [`agents/GEMINI.md`](agents/GEMINI.md) (Zuerst lesen!)

## 2. Projekt-Navigation
Für die allgemeine Agenten-Registry und zentrale Kanon-Verweise siehe:
👉 [`AGENTS.md`](AGENTS.md)

## 3. Aktueller Status (SSoT)
Status-Informationen in dieser Datei sind niemals autoritativ. Nutze immer:
- **Repo-/Engineering-Status**: [`CURRENT_STATUS.md`](CURRENT_STATUS.md)
- **Board-/Stage-Status**: [`docs/runbooks/CONTROL_REGISTER.md`](docs/runbooks/CONTROL_REGISTER.md)
- **Echtgeld-Go/No-Go (LR)**: [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md)

## 4. Kern-Guardrails
- **Solo-Maintainer Canon**: Das Working Repo ist der maßgebliche SSoT.
- **No Execution**: Keine Implementierungs- oder Ausführungsbefugnis für Gemini.
- **Evidence-First**: Systembewertungen erfordern MCP-Evidenz (Redis/Grafana), sofern verfügbar.
