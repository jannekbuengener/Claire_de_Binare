# Context trust threshold contract (operator levels)

| Field | Value |
| --- | --- |
| Status | **active** |
| Version | `context-trust-threshold/v1` |
| Issue | [#2856](https://github.com/jannekbuengener/Claire_de_Binare/issues/2856) |
| Parent meta | [#2847](https://github.com/jannekbuengener/Claire_de_Binare/issues/2847) |
| Builder | [`tools/surrealdb/trust_summary.py`](../../../tools/surrealdb/trust_summary.py) |
| MCP tool | `cdb_context_trust_summary`, `cdb_context_briefing` / `context.briefing` |
| Related | [#2851](https://github.com/jannekbuengener/Claire_de_Binare/issues/2851) DB record evidence, [#2854](https://github.com/jannekbuengener/Claire_de_Binare/issues/2854) negative controls, [#2855](https://github.com/jannekbuengener/Claire_de_Binare/issues/2855) operator senses |

## Purpose

Operators and agents need a **testable, read-only** mapping from context tooling output
to **`operator_trust_level`** (`HIGH` | `MEDIUM` | `LOW` | `BLOCKED`) without treating
trust as authorization for writes, live trading, merges, persist, or Human-GO.

Wave-14 **`trust_level`** (`strong` | `acceptable` | `weak` | `blocked`) remains for
backward compatibility. **`operator_trust_level`** is the operator SSOT ([#2856](https://github.com/jannekbuengener/Claire_de_Binare/issues/2856)).

## Safety boundaries (non-negotiable)

- LR remains **NO-GO** ([`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)).
- Board stage `trade-capable` is **not** live-go.
- Trust output **never** grants: Human-GO, Live-GO, Echtgeld-GO, `PERSIST_ALLOWED`, `MUTATION_ALLOWED`.
- **`operational_truth_allowed` is always `false`** — even at `HIGH`; trust may only assist prioritization and `recommended_next_reads`.
- `LOW` and `BLOCKED` must **not** drive operational truth (writes, live actions, merge decisions, LR verdicts).
- Caller-supplied `brain_source`, `metadata.source`, or `context_signals` overrides cannot upgrade trust without evidence ([#2638](https://github.com/jannekbuengener/Claire_de_Binare/issues/2638)).

## Dual fields on `trust-summary/v1`

| Field | Values | Role |
| --- | --- | --- |
| `trust_level` | `blocked`, `weak`, `acceptable`, `strong` | Wave-14 legacy composite bands |
| `operator_trust_level` | `BLOCKED`, `LOW`, `MEDIUM`, `HIGH` | Operator / prompt SSOT |
| `operator_trust_mapping` | object | Legacy level, composite score, applied gates |
| `limitations` | string[] | Required below `HIGH`; merged with MCP envelope defaults |
| `authorization_semantics` | object | Explicit no-GO / no-persist / no-mutation flags |

### Legacy → operator base mapping

| `trust_level` (legacy) | `operator_trust_level` (base) |
| --- | --- |
| `strong` | `HIGH` |
| `acceptable` | `MEDIUM` |
| `weak` | `LOW` |
| `blocked` | `BLOCKED` |

Gates in [`trust_summary.py`](../../../tools/surrealdb/trust_summary.py) may **lower**
the operator level (never raise above base without satisfying HIGH gates).

## Operator levels — criteria

### HIGH

All required:

- Legacy `trust_level` = `strong` (composite ≥ 0.80, no blocking findings).
- No `blocking_trust_findings`.
- No `stale_flags` or `disputed_flags` on the summary.
- `context_signals.freshness_ok` = true (when signals supplied).
- `context_signals.repo_crosscheck_present` = true (when signals supplied).
- No `context_signals.github_live_mismatch` or `ledger_stale_vs_live`.
- `context_signals.caller_supplied_source_only` = false.
- `context_signals.record_source` not `repo-only` or `in_memory` (when set).
- No `context_signals.required_db_records_missing`.

### MEDIUM

- Base mapping `acceptable`, or `strong` capped by repo-only/in-memory source, stale/disputed context, or missing repo crosscheck when signals are explicit.
- Usable for planning hints and next reads; **not** operational truth.

### LOW

- Base mapping `weak`, or caller-only source without full gates, or `freshness_ok` = false (when signals supplied).
- **Not** operational truth; must include explicit limitations.

### BLOCKED

Any of:

- Legacy `blocked` or non-empty `blocking_trust_findings`.
- `github_live_mismatch` or `ledger_stale_vs_live` in `context_signals`.
- `required_db_records_missing` when DB proof was required.
- `caller_supplied_source_only` with blocking/contradiction signals.

## Optional `context_signals` (request parameter)

Harness/tests may pass `parameters.context_signals`:

| Key | Type | Meaning |
| --- | --- | --- |
| `github_live_mismatch` | bool | Live GitHub contradicts ledger/briefing claim |
| `ledger_stale_vs_live` | bool | `CURRENT_STATUS` or ledger stale vs live GitHub |
| `repo_crosscheck_present` | bool | Repo path/commit/symbol crosscheck documented |
| `record_source` | string | `surrealdb-local`, `repo-only`, `in_memory`, … |
| `caller_supplied_source_only` | bool | Trust upgrade attempted via caller metadata only |
| `freshness_ok` | bool | Evidence freshness acceptable |
| `required_db_records_missing` | bool | Required DB records absent for scope |

When `context_signals` is **omitted**, `operator_trust_level` follows legacy base mapping only (Wave-14 regression compatibility).

## Examples (golden narratives)

1. **HIGH** — Strong fixture evidence, `repo_crosscheck_present`, `record_source=surrealdb-local`, no stale/disputed/blocking → `operator_trust_level=HIGH`, limitations still state no authorization.
2. **MEDIUM** — Acceptable composite but `record_source=repo-only` → capped to `MEDIUM`, limitations cite repo-only cap.
3. **LOW** — Weak composite + `caller_supplied_source_only` → `LOW`, limitation: not operational truth.
4. **BLOCKED** — `blocking_missing_evidence` or `github_live_mismatch` → `BLOCKED`, review before proceed.

## Agent prompt rule

In Brain Evidence and Context scope:

- Treat `operator_trust_level` of `LOW` or `BLOCKED` as **fail-closed for operational truth**.
- Do not merge, persist, mutate runtime, or infer LR/live-go from trust output alone.
- Prefer live GitHub + repo reads over trust summary text.

Canonical agent surfaces: [`agents/OPEN_CODE_AGENTS.md`](../../../agents/OPEN_CODE_AGENTS.md), [`docs/runbooks/CDB_AGENT_SENSES_OPERATOR.md`](../../runbooks/CDB_AGENT_SENSES_OPERATOR.md) §8.

## Related contracts

- [`DB_RECORD_EVIDENCE_CONTRACT.md`](DB_RECORD_EVIDENCE_CONTRACT.md) — DB-backed claim rules
- [`TOOL_INVOCATION_JSON_EVIDENCE.md`](TOOL_INVOCATION_JSON_EVIDENCE.md) — harness JSON proof
