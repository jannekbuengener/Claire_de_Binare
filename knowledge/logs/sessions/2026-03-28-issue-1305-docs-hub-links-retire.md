# Session Log — 2026-03-28 — Issue #1305: Docs-Hub-Links retire

## Ziel
Canon-Verstoß in `tools/secrets/README.md` beheben: externe `Claire_de_Binare_Docs`-Links
auf lokale kanonische Pfade umstellen.

## Durchgeführte Schritte

1. `tools/secrets/README.md` gelesen — Abschnitt `## Documentation (Docs Hub)` enthielt
   zwei externe GitHub-URLs auf den retired Docs Hub.
2. Beide Zieldateien im Working-Repo verifiziert (existieren).
3. Abschnitt umgeschrieben: Titel, Einleitung, beide Links.
4. Grep nach weiteren `Claire_de_Binare_Docs`-Referenzen: clean.
5. Commit `353ceb8` auf Branch `fix/1305-retire-docs-hub-links` erstellt und gepusht.
6. PR #1309 geöffnet (Closes #1305).
7. Issue-Kommentar gepostet, Issue #1305 geschlossen.

## Ergebnis

| | |
|---|---|
| Geänderte Datei | `tools/secrets/README.md` |
| Commit | `353ceb8` |
| Branch | `fix/1305-retire-docs-hub-links` |
| PR | #1309 |
| Issue | #1305 (closed) |

## Scope-Einhaltung
Nur `tools/secrets/README.md` angefasst. Keine weiteren Dateien. Kein Scope-Creep.
