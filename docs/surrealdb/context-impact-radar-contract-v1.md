# Impact Radar v1 — Contract

**Issues:** #2019, #2108
**Epic:** #1976
**Parent Wave:** Welle 13 (#2103–#2114)
**Status:** Implemented (`tools/surrealdb/context_impact_radar.py`)
**Schema Version:** 1.0.0

## 1. Purpose

Impact Radar v1 detects and assesses the downstream effects of a planned change
across the CDB system. It answers: *If I touch this, what else could break?*

## 2. Domain Model

### 2.1 Impact Level

| Level    | Criteria                                                |
|----------|---------------------------------------------------------|
| `low`    | Non-critical docs, minor non-code changes               |
| `medium` | Core libraries, shared utilities, test infrastructure   |
| `high`   | Services, contracts, schemas, infrastructure            |
| `blocking`| Governance, secrets, risk, execution, trading surface   |

### 2.2 Impact Type (Hard / Soft)

- **HARD**: Changes code/runtime boundaries (services, core, infrastructure,
  contracts). Has runtime implications.
- **SOFT**: Documentation, tests, non-runtime metadata changes. No direct
  runtime implications.

Derived automatically from affected paths. If any affected artifact has a path
in a hard-impact directory, the overall impact is HARD.

### 2.3 Confidence

| Confidence | Meaning                                                    |
|------------|------------------------------------------------------------|
| `high`     | Full indexer data; all edges resolved; no inferred edges   |
| `medium`   | Real indexer data; some edges inferred                     |
| `low`      | Mocked or minimal data; most edges unknown                 |

### 2.4 Gate Risks

Detected gaps that could violate governance or safety constraints:
- `governance_touched` — governance/policy/constitution paths changed
- `risk_surface_touched` — risk service / limits / kill-switch paths changed
- `execution_surface_touched` — execution / trading paths changed
- `contract_drift_possible` — contract/schema paths changed
- `secrets_surface_touched` — secrets/tresor paths referenced
- `lr_surface_touched` — live-readiness paths changed

### 2.5 Required Validation

Derived deterministically from affected paths and symbols:
- Unit tests for affected modules
- Contract tests for schema/interface changes
- Docs to review
- Evidence to collect
- Commands to consider (never auto-run)
- Manual review requirements
- Blocking preconditions

## 3. Input Contract

```python
@dataclass(frozen=True)
class ImpactRadarInput:
    target_paths: tuple[str, ...]       # Paths being changed
    target_symbols: tuple[str, ...]     # Symbol names being changed
    target_issue: str | None            # Related issue (e.g. "#2108")
    target_concepts: tuple[str, ...]    # Ontology concepts in scope
    operation_mode: str                 # read_only | dry_run | write (code/docs) | write (config/infra)
    dependency_edges: tuple[DependencyEdge, ...]  # From indexer/context_graph
    code_symbols: tuple[dict, ...]      # Flattened symbol data
    artifacts: tuple[dict, ...]         # Flattened artifact data
```

## 4. Output Contract

```python
@dataclass(frozen=True)
class ImpactReport:
    impact_id: str                      # Deterministic ID
    target_refs: tuple[str, ...]        # Canonical target references
    impact_level: str                   # low | medium | high | blocking
    impact_type: str                    # HARD | SOFT
    affected_artifacts: tuple[dict, ...]    # {path, artifact_type, hash}
    affected_symbols: tuple[dict, ...]      # {symbol_id, name, qualified_name, symbol_type, source_path}
    affected_tests: tuple[dict, ...]        # {test_id, test_name, source_path, test_type}
    affected_docs: tuple[dict, ...]         # {path, title, section_count}
    affected_decisions: tuple[str, ...]     # Decision refs touched
    affected_evidence: tuple[str, ...]      # Evidence refs potentially invalidated
    affected_memory_refs_read_only: tuple[str, ...]  # Memory entries to re-check
    graph_paths: tuple[list[str], ...]      # Traced dependency chains
    gate_risks: tuple[str, ...]             # Detected gate risks
    confidence: str                         # high | medium | low
    required_validation: dict[str, Any]     # Structured validation requirements
    stop_conditions: tuple[dict[str, Any], ...]  # Resolved stop conditions
```

## 5. Implementation

Module: `tools/surrealdb/context_impact_radar.py`

### 5.1 Core Function

```python
def compute_impact(input: ImpactRadarInput) -> ImpactReport
```

Pure function. Deterministic. No DB, no network, no file I/O. Delegates stop
condition resolution to `context_stop_resolver.resolve_stop_conditions()`.

### 5.2 Impact Level Computation

```
blocking >= governance OR risk OR execution OR secrets paths
high     >= services OR contracts OR schemas OR infrastructure paths
medium   >= core OR tools OR test infrastructure paths
low      >= docs OR .github paths
```

Uses path-prefix matching against canonical CDB directory structure:
- `knowledge/governance/` → blocking
- `services/risk/`, `services/execution/` → blocking
- `services/*` → high
- `infrastructure/` → high
- `core/`, `tools/`, `tests/` → medium
- `docs/`, `.github/` → low

### 5.3 Stop Condition Propagation

Impact Radar delegates to `context_stop_resolver`:
- If operation_mode is write-capable, S6 (write requires Human-GO) is added
- If governance paths touched with write mode, H1-H5 conditions added
- If trading/risk/execution paths touched, S7 condition added
- Gate risks are mapped to appropriate stop conditions

## 6. Guardrails

- Impact is analysis, never a write-go
- No automatic action permission derived from impact
- No Live-Readiness upgrade
- No Echtgeld-Go
- No trading runtime, orders, positions, fills, secrets, broker/execution state
- No SurrealDB production write
- Same inputs always produce same outputs (deterministic)

## 7. Compatibility

- #2109 Validation Plan Generator: Consumes `required_validation` field
- #2111 Impact Radar MCP Tool: Wraps `compute_impact()` as read-only MCP tool
- #2112 Tests/Fixtures: Fixture-backed test suite in `test_context_impact_radar.py`
