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
**not** a GitHub App Check Run. Live Branch Protection (#4169) requires
`cdb-local-ci` as that Commit Status context. Required-path publish enforces
mandatory PR + local policy mirror. Preview context `cdb-local-ci-preview`
remains non-required for smoke tests.

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

## Identity preflight and handoff when `statuses:write` is missing

Before attempting `publish`, a session should preflight its own capability
rather than discover the failure mid-merge attempt:

1. `gh auth status` — confirm an authenticated identity exists.
2. Confirm a usable token per the resolution order above
   (`GITHUB_TOKEN` → `GH_TOKEN` → `gh auth token`).
3. Attempt `python -m ci.publisher dry-run ...` first; a dry-run failure due
   to insufficient scope (no Commit-statuses write) surfaces as a clear
   `REJECT:` without mutating anything.

If the preflight shows the session cannot write the required Commit Status
(no `statuses:write`-capable token, no authenticated identity, or the token
owner lacks permission on this repo): do not fall back to `--admin` merge
and do not loop retries. Report `DONE_PR_OPEN_MERGE_HANDOFF` /
`BLOCKED_AUTH_PUBLISHER` (see
[`merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md) §
Capability-based Autonomous Merge) with the exact missing capability
(e.g. "no fine-grained PAT with Commit statuses: Write available in this
session") and the concrete next command for a capable session/human to run.

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

## Branch Protection (live, #4169)

Live required status checks on `main` are:

- context: `cdb-local-ci`
- type: Commit Status (`app_id` null)

This docs/PR slice does **not** mutate Branch Protection via API; baselines and
governance guards track the live state. GitHub-hosted `ci.yml` /
`policy-gate.yml` remain available as workflow content but are **not**
BP-required.

Use `cdb-local-ci-preview` for optional smoke publishes without the mandatory
PR constraint of the required path.

## Future hardening

After publisher parity + security review, evaluate GitHub-App Check Runs and
retiring or thinning GitHub-hosted heavy CI. Until then, `cdb-local-ci` remains
the interim Commit Status required context.

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
