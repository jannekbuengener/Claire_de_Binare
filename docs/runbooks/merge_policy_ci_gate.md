# Merge Policy and CI Gate

## Delivery slices versus merge candidates

Ein normaler Issue-Slice wird in den durch `cdb-pr-router` bestimmten PR
geliefert. Targeted Tests, betroffener Lint/Format-Scope und
`git diff --check` reichen für den Slice-Handoff; Full Fast-CI,
`cdb-local-ci`, Merge und Issue-Closure sind dabei `false`.

### Slice Validation vs Merge Acceptance (#4204)

| Oberfläche | Zweck | Merge-Evidence? |
|---|---|---|
| **Slice Validation** (`--profile slice` / `--slice`) | Deterministische, path-/lane-/profile-basierte Testgruppen für schnelle Entwicklungsprüfungen. Policy: `ci/config/slice_validation_policy.v1.yaml`. Report: `reports/slice_selection.json` mit `merge_evidence=false`. | **Nein** — Publisher lehnt `merge_evidence=false` und `profile=slice` ab. |
| **Final-Head / Fast-CI** (`--profile fast`) | Unveränderter vollständiger Unit-Selektor `pytest -q -k "not test_mcp_time_server_runtime"` plus lint/docs/governance. | Nur nach Publish als App-gebundenem Check Run `cdb-local-ci` (`app_id=4410232`) auf exaktem Head. |

Fail-closed: unbekannte/nicht klassifizierte Pfade, Policy-/Schema-/Parsefehler
oder Runtime-/Risk-/Docker-Pfade erzwingen automatisch das vollständige
Fast-CI-Unit-Profil. Marker dürfen ergänzend dokumentiert sein, sind aber
keine alleinige Auswahlgrundlage. Slice-Grün ersetzt niemals Final-Head-
Abdeckung.

Transport-`steward_state=merge_candidate` startet die Acceptance-Phase
`COMPLETENESS_REVIEW` (`cdb-pr-completeness-review`). Nur ein schema-valides
Completeness-Verdikt `MERGE_CANDIDATE` darf in die Conductor-Phase
(`cdb-batch-merge-conductor`: Freeze → Main-Integration → Final Validation →
`FINAL_HEAD_READY_FOR_APPROVAL`). Conductor mergt nicht. Danach folgen
HEAD-gebundenes APPROVE durch `cdb_final_head_pr_approval_gate` und regulärer
Merge durch `cdb_final_head_merge_executor`
(SSOT: `docs/contracts/final_head_merge_pipeline.v1.md`). Slice-Evidence darf
nie als Final-Head-Evidence wiederverwendet werden. Der finale Nachweis bindet
sowohl PR-Head als auch den integrierten Base-SHA. Head-/Base-Drift erzwingt
erneute Completeness Review und invalidiert Approval.

## Verbindlicher Vertrag

Für Pull Requests auf `main` gilt genau ein merge-relevanter Required Context
(Branch Protection, live via `gh api`):

| Quelle | Context | Typ |
|---|---|---|
| Local CI Status Publisher | `cdb-local-ci` | **GitHub App Check Run** (`app_id=4410232`) |

Die früheren Required Checks `ci (Unit/Integration + Lint gesammelt)` und
`policy-gate` sind **nicht mehr** branch-protection-required (Migration #4169).
Ab #4401 startet die breite hosted Fast-CI (`ci.yml`) **nicht** mehr auf
jedem `pull_request` — sie bleibt als post-merge/`workflow_dispatch`-Mirror
für den Squash-Tip auf `main`. `policy-gate.yml` bleibt ein leichter
hosted PR-Safety-Gate (Labels/Scope/Workflow-Permissions). Beide ersetzen
den Required Context `cdb-local-ci` nicht.

**Post-#4170 Phase D (live):** Branch Protection akzeptiert `cdb-local-ci`
ausschließlich als Check Run der GitHub App `4410232`. Ein gleichnamiger
**Commit Status ist wirkungslos** für den Merge-Gate. Kanonischer Publish:

```powershell
python -m ci.publisher publish `
  --publisher-backend check-run `
  --evidence-dir ci/artifacts/<run_id> `
  --commit-sha <exact_pr_head> `
  --pr-number <n>
```

Auto-Mint aus `CDB_GH_APP_ID` / `CDB_GH_APP_INSTALLATION_ID` /
`CDB_GH_APP_PRIVATE_KEY_PATH` (siehe
[`cdb_local_ci_app_check_run_cutover.md`](cdb_local_ci_app_check_run_cutover.md),
[`local-status-publisher.md`](../ci/local-status-publisher.md)).
`--publisher-backend commit-status` bleibt nur als Legacy/Debug-Pfad und
erfüllt die Required Protection **nicht**.

Lint/Format (orchestrator stage `lint`, Issue #4206): Black und Ruff kommen
ausschließlich aus dem Pin in `requirements-dev.txt`. Black läuft als
`python -m black --check` auf dem Changed-File-Satz mit hartem Timeout
(Default 300s); Timeout und Toolauflösungsfehler sind Stage-`FAIL` mit Reason
Code, niemals Fake-Green. Details: `ci/README.md` § Black toolchain SSOT.

## Merge-Gates

Vor einem Merge muss `cdb-local-ci` für den aktuellen PR-Head-SHA erfolgreich
gesetzt sein (Publisher nach validierter lokaler Evidence + Policy-Mirror).
Alte grüne GitHub-Actions-Runs, lokale Tests ohne Publish oder andere Actions
ersetzen diesen Context nicht.

Der on-demand Workflow `required-checks-audit.yml` kann die Konfiguration
prüfen, erzeugt selbst aber keinen merge-relevanten Ersatzcheck.

## Sicherheitsmodell

- Untrusted Fork-Code darf nicht auf privilegierten self-hosted Runnern laufen.
- `pull_request_target` darf keinen untrusted Checkout ausführen
  (`policy-gate.yml` prüft das weiterhin).
- Code-Owner- und Review-Signale bleiben wichtig, auch wenn die aktuelle Branch
  Protection keine Mindestzahl genehmigender Reviews erzwingt.
- Required-path Publish (`cdb-local-ci`) erzwingt `--pr-number > 0` und den
  lokalen Policy-Gate-Mirror (`tools/ci/policy_gate_local.py`).

## Diagnose

1. PR-Head-SHA ermitteln.
2. App-gebundenen Check Run `cdb-local-ci` (`app_id=4410232`) für exakt
   diesen SHA prüfen (`gh api repos/.../commits/<sha>/check-runs`).
3. Fehlenden Check Run von einem fehlgeschlagenen Check Run unterscheiden.
   Ein gleichnamiger Commit Status zählt nicht.
4. Publisher-Evidence und Policy-Mirror-Fail prüfen.
5. Erst nach erfolgreichem aktuellem App-Check-Run `cdb-local-ci` mergen.

## Final-Head Approval and Merge Pipeline

There is exactly one canonical final merge executor:
`cdb_final_head_merge_executor` (Cursor display: Merge Agent).
Capability alone does **not** authorize any session to bypass
PR Reviewer → Merge Agent.

Required sequence after Completeness `MERGE_CANDIDATE`:

1. `cdb-batch-merge-conductor` prepares Final Head (freeze, integrate main,
   Full Fast-CI, publish/verify App Check Run `cdb-local-ci` /
   `app_id=4410232`) and stops at `FINAL_HEAD_READY_FOR_APPROVAL`.
2. `cdb_final_head_pr_approval_gate` (PR Reviewer) issues GitHub APPROVE
   bound to the exact final `HEAD_SHA` (Risk LOW, no blockers). Cannot merge.
3. `cdb_final_head_merge_executor` re-verifies approval HEAD binding, drift,
   required Check Run, reviews, and mergeability, then runs
   `gh pr merge <PR> --squash --delete-branch`. Cannot approve. Never `--admin`.
4. `cdb-session-close` verifies live MERGED and closes only eligible
   `SLICE_DELIVERED` issues.

Cloud Reviewer/Merger are repo-only; they consume published Check Run
evidence and must not require local `cdb_context` or fabricate CI.

`--admin` is **never** a bypass for a missing/red/stale `cdb-local-ci`.
Fake-green claims and merging an untested head are forbidden.

### Honest handoff when Final-Head readiness is missing

If Conductor cannot publish/verify `cdb-local-ci` or Final-Head gates fail:
leave the PR open, do not use `--admin`, do not loop the same blocked
attempt, and report `DONE_PR_OPEN_MERGE_HANDOFF` with the exact missing
capability. See `.cursor/rules/CDB-Checks-and-Merge-Rule.mdc` for the status
taxonomy (`DONE_MERGED_CLOSED`, `DONE_PR_OPEN_MERGE_HANDOFF`,
`BLOCKED_REQUIRED_STATUS`, `BLOCKED_AUTH_PUBLISHER`, `HOLD_SCOPE_OR_REVIEW`,
`HOLD_MAIN_OR_HEAD_DRIFT`).

### Auth token override for the publisher

The publisher (`ci.publisher`, see
[`local-status-publisher.md`](../ci/local-status-publisher.md)) reads its
token only from the environment, in this order: `GITHUB_TOKEN`, then
`GH_TOKEN`, else falling back to `gh auth token`. A fine-grained PAT with
**Commit statuses: Write** is sufficient; no admin, branch-protection, or
contents-write scope is required or should be granted for publishing.
Never pass a token as a CLI argument or commit it to the repo.

### Merge waves

When merging multiple PRs in sequence: after each squash merge, rebase the
next PR onto the updated `main` and fully revalidate — rerun local Fast-CI
and confirm `cdb-local-ci` SUCCESS on the new head — before merging the next
PR in the wave. Do not batch-merge later PRs on evidence collected before
the wave started; treat `main` movement mid-wave as `HOLD_MAIN_OR_HEAD_DRIFT`
until revalidated.

### Anti-repush

After `gh pr merge --squash --delete-branch`, do not automatically re-push,
recreate, or resurrect the deleted remote branch. If follow-up work is
needed on the same topic, open a new branch explicitly instead of reviving
the merged/deleted one.

## Dokumentationspflicht

Änderungen an Check-Namen, Triggern oder Branch Protection müssen gemeinsam in
`docs/ci/index.md`, diesem Runbook, dem Workflow-Register und den
Required-Check-Contract-Tests aktualisiert werden.

## Local Docker CI + Status Publisher

Lokale Docker-CI unter `ci/` (siehe [`ci/README.md`](../../ci/README.md)) und
Publisher (siehe [`docs/ci/local-status-publisher.md`](../ci/local-status-publisher.md)):

- Lokale Evidence allein autorisiert keinen Merge; erst der published
  App-gebundene Check Run `cdb-local-ci` (`app_id=4410232`) ist der Required
  Context.
- Branch Protection: context `cdb-local-ci` mit `checks[].app_id == 4410232`.
- Dirty worktree ⇒ lokale Evidence `BLOCKED` und kein Publish.
- Publish-Pfad erzwingt Policy-Gate-Mirror (Parität zu
  `.github/workflows/policy-gate.yml`).
- Kein Fake-Green: dirty, stale, SHA-Mismatch, Hash-Mismatch, required SKIPPED,
  Anti-Replay, fehlende PR-Nummer oder Policy-Gate-Fails blockieren Publish.
- Lokales CodeQL/SARIF ersetzt nicht den GitHub Security-Tab.

Live Branch-Protection-Hinweis (reverify with `gh api`):
`required_status_checks.checks == [{"context":"cdb-local-ci","app_id":4410232}]`,
`strict: true`.

Windows front door:

```powershell
pwsh -File ci/scripts/run_all.ps1 -Profile fast
python -m ci.publisher publish `
  --publisher-backend check-run `
  --evidence-dir ci/artifacts/<run_id> `
  --commit-sha <exact_pr_head> `
  --pr-number <n>
```
