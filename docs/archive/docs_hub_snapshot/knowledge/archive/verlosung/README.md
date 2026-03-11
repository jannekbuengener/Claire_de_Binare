
# Claire de Binare — GitHub Ops Pack

Dieses Paket richtet das Repo so ein, dass möglichst viel **nur über GitHub** läuft:
- Issue/PR Standards (Templates + DoD)
- CI (sanity checks + optional tests)
- Docker Build & Push nach GHCR
- Security Baseline (CodeQL + Dependency Review + Container CVE Scan)
- Governance-Automation: Milestone-Autofix aus `Phase X` im Issue-Titel

## Quick Start
1) Zip entpacken **im Repo-Root** (so dass `.github/` oben liegt).
2) Commit + Push auf deinen Branch.
3) In GitHub prüfen:
   - Actions → Workflows laufen durch
   - Security → Code scanning alerts (CodeQL) initialisiert sich nach dem ersten Run
   - Packages → GHCR bekommt Images bei Push auf `main`

## Hinweise
- Container Push/Scan ist auf `main` ausgelegt. PRs bauen nur (ohne Push).
- Für Project-Board-Automation ist ein extra Token nötig (optional, nicht aktiv in diesem Pack).
- `Issue Milestone Autofix`: erwartet Titel mit Muster `... - Phase <N> - ...`.

## Default-Mapping Phase → Milestone
- Phase 0 → M1
- Phase 1 → M2
- Phase 2 → M3
- Phase 3 → M4
- Phase 4 → M7
- Phase 5 → M8
- Phase 6 → M6
- Final → M9 (nicht automatisch, außer Titel enthält `Final`)
