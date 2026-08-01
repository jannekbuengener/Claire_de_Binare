# Local CI Status Publisher (Phase 3a)

Trusted, fail-closed publisher that turns **validated** local Docker CI evidence
into a GitHub **App-bound Check Run** for the exact commit SHA.

Issue: [#4164](https://github.com/jannekbuengener/Claire_de_Binare/issues/4164)
Related: [#4169](https://github.com/jannekbuengener/Claire_de_Binare/issues/4169),
[#4170](https://github.com/jannekbuengener/Claire_de_Binare/issues/4170) (CLOSED — Phase D cutover)

## Architecture and trust boundary

```
local Docker CI (ci/scripts/run.py)
  → ci/artifacts/<run_id>/manifest.json + manifest.sha256
  → ci.publisher validate / dry-run / publish
  → local policy-gate mirror (tools/ci/policy_gate_local.py) when --pr-number set
  → GitHub App Check Run (name cdb-local-ci, app_id=4410232)
```

GitHub remains the PR / status / merge platform. Rechenintensive CI bleibt lokal.

**Live trust model (post-#4170 Phase D):** Branch Protection requires
`cdb-local-ci` as an **App-bound Check Run** (`app_id=4410232`). Default CLI
backend is `--publisher-backend check-run` with App auto-mint. A same-named
**Commit Status does not satisfy** the required gate. Preview/shadow name
`cdb-local-ci-app-preview` remains non-required for smoke tests.

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

**Default (post-#4170 Phase D):** App-bound Check Run
(`POST /repos/{owner}/{repo}/check-runs`) via `--publisher-backend check-run`
with auto-mint. Live Branch Protection requires `cdb-local-ci` with
`app_id=4410232`.

**Legacy Commit Status** (`--publisher-backend commit-status`) remains for
debug only and does **not** satisfy Branch Protection.

| Surface | Auth needed | Status |
|---------|-------------|--------|
| Check Run | App ID + Installation ID + PEM (auto-mint) **or** `CDB_GH_APP_INSTALLATION_TOKEN` override | **Default / required path** |
| Commit Status | PAT / `gh` with statuses write | Legacy only (not BP-sufficient) |

`GitHubStatusClient` still has no `create_check_run` method. Check Runs live in
`ci.publisher.backends.CheckRunBackend`. User/OAuth/`gh auth` tokens are **not**
accepted as App identity proof for Check Run mode.

### Check Run auth priority

1. Explicit test inject (programmatic only)
2. `CDB_GH_APP_INSTALLATION_TOKEN` (optional override)
3. Auto-mint via `ci.publisher.app_auth` from `CDB_GH_APP_ID` +
   `CDB_GH_APP_INSTALLATION_ID` + (`CDB_GH_APP_PRIVATE_KEY` **or**
   `CDB_GH_APP_PRIVATE_KEY_PATH`)
4. Fail closed — **no** `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth` fallback

Documented aliases: `CDB_GITHUB_APP_ID`, `CDB_GITHUB_APP_INSTALLATION_ID`,
`CDB_GITHUB_APP_PRIVATE_KEY_PATH`.

Normal Check Run operation does **not** require manual JWT / installation-token
steps when PEM + IDs are configured. For permission smoke without evidence
gates:

```bash
python -m ci.publisher app-auth-probe --commit-sha <exact_probe_sha>
```

Shadow only (`cdb-local-ci-app-preview`). Refuses required name `cdb-local-ci`.

Troubleshooting:

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| 401 on mint / Check Run | Bad PEM, wrong App ID, expired JWT clock skew | Recheck PEM path + IDs; do not print secrets |
| 403 on Check Run create | Missing App permission `checks:write` | **STOP** `BLOCKED_APP_PERMISSION`; fix App permissions (no Commit Status bypass) |
| 404 on `/app/installations/.../access_tokens` | Wrong installation ID or App not installed on repo | Fix installation ID / install App on canonical repo |

### CLI backend switch

```bash
# Default — App-bound required Check Run path (satisfies BP)
python -m ci.publisher publish --evidence-dir ci/artifacts/<run_id> \
  --commit-sha <sha> --pr-number <n>

# Legacy Commit Status (does NOT satisfy Branch Protection after Phase D)
python -m ci.publisher publish --publisher-backend commit-status \
  --evidence-dir ci/artifacts/<run_id> --commit-sha <sha> --pr-number <n>
```

Live BP requires App `4410232`. Same-named Commit Status is not merge-sufficient.

## Authentication (least privilege)

**Required path (Check Run):** App auto-mint — `CDB_GH_APP_ID` +
`CDB_GH_APP_INSTALLATION_ID` + PEM path/env (see Check Run auth priority
above). Needs App permission **checks:write**. No PAT required for publish.

**Legacy Commit Status only:** Token from `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth
token` with **Commit statuses: Write**. Never pass tokens as CLI args. This
path does **not** satisfy Branch Protection after Phase D.

Authorization headers and token-like strings are redacted from logs/errors.

### Windows App credential setup (required path)

```powershell
$env:CDB_GH_APP_ID = "4410232"
$env:CDB_GH_APP_INSTALLATION_ID = "<installation-id>"
$env:CDB_GH_APP_PRIVATE_KEY_PATH = "$env:USERPROFILE\Documents\.secrets\.cdb\cdb-local-ci-app.pem"
```

Then:

```powershell
pwsh -File ci/scripts/publish_status.ps1 -Command dry-run -EvidenceDir ci/artifacts/<run_id> `
  -PrNumber <n>
```

## Identity preflight and handoff when Check Run publish is blocked

Before attempting `publish`, a session should preflight its own capability
rather than discover the failure mid-merge attempt:

1. Confirm App IDs + PEM path (or `CDB_GH_APP_INSTALLATION_TOKEN` override).
2. Optional: `python -m ci.publisher app-auth-probe --commit-sha <probe-sha>`
   (shadow name only).
3. Attempt `python -m ci.publisher dry-run ...` first; auth/permission failures
   surface as clear `REJECT:` without mutating Branch Protection.

If the preflight shows the session cannot create the required App Check Run
(missing PEM/IDs, no `checks:write`, mint 401/403): do not fall back to
`--admin` merge, do not publish a same-named Commit Status as a substitute,
and do not loop retries. Report `DONE_PR_OPEN_MERGE_HANDOFF` /
`BLOCKED_AUTH_PUBLISHER` (see
[`merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md) §
Capability-based Autonomous Merge) with the exact missing capability
(e.g. "App PEM / installation mint unavailable in this session") and the
concrete next command for a capable session/human to run.

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

## Branch Protection (live, post-#4170 Phase D)

Live required status checks on `main` are:

- context / check name: `cdb-local-ci`
- type: GitHub App Check Run (`app_id=4410232`)
- same-named Commit Status: **not** merge-sufficient

Baselines and governance guards track the live state. GitHub-hosted `ci.yml` /
`policy-gate.yml` remain available as workflow content but are **not**
BP-required.

Use `cdb-local-ci-app-preview` for optional shadow smoke without the required
name.

## Post-cutover operations

Phase D cutover is **complete** (#4170 closed). Normal merge publish uses
`--publisher-backend check-run` (CLI default) with App auto-mint. See
[`docs/runbooks/cdb_local_ci_app_check_run_cutover.md`](../runbooks/cdb_local_ci_app_check_run_cutover.md)
for rollback notes and permission matrix.

## Rollback / revocation

- Stop publishing; statuses are historical commit annotations
- Rotate/revoke the PAT used for publish
- Delete or quarantine a corrupted local ledger (fail closed until repaired)
- Do not use admin bypass to force merges

## Related

- [`ci/README.md`](../../ci/README.md)
- [`docs/runbooks/merge_policy_ci_gate.md`](../runbooks/merge_policy_ci_gate.md)
- [`docs/runbooks/cdb_local_ci_app_check_run_cutover.md`](../runbooks/cdb_local_ci_app_check_run_cutover.md)
- [`tools/ci/policy_gate_local.py`](../../tools/ci/policy_gate_local.py)
- Phase 1 evidence contract + PR #4166
