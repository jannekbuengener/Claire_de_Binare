# Merge Policy and CI Gate

## Delivery slices versus merge candidates

Ein normaler Issue-Slice wird in den durch `cdb-pr-router` bestimmten PR
geliefert. Targeted Tests, betroffener Lint/Format-Scope und
`git diff --check` reichen für den Slice-Handoff; Full Fast-CI,
`cdb-local-ci`, Merge und Issue-Closure sind dabei `false`.

Erst `steward_state=merge_candidate` friert den PR ein und aktiviert die
folgenden Merge-Gates. Slice-Evidence darf nie als Final-Head-Evidence
wiederverwendet werden. Der finale Nachweis bindet sowohl PR-Head als auch den
integrierten Base-SHA.

## Verbindlicher Vertrag

Für Pull Requests auf `main` gilt genau ein merge-relevanter Required Context
(Branch Protection, live via `gh api`):

| Quelle | Context | Typ |
|---|---|---|
| Local CI Status Publisher | `cdb-local-ci` | Commit Status (`app_id` null) |

Die früheren Required Checks `ci (Unit/Integration + Lint gesammelt)` und
`policy-gate` sind **nicht mehr** branch-protection-required (Migration #4169).
`ci.yml` und `policy-gate.yml` bleiben als Workflow-Inhalt / Safety-Gates
nützlich, ersetzen aber den Required Context nicht.

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
2. Commit Status `cdb-local-ci` für exakt diesen SHA prüfen.
3. Fehlenden Status von einem fehlgeschlagenen Status unterscheiden.
4. Publisher-Evidence und Policy-Mirror-Fail prüfen.
5. Erst nach grünem aktuellem `cdb-local-ci` mergen.

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
7. `cdb-local-ci` SUCCESS on the exact PR head SHA (live via `gh api`).
8. The session can perform the regular squash merge itself (has merge
   permission / `statuses:write`), and can publish `cdb-local-ci` itself if
   it is still missing and the session holds bound evidence to do so.

`--admin` is **never** a bypass for a missing/red/stale `cdb-local-ci`.
Fake-green claims and merging an untested head are forbidden.

### Honest handoff when capability is missing

If a session lacks any gate above (no `statuses:write`, no verifiable
identity, evidence not bound to the exact head, publisher auth blocked):
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
  Commit Status `cdb-local-ci` ist der Required Context.
- Branch Protection required contexts: `["cdb-local-ci"]` (Commit Status).
- Dirty worktree ⇒ lokale Evidence `BLOCKED` und kein Publish.
- Publish-Pfad erzwingt Policy-Gate-Mirror (Parität zu
  `.github/workflows/policy-gate.yml`).
- Kein Fake-Green: dirty, stale, SHA-Mismatch, Hash-Mismatch, required SKIPPED,
  Anti-Replay, fehlende PR-Nummer oder Policy-Gate-Fails blockieren Publish.
- Lokales CodeQL/SARIF ersetzt nicht den GitHub Security-Tab.

Live Branch-Protection-Hinweis (reverify with `gh api`):
`required_status_checks.contexts == ["cdb-local-ci"]`, `checks[].app_id == null`.

Windows front door:

```powershell
pwsh -File ci/scripts/run_all.ps1 -Profile fast
pwsh -File ci/scripts/publish_status.ps1 -Command publish `
  -EvidenceDir ci/artifacts/<run_id> -StatusContext cdb-local-ci -PrNumber <n>
```
