# Context Package Model v2

**Issue**: #2798
**Status**: Contract Defined
**Date**: 2026-06-02
**Parent**: #2778 (Phase-2 epic)
**Epic**: #1976

## Overview

Context Package v2 is the governed agent handoff envelope for the read-only Context
Intelligence layer. It packages retrieval ingredients, required reads, ranked context,
evidence links, and decision replay links into a bounded, redacted, deterministic output.

Implementation: [`tools/surrealdb/context_package_v2.py`](../../tools/surrealdb/context_package_v2.py)

## Purpose

- Standardized agent handoff schema with explicit guardrails
- Deterministic multi-artifact hashing for replay and audit
- Granular redaction with attributable `redaction_summary`
- Integration hooks for hybrid ranking (#2799) and decision replay (#2800)
- Fail-closed limitations when upstream inputs are missing or unverified

## Non-Goals

- No authorization, Live-Go, or Echtgeld-Go derivation
- No productive SurrealDB writes; `PERSIST_ALLOWED=False`, `MUTATION_ALLOWED=False`
- No trading/risk/execution/strategy effects
- No automatic code or issue actions from package output
- No replacement of MCP `context.package` v0 handler in this slice

## Relationship to v1

| Surface | Role |
|---------|------|
| [`context-package-model-v1.md`](context-package-model-v1.md) | Rich retrieval lifecycle model (#2016) — unchanged |
| MCP `context.package` handler | Repo/registry packaging v0 — unchanged |
| **Context Package v2** | Pure builder envelope for governed handoffs (#2798) |

Briefings reference packages via `context_package_ref` (package_id). v2 uses
`schema_version: "context-package/v2"`.

---

## Envelope Schema

All packages **must** include these top-level fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Always `"context-package/v2"` |
| `package_id` | string | Yes | Deterministic ID (`pkg_<12 hex chars>`) |
| `generated_at_or_as_of` | string | Yes | ISO8601 timestamp or as-of marker |
| `target_scope` | string | Yes | Task/issue/scope identifier |
| `source_priority` | string[] | Yes | Truth-order for downstream consumers |
| `required_reads` | object[] | Yes | Structured required read entries |
| `artifacts` | object[] | Yes | Redacted artifact payloads |
| `ranked_context` | object \| null | Yes | Hybrid ranking output (#2799) or null |
| `evidence_links` | object[] | Yes | Evidence references (may be empty) |
| `decision_replay_links` | object[] | Yes | Replay references (#2800) |
| `redaction_summary` | object[] | Yes | What was redacted (path/field/type only) |
| `limitations` | string[] | Yes | Missing/unverified upstream signals |
| `guardrails` | string[] | Yes | Non-authorizing boundary statements |
| `determinism` | object | Yes | Hash metadata block |

### Example

```json
{
  "schema_version": "context-package/v2",
  "package_id": "pkg_a1b2c3d4e5f6",
  "generated_at_or_as_of": "2026-06-02T12:00:00+00:00",
  "target_scope": "issue:2798",
  "source_priority": [
    "github_live",
    "repo_live",
    "verified_context_db_mcp_evidence",
    "canonical_governance_files",
    "ledger_files",
    "memory"
  ],
  "required_reads": [
    {
      "path": "AGENTS.md",
      "priority": "required",
      "reason": "Root pointer"
    }
  ],
  "artifacts": [
    {
      "artifact_id": "docs/surrealdb/context-package-model-v1.md",
      "artifact_type": "doc",
      "summary": "Baseline package model"
    }
  ],
  "ranked_context": null,
  "evidence_links": [],
  "decision_replay_links": [],
  "redaction_summary": [],
  "limitations": [
    "ranked_context_not_provided",
    "decision_replay_links_not_provided",
    "evidence_links_not_provided"
  ],
  "guardrails": [
    "Context Package is orientation, not authorization.",
    "LR remains NO-GO; no Live-Go.",
    "No Echtgeld-Go.",
    "No automatic code or issue action from package output.",
    "No DB-backed claim without tool/query/record evidence."
  ],
  "determinism": {
    "hash_algorithm": "canonical_sha256",
    "wall_clock_excluded": true,
    "artifact_count": 1,
    "content_hash": "<64-char hex>"
  }
}
```

---

## Artifact Input Contract

Each artifact ingredient must include:

- `artifact_id` (or `id`)
- `artifact_type` (or `type`)

Optional nested fields (metadata, source_refs, summaries) are redacted in place.
Transient fields (`generated_at`, `created_at`, `updated_at`, `as_of`) are excluded
from per-artifact hash input.

---

## Redaction Rules

1. **Sensitive keys** matching `(token|secret|password|api_key|credential|private_key|auth)`
   (case-insensitive) → value replaced with `"[REDACTED]"`.
2. **Secret value patterns** in string values (Bearer tokens, `sk-…`, JWT `eyJ…`) → redacted.
3. **Raw secret values must never appear** in package output.
4. **`redaction_summary`** records `{ "path", "field", "redaction_type" }` only — never
   the original value.
5. Unresolved or unsafe inputs produce `limitations` entries, not fake verification.

### redaction_type Values

| Type | Meaning |
|------|---------|
| `sensitive_key` | Field name matched sensitive key pattern |
| `secret_value_pattern` | String value matched secret pattern |

---

## Multi-Artifact Hash Algorithm

Uses [`core/replay/canonical_json.py`](../../core/replay/canonical_json.py) (`canonical_hash`).

1. **Redact** all artifact payloads and nested link maps.
2. **Sort artifacts** by `(artifact_id, artifact_type, canonical_json(payload))`.
3. **Per-artifact hash:** `canonical_hash(redacted_payload_without_transient_fields)`.
4. **Build hash input** (wall-clock excluded):

```json
{
  "schema_version": "context-package/v2",
  "target_scope": "...",
  "source_priority": ["..."],
  "required_reads": [],
  "artifact_hashes": ["..."],
  "ranked_context_fingerprint": null,
  "evidence_links_fingerprint": null,
  "decision_replay_links_fingerprint": null
}
```

5. **`content_hash`** = `canonical_hash(hash_input)` (full 64-char hex).
6. **`package_id`** = `"pkg_" + content_hash[:12]`.
7. **`generated_at_or_as_of`** is in the envelope but **excluded** from hash input.

---

## Source Priority / Truth Order

Default `source_priority`:

1. `github_live`
2. `repo_live`
3. `verified_context_db_mcp_evidence`
4. `canonical_governance_files`
5. `ledger_files`
6. `memory`

Consumers must treat higher-priority sources as authoritative over lower tiers.
Package output itself is orientation — not authorization.

---

## Upstream Integration

| Upstream | Field | Missing behaviour |
|----------|-------|-----------------|
| #2799 `rank_retrieval_ranking` | `ranked_context` | `limitations: ranked_context_not_provided` |
| #2800 `decision_replay_builder` | `decision_replay_links` | `limitations: decision_replay_links_not_provided` |
| `context_required_reads` | `required_reads` | Empty list allowed |
| Evidence resolver (future) | `evidence_links` | `limitations: evidence_links_unverified` when refs-only |

No live DB is required. All integration is via in-memory dict inputs.

---

## Operator / Agent Consumption

- Use the package for **orientation** before planning or handoff.
- Read `limitations` before trusting ranked/evidence/replay sections.
- Check `guardrails` and `redaction_summary` before citing package content.
- **`context_package_ref` in briefings** should reference `package_id` from this envelope.
- **LR remains NO-GO** — package output does not authorize live trading or Echtgeld.

---

## Guardrails

Non-negotiable statements included in every package:

- Context Package is orientation, not authorization.
- LR remains NO-GO; no Live-Go.
- No Echtgeld-Go.
- No automatic code or issue action from package output.
- No DB-backed claim without tool/query/record evidence.

---

## Validation

Contract tests: [`tests/unit/surrealdb/test_context_package_v2.py`](../../tests/unit/surrealdb/test_context_package_v2.py)

---

## References

| Item | Link |
|------|------|
| v1 model | [`context-package-model-v1.md`](context-package-model-v1.md) |
| Hybrid ranking | [`context-hybrid-retrieval-strategy-v1.md`](context-hybrid-retrieval-strategy-v1.md) |
| Decision replay | [`decision_replay_query_contract.md`](decision_replay_query_contract.md) |
| Briefing schema | [`context-agent-briefing-schema-v1.md`](context-agent-briefing-schema-v1.md) |
| Issue #2798 | Context Package v2 implementation |
| Issue #2778 | Phase-2 parent epic |
