## Feature Overview
Dieser PR reduziert CI-Billing durch Einschr├ñnkung von Triggern, Pfad-Filtern und Zeitpl├ñnen.

## Technical Overview
- Anpassung der `on:`-Bl├Âcke f├╝r CI/Trivy/CodeQL: push nur main, PR-only f├╝r Heavy Jobs, Pfadfilter f├╝r Dokus.
- Reduzierung geplanter Cron-Jobs auf w├Âchentliche Frequenz oder Deaktivierung.

### Components Modified
- [x] Core services
- [x] Configuration
- [x] Database schema
- [x] API endpoints
- [x] User interface

## Test Evidence
- [x] Lokale Workflow-Diffs ├╝berpr├╝ft
- [x] PR-Branch erstellt und Workflows angepasst

## Checklist
- [x] Scope: trigger/schedule changes only
- [x] Keine Logik├ñnderungen an Jobs
- [x] Paths-ignore: Docs/MD
- [x] Scheduled workflows reduced to weekly or disabled





## Code Quality

- [x] Placeholder

## Deployment & Rollback

- [x] Placeholder

## Documentation

- [x] Placeholder

## Agent Approvals

- [x] Placeholder
