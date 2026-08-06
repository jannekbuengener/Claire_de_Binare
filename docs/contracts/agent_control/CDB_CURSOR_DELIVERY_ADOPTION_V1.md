# CDB Cursor Delivery Adoption v1

Status: Canonical (reconciliation slice `#4258`)  
Schema id: `cdb.cursor_delivery_adoption.v1`  
Schema: [`../cdb_cursor_delivery_adoption.v1.schema.json`](../cdb_cursor_delivery_adoption.v1.schema.json)

## Purpose

Import an **already existing**, externally produced Cursor Cloud GitHub
delivery into the ACP pilot as a separate **adoption receipt**. The path is
read-only toward Cursor and toward the source PR. It never creates a Cursor
agent/run, never posts to Cursor HTTP create/resume endpoints, and never
mutates the evidence-source PR.

## When to use

Use only when live GitHub evidence jointly binds:

1. exact repository (`owner/name`)
2. Cursor agent id (PR body + commit provenance; footer alone is insufficient)
3. branch tip
4. commit SHA
5. open (or otherwise observed) PR head matching that tip

## Authority limits (hardcoded false)

| Limit | Value |
| --- | --- |
| `merge` | `false` |
| `approval` | `false` |
| `live` | `false` |
| `runtime_mutation` | `false` |
| `github_delivery_create` | `false` |
| `cursor_http_posts` | `false` |
| `publish_cdb_local_ci` | `false` |

## Identity separation

- `adoption_id` / `adopted_delivery_id` identify the adoption receipt.
- Prior failed CDB/Cursor run IDs stay in `original_cdb_run_ids` and are
  **never** rewritten as this delivery.
- `provider_dispatch_proven` is `false` unless a CDB ACP create is proven for
  **this** delivery. External cloud PRs must keep it `false`.

## Determinism

- Canonicalization: JCS / RFC 8785
- Digest: `sha256:<hex>` over the receipt body excluding digest fields and
  wall-clock `metadata`
- Repeated adoption of the same bindings yields the same `adoption_id` and
  `canonical_digest`
- Different head, PR, agent, repo, or branch → fail-closed HOLD

## CLI

```bash
python -m tools.agent_control pilot cursor-adopt-delivery \
  --issue 4258 \
  --repository jannekbuengener/Claire_de_Binare \
  --cursor-agent-id bc-<uuid> \
  --delivery-pr <N> \
  --expected-head <40-hex> \
  [--expected-branch <name>] \
  [--out <receipt.json>]
```

## Safety

- LR remains **NO-GO**
- No secrets in receipts
- No GitHub writes from the verifier
- No claim that an external PR was produced by a prior CDB pilot run
- Approval Context / Handoff may bind this receipt; they do not approve or merge
