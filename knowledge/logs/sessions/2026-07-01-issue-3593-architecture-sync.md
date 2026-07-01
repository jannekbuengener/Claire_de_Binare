# Session Log: 2026-07-01 — Issue #3593 Architecture Docs Sync

## Auftrag

Docs-only Reconciliation: `ARCHITECTURE_MAP`, `ARCHITECTURE_COCKPIT` und `SERVICE_CATALOG` nach Dependabot-Merges #3528 (Redis 8.8) und #3530 (Postgres 18) sowie Control-Reconcile #3602/#3603 synchronisieren. Closes #3593.

## Ausgangslage

- PR #3528 (`9a4ea814`): Redis `7.4.9-alpine` → `8.8.0-alpine` in Compose + `security-scan.yml`; `SERVICE_CATALOG` nicht nachgezogen
- PR #3530 (`7973a66f`): Postgres `15.17-alpine` → `18.4-alpine` in Compose; `SERVICE_CATALOG` Postgres-Zeile aktualisiert, Redis blieb `7.4.8-alpine`
- PR #3602/#3603: `CONTROL_REGISTER` + Ledger für Control-Reconcile — `ARCHITECTURE_MAP` explizit out of scope (#3593)
- `origin/main`: `f5cb5932`

## Befund (real drift)

| Datei | Drift | Fix |
|---|---|---|
| `knowledge/governance/SERVICE_CATALOG.md` | Redis `7.4.8-alpine` vs Compose `8.8.0-alpine` | → `redis:8.8.0-alpine` |
| `knowledge/ARCHITECTURE_MAP.md` | Kein Changelog/Image-SSOT-Hinweis für #3528/#3530 | Changelog + §7 Hinweis |
| `knowledge/ARCHITECTURE_COCKPIT.md` | Keine Links zu kanonischen Arch-Docs | Cross-Ref-Block ergänzt |

Out of scope: `redis_aof_corruption_recovery.md` (noch `7.4.9`), Runtime-Rebuilds #3592/#3594/#3600.

## Implementierung

| Datei | Änderung |
|---|---|
| `knowledge/governance/SERVICE_CATALOG.md` | Redis image + Changelog #3593 |
| `knowledge/ARCHITECTURE_MAP.md` | §7 Image-SSOT-Hinweis + Changelog |
| `knowledge/ARCHITECTURE_COCKPIT.md` | Kanonische Architektur-Docs Block |
| `CURRENT_STATUS.md` | Ledger-Eintrag #3593 |
| `knowledge/logs/sessions/2026-07-01-issue-3593-architecture-sync.md` | Dieses Log |

Branch: `docs/3593-architecture-sync` von `origin/main` (`f5cb5932`).

## Validation

- `git diff --check`: pass
- Stale image tags in primary architecture docs: none (`SERVICE_CATALOG` Redis `8.8.0-alpine`, Postgres `18.4-alpine`)
- Diff docs-only: 5 markdown files

## Safety Boundaries

- LR NO-GO unverändert
- Keine Compose/Docker/Runtime/Secret/DB-Mutation
- Redis = Runtime/Messaging; SurrealDB = Brain (unberührt)

## Merge / Close

- PR: #3604 MERGED
- Merge SHA: `f20ef70bd50fb5c648f054a8a9cb7464fdf8f458`
- Issue #3593: CLOSED (2026-07-01T00:12:51Z)
