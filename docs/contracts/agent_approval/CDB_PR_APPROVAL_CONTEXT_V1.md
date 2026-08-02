# CDB PR Approval Context v1

Status: Canonical (delivery slice `#4257`)  
Schema id: `cdb.pr_approval_context.v1`  
Schema: [`../cdb_pr_approval_context.v1.schema.json`](../cdb_pr_approval_context.v1.schema.json)

## Purpose

Provide a **repo-backed, deterministic, read-only** approval context for pull
requests. The envelope may produce at most one **recommendation**. It never
merges, never publishes `cdb-local-ci`, never changes branch protection or
rulesets, and never authorizes Live/Echtgeld actions.

Downstream E2E pilot work remains `#4258` and is out of scope for this contract.

## Authority limits (hardcoded false)

| Limit | Value |
| --- | --- |
| `merge` | `false` |
| `publish_cdb_local_ci` | `false` |
| `modify_branch_protection` | `false` |
| `modify_rulesets` | `false` |
| `execute_live_agent` | `false` |
| `live_go` | `false` |
| `real_money_go` | `false` |

## Recommendation enum

`APPROVE_RECOMMENDED` | `REQUEST_CHANGES` | `ABSTAIN` | `HOLD` | `BLOCKED` |
`UNKNOWN`

Never use the unqualified word `APPROVE` as an authority state.
`UNKNOWN` or missing evidence never yields `APPROVE_RECOMMENDED`.
Drift other than `NONE` never yields `APPROVE_RECOMMENDED`.

## Reason codes

Machine-readable codes live in `reason_codes[]`. Important examples:

- `STALE_HEAD` — checks/reviews/previous context bound to a different head
- `MISSING_HEAD` / `INVALID_HEAD` / `CONFLICTING_HEAD`
- `MECHANISM_MISMATCH` / `APP_ID_MISMATCH`
- `REQUIRED_CHECK_PENDING` / `REQUIRED_CHECK_FAILED` / `REQUIRED_CHECK_MISSING`

`STALE_HEAD` is a **reason/error code**, not a recommendation value.

## Head-SHA binding

- `subject.head_sha` and `subject.base_sha` must be 40-hex when valid.
- Output and `context_digest` bind the exact head.
- Checks and review evidence must refer to the same head.
- Re-evaluation on a new head yields a new context and digest.

## Policy and prompt versioning

Repo files:

- `config/agent-control/policies/approval/pr_approval.v1.yaml`
- `config/agent-control/prompts/approval/pr_approval.v1.md`

Envelope fields: `version`, `source_path`, `content_sha256`.

`content_sha256` is **computed at load time** from file bytes. Source files must
**not** embed their own hash (no circular contract).

## Required checks

Each observation includes `name`, `mechanism`
(`check_run` | `commit_status` | `unknown`), `status`, `matches_protection`,
and optional `app_id` / `conclusion` / `source_sha`.

Hard rules:

- Check Run and Commit Status are never equated.
- Name alone is insufficient for `matches_protection`.
- When protection requires an `app_id`, it must match.
- Operative truth is the **injected protection/ruleset snapshot**.
- Current default documentation (not hardcoded universal truth): required
  context `cdb-local-ci` as App Check Run `app_id=4410232` — see
  [`../../runbooks/merge_policy_ci_gate.md`](../../runbooks/merge_policy_ci_gate.md).

## Drift

`NONE` | `POLICY` | `PROMPT` | `ADAPTER` | `PROTECTION_VIEW` | `UNKNOWN`

Missing baseline → `UNKNOWN` (never silently treated as `NONE`).
Hash mismatch is fail-closed.

## Determinism

- Canonicalization: JCS / RFC 8785 via `tools.agent_execution_contract.jcs`
- Digest: SHA-256 (`sha256:<hex>`), digest fields excluded from hash material
- Wall-clock metadata may exist under `metadata` but must not affect
  `context_digest`

## CLI

```bash
python -m tools.agent_control approval context --pr <N> --snapshot <PATH>
python -m tools.agent_control approval drift --baseline <PATH>
```

CLI reads local/injected snapshots only. No GitHub mutation. No dispatcher run.
No merge.

## Safety

- LR remains **NO-GO**
- Board stage `trade-capable` is not Live-Go
- No productive DB/MCP writes
- No secrets in inputs or outputs
- Approval recommendation ≠ merge authority
