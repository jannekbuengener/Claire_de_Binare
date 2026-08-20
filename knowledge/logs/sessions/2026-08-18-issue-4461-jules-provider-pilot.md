# Issue #4461 — Jules Provider Recorded Pilot Handoff

Date: 2026-08-18
Mode: recorded/fake transport only
Base: `534c344f13830c66e37cb78484448ae72a869d69`
Provider: `jules-api`
Live Jules API request: **not executed**
Secret read/value: **not performed / not recorded**
Live-Readiness verdict: **NO-GO unchanged**

## Purpose

Validate the CDB-specific Jules lifecycle behind the existing Agent Control Plane without creating a second control plane and without making a live provider-readiness claim.

The common MCP/CLI Jules gateway remains the preferred coarse dispatch path. This pilot covers only the governed REST capabilities CDB needs beyond that gateway: explicit plan approval, Session state/Activities, follow-up, capability drift, and PR/result handoff.

## Recorded evidence

The fake HTTP transport exercised the same provider adapter and ACP dispatch path without network access or credentials.

Validated behaviors:

- Session creation requests `requirePlanApproval=true` by default.
- `AUTO_CREATE_PR` is emitted only when the signed Execution Contract grants `open_pr=true`; registry capability cannot widen the contract.
- `AWAITING_PLAN_APPROVAL` is normalized as a running wait state and approval is rejected from any other state.
- Session listing returns bounded, prompt-free metadata only.
- Activities persist only safe identifiers/types/timestamps and plan metadata; free-form provider/user text is excluded.
- Follow-up targets the already-bound Session and does not silently create a replacement Session.
- `401/403`, `429`, malformed/unknown state, timeout/network abort after mutating POST, and mutating `5xx` fail closed.
- Mutating unknown outcome is not blindly retried.
- The documented v1alpha surface has no supported CDB cancel RPC; cancel remains unconfirmed with `PROVIDER_CANCEL_UNSUPPORTED` and makes no network request.
- `JULES_API_KEY` is a runtime-only `provider_api_key` reference and `X-Goog-Api-Key` is rejected from durable provider evidence.
- A Jules `COMPLETED` Session and returned PR are delivery handoff only. Without the independent CDB delivery receipt, the ACP run remains `BLOCKED` rather than PASS.

## Focused validation

Completed during the #4461 implementation worktree:

- Jules provider core: 10/10 PASS.
- Jules timeout/session-list contract edges: 2/2 PASS.
- Cursor provider regression: 19/19 PASS.
- Agent registry regression: 32/32 PASS.
- Agent dispatcher regression: 46/46 PASS.
- Agent environment profile regression: 19/19 PASS.
- Skill surface/mirror validator: 50/50 PASS.
- Ruff repository check: PASS.

The repository-wide Black baseline is not clean independently of this slice; it reports many pre-existing files outside #4461. No broad formatting rewrite was performed.

## Redacted handoff shape

A completed provider handoff may expose only safe data such as:

```text
provider_id: jules-api
session_name: sessions/<redacted-id>
status: COMPLETED
activities: identifiers/types/timestamps + plan ids/step titles
pull_request: validated GitHub URL/title if present
secret_values: absent
prompt_text: absent from durable run evidence
cdb_acceptance: independent / not implied by provider completion
```

## Live smoke decision

No live Jules REST smoke is part of this recorded pilot. A live request remains a separate explicit Human-GO action and additionally requires a safe runtime `JULES_API_KEY`, current capability verification, source binding, and the normal CDB execution/evidence gates.

This recorded pilot authorizes no Trading, Risk, Execution, productive DB, MCP-live, `cdb-local-ci`, merge, approval, or issue-close capability for Jules.
