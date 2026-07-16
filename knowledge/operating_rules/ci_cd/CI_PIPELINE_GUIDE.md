# CI Pipeline Guide

**Stand:** 2026-07-16

## Merge-relevante Pipeline

Das Repository besitzt einen kanonischen PR-CI-Pfad:

| Workflow | Check |
|---|---|
| `.github/workflows/ci.yml` | `ci (Unit/Integration + Lint gesammelt)` |
| `.github/workflows/policy-gate.yml` | `policy-gate` |

Beide Checks müssen dem aktuellen PR-Head-SHA zugeordnet und erfolgreich sein.
Andere Actions sind ergänzende Prüf- oder Automationspfade.

## Ergänzende Workflows

- `contracts.yml` und `python-compat.yml`: Verträge und Laufzeitkompatibilität
- `e2e.yml`, `e2e-tests.yml`, `e2e-happy-path.yaml`: E2E-Surfaces
- `gitleaks.yml`, `trivy.yml`, `security-scan.yml`, `codeql-python.yml`: Security
- `docs-hub-guard.yml`, `docs-conflict-guard.yml`, `core-guard.yml`: Guards
- `required-checks-audit.yml`: manueller Branch-Protection-Abgleich

## Diagnose

1. PR-Head-SHA und fehlenden/roten Check bestimmen.
2. Workflow-Run und Job-Logs für exakt diesen SHA lesen.
3. Trigger, Branch- und Path-Filter direkt in der YAML prüfen.
4. Lokale Reproduktion nur als Diagnose, nicht als Ersatz für GitHub-Checks verwenden.
5. Nach dem Fix aktuelle Checks erneut abwarten.

## Governance

Workflow-Inventar und Status stehen ausschließlich im
[GitHub Workflow Register](../../../docs/runbooks/GITHUB_WORKFLOW_REGISTER.md).
Entfernte oder historische Workflow-Namen dürfen nicht als aktive Pipeline
dokumentiert werden.
