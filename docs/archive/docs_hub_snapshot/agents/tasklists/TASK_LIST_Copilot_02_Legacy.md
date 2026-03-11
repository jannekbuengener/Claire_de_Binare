---
role: tasklist
agent: COPILOT
status: deprecated
source: 2TASK-LISTcopilot.txt
replaced_by: COPILOT_TASKLIST_01.md
---

# Copilot Tasklist 01 (LEGACY)

**⚠️ DEPRECATED:** This tasklist has been replaced by `COPILOT_TASKLIST_01.md`

## Original Content

📋 Copilot Tasklist 01
Prompt-Migration .txt → .md

Ziel:
Altlasten beseitigen, Lesbarkeit + Konsistenz erhöhen, ohne Inhalte neu zu erfinden.

Scope:
agents/prompts/*.txt, copilot.txt, gemini.txt

Copilot Aufgaben:

Alle .txt Prompt-Dateien lokalisieren

Für jede Datei:

1:1 Inhalt übernehmen

nach .md konvertieren

Standard-Frontmatter ergänzen:

---
role: prompt
agent: <COPILOT|GEMINI|CLAUDE|CODEX>
status: migrated
source: <original filename>
Klaren Titel als H1 setzen

Falls Datei deprecated:

deutlich kennzeichnen (Status: deprecated)

Hinweis auf neue Zieldatei

Original .txt nicht löschen

sondern mit DEPRECATED – migrated to … markieren

Keine inhaltlichen Änderungen

Keine neuen Prompts erfinden

Output:

Neue .md Dateien

Minimaler Diff

Kurze Liste: migriert / deprecated

Stop-Regel:
Unklarer Agentenbezug → STOP & Rückfrage
