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

## Copilot Tasklist 03 — Weekly Status Digest (1 Seite)
**Ziel:** Wöchentliche Steuerungsübersicht, max. 1 Seite.  
**Scope:** Docs Hub (Logs/Reports)

- Digest-Template definieren (max 1 Seite) mit:
  - Changes (Commits/Files)
  - Issues/PRs (Delta + Top 5)
  - Milestones (Bewegung)
  - Blocker (max 3)
- Ordner anlegen (falls fehlt): `knowledge/logs/weekly_reports/`
- Datei ablegen: `weekly_report_TEMPLATE.md`
- Beispielreport erzeugen: `weekly_report_2025-12-16.md` (Dummy, Format demonstrieren)
- Optional: Automation nur vorschlagen (kein Autowrite ohne Freigabe).

**Stop-Regel:** Keine GitHub API/Secrets/Token-Annahmen.

