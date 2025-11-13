# Kommunikationspakete

## Stakeholder-Mail – Sanitation & Re-Clone
**Subject:** Cleanroom Security Sanitation – Wartungsfenster & Re-Clone erforderlich

Hallo zusammen,

am <DATE> zwischen <MAINT_WINDOW> führen wir die Security-Sanitation des Repositories durch. Dabei rotieren wir alle Secrets, bereinigen die Git-Historie und aktivieren Push Protection.

**Aktionen für euch:**
1. Während des Fensters bitte keine Commits/Pushes.
2. Nach Abschluss **neu klonen**:
```bash
git clone <REMOTE> cleanroom
```
3. Alte lokale Klone archivieren/löschen.

Wir melden uns mit „Done“ + CI-Status, sobald alles abgeschlossen ist. Fragen jederzeit an `<SECURITY_OWNER>`.

Danke & viele Grüße
`<PROJECT_MANAGER>`

## PR-Bodies (final)

### PR #1 – Dry Run
**Zweck**
Erster Struktur-PR, der neue Dokumentorganisation, Secret-Sanitation-Vorbereitung und Gitignore-Anpassungen vorschlägt, ohne produktive Dateien zu löschen.

**Checkliste**
- [ ] Build/Test laufen grün (CI + lokaler Pytest)
- [ ] Keine Secrets oder vertraulichen Werte verbleiben im Diff
- [ ] Neue Doc-Pfade stimmen mit Migration Map überein
- [ ] `.gitignore` deckt Artefakte & Secrets konsistent ab
- [ ] Hinweise aus CLEANUP_PLAN.md umgesetzt, aber Phase-5-Löschungen noch ausstehend

**Done-Definition**
- CI-Pipeline erfolgreich (Tests, Lint, Security-Scan)
- Secretscanner (z. B. Gitleaks) ohne Treffer
- Dokumentationslinks angepasst und validiert
- Stakeholder haben Security Sanitation Plan freigegeben

**Rollback-Strategie**
- `git revert <merge-commit>`
- Vor Merge Branch-Snapshot taggen (`dryrun-before-cleanroom`)
- Bei vergessenen Pfaden: Follow-up-PR mit gezieltem Fix (keine Hotfixes auf Main)

**Referenzen**
- docs/CLEANUP_PLAN.md
- docs/MIGRATION_MAP.md
- docs/SECURITY_SANITATION_PLAN.md
- .gitignore.patch

### PR #2 – Security Sanitation
**Ziel**
Entfernt alle versionierten Secrets, rotiert Zugangsdaten und aktiviert Repo-weite Schutzmechanismen.

**Ablauf**
- Secrets rotieren (Owners informieren, Services umstellen).
- `git filter-repo` / BFG nach freigegebener Liste ausführen.
- Force-Push des bereinigten Historienstands (koordiniert).
- GitHub Secret Scanning + Push Protection aktivieren.
- Re-Clone-Anleitung an alle Beitragenden verteilen.
- Verifikation: Gitleaks, Trivy, Bandit, Pytest, Compose Smoke.

**Risiken**
- Fehlende Rotation → Produktionsausfall.
- Vergessenes Secret → erneuter Rewrite nötig.
- Force-Push bricht lokale Historien → klare Kommunikation.

**Kommunikation**
- Stakeholder-Mail (siehe oben).
- Hinweis im Slack/Teams-Kanal: „History rewritten – bitte neu klonen.“

**Rollback**
- Nutzung des gesicherten Mirror-Backups.
- Notfall-Tag `pre-sanitize` wiederherstellen, Force-Push rückgängig machen.

**Force-Push expected?**
Yes (coordinated) – nur nach expliziter Freigabe.
