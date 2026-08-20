# CDB Jules Provider Dispatch Runbook

Status: governed provider integration for issue #4461
Scope: CDB Agent Control Plane only
External surface: official Google Jules REST API `v1alpha`

## 1. Purpose

This runbook defines how CDB may use Jules as an execution provider without creating a second control plane or transferring CDB authority to the provider.

CDB remains authoritative for routing, Execution Contract permissions, Human-GO, validation, `cdb-local-ci`, merge and issue closure. Jules may execute only the bounded provider work order and return normalized delivery evidence.

## 2. Reuse rule

Use the existing common MCP/CLI Jules gateway for simple dispatch when it provides the needed capability. Use the CDB `jules-api` adapter only when the CDB lifecycle needs official REST capabilities that the common gateway does not expose, specifically:

- explicit plan approval;
- Session state/watch;
- Activities and plan metadata;
- session-bound follow-up;
- PR/result handoff.

Do not build or maintain a parallel dispatcher, authority model, merge path or generic second Jules client.

## 3. Official documentation

Required external references before changing the adapter or capability baseline:

- Jules API overview: https://developers.google.com/jules/api
- REST v1alpha reference: https://developers.google.com/jules/api/reference/rest
- Sessions resource: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions
- Approve plan: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions/approvePlan
- Send message: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions/sendMessage
- Activities list: https://developers.google.com/jules/api/reference/rest/v1alpha/sessions.activities/list

The provider adapter is pinned to the documented service endpoint `https://jules.googleapis.com` and the checked-in `v1alpha` capability baseline. Undocumented/private endpoints are forbidden.

## 4. Secret boundary

`JULES_API_KEY` is a runtime secret. The registry stores only `env:JULES_API_KEY` with secret class `provider_api_key`.

The key value must never be written to:

- repo files;
- provider work-order prompts;
- run records;
- evidence JSON;
- logs or exception text;
- issue/PR comments;
- provider result refs.

The live stdlib HTTP transport reads the environment value only while constructing the outgoing request and injects it as `X-Goog-Api-Key`. Returned transport data never contains request headers.

## 5. Permission attenuation

Before provider dispatch, the effective provider permissions are calculated as:

`Execution Contract ∩ Registry ceiling`

Registry capability never widens a contract. In particular, Jules `AUTO_CREATE_PR` is emitted only if the signed contract explicitly grants `open_pr=true`. `merge`, `publish_cdb_local_ci`, `close_issue`, `runtime_mutation`, `database_mutation`, and `mcp_live_mutation` remain false for the Jules provider profile.

## 6. Session creation and plan gate

For nontrivial CDB work, create the Session with `requirePlanApproval=true`.

Expected lifecycle:

1. Dispatch sealed provider work order.
2. Watch normalized Session state.
3. If state is `AWAITING_PLAN_APPROVAL`, read plan metadata and stop provider progress.
4. Approve only through the authorized explicit approval path.
5. Continue watching the same Session.
6. Use follow-up only against the known bound Session.

Never auto-approve because Jules generated a plan, because a provider state changed, or because a PR exists.

## 7. State normalization

CDB normalizes official Jules Session states as follows:

| Jules state | CDB provider status |
|---|---|
| `QUEUED` | `QUEUED` |
| `PLANNING` | `RUNNING` |
| `AWAITING_PLAN_APPROVAL` | `RUNNING` + explicit wait flag |
| `AWAITING_USER_FEEDBACK` | `RUNNING` + feedback flag |
| `IN_PROGRESS` | `RUNNING` |
| `PAUSED` | `RUNNING` + paused flag |
| `FAILED` | `FAILED` |
| `COMPLETED` | `SUCCEEDED` |
| unknown/unspecified | `UNKNOWN` / fail closed |

`SUCCEEDED` is provider execution status only. It is not CDB acceptance.

## 8. Activities and evidence

Durable result refs may contain only audit-safe metadata:

- Session name/id/url/state;
- Activity name/id/type/time/originator;
- Plan id and step id/index/title;
- validated GitHub PR URL/title handoff.

Do not persist free-form provider/user messages, bash output, raw patches, media, authentication data, presigned URLs, or provider-authored PR descriptions as durable ACP evidence.

A Jules PR is a handoff artifact. The ACP dispatcher still requires independent delivery receipt verification; a PR alone must end blocked rather than PASS.

## 9. Error and retry policy

Fail closed on:

- `401/403` → `AUTH_BLOCKED`;
- `429` → `PROVIDER_RATE_LIMITED`;
- unknown Session state;
- malformed provider response;
- missing required capability or API version drift;
- network abort after mutating POST;
- `5xx` after mutating POST where the outcome is unknown;
- repo/source/session binding ambiguity.

Do not blindly retry a mutating request whose outcome is unknown unless a future contract proves safe idempotency.

## 10. Cancel / timeout

The current documented Jules `v1alpha` surface has no CDB-supported cancel operation. The adapter must not fabricate one. `cancel()` therefore returns unconfirmed/unknown with `PROVIDER_CANCEL_UNSUPPORTED` and makes no network request.

Any workflow that requires confirmed cancellation remains blocked until the official API exposes a verified operation and the capability baseline plus tests are updated.

## 11. Live execution gate

Recorded/fake HTTP is the default test path. It may run under an offline-only `local_repo`/`mock` environment because it makes no live provider readiness claim.

A real Jules API request requires all of the following:

- separate explicit Human-GO for live provider execution;
- runtime `JULES_API_KEY` available without exposing its value;
- sealed provider work order and source binding;
- contract network allowlist containing `jules.googleapis.com`;
- capability baseline still valid;
- no Trading/Risk/Execution/DB/MCP-live/Live-Readiness authority expansion.

No live smoke is implied by recorded test success.

## 12. Validation

Minimum focused validation for adapter changes:

```text
pytest tests/unit/governance/test_jules_provider_v1.py
pytest tests/unit/governance/test_cursor_providers_v1.py
pytest tests/unit/governance/test_agent_registry_v1.py
pytest tests/unit/governance/test_agent_dispatcher_v1.py
python tools/validate_skill_surface_mirror.py --skill cdb-jules-dispatch
ruff check <changed Python files>
git diff --check
```

Any regression in existing Cursor/Mock provider behavior blocks delivery.
