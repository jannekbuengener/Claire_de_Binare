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
regulärer Squash-Merge). Slice-Evidence darf nie als Final-Head-Evidence
wiederverwendet werden. Der finale Nachweis bindet sowohl PR-Head als auch den
integrierten Base-SHA. Head-/Base-Drift erzwingt erneute Completeness Review.

## Verbindlicher Vertrag

Für Pull Requests auf `main` gilt genau ein merge-relevanter Required Context
(Branch Protection, live via `gh api`):

| Quelle | Context | Typ |
|---|---|---|
| Local CI Status Publisher | `cdb-local-ci` | **GitHub App Check Run** (`app_id=4410232`) |

Die früheren Required Checks `ci (Unit/Integration + Lint gesammelt)` und
`policy-gate` sind **nicht mehr** branch-protection-required (Migration #4169).
`ci.yml` und `policy-gate.yml` bleiben als Workflow-Inhalt / Safety-Gates
nützlich, ersetzen aber den Required Context nicht.

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

## Capability-based Autonomous Merge

Autonomous squash merge is **capability-based, not agent-type-based**. Any
session (local or cloud) may autonomously run
`gh pr merge <PR> --squash --delete-branch` once all of the following are
proven true for the exact PR head SHA:

1. PR is a frozen `merge_candidate` and
   `autonomous_regular_merge_allowed` applies to this task scope.
2. PR fully in approved scope, not draft, mergeable.
3. No blocking reviews / unresolved scope or governance blockers.
4. Full local Fast-CI PASS for the exact PR head.
5. Evidence bound to the exact PR head (no stale/other-SHA evidence).
6. Validated `main` unchanged since validation (no drift since evidence).
7. `cdb-local-ci` SUCCESS as App Check Run (`app_id=4410232`) on the exact
   PR head SHA (live via `gh api`). Same-named Commit Status is not enough.
8. The session can perform the regular squash merge itself (has merge
   permission) and can publish `cdb-local-ci` via `--publisher-backend
   check-run` / App auto-mint if it is still missing and the session holds
   bound evidence to do so.

`--admin` is **never** a bypass for a missing/red/stale `cdb-local-ci`.
Fake-green claims and merging an untested head are forbidden.

### Honest handoff when capability is missing

If a session lacks any gate above (no App Check Run publish capability,
no verifiable identity, evidence not bound to the exact head, publisher
auth blocked):
leave the PR open, do not use `--admin`, do not loop the same blocked
attempt, and report `DONE_PR_OPEN_MERGE_HANDOFF` with the exact missing
capability and the next command for a capable session/human. See
`.cursor/rules/CDB-Checks-and-Merge-Rule.mdc` for the full status taxonomy
(`DONE_MERGED_CLOSED`, `DONE_PR_OPEN_MERGE_HANDOFF`, `BLOCKED_REQUIRED_STATUS`,
`BLOCKED_AUTH_PUBLISHER`, `HOLD_SCOPE_OR_REVIEW`, `HOLD_MAIN_OR_HEAD_DRIFT`).

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
