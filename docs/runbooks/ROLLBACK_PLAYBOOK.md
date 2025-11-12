# Rollback Playbook

## Szenario 1: PR Dry-Run revertieren
- Auslöser: Reviewer findet Blocker, PR darf nicht mergen.
- Schritte:
  1. Lokal: `git checkout feature/cleanroom-dryrun`
  2. `git revert HEAD`
  3. `git push`
  4. PR schließen, Kommentar: „Rollback durchgeführt, Neuer PR folgt.“
- Kommunikation: Kurzmeldung im Team-Channel mit Link zum Revert-Commit.
- Beweis: PR Status „Closed“, revert commit existiert.

## Szenario 2: History-Rewrite rückgängig machen
- Auslöser: Nach Force-Push treten unerwartete Fehler auf.
- Schritte:
  1. Lokales Mirror-Backup verwenden:
     ```bash
     git remote add rollback ../repo-cleanroom-backup.git
     git fetch rollback
     git push --force origin rollback/<MAIN>:<MAIN>
     ```
  2. Stakeholder informieren: „Rewrite revertiert, bitte alte Klone weiterverwenden.“
- Kommunikationstext: 
  > „Rewrite rückgängig gemacht, Repository entspricht dem Stand vor `<timestamp>`. Keine weiteren Aktionen nötig.“
- Beweis: Git log zeigt ursprüngliche Commit-IDs.

## Szenario 3: Dokumentpfade falsch verschoben
- Auslöser: Link-Checker zeigt 404 nach Merge.
- Schritte:
  1. `git revert <commit>` (der betroffene Move-Commit).
  2. Alternativ in neuem Fix-PR Pfad korrigieren.
  3. Link-Checker erneut laufen lassen.
- Kommunikation: Kommentar im PR + Verweis auf Link-Checker-Log.
- Beweis: Link-Check „All links OK“, betroffene Dokumente wieder erreichbar.
