# Session: Issue #1300 — Docs-Hub-Referenzen aus aktiven Dateien entfernt

**Datum:** 2026-03-29
**Issue:** #1300
**PR:** #1330
**Branch:** `docs/1300-retire-docs-hub-refs`
**Agent:** Claude Code (Opus 4.6)

## Ergebnis

- 6 aktive non-archive Dateien korrigiert, die auf den retired Docs Hub als Default-Pfad verwiesen
- 1 lokale Datei (`.claude/CLAUDE_BOOTLOADER.md`, gitignored) bereinigt
- Re-Scan: alle ~80 Resttreffer als historical-acceptable klassifiziert
- PR #1330 erstellt, Issue-Kommentar gepostet
- Issue #1300 bleibt offen bis PR gemerged

## Geänderte Dateien

- `tools/secrets/README.md` — Docs Hub GitHub-Links durch lokale Pfade ersetzt
- `knowledge/reviews/CLAUDE_PROJECT_OVERVIEW.md` — als historisch (2025-12-19) markiert
- `knowledge/migrations/LEGACY_FILES.md` — Redirect-Stub durch Archive-Pointer ersetzt
- `knowledge/decisions/ADR-001-documentation-only-repository.md` — Status Accepted zu Superseded
- `knowledge/logs/sessions/README.md` — "for Docs Hub work" entfernt
- `knowledge/content/FINAL_HANDOFF.md` — historischer Marker ergaenzt

## Blocker

- Branch Protection: Direct Push auf main blockiert, daher PR-Weg
- CI + Merge stehen noch aus

## Naechster Schritt

- Nach CI-Gruen und Merge: Final-Kommentar auf #1300, dann Close
