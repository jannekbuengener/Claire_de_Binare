# Knowledge Refresh Loop Contract v1

**Schema:** `knowledge-refresh-report/v1`  
**Status:** MVP read-only closure slice  
**Issue:** [#2717](https://github.com/jannekbuengener/Claire_de_Binare/issues/2717)  
**Parent Epic:** [#1976](https://github.com/jannekbuengener/Claire_de_Binare/issues/1976)  
**Live-Readiness:** `NO-GO` — report is signal only, no live-go implication  
**Board Stage:** `trade-capable` — orthogonal to LR; no live capital

---

## Purpose

The Knowledge Refresh Loop Report composes existing Wave-16–20 read-only modules
into one deterministic operator report:

- `stale_knowledge_scan.py` → stale findings
- `stale_refresh_plan.py` → refresh plan items (`write_authorized=false`)
- `quality_scoring.py` → quality summary
- `architect_signals.py` → architect signal summary
- `agent_os_readiness.py` → optional readiness summary signal

The report surfaces documentation/knowledge refresh candidates. It does **not**
delete, archive, write memory, open GitHub issues, or mutate SurrealDB.

---

## Producer

| Component | Path |
|---|---|
| Orchestrator | `tools/surrealdb/knowledge_refresh_report.py` |
| CLI | `tools/surrealdb/knowledge_refresh_cli.py` |
| Entry point | `generate_knowledge_refresh_report_v1(bundle, as_of=None, include_readiness=True)` |

**Pure-report path constraints:**

- No SurrealDB SDK import
- No network I/O
- No GitHub API calls
- No filesystem writes from the report generator

---

## Input Bundle

Same in-memory bundle shape as stale/quality/architect modules. Minimum:

```json
{
  "meta": {
    "scope_id": "example-scope",
    "level": "domain",
    "as_of": "2026-05-06T12:00:00+00:00"
  },
  "sources": [],
  "decisions": [],
  "evidence_records": [],
  "memory_records": [],
  "dependency_edges": [],
  "context_packages": [],
  "briefings": []
}
```

Optional keys reused by quality/architect/readiness:

- `evidence_items`, `contradiction_findings`, `stale_findings`, `scope_drift_findings`, `memory_items`

When `evidence_items` is absent but `evidence_records` is present, the orchestrator
maps records into `evidence_items` for downstream scoring.

---

## Output Schema (`knowledge-refresh-report/v1`)

Top-level fields:

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | Always `knowledge-refresh-report/v1` |
| `report_id` | string | Deterministic SHA256 prefix (`scope_id\|as_of\|schema`) |
| `scope_id` | string | From `meta.scope_id` or default |
| `as_of` | string | ISO-8601 UTC reference time |
| `status` | string | `ok` or `error` |
| `classification_summary` | object | Counts per classification |
| `items` | array | Classified refresh candidates |
| `stale_scan` | object | Scan summary |
| `refresh_plan` | object | Plan summary; `write_authorized=false` |
| `quality` | object | Overall grade/score summary |
| `architect_signals` | object | Signal counts |
| `agent_os_readiness` | object \| null | Optional summary signal |
| `guardrails` | array | Non-empty guardrail strings |
| `errors` | array | Non-fatal sub-evaluator errors |

### Refresh report item

| Field | Type | Notes |
|---|---|---|
| `item_id` | string | Deterministic SHA256 prefix |
| `target_ref` | string | Path or artifact ref (source paths resolved from `source_id`) |
| `classification` | string | See classifications below |
| `reason` | string | Human-readable rationale |
| `write_authorized` | bool | **Always `false`** |
| `canon_protected` | bool | True when path matches canon prefix list |
| `stale_type` | string \| omitted | From stale scan when applicable |
| `severity` | string \| omitted | From stale finding |
| `priority` | string \| omitted | From refresh plan (`P0`–`P3`) |
| `plan_id` | string \| omitted | Refresh plan item id |
| `recommended_action` | string \| omitted | Canonical refresh action |
| `architect_signal_ids` | array \| omitted | Linked architect signals |
| `issue_proposal` | string \| omitted | Text-only proposal; never auto-submitted |

---

## Classifications

| Classification | Meaning |
|---|---|
| `canon_protected` | Canon path with no open stale finding requiring action |
| `refresh_required` | Open stale finding; includes canon paths (never archive-only) |
| `archive_candidate` | Non-canon deleted source; non-blocking delete signal |
| `needs_issue_proposal` | Blocking delete, P0 plan item, or blocking architect signal |
| `stale_but_accepted` | Finding status `accepted_stale` or `false_positive` |
| `orphan_candidate` | Source without owner/coverage/references |
| `no_action` | No refresh action indicated |

**Hard invariant:** Canon-protected sources are never classified as
`archive_candidate` or delete-only outcomes.

---

## Canon Protected Prefixes

Paths normalized to forward slashes and matched by prefix:

- `AGENTS.md`
- `agents/AGENTS.md`
- `agents/roles/`
- `knowledge/governance/`
- `docs/live-readiness/`
- `docs/runbooks/CONTROL_REGISTER.md`
- `CURRENT_STATUS.md`
- `CLAUDE.md`

---

## Determinism

- JSON output uses `core.replay.canonical_json.canonical_json_dumps` (sorted keys, compact).
- Repeated calls with the same bundle and `as_of` produce identical JSON.
- Timestamps default from `meta.as_of` when provided.

---

## Non-Goals (v1)

- DB write / memory write / GitHub write
- Auto-issue / auto-delete / auto-archive
- CI scheduler / dashboard / MCP tool exposure

---

## Related Issues

| Issue | Relationship |
|---|---|
| #1976 | Parent epic |
| #2204, #2603–#2606 | Related context/memory epics |
| #2689 | Out of scope (Gordon/Docker AI doc cleanup) |
| #2606 | Not blocking while MVP stays read-only |
