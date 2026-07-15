# CI Required Checks Audit (main) - 2026-02-19

## Scope / Constraints
- Read-only Audit: Branch Protection + Required Checks + Promotion-Plan.
- Keine Änderung an Repo-Settings, Workflows, Docker/Compose/Dockerfile oder Trading-Logik.

## Step 0 - Hygiene
- `git status -sb` -> `## main...origin/main` (clean).
- `git pull --ff-only` -> `Already up to date.`

## Step 1 - IST Branch Protection (main)
Snapshot:
- Timestamp: `2026-02-19 18:12:41 +01:00`
- Source command:

```bash
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection > /tmp/main_protection.json
```

Extracted state (`/tmp/main_protection.json`):

### required_status_checks
- `strict: true`
- required contexts (exact strings):
  - `ci (Unit/Integration + Lint gesammelt)`

### required_pull_request_reviews
- `dismiss_stale_reviews: false`
- `require_code_owner_reviews: false`
- `require_last_push_approval: false`
- `required_approving_review_count: 0`

### restrictions
- `null` (keine Branch-Restrictions gesetzt)

## Step 2 - Mapping required checks -> Workflows/Jobs

### 2.1 Aktuell required contexts
| Check-Name | Workflow-Datei | Jobname | Trigger (PR/push/schedule/dispatch) | Notes (matrix/double) |
|---|---|---|---|---|
| `ci (Unit/Integration + Lint gesammelt)` | `.github/workflows/ci.yml` | Job-ID `ci`, Job-Name `ci (Unit/Integration + Lint gesammelt)` | `pull_request` auf `main`; `push` mit `paths`-Filter (`core/**`, `services/**`, `tests/**`, `infrastructure/**`, `.github/workflows/**`, `requirements*.txt`, `pyproject.toml`) | Kein Matrix-Job in diesem Workflow (single job). Check-Name ist 1:1 gleich dem required context. |

Evidence (1:1 Check-Name):
- `gh run view 22191851170 --json workflowName,jobs,event,headBranch,conclusion,url`
- Result: Workflow `ci`, Job-Name `ci (Unit/Integration + Lint gesammelt)`.

### 2.2 Promotion-Kandidaten (noch nicht required)
| Check-Name | Workflow-Datei | Jobname | Trigger (PR/push/schedule/dispatch) | Notes (matrix/double) |
|---|---|---|---|---|
| `trivy (kritische CVEs/Supply-Chain)` | `.github/workflows/trivy.yml` | Job-ID `trivy-image`, Job-Name `trivy (kritische CVEs/Supply-Chain)` | `push` auf `main`/`release/*` (nur bei `Dockerfile`, `infrastructure/**`, `services/**`), `schedule`, `workflow_dispatch` | Kein PR-Trigger aktuell. Job ist aktuell non-blocking (`continue-on-error: true`, Trivy `exit-code: "0"`). |
| `E2E Happy Path` | `.github/workflows/e2e-happy-path.yaml` | Job-ID `e2e_happy_path`, Job-Name `E2E Happy Path` | `pull_request` auf `main`, `push` auf `main`, `schedule`, `workflow_dispatch` | Kein Matrix-Job. Step-level Skips (docs-only, fork-PR). Fail-closed Guard für protected STUB ist vorhanden. |

Evidence (1:1 Check-Namen):
- `gh run view 22191868199 --json workflowName,jobs,event,headBranch,conclusion,url` -> Job `trivy (kritische CVEs/Supply-Chain)`
- `gh run view 22191851120 --json workflowName,jobs,event,headBranch,conclusion,url` -> Job `E2E Happy Path`

### 2.3 Doppelungen / Überschneidungen
- Trivy erscheint in zwei Pfaden:
  - Standalone: `.github/workflows/trivy.yml` -> `trivy (kritische CVEs/Supply-Chain)`
  - Zentraler Pipeline-Workflow: `.github/workflows/ci.yaml` -> `Container Scan (Trivy)`
- E2E hat mehrere Workflows:
  - `.github/workflows/e2e-happy-path.yaml`
  - `.github/workflows/e2e-tests.yml`
  - `.github/workflows/e2e.yml`
- Matrix-Beispiel (nicht aktuell required): `.github/workflows/ci.yaml` Job `Tests (Python ${{ matrix.python-version }})` erzeugt mehrere Check-Runs.

## Step 3 - Risikoanalyse (determinism/stability)

### A) Flaky / secrets-abhängig
- `E2E Happy Path` nutzt required secrets (`SMTP_*`, `ALERT_EMAIL_TO`, `MEXC_*`) im Preflight.
- Fork-PRs laufen explizit in `NON-BLOCKING / STUB ONLY`-Pfad (Step-Skip mit success); dadurch ist "green" nicht automatisch gleich "REAL E2E".
- In PR-Kontexten kann docs-only bewusst als success mit Skip enden (deterministisch, aber reduzierte Testabdeckung).

### B) Heavy checks
- `trivy` ist DB-/scanner-lastig (Cache, JSON+SARIF, Upload), damit potenziell schwankungsanfälliger als reines Lint/Test.
- Separate Trivy-Implementierungen (`trivy.yml` und `ci.yaml`) erzeugen Governance-Komplexität.

### C) Skip-/Trigger-Risiken
- `trivy.yml` hat keinen `pull_request`-Trigger und `push`-path-Filter. Ein required Check muss aber für PRs deterministisch lieferbar sein.
- `ci.yml` hat für `push` einen path-filter; für PR auf `main` läuft es immer (gut für Required-Check-Stabilität).
- `E2E Happy Path` ist absichtlich "always run" auf `push main` ohne `paths-ignore`, aber kann Schritt-seitig skippen.

## Step 4 - Deterministischer Promotion Plan (Trivy + E2E)

### Gate-Definition (für jeden Kandidaten-Check)
Promotion ist nur erlaubt, wenn **alle** Bedingungen erfüllt sind:

1. **Main-Stability Gate**
   - Entweder `10` aufeinanderfolgende erfolgreiche Runs auf `main` (Events: `push` oder `workflow_dispatch`)
   - Oder `7` volle Kalendertage ohne nicht-success Conclusion im selben Event-Set.

2. **PR-Stability Gate**
   - `3` aufeinanderfolgende erfolgreiche `pull_request`-Runs mit exakt gleichem Check-Namen.

3. **Determinism Gate**
   - Check muss in allen relevanten Kontexten verlässlich emitted werden (kein "missing required check").
   - Kein stilles Fail-Open Verhalten.

4. **Rollback Trigger (global)**
   - `2` Failures innerhalb `24h` ohne Code-Änderung im betroffenen Bereich (Flake-Indikator), oder
   - Secrets-/Guard-Regression (z.B. fail-closed nicht wirksam, protected run fällt auf STUB zurück).

### A) Trivy Promotion Kriterien (`trivy (kritische CVEs/Supply-Chain)`)
Zusatzkriterien vor Promotion:
- Der Check muss auf `pull_request` und `main` verfügbar sein (gleicher Check-Name).
- Der Check muss policy-wirksam sein (disallowed Findings dürfen nicht dauerhaft durch `continue-on-error` + `exit-code: 0` neutralisiert werden).

Aktueller Snapshot-Status:
- Main-Streak (push/dispatch auf `main`): `1`
- PR-Streak: `0`
- Ergebnis: **nicht promotionsreif**.

### B) E2E Promotion Kriterien (`E2E Happy Path`)
Zusatzkriterien vor Promotion:
- REQUIRED_SECRETS für protected Kontexte vorhanden und stabil:
  - `SMTP_FROM`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_EMAIL_TO`, `MEXC_API_KEY`, `MEXC_API_SECRET`
- Fail-closed Guard bleibt aktiv (`Fail closed on protected STUB mode`).
- REAL-Preflight in protected Kontexte konsistent (kein protected STUB-Fall).

Aktueller Snapshot-Status:
- Main-Streak (push/dispatch auf `main`): `6`
- PR-Streak: `6`
- Ergebnis: **nahe dran, aber Main-Gate (10) noch nicht erreicht**.

## Operativer Promotionsablauf (ohne Umsetzung in diesem PR)
1. Täglich Gate-Metriken mit `gh run list`/`gh run view` evaluieren.
2. Erst bei erfüllten Gates Promotion-Change in separatem PR vorbereiten.
3. Branch Protection erst dann erweitern um:
   - `trivy (kritische CVEs/Supply-Chain)`
   - `E2E Happy Path`
4. Nach Promotion 7 Tage enges Monitoring; bei Rollback-Triggern sofort Demotion in separatem Incident-PR.

## Reproduzierbarkeit (Commands)
```bash
# Hygiene
git status -sb
git pull --ff-only

# Branch protection snapshot
gh api repos/jannekbuengener/Claire_de_Binare/branches/main/protection > /tmp/main_protection.json

# Workflow inventory
gh workflow list
rg --files .github/workflows

# Check-Name <-> Job Evidence (Beispiel-Runs)
gh run view 22191851170 --json workflowName,jobs,event,headBranch,conclusion,url
gh run view 22191868199 --json workflowName,jobs,event,headBranch,conclusion,url
gh run view 22191851120 --json workflowName,jobs,event,headBranch,conclusion,url

# Stabilitätsdaten
gh run list --workflow "E2E Happy Path" --limit 30 --json databaseId,conclusion,event,headBranch,createdAt,displayTitle
gh run list --workflow "trivy" --limit 30 --json databaseId,conclusion,event,headBranch,createdAt,displayTitle
```

## Step 5 - No-Change Statement
- In diesem Audit wurden **keine** Repo-Settings/Branch-Protection-Settings geändert.
- Keine Workflow-, Docker/Compose-, Dockerfile- oder Trading-Logic-Änderung.
- Output ist rein dokumentarisch.
