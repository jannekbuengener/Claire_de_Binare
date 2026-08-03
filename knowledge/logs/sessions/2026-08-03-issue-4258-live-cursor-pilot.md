# Session: #4258 Live Cursor Delivery and Approval Pilot v1

Date: 2026-08-03  
Branch: `dedicated/agent-skills-issue-4258`  
PR: #4302 @ `2163e1ac`  
Mode: Controlled live pilot (Plan-GO) — no merge, no `cdb-local-ci` publish

## Brain Evidence

- brain_source: repo-only / not-used (Context tools available, no enrichment records)
- repo_fallback_reason: insufficient_evidence
- context_tool_status: available

## Official API Audit

- Source: https://cursor.com/docs/cloud-agent/api/endpoints (Cloud Agents API v1 public beta)
- Auth: Basic `base64(api_key:)` — ALIGNED
- Create: POST `/v1/agents` returns `{agent, run}` — ALIGNED
- agentId must be `bc-<uuid>` or `bc-<string>-<uuid>` — FIXED (uuid5)
- No `branchName`; use `repos[].startingRef` / auto branch — ALIGNED
- Follow-up response `{run:{id,status}}` — FIXED
- Poll before delivery verify — FIXED
- Skip delivery verify on provider FAILED — FIXED

## Controlled live run (exactly one successful create)

| Field | Value |
| --- | --- |
| CDB run_id | `adr-ee0a9384bc9940a9` |
| Cursor agent_id | `bc-d1ba82b5-db1a-5040-b50a-2007040a65c7` |
| Cursor run_id | `run-d4d336e2-f7d5-4ab6-bbd8-1af94f9a094b` |
| Cursor terminal | `ERROR` / normalized `FAILED` |
| Claimed branch | `cloud-cursor/cursor-cloud-pilot-marker-3c10` (not on GitHub; 404) |
| PR from Cursor | none |
| provider_call_count (create) | 1 |
| Resume provider_call_count | 0 |
| credential_present | true (env; value never logged) |
| Approval | SKIP (no delivery head) |
| Authority limits | all false |

Prior HTTP 400 attempt (`Invalid bcId format`) created **zero** Cursor resources; corrected create is the sole live agent/run.

## Validation

- Offline unit suites PASS after API alignment fixes
- Live: create+poll verified; delivery not on GitHub
- No second Cursor create; resume-only after ERROR

## Boundaries

- LR NO-GO unchanged
- Refs #4258 only (not Closes)
- No merge / no cdb-local-ci / no branch protection
- Approval Agents: MANUAL_BOOTSTRAP_ONLY / unproven
- Zero-Click: NOT fully proven (Cursor ERROR, no delivery PR)

## Status

`HOLD_SCOPE_BLOCKER` — live Cursor run evidenced, but GitHub delivery missing (phantom branch / provider ERROR).

---

## Follow-up diagnosis (existing run only — no second create)

Date: 2026-08-03 (same day continuation)

### Official diagnostic surfaces used
- GET agent / GET run / list runs / artifacts / usage / stream (read-only)
- Conversation/messages paths: not in public v1 (404)
- Repo listed in `GET /v1/repositories` (GitHub integration connected)

### Classification
- primary: `CURSOR_PLATFORM_INTERNAL` / `CURSOR_MODEL_OR_RUNTIME`
- secondary: claimed `git.branches` without GitHub object; Run schema lacks structured `error`
- last successful phase: create accepted
- first failed phase: terminal `ERROR` without proven push; branch still GitHub 404

### CDB MUST_FIX delivered
- Head: `cfdb04dd` on PR #4302
- claimed vs verified delivery; ERROR diagnostics preserved; recorded phantom-branch regressions
- Offline validation: targeted tests + ruff + black + registry validate + secret scan

### Status
`DONE_CDB_FIX_PUSHED_AWAITING_NEW_LIVE_GO` — next Cursor create needs new explicit Human-GO.
