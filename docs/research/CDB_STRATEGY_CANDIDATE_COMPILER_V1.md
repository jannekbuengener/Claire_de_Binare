# CDB Strategy Candidate Compiler v1

**Status:** Wave-2 contract surface (#4268)
**Parent:** #4263
**Depends on:** Wave-1 StrategyCandidate + ResearchBrief; SourceEvidence (#4267)
**Mode:** Spec + CompilerReport schema + deterministic helpers; no runtime compiler
**Live-Readiness:** NO-GO

## Purpose

Define a deterministic, fail-closed compiler contract from:

`ResearchBrief (exact id + version + hash) + sorted SourceEvidence refs + Claire/governance context`

to:

`StrategyCandidate + CompilerReport + status {READY|BLOCKED|NEEDS_RESEARCH} + output hash`

The compiler **must not invent** missing entry, exit, risk, or execution rules.

## Inputs (required)

| Input | Requirement |
|---|---|
| ResearchBrief | Exact `brief_id` + `brief_version` + immutable content hash |
| SourceEvidence | Sorted refs with `evidence_id` + `content_hash` |
| Claire / governance context | Canonical read-only context reference |
| Compiler contract version | `cdb.strategy_candidate_compiler.v1` |

Missing brief version/hash → reject (PMR-02).

## Outputs

| Output | Schema / rule |
|---|---|
| StrategyCandidate | Existing `cdb.strategy_candidate.v1` (hardened Wave-2 provenance) |
| CompilerReport | `cdb.compiler_report.v1` |
| Status | `READY` / `BLOCKED` / `NEEDS_RESEARCH` |
| Output hash | Deterministic `sha256:` over canonical JSON |
| Reject reasons | Structured list; empty only when READY |

## Status semantics

| Status | Meaning |
|---|---|
| `READY` | Complete falsifiable candidate with provenance; **ready for validation only** |
| `BLOCKED` | Contract-invalid or hard reject (e.g. non-falsifiable hypothesis) |
| `NEEDS_RESEARCH` | Falsifiable goal present, but SourceEvidence or assumptions insufficient |

### Non-authority

- `READY` ≠ Validation PASS
- `READY` ≠ PAPER_CANDIDATE
- `READY` ≠ Live-Go
- Compiler must not promote strategies

## Reject catalog (fail-closed)

- Inventing entry/exit/risk/execution rules
- Non-falsifiable hypothesis → BLOCKED
- Unclear entry/exit → block / NEEDS_RESEARCH
- Missing risk or execution assumptions → NEEDS_RESEARCH
- Unsupported claims → BLOCKED
- Duplicate candidate identity collision → BLOCKED
- Missing ResearchBrief version or hash → BLOCKED
- Invalid parent lineage for new candidate version → BLOCKED (PMR-01)

## Determinism

- Same canonical input → same StrategyCandidate content + same `output_hash`
- Changed falsifiable content → new `candidate_version` with valid parent
- Candidate-version and schema-version must not be mixed
- Helper: `tools.research_validation.wave2_cross_contract.canonical_content_hash`

## Version lineage (PMR-01)

Enforced by `validate_candidate_lineage`:

- `v1` → `parent_version = null`
- `vN` (N>1) → `parent_version = v{N-1}` exactly
- Self-parent / future-parent / missing-parent rejected

## Producer / Consumer

| Role | Responsibility |
|---|---|
| Producer | Future compiler implementation conforming to this contract |
| Consumer | GitHub Candidate Registry + Hermes validation orchestration |
| Non-authority | Risk, Execution, Live capital gates |

## Failure paths

| Condition | Status |
|---|---|
| Missing brief version/hash | BLOCKED |
| Empty SourceEvidence | NEEDS_RESEARCH |
| Missing entry/exit/risk/execution | NEEDS_RESEARCH (no invention) |
| Non-falsifiable hypothesis | BLOCKED |
| Lineage violation | BLOCKED |

## Related

- SourceEvidence: [`CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md`](CDB_RESEARCH_SOURCE_ADAPTER_CONTRACTS_V1.md)
- Registry: [`CDB_GITHUB_CANDIDATE_REGISTRY_V1.md`](CDB_GITHUB_CANDIDATE_REGISTRY_V1.md)
- Schema: [`cdb_compiler_report.v1.schema.json`](../contracts/cdb_compiler_report.v1.schema.json)
