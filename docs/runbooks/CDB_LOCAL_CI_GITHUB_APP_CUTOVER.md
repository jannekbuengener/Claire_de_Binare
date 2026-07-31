# CDB Local CI — GitHub App Cutover (Phase B/C Operator Contract)

Status: Phase-B readiness (#4170) — credential-free preflight + operator sequence
Authority: Operator runbook for the later App-bound Check Run cutover
Does **not** install a GitHub App, mutate Branch Protection, publish Check Runs,
or close #4170.

LR remains **NO-GO**. This document does not authorize live trading.

Related Phase-A code/runbook (already on `main` via PR #4214):
[`cdb_local_ci_app_check_run_cutover.md`](./cdb_local_ci_app_check_run_cutover.md)

---

## Current Trust Model

| Item | Live state (until Phase D) |
|---|---|
| Required merge context | `cdb-local-ci` |
| GitHub object | **Commit Status** |
| App binding | `app_id: null` |
| Publisher default | `--publisher-backend commit-status` |
| Risk | Any credential with Commit statuses: Write can POST `success` |

Phase A delivered `CheckRunBackend` behind an explicit flag. The live required
context remains the interim Commit Status until a real App-bound smoke succeeds
and a separate Human-GO authorizes Branch Protection cutover.

---

## Preflight Contract

Tool: `python -m tools.ci.github_app_check_run_preflight`

Properties:

- Credential-free: does **not** read `CDB_GH_APP_INSTALLATION_TOKEN`, private
  keys, `Authorization` headers, or print token values.
- Read-only: no App install, no Branch Protection writes, no Check Run publish.
- Fail-closed: missing App, Installation, or `checks:write` ⇒ `NOT_READY`.
- App-bound Check Run identity requires a positive `app.id`. A Commit Status
  with `app_id=null` is **never** App-bound.
- Secrets in evidence/output are redacted (`[REDACTED]` / `[REDACTED_PRIVATE_KEY]`).

### Verdicts

| Verdict | Meaning |
|---|---|
| `NOT_READY` | Do not start operator smoke / cutover |
| `READY_FOR_OPERATOR_SMOKE` | App + Installation + `checks:write` + unambiguous App-bound Check Run evidence present |

### CLI

```bash
# Evaluate an operator-supplied evidence snapshot (no secrets)
python -m tools.ci.github_app_check_run_preflight \
  --evidence-file path/to/app_posture.json \
  --json

# Attach live BP / status / check-run observation (gh auth, still no App token)
python -m tools.ci.github_app_check_run_preflight --live-readonly --json
```

Exit code: `0` only for `READY_FOR_OPERATOR_SMOKE`; otherwise `2`.

### Minimal evidence shape

```json
{
  "app": {
    "id": 123456,
    "permissions": {
      "checks": "write",
      "metadata": "read"
    }
  },
  "installation": {
    "id": 789012,
    "repository": "jannekbuengener/Claire_de_Binare"
  },
  "check_runs": [
    {
      "name": "cdb-local-ci-app-preview",
      "app": { "id": 123456 },
      "head_sha": "<exact_sha>",
      "conclusion": "success"
    }
  ],
  "commit_statuses": [
    { "context": "cdb-local-ci", "state": "success", "app_id": null }
  ]
}
```

Do **not** put installation tokens or private keys into the evidence file.

---

## Operator Cutover Sequence (Phase B → C → D)

Hard rule: **Branch Protection must never be switched before a successful
App-bound smoke.** No Admin-Bypass. No Fake-Green.

### Phase B — App installed (human / external only)

1. Create dedicated GitHub App (proposal: `CDB Local CI Publisher`).
2. Permissions: Metadata Read; Checks Read and Write only.
3. Install exclusively on `jannekbuengener/Claire_de_Binare`.
4. Record non-secret App ID + Installation ID.
5. Store Private Key only in external secrets SSOT (never in repo/chat/PR).
6. Build evidence JSON (no tokens) and run preflight.
7. Proceed only when preflight is not blocked on App/Installation/`checks:write`.
   For full `READY_FOR_OPERATOR_SMOKE`, unambiguous App-bound Check Run evidence
   must also be present (typically after Phase C shadow publish).

### Phase C — Operator shadow smoke (explicit credentials + Human-GO)

Shadow name: `cdb-local-ci-app-preview` (must not be the required BP context yet).

```bash
export CDB_GH_APP_INSTALLATION_TOKEN="<short-lived installation token>"
export CDB_GH_APP_ID="<app_id>"
export CDB_GH_APP_INSTALLATION_ID="<installation_id>"

python -m ci.publisher dry-run \
  --publisher-backend check-run \
  --expected-app-id "$CDB_GH_APP_ID" \
  --expected-installation-id "$CDB_GH_APP_INSTALLATION_ID" \
  --check-run-name cdb-local-ci-app-preview \
  --evidence-dir ci/artifacts/<run_id> \
  --commit-sha <exact_pr_head_sha> \
  --pr-number <n>

# Only after dry-run OK and Human-GO:
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

Re-run preflight with Check Run evidence. Require
`READY_FOR_OPERATOR_SMOKE` before any Branch Protection discussion.

### Phase D — Branch Protection cutover (separate Human-GO; not this PR)

1. Snapshot Branch Protection before-state (`required contexts: ["cdb-local-ci"]`,
   Commit Status, `app_id: null`).
2. Prove shadow smoke + preflight READY.
3. Publish App-bound Check Run named `cdb-local-ci` for the exact test SHA.
4. Verify remote `app.id`.
5. **Only then** switch Branch Protection required check to the App-bound Check Run.
6. Confirm merge without App Check remains blocked.
7. Keep rollback steps ready before applying.

Cutover may proceed **only after** a real App-bound smoke. Agents in Phase-B
readiness sessions must not mutate GitHub settings.

---

## Rollback

If cutover fails or state is unknown → **HOLD**.

1. Restore Branch Protection required context to Commit Status `cdb-local-ci`
   with `app_id: null` (before-state snapshot).
2. Keep Commit Status publisher path available:
   `python -m ci.publisher ... --publisher-backend commit-status`.
3. Stop using Check Run publishes for the required name until re-verified.
4. Rotate App credentials if compromise is suspected.
5. Do not Fake-Green. Do not use `--admin` as a substitute for the required
   App-bound Check Run.
6. Keep #4170 open until cutover is proven.

---

## Forbidden in Phase-B readiness sessions

- Install or configure the GitHub App from an agent session
- Change Branch Protection / repository settings
- Publish Check Runs or `cdb-local-ci` Commit Statuses
- Full Fast-CI as cutover evidence
- Admin-Bypass / Fake-Green
- Writing secrets into issues, PRs, logs, or repo files

---

## Validation commands (this readiness PR)

```bash
pytest -q tests/unit/tools/ci/test_github_app_check_run_preflight.py
python -m tools.ci.github_app_check_run_preflight --live-readonly --json
ruff check tools/ci/github_app_check_run_preflight.py \
  tests/unit/tools/ci/test_github_app_check_run_preflight.py
black --check tools/ci/github_app_check_run_preflight.py \
  tests/unit/tools/ci/test_github_app_check_run_preflight.py
python -m tools.validate_readme_links
git diff --check
gitleaks protect --staged
```

---

## Status semantics

| Status | Meaning |
|---|---|
| `DONE_PHASE_B_READINESS_PR` | Preflight + operator runbook delivered; no cutover performed |
| Issue #4170 | Remains OPEN until real App-bound cutover is proven |
