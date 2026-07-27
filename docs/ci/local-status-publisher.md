# Local CI Status Publisher (Phase 3a)

Trusted, fail-closed publisher that turns **validated** local Docker CI evidence
into a GitHub Commit Status for the exact commit SHA.

Issue: [#4164](https://github.com/jannekbuengener/Claire_de_Binare/issues/4164)
Related: [#4169](https://github.com/jannekbuengener/Claire_de_Binare/issues/4169)

## Architecture and trust boundary

```
local Docker CI (ci/scripts/run.py)
  → ci/artifacts/<run_id>/manifest.json + manifest.sha256
  → ci.publisher validate / dry-run / publish
  → local policy-gate mirror (tools/ci/policy_gate_local.py) when --pr-number set
  → GitHub Commit Status (context cdb-local-ci / cdb-local-ci-preview)
```

GitHub remains the PR / status / merge platform. Rechenintensive CI bleibt lokal.

**Interim trust model:** Phase 3a publishes a **Commit Status** (PAT / `gh`),
**not** a GitHub App Check Run. After Branch-Protection migration the intended
required context is `cdb-local-ci`; until BP changes, treat that context as the
required-check **path** (mandatory PR + policy mirror) but do not assume live BP
already requires it. This PR does not mutate Branch Protection.

## Why local green is not automatically trusted

A green local run is only advisory until the publisher proves:

- repository binding (`jannekbuengener/Claire_de_Binare`)
- exact commit SHA binding
- clean worktree (`dirty_worktree=false`), including a live re-check before publish
- `overall_status=PASS` with required stages PASS
- `manifest.sha256` integrity
- artifact hash re-verification
- freshness window
- anti-replay ledger (`run_id` not reused for another SHA)
- for `cdb-local-ci`: mandatory `--pr-number > 0`, PR head SHA match, and
  local policy-gate mirror PASS (same rules as `.github/workflows/policy-gate.yml`)

**No Fake-Green:** dirty worktree, stale evidence, SHA mismatch, hash mismatch,
required SKIPPED, anti-replay violations, missing PR for `cdb-local-ci`, or
policy-gate failures all block publish with a clear `REJECT:`.

Billing lock or GitHub-hosted Actions failures do **not** weaken these rules.

## Required-check path (`cdb-local-ci`)

| Context | `--pr-number` | Policy-gate local mirror |
|---------|---------------|--------------------------|
| `cdb-local-ci` (default / required path) | **Mandatory** (`> 0`) | Run on dry-run and publish after evidence OK |
| `cdb-local-ci-preview` | Optional | Run when `--pr-number` is set |

The mirror lives in `tools/ci/policy_gate_local.py` and evaluates category
(docs-only / workflows-only / infra-only / core/service), scope, and workflow
safety (`pull_request_target`, `write-all`, missing `permissions`,
`workflow_run` + checkout).

## Evidence validation rules

Shared validators live in `ci/lib/evidence.py` (reuse, no duplicate parsing).

Default required stages: `lint`, `unit`, `docs`, `governance`.

Optional stages (`integration`, `security`, `containers`) may be SKIPPED only
with an explicit `skip_reason`. Skips are disclosed in the status description.

## Check Run versus Commit Status

**Phase 3a uses Commit Status** (`POST /repos/{owner}/{repo}/statuses/{sha}`).

| Surface | Auth needed | Phase 3a |
|---------|-------------|----------|
| Commit Status | PAT / `gh` with statuses write (`repo` or fine-grained Commit statuses: Write) | **Used** |
| Check Run | GitHub App installation token with `checks:write` | Documented future path |

User/OAuth tokens from `gh auth` cannot safely create Check Runs without an App.
The client intentionally has no `create_check_run` method.

## Authentication (least privilege)

- Token **only** from environment: `GITHUB_TOKEN` or `GH_TOKEN`, else `gh auth token`
- Never pass the token as a CLI argument or store it in the repo
- Prefer a fine-grained PAT with **Commit statuses: Write** (+ metadata / contents read for PR + workflow inspection)
- No admin, no branch-protection, no contents-write required for publish
- Authorization headers and token-like strings are redacted from logs/errors

### Windows token setup

```powershell
# Option A: session env (preferred for least surprise)
$env:GITHUB_TOKEN = "<fine-grained PAT with Commit statuses: Write>"

# Option B: rely on existing gh login
gh auth status
```

Then:

```powershell
pwsh -File ci/scripts/publish_status.ps1 -Command dry-run -EvidenceDir ci/artifacts/<run_id> `
  -PrNumber <n>
```

## Commands

```bash
python -m ci.publisher validate --evidence-dir ci/artifacts/<run_id> --commit-sha <sha>
python -m ci.publisher dry-run  --evidence-dir ci/artifacts/<run_id> --commit-sha <sha> \
  --pr-number <n>
python -m ci.publisher publish  --evidence-dir ci/artifacts/<run_id> --commit-sha <sha> \
  --pr-number <n> --status-context cdb-local-ci
python -m ci.publisher dry-run  --evidence-dir ci/artifacts/<run_id> --commit-sha <sha> \
  --status-context cdb-local-ci-preview
python -m ci.publisher inspect  --commit-sha <sha> --status-context cdb-local-ci-preview
```

Make:

```bash
make ci-local-publish-dry-run EVIDENCE_DIR=ci/artifacts/<run_id> COMMIT_SHA=<sha> PR_NUMBER=<n>
make ci-local-publish EVIDENCE_DIR=ci/artifacts/<run_id> COMMIT_SHA=<sha> STATUS_CONTEXT=cdb-local-ci PR_NUMBER=<n>
make ci-local-publish-inspect COMMIT_SHA=<sha> STATUS_CONTEXT=cdb-local-ci-preview
```

Windows:

```powershell
pwsh -File ci/scripts/publish_status.ps1 -Command dry-run -EvidenceDir ci/artifacts/<run_id> `
  -CommitSha <sha> -PrNumber <n>
pwsh -File ci/scripts/publish_status.ps1 -Command publish -EvidenceDir ci/artifacts/<run_id> `
  -CommitSha <sha> -StatusContext cdb-local-ci -PrNumber <n>
```

## Failure handling

Fail closed on: missing/mismatched manifest or artifact hashes, SHA mismatch,
foreign repo, dirty worktree (evidence or live), required FAIL/SKIPPED, stale
evidence, reused `run_id`, missing `--pr-number` for `cdb-local-ci`, PR head
drift, policy-gate mirror failure, network/API ambiguity, insufficient
permissions, rate limits.

Behavior: non-zero exit, no success publish, one clear `REJECT:` reason,
redacted secrets, validation JSON on stdout.

## Anti-replay

Ledger: `ci/artifacts/published-runs.json` (gitignored via `ci/artifacts/.gitignore`).

Records `run_id`, SHA, repository, status context, manifest digest, timestamp.
Corruption or `run_id` reuse for another SHA blocks publication.

## PR head change handling

When `--pr-number` is set (mandatory for `cdb-local-ci`), the publisher reads the
PR head SHA from GitHub and rejects dry-run/publish if it differs from
`--commit-sha` / evidence SHA. Publish re-checks the head immediately before the
status write.

## Branch Protection unchanged (this PR)

This PR does **not**:

- change Branch Protection or rulesets
- disable or thin GitHub workflows
- merge any PR

Live required checks remain whatever Branch Protection currently lists (today:
`ci (Unit/Integration + Lint gesammelt)` + `policy-gate`) until a separate,
explicit BP migration.

After that migration, the required context is expected to be `cdb-local-ci` with
the local policy mirror enforced at publish time (see
[`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)).

## Future migration

After publisher parity + security review, a follow-up evaluates making
`cdb-local-ci` required and only then retiring GitHub-hosted heavy CI.
Until BP migration, use `cdb-local-ci-preview` for live smoke tests without the
mandatory PR constraint.

## Rollback / revocation

- Stop publishing; statuses are historical commit annotations
- Rotate/revoke the PAT used for publish
- Delete or quarantine a corrupted local ledger (fail closed until repaired)
- Do not use admin bypass to force merges

## Related

- [`ci/README.md`](../../ci/README.md)
- [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)
- [`tools/ci/policy_gate_local.py`](../../tools/ci/policy_gate_local.py)
- Phase 1 evidence contract + PR #4166
