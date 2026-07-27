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

| Workflow | Check-Kontext | Trigger |
|---|---|---|
| [`ci.yml`](../../.github/workflows/ci.yml) | `ci (Unit/Integration + Lint gesammelt)` | `pull_request`, gefilterter `push` |
| [`policy-gate.yml`](../../.github/workflows/policy-gate.yml) | `policy-gate` | `pull_request` |

Die frühere parallele Legacy-Pipeline wurde entfernt. Es gibt nur noch einen
kanonischen CI-Pfad; Diagnose, Branch Protection und Dokumentation müssen sich
auf die beiden Check-Kontexte oben beziehen.

## Ergänzende Prüfungen

| Bereich | Workflows |
|---|---|
| Verträge/Kompatibilität | `contracts.yml`, `python-compat.yml` |
| E2E | `e2e.yml`, `e2e-tests.yml`, `e2e-happy-path.yaml` |
| Security | `gitleaks.yml`, `trivy.yml`, `security-scan.yml`, `codeql-python.yml` |
| Guards | `repository-canon-guard.yml`, `docs-conflict-guard.yml`, `core-guard.yml` |
| Audit | `required-checks-audit.yml`, `governance-audit.yml` |

Diese Prüfungen können Fehler oder Findings liefern, sind aber keine
Ersatzquelle für die beiden branch-protected Check-Kontexte.

## Einstieg bei Fehlern

1. Betroffenen Check-Kontext und Commit-SHA bestimmen.
2. Job- und Step-Logs des konkreten Runs lesen.
3. [Merge-Policy-Runbook](../runbooks/merge_policy_ci_gate.md) anwenden.
4. Bei Inventar- oder Trigger-Drift das
   [Workflow-Register](../runbooks/GITHUB_WORKFLOW_REGISTER.md) prüfen.
