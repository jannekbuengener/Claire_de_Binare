# Context Intelligence — `decision_event` Generator Policy v1

**Status**: Design (Wave-14 Follow-up)
**Authority**: Issue #2570 / Follow-up Arc of PR #2565
**Parent**: Epic #1976
**Schema Reference**: `infrastructure/surrealdb/context_intelligence_v0.surql` (`decision_event` table)
**Guardrail**: No trading state, no secrets, no Live-Go, no Echtgeld-Go, no runtime change.

---

## 1. Purpose and Scope

The Wave-14 `decision_event` table exists in the schema and the JSONL importer accepts
`decision_events.jsonl`, but the repo indexer (`context_indexer.py`) deliberately does not
generate decision event records.

Decision events represent authoritative records of decisions made during system development and
governance. Commit messages, issue titles, and documentation fragments are contextual hints —
they are not automatically authoritative decision records.

This document defines:
- Whether a decision event generator should exist and under what constraints
- What constitutes an authoritative decision source
- Mandatory fields for valid decision event records
- The explicit semantics of `human_go`
- How to prevent invented or inferred Human-GO claims

**Scope:**
- Decision event generator policy
- Authoritative source model
- Mandatory fields for valid decision_event records
- `human_go` semantics and constraints
- Evidence requirements
- Minimal safe authoring workflow

**Non-Goals:**
- No implementation of an automated decision extractor
- No schema changes
- No DB writes
- No inference of Human-GO from commit messages or PR merges
- No Live-Readiness assertion from decision events
- No Echtgeld-Go from decision events
- No GitHub network dependency by default

---

## 2. Core Design Decision

**A fully automated decision event generator MUST NOT be implemented.**

Reasons:
1. Decisions require human intent. Commit messages and issue titles describe what changed,
   not why it was decided to be the correct choice.
2. Automatically deriving `human_go: true` from a PR merge would falsify governance state.
   A merged PR is evidence that a change was integrated — it is not evidence that an
   explicit Human-GO was given.
3. An automated generator risks producing governance records that appear authoritative
   but represent inferred, not actual, decisions.

**Minimal safe slice:** Human-authored JSONL is the only unconditionally permitted path.
Agent-assisted authoring is permitted with Human-GO (see Section 4).

---

## 3. Authoritative Decision Sources

| Source | Allowed | `human_go` | Notes |
|---|---|---|---|
| Human manual authoring (JSONL) | ✅ Yes | As specified by author | Author explicitly sets `true` or `false` |
| Explicit governance documents (CONTROL_REGISTER.md, LR docs) | ✅ Yes (as basis) | Specified per-entry | Docs provide evidence; human transcribes as JSONL |
| Agent-drafted, human-reviewed (JSONL) | ✅ Yes | Human reviewer must confirm `human_go` | Agent MUST NOT self-assign `human_go: true` |
| PR merge event | ⚠️ Permitted with constraints | `false` only | `decision_type: "merge_decision"` — see Section 3.1 |
| Commit message parsing | ❌ No | N/A | Not authoritative |
| Issue title extraction | ❌ No | N/A | Not authoritative |
| Doc heading extraction | ❌ No | N/A | Not authoritative |
| Automated repo scanner | ❌ No | N/A | Prohibited |

### 3.1 PR Merge Events as Decision Evidence

PR merges are episodic events that may be recorded as decision events under the following
constraints:
- `decision_type` MUST be `"merge_decision"`
- `human_go` MUST be `false` (a merge is not a Human-GO signal)
- `evidence_refs` MUST include at least one `evidence_id` pointing to the PR or CI evidence
- `title` MUST describe the actual decision (not just the PR title)
- The record is NOT a substitute for an explicit governance decision

**Example valid merge decision event:**
```json
{
  "decision_id": "dec-merge-2574",
  "title": "Adopt Windows-compatible ops target for context-status",
  "question": "Should context-status target use PowerShell instead of bash?",
  "answer": "Yes — Makefile target updated to PowerShell for Windows compatibility.",
  "decision_type": "merge_decision",
  "status": "current",
  "scope": "ops",
  "evidence_refs": ["ev-pr-2574"],
  "claim_refs": [],
  "human_go": false,
  "confidence": 0.9,
  "created_at": "2026-05-18T19:00:00Z"
}
```

---

## 4. Mandatory Fields for a Valid `decision_event` Record

Every `decision_event` record imported via `decision_events.jsonl` MUST include the following
fields. Records missing mandatory fields MUST be rejected by the importer with a blocking finding.

| Field | Type | Requirement | Notes |
|---|---|---|---|
| `decision_id` | string | Mandatory | Stable deterministic ID (e.g., `dec-<scope>-<seq>`) |
| `title` | string | Mandatory | Human-readable short title of the decision |
| `question` | string | Mandatory | The question the decision answers |
| `answer` | string | Mandatory | The chosen answer/option |
| `decision_type` | string | Mandatory | One of: `architecture`, `governance`, `merge_decision`, `scope_decision`, `policy_decision` |
| `status` | string | Mandatory | One of: `proposed`, `current`, `superseded`, `invalidated` |
| `scope` | string | Mandatory | Scope identifier |
| `evidence_refs` | array | Mandatory (≥1) | At least one `evidence_id` from `evidence_ref` table |
| `human_go` | bool | Mandatory | Explicit: `true` only if a human GO signal was recorded; default `false` |
| `confidence` | float | Mandatory | In [0.0, 1.0] |
| `created_at` | datetime | Mandatory | ISO 8601 |

Optional fields: `claim_refs`, `affected_artifacts`, `agent`, `superseded_by`,
`invalidated_by`, `uncertainty`, `comment`.

---

## 5. `human_go` Semantics

`human_go` is a boolean field on `decision_event` that records whether an explicit human
GO signal was associated with the decision.

**Rules:**
- Default is `false`. A decision event may exist without a Human-GO.
- `true` MUST only be set when a verifiable human GO signal was given (e.g., explicit
  comment in the referenced issue/PR, documented sign-off in a governance file).
- An agent MUST NOT self-assign `human_go: true`.
- A PR merge does NOT constitute `human_go: true` — use `false` for all merge decisions.
- `human_go: true` does NOT grant Live-Readiness, Echtgeld-Go, or trading approval.
  Those require the LR gate (`docs/live-readiness/`), which remains NO-GO.

---

## 6. Prohibited `decision_event` Content

| Prohibited Content | Reason |
|---|---|
| `"human_go": true` inferred from PR merge | Merge ≠ Human-GO |
| Decision asserting Live-Readiness or Echtgeld-Go | LR gate required |
| Decision derived from commit message text alone | Not authoritative |
| `evidence_refs: []` on any record | No provenance = invalid |
| `human_go: true` set by automated process | Prohibited; agent MUST NOT self-assign |

---

## 7. Validation Gates Before Import

| Gate | Severity | Description |
|---|---|---|
| Missing mandatory field | Blocking | Any field in Section 4 is absent |
| `evidence_refs` empty | Blocking | No evidence = unacceptable |
| `human_go` absent | Blocking | Must be explicit boolean |
| `decision_type` not in allowed set | Blocking | Unknown type |
| `status` not in allowed set | Blocking | Unknown status |
| `confidence` outside [0.0, 1.0] | Blocking | Numeric contract violation |
| `evidence_refs[*]` not in current batch | Warning | Cross-batch reference may be valid |
| `claim_refs[*]` not in current batch | Warning | Cross-batch reference may be valid |
| `human_go: true` with no verifiable GO source in `evidence_refs` | Warning | Suspicious; human reviewer must confirm |

---

## 8. Guardrail Review (G1–G10)

| # | Guardrail | Result |
|---|---|---|
| G1 | No trading state | ✅ No orders/positions/fills/balances |
| G2 | No secrets | ✅ No credentials or keys |
| G3 | No Live-Go | ✅ LR remains NO-GO; `human_go: true` explicitly does not grant LR |
| G4 | No Echtgeld-Go | ✅ Explicitly prohibited |
| G5 | No runtime change | ✅ No service or compose change |
| G6 | No autonomy without Human Gate | ✅ Agent cannot self-assign human_go; requires human review |
| G7 | No Board-Stage to LR-Go mapping | ✅ Not mentioned as Live-Go |
| G8 | No productive apply | ✅ No SurrealDB apply commands |
| G9 | Git/Repo is SSoT | ✅ Issues and schema cited as authority |
| G10 | Hash-backed evidence | ✅ `evidence_refs` mandatory; source_refs on backing evidence required |

---

## 9. Provenance

| Source | Type | Status |
|---|---|---|
| Issue #2570 | Authority | OPEN (closed by this document) |
| PR #2565 | Context | MERGED |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema | PRESENT |
| `docs/surrealdb/context-evidence-ref-semantics-v1.md` | Dependency | This PR |
| `docs/surrealdb/context-evidence-claim-memory-runbook.md` | Retrieval runbook | PRESENT |
| `docs/surrealdb/decision_replay_query_contract.md` | Decision query contract | PRESENT |
| Epic #1976 | Parent | OPEN |
