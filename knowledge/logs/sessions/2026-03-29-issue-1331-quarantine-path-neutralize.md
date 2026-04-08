# Session: Issue #1331 — Neutralize retired Docs-Hub quarantine-path references

**Datum:** 2026-03-29
**Branch:** `fix/1329-decision-docs-hub-drift`
**Commit:** `f90b2bb`
**Issue:** #1331

## Ziel

Quarantine-Pfad-Referenzen (`Claire_de_Binare_Docs/_legacy_quarantine/...`) in zwei Legacy-Analyse-Dokumenten so framen, dass sie nicht mehr als aktive Arbeits-/Analysepfade wirken.

## Scope-Dateien

- `knowledge/architecture/LEGACY_ANALYSIS.md` (Zeile 5)
- `knowledge/compliance/HARDENING_VERIFICATION.md` (Zeile 559)

## Befund

- Beide Dokumente stammen vom 2025-12-24 (pre-consolidation)
- Quarantine-Pfade wurden bei Monorepo-Konsolidierung nie als retired markiert
- Je 1 Treffer pro Datei, Bewertung: `active-looking legacy path`

## Änderungen

- `LEGACY_ANALYSIS.md:5` — Pfad als "now-retired … pre-consolidation, December 2024" geframed; Hinweis ergänzt, dass Pfad nicht mehr als aktive Quelle existiert
- `HARDENING_VERIFICATION.md:559` — Parenthese "(retired pre-consolidation source, December 2024)" eingefügt

## Re-Scan

- Beide Scope-Dateien: clean (Pfade nur noch mit Retirement-Framing)
- ~80 weitere Treffer in `knowledge/archive/`, `agent_trust/ledger/`, `reviews/`, `context_build/`, `logs/sessions/` — alle archivisch, out of scope

## Restunsicherheiten

- Breit-Sweep der ~80 archivischen Treffer nicht durchgeführt (bewusst out of scope)
- Separates Issue empfohlen falls gewünscht
