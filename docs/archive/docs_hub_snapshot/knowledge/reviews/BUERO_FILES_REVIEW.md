---
type: report
date: 2025-12-17
issue: "#119"
status: completed
---

# Büro-Files Review (Docs Hub)

Scope: Neue/untracked Büro-Files gemäß `git status --short` (2025-12-17).  
Methodik: Sichtprüfung der Dateien, keine Änderungen vorgenommen.

| Pfad | Zweck (1 Satz) | Klassifikation | Notiz / Duplikat-Risiko |
| --- | --- | --- | --- |
| agents/charters/charter-template.yaml | Vorlage für Agenten-Charters (v1.0.0) | OK+Hinweis | Überschneidung mit ehemaligem `agents/charter-template.yaml` – kanonischen Speicherort festlegen. |
| agents/roles/AGENTS.md | Gemeinsame Agenten-Charter (shared) | Konfliktpotenzial | Doppelung zu bisherigem `agents/AGENTS.md` (gelöscht) – Quelle/Canonical klären. |
| agents/roles/CLAUDE.md | Rolle CLAUDE (Session Lead) | Konfliktpotenzial | Überlappt mit bisherigem `agents/CLAUDE.md` – Single Source definieren. |
| agents/roles/CODEX.md | Rolle CODEX (Execution Agent) | Konfliktpotenzial | Überlappt mit bisherigem `agents/roles/CODEX.md`. |
| agents/roles/COPILOT.md | Rolle COPILOT (Assistenz) | Konfliktpotenzial | Überlappt mit bisherigem `agents/COPILOT.md`. |
| agents/roles/GEMINI.md | Rolle GEMINI (Audit & Review) | Konfliktpotenzial | Überlappt mit bisherigem `agents/GEMINI.md`. |
| agents/roles/roles.yaml | Registry der Agentenrollen & Kategorien | OK+Hinweis | Neue Taxonomie – Abgleich mit `CDB_AGENT_POLICY.md`/`AGENTS.md` nötig, um Divergenzen zu vermeiden. |
| knowledge/operating_rules/OPERATING_BASELINE.md | Betriebs-Baseline (Gesundheit/Beobachtbarkeit) | OK+Hinweis | Mit Working-Repo-Runbooks abgleichen (keine Konflikte erkennbar). |
| knowledge/operating_rules/INCIDENT_LOOP.md | Incident-Handling-Prozess | OK+Hinweis | Mit OPERATING_BASELINE konsistent; Integration in Runbooks/Playbooks offen. |

Zusatzbeobachtung: `git status` zeigt gelöschte frühere Agenten-Dateien (agents/AGENTS.md, agents/CLAUDE.md, …); diese sind nicht Teil dieses Reports, markieren aber den Bedarf, einen kanonischen Ablageort für Agenten-Charters festzulegen.

Keine Entscheidungen oder Änderungen vorgenommen; nur Fakten-Scan.
