## Summary
- [ ] Zweck des PRs klar beschrieben
- [ ] Rollback-Plan dokumentiert

## Required Checks (Non-Bypass)
- [ ] CI gruen (Tests, Lint)
- [ ] Write-Zonen-Validierung (scripts/validate_write_zones.sh) erfolgreich
- [ ] Secrets-Scan erfolgreich (truffleHog/detect-secrets)
- [ ] Conversations resolved
- [ ] Dev-Freeze geprueft (`.dev_freeze_status`), falls aktiv: Merge blockiert

## Approvals
- [ ] Reviews gemaess CODEOWNERS (>=2 fuer /governance und /core, sonst >=1)

## Notes
- Keine Direct/Force Pushes; PR-only Workflow.
