# Session: Issue #1231 — Root Cleanup First Cut

**Date:** 2026-03-28
**Branch:** cleanup/1231-rm-360-systemcheck-stub
**PR:** #1292
**Status:** PR offen, weitere Zuarbeit nötig

---

## Was wurde getan

### Referenzprüfung (rg)

Alle Kandidaten für Root-Moves/Deletes wurden vor Ausführung mit `rg` geprüft:
- `governance-audit-2026-01-15.md`: aktive Refs in README.md + GOVERNANCE_CORE_STATUS_REPORT_v4.md → Root belassen
- `360-SYSTEMCHECK.md`: nur Self-Match außerhalb Archive/Logs → sicher deletierbar
- `PROJECT_ANALYTICS.md`: Migration-Docs + Duplizierung in `knowledge/analysis/` → klären
- `.gitignore`-Lücken-Hypothese: widerlegt durch `.git/info/exclude`-Prüfung

### Patch (PR #1292)

- `git rm 360-SYSTEMCHECK.md` — redundanter 7-Zeilen-Pointer
- `docs/archive/LEGACY_FILES.md` — verwaisten Listeneintrag entfernt
- `tools/enforce-root-baseline.ps1`: PASS
- Commit: `d2ca996`

---

## Bewusst nicht angefasst

| Datei | Nächster Schritt |
|---|---|
| `governance-audit-2026-01-15.md` | git mv → docs/archive/ + Link-Fix README.md:191 + GOVERNANCE_CORE_STATUS_REPORT_v4.md:93 |
| `PROJECT_ANALYTICS.md` | Duplikat-Klärung mit knowledge/analysis/ zuerst |
| `PRs — issues.md`, `Repository‑Überblick.md` | Referenzlage vollständig prüfen |
| `.gitignore` | Optional: Canonicalization von .git/info/exclude → .gitignore als explizite Repo-Policy |

---

## Lektionen dieser Session

- `.git/info/exclude` vor .gitignore-Lücken-Behauptungen prüfen
- `rg` mit Glob-Excludes statt `grep`-Piping (grep nicht zuverlässig in Git Bash)
- Self-Match bei `rg -l` ist kein Fehler, muss im erwarteten Ergebnis explizit stehen
- `docs/archive/LEGACY_FILES.md` als Kopplungspunkt bei Root-Stub-Deletions mitziehen
