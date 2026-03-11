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

## Copilot Tasklist 02 — Büro-Files Scan (Consistency Review)
**Ziel:** Neue Büro-Dateien einordnen (OK / OK+Hinweis / Konfliktpotenzial).  
**Scope:** Docs Hub (read-only Analyse + Report)

- Liste der neuen Büro-Files erstellen (Pfad + 1 Satz Zweck).
- Klassifizieren: **OK / OK+Hinweis / Konfliktpotenzial** (1 Satz Begründung).
- Speziell prüfen:
  - `governance/CONSTITUTION.md` vs `governance/CDB_CONSTITUTION.md` → Duplicate-Risiko flaggen.
- Abgleich mit `DOCS_HUB_INDEX.md`: Ordner/Dateien konsistent?
- Output: 1 Markdown-Report `BUERO_FILES_REVIEW.md`.

**Stop-Regel:** Wenn Policy-Interpretation nötig wird → STOP (nur Fakten + Flags).

