# cdb-local-ci App-bound Check Run Cutover

Status: Phase A code-ready preparation (#4170)
Authority: Operational runbook for migrating the required merge context from
interim Commit Status (`app_id=null`) to a GitHub-App-bound Check Run.
Live Branch Protection is **not** changed by the publisher code PR.

LR remains **NO-GO**. This runbook does not authorize live trading.

---

## Why Commit Status `app_id=null` is not the target model

After #4169 the sole Branch Protection required context on `main` is
`cdb-local-ci` as a **Commit Status** with `app_id: null`. Any credential with
Commit statuses: Write can POST `success` for that context. Evidence gates in
`ci/publisher/` reduce accidental misuse, but they do not cryptographically bind
the status to a single publisher identity.

Target model: only a dedicated GitHub App may create the required Check Run
named `cdb-local-ci`, bound to App identity, exact PR head SHA, and validated
local CI evidence.

---

## Publisher backend architecture

| Backend | CLI | Auth | GitHub object |
|---|---|---|---|
| `commit-status` (default) | `--publisher-backend commit-status` | `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth` via existing resolver | Commit Status |
| `check-run` (explicit) | `--publisher-backend check-run` | App credentials auto-mint **or** `CDB_GH_APP_INSTALLATION_TOKEN` (never PAT/`gh`) | Check Run |

Shared fail-closed gates (unchanged): evidence validation, exact SHA bind,
`--pr-number` for required context, local policy-gate mirror, dirty-worktree
reject, anti-replay ledger, no Fake-Green, no Admin bypass.

Check Run path adds: expected App ID + Installation ID, remote `app.id`
readback, deterministic `external_id={run_id}:{sha}`, no fallback to Commit
Status on error.

---

## Exact minimal App permissions

| Permission | Level | Required by |
|---|---|---|
| Metadata | Read | Installation / repository binding |
| Checks | Read and Write | `POST /check-runs`, `GET /check-runs/{id}`, list by SHA |

### Prohibited (forbidden) permissions

- Administration: Write
- Actions: Write
- Contents: Write
- Commit statuses: Write
- Deployments: Write
- Secrets: Read or Write

Pull requests / Contents Read are only needed if the same installation token
performs those reads; Phase A keeps PR/policy reads on the existing read token
path so Checks R/W + Metadata Read is the minimum for the Check Run writer.

---

## Migration phases

### A_CODE_READY (this PR)

- Implement Check Run backend, tests, docs.
- Keep Commit Status path active as default.
- Do **not** change Branch Protection baselines or live BP.
- Do **not** create a GitHub App from the agent session.

### B_APP_INSTALLED (human / external only)

1. Create a dedicated GitHub App (display name proposal: `CDB Local CI Publisher`).
2. Set minimal permissions above.
3. Install exclusively on the canonical Claire de Binare GitHub repository
   (owner/name from publisher `EXPECTED_REPOSITORY`).
4. Record App ID and Installation ID (non-secret).
5. Store Private Key **outside** the repository (secrets SSOT directory only).
6. Do **not** reuse the Control-Board / Projects App as the local-ci publisher
   unless explicitly decided; least privilege prefers a dedicated App.

### C_SHADOW_SMOKE (App credentials + Human-GO; publisher auto-mints)

Recommended shadow name: `cdb-local-ci-app-preview` (not required).

Phase C (#4170): the publisher mints a short-lived installation token from
App ID + Installation ID + private key (path or inline). Manual
`CDB_GH_APP_INSTALLATION_TOKEN` remains optional override.

```bash
export CDB_GH_APP_ID="<app_id>"
export CDB_GH_APP_INSTALLATION_ID="<installation_id>"
export CDB_GH_APP_PRIVATE_KEY_PATH="/path/to/cdb-local-ci-app.pem"
# optional override: export CDB_GH_APP_INSTALLATION_TOKEN="<short-lived token>"

# Disposable probe SHA (no full evidence gates); refuses required name cdb-local-ci:
python -m ci.publisher app-auth-probe --commit-sha <exact_probe_sha>

# Full evidence path for shadow Check Run (after dry-run OK + Human-GO):
python -m ci.publisher dry-run \
  --publisher-backend check-run \
  --expected-app-id "$CDB_GH_APP_ID" \
  --expected-installation-id "$CDB_GH_APP_INSTALLATION_ID" \
  --check-run-name cdb-local-ci-app-preview \
  --evidence-dir ci/artifacts/<run_id> \
  --commit-sha <exact_pr_head_sha> \
  --pr-number <n>

python -m ci.publisher publish \
  --publisher-backend check-run \
  --expected-app-id "$CDB_GH_APP_ID" \
  --expected-installation-id "$CDB_GH_APP_INSTALLATION_ID" \
  --check-run-name cdb-local-ci-app-preview \
  --evidence-dir ci/artifacts/<run_id> \
  --commit-sha <exact_pr_head_sha> \
  --pr-number <n>

python -m ci.publisher inspect \
  --publisher-backend check-run \
  --expected-app-id "$CDB_GH_APP_ID" \
  --expected-installation-id "$CDB_GH_APP_INSTALLATION_ID" \
  --check-run-name cdb-local-ci-app-preview \
  --commit-sha <exact_pr_head_sha>
```

Verify remote: `name`, `head_sha`, `conclusion`, `external_id`, **`app.id`**.
On 403 / missing `checks:write` → **STOP** `BLOCKED_APP_PERMISSION`
(no Commit Status bypass).

### D_CUTOVER (separate Human-GO; not this PR)

1. Snapshot current Branch Protection (before-state).
2. Prove shadow smoke success.
3. Publish App-bound Check Run named `cdb-local-ci` for the exact test SHA.
4. Verify remote `app.id`.
5. Atomically switch Branch Protection required check to the App-bound Check Run.
6. Confirm merge without App Check remains blocked.
7. Remove interim Commit Status required context only after verification.
8. Document rollback steps before applying.

### E_RETIRE_INTERIM (after stable cutover evidence)

- Retire Commit Status publisher default only after stable cutover evidence.
- Refresh baselines and docs.
- Re-evaluate #4165 (hosted heavy CI retirement) separately.

---

## Secrets, rotation, token lifetime

| Name | Kind | Notes |
|---|---|---|
| `CDB_GH_APP_ID` | non-secret config | Expected App ID for readback (+ JWT `iss`) |
| `CDB_GH_APP_INSTALLATION_ID` | non-secret config | Installation used for token mint |
| `CDB_GH_APP_PRIVATE_KEY_PATH` / `CDB_GH_APP_PRIVATE_KEY` | secret | PEM path (preferred) or inline; external SSOT only |
| `CDB_GH_APP_INSTALLATION_TOKEN` | ephemeral secret | Optional override (~1h); else publisher auto-mints |

Documented read aliases (User-env convenience): `CDB_GITHUB_APP_ID`,
`CDB_GITHUB_APP_INSTALLATION_ID`, `CDB_GITHUB_APP_PRIVATE_KEY_PATH`.

Rotation:

1. Generate new Private Key in GitHub App settings (or rotate App).
2. Store in external secrets SSOT; sync to GitHub repo secrets if needed.
3. Revoke old key.
4. Re-run shadow smoke / `app-auth-probe` (publisher mints a fresh installation token).

Publisher Check Run mode **auto-mints** the installation token when App
credentials are present (`ci.publisher.app_auth`). Explicit
`CDB_GH_APP_INSTALLATION_TOKEN` still wins when set.

Collision note: Control-Board workflows already document `CDB_GH_APP_ID` /
`PRIVATE_KEY` / `INSTALLATION_ID`. Prefer a **dedicated** local-ci App and
document which values the publisher expects. Do not overwrite Control-Board
secrets blindly.

---

## Preflight checklist (before shadow / cutover)

- [ ] App ID known
- [ ] Installation ID known
- [ ] App installed only on the canonical Claire de Binare repository
- [ ] Permission matrix matches this runbook (no prohibited grants)
- [ ] Shadow check name `cdb-local-ci-app-preview` chosen
- [ ] Test PR number and exact head SHA recorded
- [ ] App PEM path or inline key available (or optional installation token override)
- [ ] Local evidence validated for that SHA

---

## Cutover checklist

- [ ] Capture Branch Protection before-state
- [ ] Shadow Check verified (`app.id`, SHA, name, conclusion)
- [ ] App-bound `cdb-local-ci` Check Run on current test SHA
- [ ] Remote `app.id` matches expected App ID
- [ ] Branch Protection changed only after the above
- [ ] Required check bound to App identity
- [ ] Merge attempt without App Check remains blocked
- [ ] Rollback sequence documented and ready

---

## Rollback

If cutover fails or state is unknown → **HOLD** (do not Fake-Green, do not
`--admin`).

1. Restore Branch Protection required context to Commit Status `cdb-local-ci`
   with `app_id: null` (before-state snapshot).
2. Keep Commit Status publisher path available (`--publisher-backend commit-status`).
3. Stop using Check Run publishes for the required name until re-verified.
4. Rotate App credentials if compromise is suspected.
5. File / update follow-up with evidence; do not close #4170 until cutover proven.

---

## Emergency rule

Unknown API write result, ambiguous readback, missing `app.id`, SHA drift, or
policy-mirror failure ⇒ **HOLD / FAIL**. Never assume success.

---

## APP_BOUND_CHECK_RUN_CUTOVER_HANDOFF

```yaml
artifact: APP_BOUND_CHECK_RUN_CUTOVER_HANDOFF
issue: 4170
phase_completed_by_code_pr: A_CODE_READY
github_app_display_name_proposal: "CDB Local CI Publisher"
expected_app_id: "<SET_AFTER_APP_CREATE>"
expected_installation_id: "<SET_AFTER_INSTALL>"
repository_installation_scope: "canonical Claire de Binare repository only (EXPECTED_REPOSITORY)"
minimal_permissions:
  - "Metadata: Read"
  - "Checks: Read and Write"
prohibited_permissions:
  - "Administration: Write"
  - "Actions: Write"
  - "Contents: Write"
  - "Commit statuses: Write"
  - "Deployments: Write"
  - "Secrets: Read or Write"
secret_names:
  installation_token: CDB_GH_APP_INSTALLATION_TOKEN
  expected_app_id: CDB_GH_APP_ID
  expected_installation_id: CDB_GH_APP_INSTALLATION_ID
  private_key_path: CDB_GH_APP_PRIVATE_KEY_PATH
  private_key_inline: CDB_GH_APP_PRIVATE_KEY
private_key_storage: "External secrets SSOT only (never repository)"
token_minting_responsibility: "Publisher auto-mint via ci.publisher.app_auth (Phase C); optional INSTALLATION_TOKEN override"
shadow_check_name: cdb-local-ci-app-preview
shadow_smoke_command: >
  python -m ci.publisher app-auth-probe --commit-sha <PROBE_SHA>
phase_c_completed_by_code: true
expected_remote_app_id_verification: "GET check-run → app.id == CDB_GH_APP_ID"
branch_protection_before:
  required_contexts: ["cdb-local-ci"]
  type: "Commit Status"
  app_id: null
branch_protection_after_planned:
  required_check: "cdb-local-ci"
  type: "Check Run bound to dedicated App"
  app_id: "<SET_AFTER_APP_CREATE>"
rollback_sequence:
  - "Restore BP required context to Commit Status cdb-local-ci app_id=null"
  - "Use --publisher-backend commit-status"
  - "HOLD until re-verified; rotate credentials if needed"
human_go_points:
  - "B_APP_INSTALLED"
  - "C_SHADOW_SMOKE"
  - "D_CUTOVER"
unresolved_risks:
  - "Live BP not writable/readable by cloud integration (403 observed)"
  - "Control-Board CDB_GH_APP_* name collision if shared carelessly"
  - "Live App checks:write still required for probe; BP cutover remains Phase D Human-GO"
```
