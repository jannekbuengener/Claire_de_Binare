# Session: Issue #1231 — governance-audit-2026-01-15.md Move

**Date:** 2026-03-28
**Branch:** cleanup/1231-governance-audit-move
**PR:** #1293
**Status:** PR offen, weitere Zuarbeit nötig

---

## Was wurde getan

### Vorarbeit

- PR #1292 gemerged (56c5248), lokales main auf origin/main resettet
- Neuer Branch `cleanup/1231-governance-audit-move` von sauberem main

### Referenzprüfung

`rg -l "governance-audit-2026-01-15" -g "*.md" -g "*.yaml" -g "*.yml" -g "!docs/archive/**" -g "!knowledge/logs/**" .`

Aktive Treffer vor dem Move:
- `README.md:191` — relativer Link
- `docs/governance/status/2026-02-24/GOVERNANCE_CORE_STATUS_REPORT_v4.md:93` — GitHub-Blob-URL
- `docs/meta/WORKING_REPO_CANON.md:37` — Beispielpfad in Tabelle (kein Link, aber Pfad veraltet ohne Fix)

Nicht angefasst (historisch):
- `knowledge/logs/sessions/2026-03-22-docs-canon-alignment.md:65`
- `knowledge/logs/sessions/2026-03-28-issue-1231-root-cleanup-first-cut.md`
- `governance-audit-2026-01-15.md:541` (Self-Referenz im Dokument)

### Patch (PR #1293, Commit 388bb75)

- `git mv governance-audit-2026-01-15.md docs/archive/governance-audit-2026-01-15.md`
- `README.md:191` — Link aktualisiert
- `GOVERNANCE_CORE_STATUS_REPORT_v4.md:93` — GitHub-URL aktualisiert
- `WORKING_REPO_CANON.md:37` — Beispielpfad aktualisiert
- `enforce-root-baseline.ps1`: PASS

---

## Noch offen für #1231

- `PROJECT_ANALYTICS.md` — Duplizierung mit `knowledge/analysis/` klären
- `PRs — issues.md`, `Repository‑Überblick.md` — Referenzlage vollständig prüfen
- `.gitignore`-Canonicalization (`.git/info/exclude` → `.gitignore`) — optionaler Folge-Patch
