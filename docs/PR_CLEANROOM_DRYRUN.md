# PR: Cleanroom Dry Run

## Zweck
Erster Struktur-PR, der neue Dokumentorganisation, Secret-Sanitation-Vorbereitung und Gitignore-Anpassungen vorschlägt, ohne produktive Dateien zu löschen.

## Checkliste
- [ ] Build/Test laufen grün (CI + lokaler Pytest)
- [ ] Keine Secrets oder vertraulichen Werte verbleiben im Diff
- [ ] Neue Doc-Pfade stimmen mit Migration Map überein
- [ ] .gitignore deckt Artefakte & Secrets konsistent ab
- [ ] Hinweise aus CLEANUP_PLAN.md umgesetzt, aber Phase-5-Löschungen noch ausstehend

## Done-Definition
- CI-Pipeline erfolgreich (Tests, Lint, Security-Scan)
- Secretscanner (z. B. Gitleaks) ohne Treffer
- Dokumentationslinks angepasst und validiert
- Stakeholder haben Security Sanitation Plan freigegeben

## Rollback-Strategie
- PR revertierbar via `git revert <merge-commit>`
- Vor Merge Branch-Snapshot taggen (`dryrun-before-cleanroom`)
- Bei vergessenen Pfaden: Follow-up-PR mit gezieltem Fix (keine Hotfixes auf Main)

## Referenzen
- docs/CLEANUP_PLAN.md
- docs/MIGRATION_MAP.md
- docs/SECURITY_SANITATION_PLAN.md
- .gitignore.patch
