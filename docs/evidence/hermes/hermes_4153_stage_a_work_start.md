# Hermes durable work-start — #4153 Stage-A Replay-only

Date: 2026-08-04  
Actor: `app.HERMES` (App ID `4480891`, installation `151136371`)  
Base `main`: `43401302857ff9bfc6fd81a55b6373dd6437ac49`  
LR: **NO-GO**

## Brain Evidence

- brain_source: repo-only
- brain_status: not-used
- context_brain_attempted: true
- context_brain_used: false
- context_available: false
- repo_fallback_used: true
- repo_fallback_reason: insufficient_evidence
- Live GitHub + host SSH override ledger claims.

## Gate A — Repository selection (PASS)

Live JWT + installation-token probe (token values never logged):

| Field | Value |
| --- | --- |
| `repository_selection` | `selected` |
| `total_count` | `1` |
| Repositories | `jannekbuengener/Claire_de_Binare` only |
| App | `4480891` / `app-hermes` |

Issue evidence: https://github.com/jannekbuengener/Claire_de_Binare/issues/4289#issuecomment-5178237406

## Gate B — Token broker lifecycle (PASS)

Host `cdb-hermes-01` re-check after #4344:

| Probe | Result |
| --- | --- |
| `systemctl start hermes-github-token` | ST=0 |
| engineer `test -r` token | ENG=0 |
| assistant `test -r` token | ASST=1 |
| after `systemctl stop` | AFTER=1 (token removed) |

No token values in this evidence.

## Gate C — Stage-A Replay-only binding (PASS / execute HOLD)

Dry `plan` (writes=false) on current main:

| Field | Value |
| --- | --- |
| `window_count` | **39** |
| `run_count` | 819 |
| `stage_b_runs` | **0** |
| `stress_runs` | **0** |
| `oos_runs` | **0** |
| `run_plan_fingerprint` | `7971335597a97c1a8ceed8062a6b06dad46cbe9172e0e794d8f4dd74a4adc88c` |
| `manifest_fingerprint` | `7126f60033205d8012976376e217999e8702a83266a059f1d4c628cf4ba208da` |
| `resume_policy.allow_resume` | true |

Machine-readable binding: [`hermes_4153_stage_a_plan_binding.json`](hermes_4153_stage_a_plan_binding.json)

**Absolute bans unchanged:** Stage-B, OOS, Stress, Paper, Live, Echtgeld.

### Campaign `execute` status

Owner Campaign-GO comment `5177373358` remains **`REVOKED_CAMPAIGN_EXECUTION_CONTRACT_DEFECT`**.  
Contract requires a live-verified Owner-GO (`cdb.sensitivity_campaign_execution_authorization.v1`).  
This Hermes work-start does **not** invent a GO and does **not** run `execute`.

Status: `HOLD_CAMPAIGN_OWNER_GO_REQUIRED` for replay execution; durable Hermes **work-start** is proven via this PR + host mint lifecycle.

## Checkpoint / resume

Campaign runner resume policy (from plan): allow_resume, refuse_binding_mismatch, skip_succeeded_identical_bindings, retry_failed.  
Artifact root (when authorized): `artifacts/arvp_sensitivity/4153/{campaign_id}/{manifest_fp}/{authorization_id}` per execution contract.

## Non-goals

- No Stage-B / OOS / Stress / Paper / Live / Echtgeld
- No `cdb-local-ci` publish with App `4480891` (publisher remains App `4410232` only)
- No new PEM / client secret
- No admin merge
