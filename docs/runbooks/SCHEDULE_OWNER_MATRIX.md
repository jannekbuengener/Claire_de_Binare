# Zeitplan & Owner-Matrix

| Schritt | Verantwortlich | Start | Ende | Abhängigkeit | Beweis der Wirkung |
|---------|----------------|-------|------|--------------|---------------------|
| Dry-Run Branch anlegen | Dev Lead | T+0 09:00 | T+0 09:30 | Pre-Flight-Checklist | `git branch` Screenshot |
| Dry-Run PR erstellen | Docs Lead | T+0 10:00 | T+0 11:00 | Branch erstellt | PR Link, CI Badge grün |
| Dry-Run Review & Merge | Dev + Docs + Security | T+0 11:00 | T+0 14:00 | PR offen | Review-Kommentare abgearbeitet |
| Sanitation Vorbereitung (Backup, Freeze) | Security Lead | T+1 09:00 | T+1 10:00 | Dry-Run gemerged | Backup-Log, Freeze-Meldung |
| Secret Rotation | Ops Lead | T+1 10:00 | T+1 11:00 | Wartungsfenster frei | Rotation-Log, Healthchecks |
| History Rewrite & Force-Push | Security Lead | T+1 11:00 | T+1 12:30 | Rotation abgeschlossen | Gitleaks 0, Push Protection On |
| Re-Clone Kommunikation | Project Manager | T+1 12:30 | T+1 13:00 | Force-Push done | Mail/Slack Sendebestätigung |
| Doku-Kuration Moves | Docs Team | T+2 09:00 | T+2 12:00 | Sanitation done | Link-Checker „All links OK“ |
| Doku PR Review & Merge | Docs Lead + Dev Lead | T+2 13:00 | T+2 16:00 | PR erstellt | Review + CI grün |
| Finalisierung (Tag, Release Notes, Roadmap) | Project Manager | T+3 09:00 | T+3 11:00 | Alle Tracks abgeschlossen | `git tag -l v1.0.0-cleanroom`, Release Notes veröffentlicht |
