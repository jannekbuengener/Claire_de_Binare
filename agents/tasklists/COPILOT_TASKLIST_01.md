# CDB — Copilot Tasklists (Office Pack)
Stand: 2025-12-16

## Reihenfolge (Office Execution Order)
1. Prompt-Migration `.txt → .md`
2. Büro-Files Scan (Consistency Review)
3. Weekly Status Digest (1 Seite)
4. M7 Skeleton (Paper Trading Struktur)
5. Dockerfile & Stack Hardening (Compose/Runtime)
6. Papertrading Setup + Live-Daten + Execution Service Config

---

---

## Copilot Tasklist 01 — Prompt-Migration `.txt → .md`
**Ziel:** `.txt` Altlasten eliminieren, Prompts standardisieren (ohne Rewriting).  
**Scope:** `agents/prompts/*.txt`, Root `copilot.txt`, `gemini.txt` (Docs Hub)

- Alle `.txt` Prompt-Dateien lokalisieren.
- Für jede `.txt`: 1:1 Inhalt nach `.md` migrieren (kein Rewriting).
- Frontmatter ergänzen:
  ```yaml
  ---
  role: prompt
  agent: <COPILOT|GEMINI|CLAUDE|CODEX>
  status: migrated
  source: <original filename>
  ---
  ```
- Titel als `# ...` ergänzen (prägnant).
- Original `.txt` oben als **DEPRECATED** markieren + Link zur neuen `.md`.
- `DOCS_HUB_INDEX.md` prüfen: Referenzen auf `.txt` → auf `.md` umstellen.
- Output: Liste „migriert / deprecated / referenziert“.

**Stop-Regel:** Unklarer Agentenbezug → STOP & Rückfrage.

