# Context Intelligence — Safe Claim Generator Policy v1

**Status**: Design (Wave-14 Follow-up)
**Authority**: Issue #2569 / Follow-up Arc of PR #2565
**Parent**: Epic #1976
**Schema Reference**: `infrastructure/surrealdb/context_intelligence_v0.surql` (`claim` table)
**Guardrail**: No trading state, no secrets, no Live-Go, no Echtgeld-Go, no runtime change.

---

## 1. Purpose and Scope

The Wave-14 `claim` table exists in the schema and the JSONL importer can accept `claims.jsonl`,
but the repo indexer (`context_indexer.py`) deliberately does not generate claim records.
Claims are semantic assertions. Automatically extracting them from code comments, docs, TODOs,
or commit messages risks inventing project truth.

This document defines:
- Whether a claim generator should exist and under what constraints
- Which sources are allowed to produce claims
- What fields are required for a valid claim record
- How to prevent speculative, LR, or Echtgeld claims

**Scope:**
- Claim generator policy (what is and is not allowed)
- Allowed claim sources
- Mandatory fields for valid claim records
- Validation gates before JSONL import
- Minimal safe authoring slice

**Non-Goals:**
- No implementation of an automated claim extractor
- No schema changes
- No DB writes
- No Live-Readiness assertion from claims
- No Echtgeld-Go from claims
- No automatic `trade-capable` → Live-Go mapping
- No claim extraction from test coverage reports or CI output

---

## 2. Core Design Decision

**A fully automated claim generator MUST NOT be implemented.**

Reasons:
1. Claims are semantic assertions about system correctness, governance, or capability.
   They cannot be derived automatically from code or docs without risk of false truth.
2. Commit messages, test names, and documentation headings are context signals, not
   claim evidence. Treating them as claims introduces hallucinated governance state.
3. An automated generator would risk producing LR-adjacent claims
   (e.g., "risk service is correct") that could be misread as a Human-GO substitute.

**Minimal safe slice:** Human-authored and human-reviewed JSONL only.
An agent-assisted authoring workflow is permitted under the constraints defined in Section 4.

---

## 3. Allowed Claim Sources

| Source | Allowed | Conditions |
|---|---|---|
| Human manual authoring (JSONL) | ✅ Yes | No additional constraints beyond field requirements |
| Agent-drafted, human-reviewed (JSONL) | ✅ Yes | Human must review and sign off before import |
| Automated repo scanner (indexer) | ❌ No | Prohibited — see Section 2 |
| Commit message extraction | ❌ No | Not authoritative |
| Test name/docstring extraction | ❌ No | Test existence ≠ claim validity |
| CI output extraction | ❌ No | CI pass ≠ semantic claim |
| Documentation heading extraction | ❌ No | Heading presence ≠ claim truth |

---

## 4. Mandatory Fields for a Valid Claim Record

Every `claim` record imported via `claims.jsonl` MUST include the following fields.
Records missing mandatory fields MUST be rejected by the importer with a blocking finding.

| Field | Type | Requirement | Notes |
|---|---|---|---|
| `claim_id` | string | Mandatory | Stable, deterministic ID (e.g., `claim-<scope>-<seq>`) |
| `title` | string | Mandatory | Human-readable short title |
| `statement` | string | Mandatory | Full assertion text — the actual claim |
| `scope` | string | Mandatory | Scope identifier (e.g., `risk_service`, `wave14`) |
| `status` | string | Mandatory | One of: `proposed`, `supported`, `weakly_supported`, `disputed`, `superseded`, `stale`, `invalidated` |
| `evidence_refs` | array | Mandatory (≥1) | At least one `evidence_id` from the `evidence_ref` table |
| `source_refs` | array | Mandatory (≥1) | At least one Git path or issue/PR URL |
| `confidence` | float | Mandatory | In [0.0, 1.0]; unverified claims must use < 0.5 |
| `created_at` | datetime | Mandatory | ISO 8601 |

Optional fields: `comment`.

---

## 5. Prohibited Claim Content

The following claim types are prohibited regardless of producer:

| Prohibited Claim Type | Reason |
|---|---|
| `"The system is ready for live trading"` | LR assertion — requires LR gate |
| `"Echtgeld trading is approved"` | Echtgeld-Go — requires LR gate |
| `"Human-GO has been given"` | Human-GO assertions require actual Human-GO signal |
| Claims derived solely from `test_pass` without further evidence | `test_pass` evidence supports a narrowly-scoped technical claim, not a governance or LR claim |
| Claims with empty `evidence_refs` | No provenance = invalid |
| Claims with `status: supported` but `confidence < 0.3` | Contradictory; must be `weakly_supported` or `disputed` |

---

## 6. Validation Gates Before Import

The JSONL importer MUST enforce the following gates for `claims.jsonl`:

| Gate | Severity | Description |
|---|---|---|
| Missing mandatory field | Blocking | Any of the fields listed in Section 4 is absent |
| `evidence_refs` is empty | Blocking | No evidence = unacceptable |
| `source_refs` is empty | Blocking | No provenance = invalid |
| `confidence` outside [0.0, 1.0] | Blocking | Numeric contract violation |
| `status` not in allowed set | Blocking | Unknown status is invalid |
| `evidence_refs[*]` not in current batch | Warning | Cross-batch reference may be valid from prior import |
| Prohibited claim content (Section 5) | Blocking | Governance violation |

---

## 7. Guardrail Review (G1–G10)

| # | Guardrail | Result |
|---|---|---|
| G1 | No trading state | ✅ No orders/positions/fills/balances |
| G2 | No secrets | ✅ No credentials or keys |
| G3 | No Live-Go | ✅ LR remains NO-GO; prohibited claim types listed |
| G4 | No Echtgeld-Go | ✅ Explicitly prohibited |
| G5 | No runtime change | ✅ No service or compose change |
| G6 | No autonomy without Human Gate | ✅ Agent authoring requires human review |
| G7 | No Board-Stage to LR-Go mapping | ✅ Not mentioned as Live-Go |
| G8 | No productive apply | ✅ No SurrealDB apply commands |
| G9 | Git/Repo is SSoT | ✅ Issues and schema cited as authority |
| G10 | Hash-backed evidence | ✅ `evidence_refs` mandatory; `source_refs` required |

---

## 8. Provenance

| Source | Type | Status |
|---|---|---|
| Issue #2569 | Authority | OPEN (closed by this document) |
| PR #2565 | Context | MERGED |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema | PRESENT |
| `docs/surrealdb/context-evidence-ref-semantics-v1.md` | Dependency | This PR |
| `docs/surrealdb/context-evidence-claim-memory-runbook.md` | Retrieval runbook | PRESENT |
| Epic #1976 | Parent | OPEN |
