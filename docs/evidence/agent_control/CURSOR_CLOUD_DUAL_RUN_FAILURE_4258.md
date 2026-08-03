# Cursor Cloud Dual-Run Failure Evidence (#4258)

- Generated: `2026-08-03T02:51:10Z`
- Bundle digest: `sha256:fa2f925903d2908f0a191f377cfd05e53532a7ae183a18c53767e78060a4cae0`
- Schema: `cdb.cursor_dual_run_support_bundle.v1` `1.0.0`
- Issue: #4258 (remains OPEN)
- Third Cursor run: **not started**
- `cursor_http_posts`: 0

## Direct evidence

| Field | Run 1 | Run 2 |
| --- | --- | --- |
| CDB run | `adr-ee0a9384bc9940a9` | `adr-d97cf406ff9d486d` |
| Evidence | `are-5ae1839fa8b0c71ad7e8b902` | `are-48dbdce0fbaf7ff5654b23f4` |
| Agent | `bc-d1ba82b5-db1a-5040-b50a-2007040a65c7` | `bc-767ef75f-c948-5049-9bc2-0534fd6cf46f` |
| Run | `run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b` | `run-c2c3898b-af9e-4f73-ad91-830f600561b9` |
| Status | `ERROR` | `ERROR` |
| Duration ms | 7824 | 7501 |
| Tokens | 1041 | 1596 |
| Claimed branch | `['cloud-cursor/cursor-cloud-pilot-marker-3c10']` | `['cloud-cursor/probe-4258-documentation-69b3']` |
| GitHub ref | 404 | 404 |
| Structured error | False | False |
| Artifacts empty | True | True |

## Failure phases

- Last proven successful: `AGENT_REASONING`
- First failed/missing: `GIT_PUSH`
- Git push attempt proven: `False`

## Root-cause classification

- Primary: `UNKNOWN_OBSERVABILITY_GAP` (confidence `MEDIUM`)
- Secondary: CURSOR_PLATFORM_INTERNAL, CURSOR_GITHUB_DELIVERY, CURSOR_MODEL_OR_RUNTIME, CURSOR_ENVIRONMENT_BOOTSTRAP
- Cursor support required: `True`
- Operator configuration required: `False`
- CDB diagnostic fix required: `True`

## Excluded (public evidence)

- AUTH (create + GETs succeeded)
- MODEL_NOT_AVAILABLE (tokens > 0 on both runs)
- GITHUB_WRITE_PERMISSION_ROOT_CAUSE as sole cause (#4295 cursoragent commits exist; failed runs never verified push)
- CDB create mapping failure (agents ACTIVE, runs accepted)
- Full cold environment bootstrap as proven primary (duration ~8s with tokens; unproven)

## Documented API path note

Usage/artifacts are agent-scoped (`/v1/agents/{id}/usage`, `/v1/agents/{id}/artifacts`).
A 404 on run-scoped `/runs/{runId}/usage` is **not** evidence that usage is missing.

## Successful reference

PR #4295 / `cloud-cursor/area-entry-link-canon-4a6a` includes `cursoragent` commits.
This proves GitHub write capability on some path; it does **not** prove the failed
API runs used the same workspace binding.

## Limitations

Public Cursor API did not return a machine-readable error reason. Exact platform
root cause remains an observability gap pending Cursor backend investigation.
