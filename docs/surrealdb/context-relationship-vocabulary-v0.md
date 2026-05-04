# CDB Context Intelligence — Relationship Vocabulary v0

**Status**: Draft (Issue #1982)
**Authority**: Issue #1982 / Parent #1976
**Dependencies**: #1981 (core schema objects)
**Guardrail**: trade-capable is NOT a Live-Readiness-Go; Live-Readiness remains NO-GO.

---

## 1. Purpose

This document defines the canonical relationship vocabulary for the CDB Knowledge
Graph within the Context Intelligence System. It specifies:

- relationship types with their semantics, directionality, and cardinality
- allowed source and target types per relationship
- rules for inferred vs explicit relationships
- confidence and source reference requirements

This is a **reference specification**, not a schema implementation. It does not
define SurrealDB edge tables, RELATE statements, or graph enforcement.

---

## 2. Non-Goals

- No SurrealDB graph edge implementation
- No schema migration or .surql changes
- No runtime, compose, or service changes
- No trading state, no secrets, no live/echtgeld go
- No relationship enforcement logic
- No automatic inference rules (manual classification only)

---

## 3. Naming Convention

| Rule | Value |
|---|---|
| Format | `snake_case`, present tense verb |
| Direction | `source → target` (left → right) |
| Inverse | Explicitly named when needed (e.g. `blocks` / `unblocks`) |
| Edge table naming | Deferred to #2000 (Dependency Edge Model) |

Relation names use descriptive present-tense verbs:
`contains`, `validates`, `depends_on`. No past tense, no noun forms.

---

## 4. Allowed Source/Target Types

The following types participate in relationships. Types are schema tables from
`infrastructure/surrealdb/context_intelligence_v0.surql` plus endpoint
reference types defined below (Section 4.2).

### 4.1 Table Types

| Type | Description |
|---|---|
| `repo_artifact` | Versioned file in the working repo |
| `code_symbol` | Class, function, type, or constant |
| `doc_page` | Markdown document |
| `doc_section` | Heading-scoped section within a doc_page |
| `doc_chunk` | Token-sized content chunk |
| `concept` | Abstract domain concept |
| `evidence_ref` | Evidence artifact reference |
| `claim` | Assertion about the system |
| `decision_event` | Recorded decision with rationale |
| `agent_memory` | Per-agent scoped memory entry |
| `audit_observation` | Audit finding |
| `contradiction` | Detected conflict |
| `stale_context` | Drifted/stale context marker |
| `scope_drift_event` | Scope deviation event |
| `knowledge_quality_score` | Quality assessment |

### 4.2 Endpoint Reference Types

These are GitHub/repo-level endpoint identifiers used as relationship
endpoints. They are **not** declared as `canonical_name` entries in
`docs/surrealdb/context-ontology-v0.yaml`; they represent resolvable
identities from the repo environment (GitHub API, ownership.yaml).

| Type | Description |
|---|---|
| `agent` | Agent identity (OPENCODE/<name>, etc.) |
| `issue` | GitHub issue (referenced by number) |
| `pr` | GitHub pull request |
| `artifact_owner` | Owning domain per ownership.yaml |

---

## 5. Relationship Types

### 5.1 `contains`

Hierarchical containment. The source physically or logically contains the target.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `doc_page`, `doc_section`, `concept` |
| Target types | `doc_section` (from page), `doc_chunk` (from section), `code_symbol` (from concept) |
| Cardinality | 1:N |
| Inferred | No (explicit, structural) |
| Confidence | 1.0 (structural truth) |
| Example | `doc_page` contains `doc_section` |

### 5.2 `imports`

Code-level import or module dependency.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `code_symbol` |
| Target types | `code_symbol` |
| Cardinality | N:M |
| Inferred | No (parseable from source) |
| Confidence | 1.0 (source-parseable) |
| Example | `risk/service.py::decide_trade` imports `core/contracts/decision_contract_v1.py::DecisionContract` |

### 5.3 `tests`

Test coverage relationship.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `code_symbol` (test function) |
| Target types | `code_symbol` (production function) |
| Cardinality | N:M |
| Inferred | Partially (test naming conventions) |
| Confidence | 0.8 (naming heuristic) |
| Example | `test_risk_service.py::test_exposure_limit` tests `risk/service.py::decide_trade` |

### 5.4 `validates`

Evidence-based validation. The source provides proof that the target is correct.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `evidence_ref`, `code_symbol` (test) |
| Target types | `claim`, `decision_event`, `concept` |
| Cardinality | N:M |
| Inferred | No |
| Confidence | 1.0 (evidence-backed) |
| Example | `evidence_ref` validates `claim` "System passes 72h soak" |

### 5.5 `documents`

The source provides documentation for the target.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `doc_page`, `doc_section` |
| Target types | `code_symbol`, `concept`, `decision_event` |
| Cardinality | N:M |
| Inferred | No (explicit doc reference) |
| Confidence | 0.9 (explicit but may be stale) |
| Example | `docs/surrealdb/context-intelligence-system.md` documents `concept` "Context Intelligence System" |

### 5.6 `implements`

The source is a concrete realization of the target.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `code_symbol`, `repo_artifact` |
| Target types | `concept`, `doc_page` (spec) |
| Cardinality | N:1 |
| Inferred | Partially |
| Confidence | 0.7 (requires human classification) |
| Example | `services/risk/service.py` implements `concept` "Risk Service" |

### 5.7 `depends_on`

Operational or logical dependency. If the target is unavailable, the source is
degraded or blocked.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | any table type |
| Target types | any table type |
| Cardinality | N:M |
| Inferred | Partially (can be structural or declared) |
| Confidence | 0.6 (inferred) / 0.9 (explicit) |
| Example | `code_symbol` "ExecutionService" depends_on `code_symbol` "RiskService" |

### 5.8 `blocks`

The source prevents the target from progressing.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `decision_event`, `contradiction`, `stale_context`, `scope_drift_event` |
| Target types | `decision_event`, `claim`, `concept` |
| Cardinality | N:M |
| Inferred | No (explicit block condition) |
| Confidence | 1.0 (explicit) |
| Example | `decision_event` "LR-050 NO-GO" blocks `concept` "Live-Readiness" |

### 5.9 `unblocks`

The source removes a block on the target (inverse of `blocks`).

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `decision_event`, `evidence_ref` |
| Target types | `decision_event`, `claim` |
| Cardinality | N:M |
| Inferred | No (explicit unblock) |
| Confidence | 1.0 (explicit) |
| Example | `evidence_ref` "P4 PASS 72h soak" unblocks `decision_event` "LR-040 INCONCLUSIVE" |

### 5.10 `supersedes`

The source replaces or obsoletes the target.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `doc_page`, `code_symbol`, `decision_event`, `agent_memory` |
| Target types | same as source type |
| Cardinality | 1:1 |
| Inferred | No (explicit replacement) |
| Confidence | 1.0 (explicit) |
| Example | `decision_event` v2 supersedes `decision_event` v1 |

### 5.11 `contradicts`

The source is in logical conflict with the target.

| Property | Value |
|---|---|
| Direction | source → target (symmetric) |
| Source types | `claim`, `evidence_ref`, `doc_page` |
| Target types | `claim`, `evidence_ref`, `doc_page`, `code_symbol` |
| Cardinality | N:M |
| Inferred | Partially (detection-based) |
| Confidence | 0.5 (detection heuristic) / 0.9 (human-confirmed) |
| Example | `claim` "System is deterministic" contradicts `evidence_ref` "non-deterministic output observed" |

### 5.12 `requires_evidence`

The source claim or decision must be backed by the target evidence.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `claim`, `decision_event` |
| Target types | `evidence_ref` |
| Cardinality | 1:N |
| Inferred | No (explicit evidence requirement) |
| Confidence | 1.0 (structural) |
| Example | `claim` "Contract drift protected" requires_evidence `evidence_ref` "LR-003-FINGERPRINT.json" |

### 5.13 `derived_from`

The source was generated, extracted, or computed from the target.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `doc_chunk`, `concept`, `knowledge_quality_score`, `audit_observation` |
| Target types | `doc_page`, `code_symbol`, `repo_artifact`, `evidence_ref` |
| Cardinality | N:1 |
| Inferred | No (explicit provenance) |
| Confidence | 1.0 (hash-backed) |
| Example | `doc_chunk` derived_from `doc_page` "AGENTS.md" |

### 5.14 `owned_by`

Ownership attribution per `ownership.yaml` domains.

The endpoint reference type `agent` and `artifact_owner` are identity
aliases resolved at ingestion time. Persisted graph edges MUST store
the resolved target as a record-link-capable reference (`from_ref` /
`to_ref` convention per Section 9). Implementations MUST NOT persist
loose identity strings as edge targets directly.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | `repo_artifact`, `code_symbol`, `doc_page` |
| Target types | `agent` (resolved to `agent_memory` record), `artifact_owner` (resolved record reference from ownership.yaml) |
| Cardinality | N:1 |
| Inferred | No (explicit ownership assignment) |
| Confidence | 1.0 (canonical) |
| Example | `repo_artifact` "risk/service.py" owned_by `agent_memory` record for "trading_services" |

### 5.15 `mentions`

Weak, informational reference. The source textually references the target but
no stronger relation is asserted.

Relations with lower extraction confidence (< 0.5) may exist in the
extraction pipeline but MUST NOT be persisted as graph edges. Such
low-confidence signals may be captured as `audit_observation` entries
flagged for human review.

| Property | Value |
|---|---|
| Direction | source → target |
| Source types | any table type |
| Target types | any table type |
| Cardinality | N:M |
| Inferred | Yes (text extraction) |
| Confidence | 0.5 (extraction) / 0.7 (explicit annotation) |
| Example | `doc_chunk` mentions `code_symbol` "generate_uuid" |

### 5.16 `related_to`

General-purpose bidirectional relation when no stronger type applies. Use
sparingly; prefer specific relation types.

Weak associations below confidence 0.5 MUST NOT be persisted as graph
edges and may be captured as `audit_observation` entries instead.

| Property | Value |
|---|---|
| Direction | bidirectional |
| Source types | any table type |
| Target types | any table type |
| Cardinality | N:M |
| Inferred | Yes (weak association) |
| Confidence | 0.5 (fallback) |
| Example | `concept` "Risk Service" related_to `concept` "Execution Service" |

### 5.17 `caused_by`

Trace-level causal linkage. The source (effect) was caused by the target
(cause). This is a directional trace relation used in lineage records.

| Property | Value |
|---|---|
| Direction | source (effect) → target (cause) |
| Source types | `claim`, `decision_event`, `audit_observation`, `evidence_ref` |
| Target types | `decision_event`, `claim`, `code_symbol`, `scope_drift_event` |
| Cardinality | N:M |
| Inferred | No (explicit attribution) / Yes (heuristic linkage) |
| Confidence | 1.0 (explicit attribution) / 0.7 (heuristic linkage) |
| Example | `claim` "Scope drift detected" caused_by `scope_drift_event` "module boundary change" |

### 5.18 `used_by`

Inverse of `depends_on`. The source is used (depended upon) by the target.
This is the canonical reverse-edge type for downstream trace traversal.

| Property | Value |
|---|---|
| Direction | source (dependency) → target (consumer) |
| Source types | any table type |
| Target types | any table type |
| Cardinality | N:M |
| Inferred | Yes (derived from `depends_on` edges) |
| Confidence | 0.6 (inferred from depends_on) / 0.9 (explicit) |
| Example | `code_symbol` "RiskService" used_by `code_symbol` "ExecutionService" |

---

## 6. Confidence and Source Reference Rules

### 6.1 Confidence Scale

| Level | Range | Semantics |
|---|---|---|
| `certain` | 1.0 | Structural truth, hash-backed, or explicit declaration |
| `high` | 0.8–0.9 | Explicit but potentially stale; well-supported heuristic |
| `medium` | 0.5–0.7 | Heuristic or partial evidence |
| `low` | 0.3–0.4 | Weak extraction signal; inference fallback |
| `untrusted` | <0.3 | Should not be stored as a relation |

### 6.2 Source Reference Requirement

Canonical graph relation records SHOULD carry `source_ref` and `source_type`
fields for provenance:

| Field | Required | Description |
|---|---|---|
| `source_ref` | Target-state | Reference to the artifact, tool, or agent that established the relation |
| `source_type` | Target-state | `parser`, `heuristic`, `human`, `agent:<id>`, `inferred` |
| `evidence_refs` | No | Array of evidence_id references backing the relation |

`source_ref` and `source_type` are a **target-state contract** for
canonical graph relation records. Existing `dependency_edges` produced by
the current indexer/importer (#2000 tooling) are not retroactively
required to carry these fields. The indexer and importer gap is tracked
separately (see Section 9) and is not part of this vocabulary specification.

### 6.3 Inference Rules

Inferred relations differ from explicit relations:

- Inferred relations MUST set `inferred: true`.
- Inferred relations MUST have `confidence ≤ 0.8`.
- Inferred relations MUST document the inference method in `source_type`.
- Inferred relations MUST NOT participate in automated decision gates.
- Inferred relations MUST NOT be treated as ground truth for governance claims.

**Rule**: When confidence < 0.5, do not persist the relation as a graph edge.
Store as an `audit_observation` flagged for human review instead.

---

## 7. Cross-Reference Matrix

| Relation | Source Types | Target Types | Inferred? | Min Confidence |
|---|---|---|---|---|
| `contains` | doc_page, doc_section, concept | doc_section, doc_chunk, code_symbol | No | 1.0 |
| `imports` | code_symbol | code_symbol | No | 1.0 |
| `tests` | code_symbol | code_symbol | Partial | 0.8 |
| `validates` | evidence_ref, code_symbol | claim, decision_event, concept | No | 1.0 |
| `documents` | doc_page, doc_section | code_symbol, concept, decision_event | No | 0.9 |
| `implements` | code_symbol, repo_artifact | concept, doc_page | Partial | 0.7 |
| `depends_on` | any | any | Partial | 0.6 |
| `blocks` | decision_event, contradiction, stale_context, scope_drift_event | decision_event, claim, concept | No | 1.0 |
| `unblocks` | decision_event, evidence_ref | decision_event, claim | No | 1.0 |
| `supersedes` | doc_page, code_symbol, decision_event, agent_memory | same as source | No | 1.0 |
| `contradicts` | claim, evidence_ref, doc_page | claim, evidence_ref, doc_page, code_symbol | Partial | 0.5 |
| `requires_evidence` | claim, decision_event | evidence_ref | No | 1.0 |
| `derived_from` | doc_chunk, concept, knowledge_quality_score, audit_observation | doc_page, code_symbol, repo_artifact, evidence_ref | No | 1.0 |
| `owned_by` | repo_artifact, code_symbol, doc_page | agent, artifact_owner | No | 1.0 |
| `mentions` | any | any | Yes | 0.5 |
| `related_to` | any | any | Yes | 0.5 |
| `caused_by` | claim, decision_event, audit_observation, evidence_ref | decision_event, claim, code_symbol, scope_drift_event | No | 0.7 |
| `used_by` | any | any | Yes | 0.6 |

---

## 8. Guardrails

- No relation implies trading-write capability.
- No relation implies live-trading authorization.
- No relation implies governance gate bypass.
- No relation substitutes for explicit Human-GO.
- Inferred relations MUST NOT gate automated decisions.
- Relations with confidence < 0.5 MUST NOT be stored as graph edges.
- Canonical graph relation records SHOULD carry `source_ref` and `source_type` for provenance (target-state contract per Section 6.2).
- `trade-capable` is never modeled as a Live-Readiness-Go via any relation.
- All relation targets that reference schema tables must exist in `context_intelligence_v0.surql`.

---

## 9. Relationship to Dependency Edge Model (#2000)

This vocabulary defines the **semantic types** of relations. The Dependency Edge
Model (#2000) will:

- Define the SurrealDB edge table structure for `dependency_edge`
- Specify graph traversal patterns (including inverse types `used_by`
  as the downstream counterpart to `depends_on`)
- Define `from_ref` / `to_ref` record link conventions
  (used by `owned_by` to resolve endpoint reference types to records)

This vocabulary is upstream of #2000 and constrains which relation types are valid
in the dependency edge table. #2000 MUST NOT introduce relation types not defined here.

**Indexer / Importer Gap (separate tracking):** The current `context_indexer.py`
(`DependencyEdge.to_payload`) does not yet emit `source_ref` / `source_type`
fields. The importer validation does not yet enforce them. These gaps are tracked
as implementation slices under #2000 / #2001 and are **not** in scope of this
vocabulary specification (#1982).

---

## 10. Downstream Consumers

| Consumer | Issue | Usage |
|---|---|---|
| Dependency Edge Model | #2000 | Edge table structure constrained by vocabulary |
| Graph Import | #2001 | Import logic uses vocabulary types |
| Trace Context | context.trace (tool-contracts) | Lineage trace uses `caused_by`, `derived_from`, `related_to` |
| Graph Query | context_query.py | Traversal uses `depends_on`, `used_by` (downstream inverse) |
| Impact Radar | #2108 | Impact analysis uses `depends_on`, `blocks`, `contains` |
| Agent OS Briefing | #2105 | Briefing context uses `documents`, `validates`, `derived_from` |

---

## 11. Validation Checklist

- [ ] All 18 relation types are defined with semantics, direction, and cardinality
- [ ] Source/target types reference only existing schema tables and endpoint reference types
- [ ] Confidence rules are defined per type (minimum confidence ≥ 0.5 for graph edge persistence)
- [ ] Source reference requirement is specified as target-state contract (Section 6.2)
- [ ] Inference rules are specified (Section 6.3)
- [ ] Guardrails Section 8 is present
- [ ] No trading-state references
- [ ] No secrets references
- [ ] No live/echtgeld go inference
- [ ] No runtime/compose/service changes implied
- [ ] Downstream consumer mapping is present (Section 10)

---

## Provenance / Sources

- **Issue**: #1982
- **Parent**: #1976
- **Dependencies**: #1981 (core schema objects), #1980 (ontology)
- **Referenced documents**:
  - `infrastructure/surrealdb/context_intelligence_v0.surql`
  - `docs/surrealdb/context-ontology-v0.yaml`
  - `docs/surrealdb/context-intelligence-system.md`
  - `docs/surrealdb/context-intelligence-namespace-layout.md`
  - `docs/surrealdb/context-intelligence-validation.md`
   - `infrastructure/config/surrealdb/ownership.yaml`

