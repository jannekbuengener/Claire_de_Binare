# Session 36 — Issue #1449: Policy-Gate RCA

**Datum:** 2026-04-06
**Issue:** #1449 — stability: investigate recurring policy-gate blockage
**Branch:** chore/session-36-close

---

## Ziel

Wiederkehrende policy-gate-Blockade als Blocker-Familie klassifizieren ohne PR-Disposition oder Workflow-Änderungen.

---

## Befund

Eine Blocker-Familie, vier strukturelle Ausprägungen — gemeinsamer Mechanismus: Kategorie fällt auf `core/service`-Default, kein Inferenz-Pfad greift, kein Override-Label vorhanden.

**A — Fehlende infra-only-Datei-Inferenz:**
`isInfraFile()` ist in policy-gate.yml Zeile 50 definiert, wird aber nie für automatische Kategorisierung genutzt. `infra-only` file-inference existiert nicht — nur `docs-only` und `workflows-only` werden automatisch erkannt (Zeilen 111–117).

**B — Mixed-file-set (infra + tests):**
`tests/`-Dateien gehören zu keiner privilegierten Kategorie → Mixed-PRs immer `core/service`.

**C — Skripte in nicht-privilegierten Pfaden:**
`knowledge/operations/disaster_recovery/*.ps1` ist weder `docs/`, noch `infrastructure/`, noch `.github/workflows/` → immer `core/service`.

**D — Dependabot-Labels nicht als Override:**
Labels `dependencies`, `python` nicht in Override-Liste (`manual-approval`, `allow-core-change`).

## Stichprobe

- #1397 → Ausprägung C (`.ps1` unter `knowledge/operations/`)
- #1285 → Ausprägung A+B (infra + tests)
- #1237, #1217 → core/service + weitere CI-Failures (nicht allein policy-gate)
- #1365/#1366/#1367 → Ausprägung D (Dependabot)
- #1396 → PASS (alle Dateien `docs/` → file-inference korrekt)
- #1286 → PASS (Label `allow-core-change`)
- #1398 → PASS (Label `manual-approval`)

## Nicht die Ursache

- Workflow-Safety-Regeln (pull_request_target / write-all / permissions): kein FAIL-PR ändert Workflow-Dateien
- PR-Intent-Routing-Workflows: setzen keine Override-Labels

## Output

Vollständiger RCA-Kommentar in Issue #1449 gepostet.

---

## Restunsicherheiten

- #1237 und #1217: CI-Failure-Ursachen nicht untersucht (außerhalb Scope)
- `actions/github-script` Node.js 20 Deprecation (bis 2026-06-02 Pflicht-Upgrade)
