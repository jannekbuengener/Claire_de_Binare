# CI Index

## Local Docker CI (Phase 1)

- Entry: [`ci/README.md`](../../ci/README.md)
- Front door (Windows): `pwsh -File ci/scripts/run_all.ps1`
- Make: `make ci-local` / `ci-local-stage` / `ci-local-report` / `ci-local-clean`
- Local evidence under `ci/artifacts/<run_id>/` is **not** a GitHub Required Check.
- Branch Protection and GitHub workflows remain unchanged in Phase 1.
- See [merge_policy_ci_gate.md](../runbooks/merge_policy_ci_gate.md) § Local Docker CI Phase 1.

## Local status publisher (Phase 3a)

- Doc: [`local-status-publisher.md`](local-status-publisher.md)
- Entry: `python -m ci.publisher` / `pwsh -File ci/scripts/publish_status.ps1`
- Make: `ci-local-publish-dry-run` / `ci-local-publish` / `ci-local-publish-inspect`
- Publishes a **non-required** Commit Status only after fail-closed evidence validation.
- Preferred preview context: `cdb-local-ci-preview`. Branch Protection unchanged.

## Kanonischer PR-Merge-Vertrag

SSOT: [`merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md). Der
einzige merge-relevante Required Context auf `main` ist `cdb-local-ci`
(Commit Status, lokaler Publisher, exakter PR-Head-SHA), live verifizierbar
via `gh api`.

| Quelle | Check-Kontext | Typ |
|---|---|---|
| Local CI Status Publisher | `cdb-local-ci` | Commit Status |

| Workflow | Rolle | Trigger |
|---|---|---|
| [`ci.yml`](../../.github/workflows/ci.yml) | Hosted Actions, advisory | `pull_request`, gefilterter `push` |
| [`policy-gate.yml`](../../.github/workflows/policy-gate.yml) | Hosted Actions, advisory | `pull_request` |

`ci.yml` und `policy-gate.yml` sind seit Migration #4169 **nicht mehr**
branch-protection-required. Sie bleiben als Workflow-Inhalt / Safety-Gates
nützlich (Hosted-Actions-Signal), ersetzen aber nicht `cdb-local-ci`. Ein
rotes/blockiertes Hosted-Actions-Billing-/Runner-Lock ist eine
Infrastruktur-Bedingung, kein Code-Fehler, und darf nicht mit einem
fehlenden/roten `cdb-local-ci` verwechselt werden.

## Ergänzende Prüfungen

| Bereich | Workflows |
|---|---|
| Verträge/Kompatibilität | `contracts.yml`, `python-compat.yml` |
| E2E | `e2e.yml`, `e2e-tests.yml`, `e2e-happy-path.yaml` |
| Security | `gitleaks.yml`, `trivy.yml`, `security-scan.yml`, `codeql-python.yml` |
| Guards | `repository-canon-guard.yml`, `docs-conflict-guard.yml`, `core-guard.yml` |
| Audit | `required-checks-audit.yml`, `governance-audit.yml` |

Diese Prüfungen können Fehler oder Findings liefern, sind aber keine
Ersatzquelle für den einzigen branch-protected Check-Kontext `cdb-local-ci`.

## Einstieg bei Fehlern

1. `cdb-local-ci` live für den exakten PR-Head-SHA prüfen (`gh api`), nicht
   aus veralteten Tabellen ableiten.
2. Job- und Step-Logs des konkreten Runs (Hosted Actions, advisory) lesen.
3. [Merge-Policy-Runbook](../runbooks/merge_policy_ci_gate.md) anwenden.
4. Bei Inventar- oder Trigger-Drift das
   [Workflow-Register](../runbooks/GITHUB_WORKFLOW_REGISTER.md) prüfen.
