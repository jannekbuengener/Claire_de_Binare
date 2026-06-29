# CDB Context Drift / Stale / Contradiction Contract

**Status:** CONTRACT_ONLY — warning-layer contract only, no operational detection.

**Issues:** [#3491], [#3483], [#3485], [#3490], [#3479]

## 1. Purpose

This contract defines the top-level CDB warning layer for drift, stale knowledge,
and contradiction findings around Context / SurrealDB surfaces.

Practical meaning in CDB:

- **stale** means a repo, GitHub, claim, decision, or memory statement is no
  longer fresh enough to be trusted without re-checking the source of truth
- **contradiction** means two authoritative or quasi-authoritative sources
  disagree and need human review
- **drift** means repo docs, live GitHub reality, or declared scope have
  diverged enough that an agent must stop, warn, or narrow its claim

This slice is intentionally limited to:

- one concise contract document
- one machine-readable contract artifact
- warning-layer semantics only

This slice does **not** build:

- a drift engine
- a stale scanner
- a contradiction resolver
- auto-resolution
- DB-backed detection
- productive Evidence / Claim / Decision / Memory writes

## 2. Contract Posture

Hard rules for this slice:

- `operational=false`
- `DB_BACKED_READONLY_PROVEN` must not be claimed
- `live_detection_enabled=false`
- `mutation_allowed=false`
- no automatic issue closure
- no automatic LR or live-gate change
- no automatic DB mutation
- no claim truth promotion without evidence
- the warning layer may mark and recommend, but never authorise
- CDB governance wins over SurrealDB capabilities

Repo-backed context for the current warning surfaces:

- the Wave-15/16/17/20 tools exist as read-only signal surfaces
- `artifacts/context_tool_inventory/tool_inventory.json` keeps the warning tools
  at `CONTRACT_ONLY`
- `artifacts/mcp/mcp_access_boundary_matrix.json` keeps them
  `ALLOWED_READONLY` but `DB_BACKED_READONLY_UNPROVEN`

Therefore the contract must stay **signal-only** and **non-operational**.

## 3. Detectable Signal Types

Each signal type carries:

- `source_category`
- `evidence_required`
- `freshness_policy`
- `detection_basis`
- `severity`
- `resolution_state`
- `owner`
- `allowed_action`

### Signal matrix

| Signal | Meaning | Typical source | Severity | Allowed action |
|---|---|---|---|---|
| `stale_doc` | repo doc is older than its verified repo truth | repo file | `warning` | recommend refresh only |
| `stale_issue_status` | issue narrative is stale against GitHub live | GitHub issue | `warning` | recommend live recheck only |
| `stale_pr_status` | PR narrative is stale against GitHub live | GitHub PR | `warning` | recommend live recheck only |
| `stale_claim` | claim freshness or linked evidence is stale | claim + evidence | `warning` | recommend evidence recheck only |
| `stale_memory` | scoped memory expired or lost freshness | agent memory | `warning` | recommend memory refresh only |
| `contradicted_claim` | a claim is disputed by evidence or source truth | claim + evidence | `blocking` | request human review only |
| `contradicted_decision` | a decision conflicts with newer evidence or canon | decision + evidence | `blocking` | request human review only |
| `repo_doc_drift` | repo docs and current repo-backed contract surfaces diverge | repo docs + artifacts | `warning` | recommend repo reconcile only |
| `github_repo_drift` | GitHub live state and repo/ledger claim diverge | GitHub + repo | `warning` | recommend live reconcile only |

## 4. Evidence And Freshness Rules

The warning layer inherits evidence and freshness boundaries from the foundation
contracts:

- repo-backed surfaces require source hashes where applicable
- GitHub-backed surfaces require live issue/PR references and refresh on state
  change or TTL expiry
- claim and evidence surfaces require provenance plus source-linked evidence
- decision surfaces point back to the Git ledger
- memory surfaces remain scoped, TTL-bound, and non-authoritative

Practical freshness policy by family:

| Family | Freshness rule |
|---|---|
| repo docs / repo artifacts | hash-verified or refresh on main merge |
| GitHub issue / PR mirrors | stale after 24h or state change |
| claims / evidence | hash-verified, no truth without evidence |
| decisions | no-expiry ledger pointer, but contradiction possible against new evidence |
| agent memory | TTL-bound or refresh on issue/session/state change |

## 5. Resolution States

The contract recognises six resolution states:

| State | Meaning |
|---|---|
| `open` | finding exists and is not yet triaged |
| `confirmed` | finding is real and acknowledged |
| `dismissed` | finding was reviewed and rejected |
| `superseded` | a newer finding or decision replaces it |
| `fixed` | the underlying source divergence was reconciled |
| `parked` | deferred intentionally without pretending the gap disappeared |

These states classify a finding. They do not authorise write actions by
themselves.

## 6. Explicitly Forbidden Auto-Resolutions

The following actions must remain blocked:

- `auto_close_issue`
- `auto_change_live_gate`
- `auto_override_lr_status`
- `auto_delete_memory`
- `auto_mutate_db`
- `auto_mark_claim_true_without_evidence`

If a warning surface suggests any of the above, the correct interpretation is:

- stop
- gather evidence
- require human review or a separate implementation/governance slice

## 7. Foundation Contract Linkage

This contract sits above three foundation contracts:

1. **#3483 Ownership**
   - `docs/surrealdb/CDB_CONTEXT_DATA_MODEL_OWNERSHIP.md`
   - `artifacts/surrealdb/context_data_model_ownership_matrix.json`
   - supplies source-of-truth, owner, mirror, persistence, and forbidden-domain boundaries
2. **#3485 Fulltext / BM25**
   - `docs/surrealdb/CDB_CONTEXT_FULLTEXT_BM25_CONTRACT.md`
   - `artifacts/surrealdb/context_fulltext_bm25_contract.json`
   - supplies repo/GitHub/evidence/claim/decision freshness cues and the fulltext exclusion posture
3. **#3490 Agent Memory**
   - `docs/surrealdb/CDB_AGENT_MEMORY_CONTRACT.md`
   - `artifacts/surrealdb/agent_memory_contract.json`
   - supplies scoped memory TTL, evidence, and non-authoritative read/write boundaries

## 8. Safety Boundaries

This contract does not authorise:

- runtime or BLUE/RED changes
- productive SurrealDB writes
- MCP mutation
- live detection
- live trading or Echtgeld actions
- LR uplift
- GitHub issue state changes without separate human-directed evidence

The only truthful outcome of this slice is:

- a documented contract surface
- a machine-readable artifact
- repo-backed tests turning green for the contract-only warning layer

## 9. References

- `artifacts/surrealdb/context_data_model_ownership_matrix.json`
- `artifacts/surrealdb/context_fulltext_bm25_contract.json`
- `artifacts/surrealdb/agent_memory_contract.json`
- `artifacts/mcp/mcp_access_boundary_matrix.json`
- `artifacts/context_tool_inventory/tool_inventory.json`
- `docs/surrealdb/context-contradiction-detection-runbook.md`
- `docs/surrealdb/stale-knowledge-runbook.md`
- `docs/surrealdb/scope-drift-runbook.md`
