# Cleanroom Checklisten

## Pre-Flight (vor Start)
- [ ] Alle offenen PRs gemerged/geparkt (Beweis: GitHub PR-Liste leer/markiert).
- [ ] CI letzter Run erfolgreich (Beweis: CI Dashboard Screenshot).
- [ ] Mirror-Backup erstellt (`git clone --mirror`) (Beweis: Ordner + Log).
- [ ] Owner & Stakeholder bestätigen Teilnahme (Beweis: Slack/Mail-Thread).
- [ ] Wartungsfenster `<MAINT_WINDOW>` schriftlich bestätigt.

## During – Track 1 Dry-Run
- [ ] Branch `feature/cleanroom-dryrun` erstellt.
- [ ] `docs/CLEANUP_PLAN.md` hinzugefügt.
- [ ] `docs/MIGRATION_MAP.md` hinzugefügt.
- [ ] `docs/SECURITY_SANITATION_PLAN.md` hinzugefügt.
- [ ] `docs/PR_CLEANROOM_DRYRUN.md` hinzugefügt.
- [ ] `.gitignore` Patch eingefügt.
- [ ] Commit & Push erfolgreich.
- [ ] PR erstellt mit richtigen Labels/Milestone.
- [ ] CI auf PR grün.

## During – Track 2 Security-Sanitation
- [ ] Freeze kommuniziert.
- [ ] Neues Secret-Set generiert & verteilt (Beweis: Rotation-Log).
- [ ] filter-repo/BFG Trockentest (Beweis: lokale Repo-Logs).
- [ ] Gitleaks, Pytest, Compose Smoke erfolgreich.
- [ ] Push Protection aktiviert (Screenshot GitHub Settings).
- [ ] Force-Push koordiniert.
- [ ] Re-Clone-Kommunikation versendet.

## During – Track 3 Doku-Kuration
- [ ] MIGRATION_MAP Todos abgehakt.
- [ ] Markdown-Link-Check „All links OK“.
- [ ] Session-Memos kuratiert, Duplikate entfernt.
- [ ] PR erstellt mit Dokumentations-Checkliste.

## Post-Flight
- [ ] Gitleaks + Security Scan erneut (Beweis: Logs).
- [ ] Tag `v1.0.0-cleanroom` erstellt (`git tag`).
- [ ] Release Notes veröffentlicht.
- [ ] Roadmap N+1 aktualisiert (Beweis: Link/Doc).
- [ ] Risk Register aktualisiert (Risiken auf Grün/Gelb).
