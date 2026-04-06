# Session Log — 2026-03-29 — Issue #1328: Docs-Hub Topology Neutralization

## Ziel
Stale Docs-Hub-Topologie-Claims in `knowledge/reviews/CLAUDE_PROJECT_OVERVIEW.md` neutralisieren, ohne die Datei komplett umzuschreiben.

## Ergebnis
- Frontmatter: `status: historical`, `superseded_by: knowledge/SYSTEM.CONTEXT.md`
- In-Body-Tombstone: erklärt Docs-Hub-Retirement und Mono-Repo-Konsolidierung
- Section "Repo Topology" als `(pre-consolidation, retired)` markiert, Claims durchgestrichen
- Alle 4 Docs-Hub-Referenzen im Body mit `(retired)` getaggt
- 1 file, +16/−8

## Commit
- `a11a339` auf `fix/1329-decision-docs-hub-drift`, gepusht

## Issue-Update
- Kommentar mit Befund-Tabelle und Validierung gepostet

## Restunsicherheiten
- Keine innerhalb des Issue-Scope
- Die unter "Key Files (Docs Hub retired)" gelisteten Pfade könnten im Mono-Repo unter anderen Pfaden existieren — out-of-scope für #1328
