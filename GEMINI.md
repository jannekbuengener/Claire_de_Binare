# CDB Gemini Bootloader

1. **Tool-first Pflicht**
   - Zu Beginn jeder CDB-Aufgabe verfügbare Skills, Agents, MCP-Tools, Extensions und lokale Tools inventarisieren.
   - Die lokale Gemini-Runtime-Fläche und die repo-kanonische CDB-Skill-Fläche sind getrennt zu prüfen.
   - Repo-kanonische CDB Skills liegen unter:
     - `.codex/cdb_skills/`
     - Windows-Beispiel: `D:\Dev\Workspaces\Repos\Claire_de_Binare\.codex\cdb_skills`
   - Falls die Umgebung lokalen Zugriff erlaubt, sind zudem folgende Pfade der lokalen Runtime zwingend zu prüfen:
     - `C:\Users\janne\.gemini\skills`
     - `C:\Users\janne\.gemini\extensions`
     - `C:\Users\janne\.gemini\extensions\system-agents\system-agents`
     - `C:\Users\janne\.gemini\extensions\system-agents\custom`
     - `C:\Users\janne\.gemini\extensions\extension-enablement.json`
   - Wenn einer dieser Pfade nicht zugreifbar ist, muss Gemini dies im Tool-Check offen angeben.
   - Für CDB-Repo-/PR-/Governance-Arbeit sind besonders folgende Skills/Agents (falls verfügbar) heranzuziehen:
     - `cdb-session-start`, `cdb-control-intake`, `cdb-ci-cd-guard`, `cdb-contract-evidence-gatekeeper`
     - `gh-fix-ci`, `gh-address-comments`
     - `diff-auditor`, `evidence-scout`, `scope-sentinel`, `secret-gatekeeper`, `supply-chain-watchdog`
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

5. **Antwort-Standard (Evidence-Abgrenzung)**
    Jede CDB-Antwort beginnt mit:
    - Tool-/Skill-/Agent-/MCP-/Extensions-Check
    - Gelesene Canon-Dateien
    - Evidence-Abgrenzung: Repo-/Canon-/Onboarding-Status geprüft; GitHub-/Check-Live nicht geprüft, sofern keine konkreten git/gh/check-Kommandos ausgeführt wurden.
    - GitHub-/Repo-Live geprüft nur mit konkreten git/gh/check-Kommandos und Ergebnissen.
    - Stop-Grund, falls kein Live-Check möglich

6. **Wording Contract**
    - `tools.onboarding_orchestrator` zählt als Onboarding-Statusprüfung, nicht als GitHub-/Check-Live-Wahrheit.
    - `trade-capable` ist Board-/Stage-Kontext, kein Live-Go.
    - `CURRENT_STATUS.md` ist Engineering-Ledger, nicht Live-Wahrheit.
    - LR-SSOT ist `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
    - Setup nur nach explizitem Setup-GO; kann lokale Dateien erzeugen.
    - Ohne Setup-GO: read-only bleiben. Kein "Führt cp .env.example .env aus" als UI-Erklärung.

7. **Onboarding-Intent-Router**
   - If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, `mach onboarding`, `fresh agent onboarding`, or equivalent, run: `python -m tools.onboarding_orchestrator`
   - Do not start `cdb-session-start` or `onboarding_doctor` as the primary path for onboarding intent.
   - Default output is the CDB Onboarding status card.
   - Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.

8. **Guided-Rehearsal-Intent**
   - If the user says `onboarding rehearsal`, `guided rehearsal`, `rehearsal mode`, `generalprobe`, `tu so als waere ich neuer entwickler`, `reisefuehrer`, `nicht staendig fragen`, `realitaetsnah simulieren`, `onboarding als test-szenario`, or equivalent, run: `python -m tools.onboarding_simulation --mode guided-rehearsal --role developer`
   - Guided rehearsal ist kein Setup-GO und kein Live-Go.
   - Mutierende Schritte werden nur simuliert.
   - Der Agent fuehrt als Reisefuehrer autonom, kein Fragebogen.
   - **Nach dem Lauf:** KEINE Anschlussfrage, keine Einladung, kein "Wenn du willst..." mit Optionen. Der letzte Absatz MUSS Abschluss sein: Status, ein naechster Schritt, STOP.

---

# Gemini Agent Context (Bootstrap)

Diese Datei dient als primärer Einstiegspunkt für den Gemini-Agenten im Claire de Binare repository.

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
- **Solo-Maintainer Canon**: Das Claire de Binare repository ist der maßgebliche SSoT.
- **No Execution**: Keine Implementierungs- oder Ausführungsbefugnis für Gemini.
- **Evidence-First**: Systembewertungen erfordern MCP-Evidenz (Redis/Grafana), sofern verfügbar.
