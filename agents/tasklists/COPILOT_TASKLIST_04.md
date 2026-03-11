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

## Copilot Tasklist 04 — M7 Skeleton (Paper Trading Struktur)
**Ziel:** M7 als arbeitbaren Plan strukturieren (Cluster + Abhängigkeiten).  
**Scope:** Working Repo oder Docs Hub (nur Artefakt-Text)

- Zerlege „M7 Paper Trading“ in 5–8 Cluster:
  - Data/Feed, Signal, Risk, Execution, PSM/State, Observability, Reporting, Ops
- Pro Cluster: 3–7 Subtasks (Issue-Skeleton) mit:
  - Titel
  - Akzeptanzkriterium (1–2 Sätze)
- Abhängigkeiten markieren (`depends-on`, `blocked-by`)
- Output: `M7_SKELETON.md` (oder Issue-Liste in Markdown).

**Stop-Regel:** Keine Architekturentscheidungen treffen, nur Struktur.

