# Governance Documentation

This directory contains governance artifacts for the Claire de Binare (CDB) trading system.

## System Invariants (Canonical)

**Location**: `knowledge/governance/SYSTEM_INVARIANTS.md`

**Purpose**: Defines the 20 non-negotiable system contracts that govern CDB's behavior. All service logic, tests, schemas, and CI enforcement must conform to these invariants.

**Key Invariants Include**:
- Fail-closed trade decisions (INV-001)
- Deterministic decision logic (INV-002)
- Risk-first hierarchy (INV-003)
- Schema strictness (INV-008)
- Decision traceability (INV-012)
- Live trading authorization gates (INV-006)
- Contract drift protection (INV-007)

**Change Policy**:
- Any change to system invariants requires:
  1. Update to the canonical document in this working repo
  2. Updated references and enforcement mechanisms
  3. Passing all contract tests and drift guards
  4. Human approval via PR review

**Local Canon Rule**:
- `SYSTEM_INVARIANTS.md` lives in `knowledge/governance/`
- Enforcement mechanisms live in the same working repo (tests, schemas, CI, guards)
- Legacy Docs-Hub references are archival only and not the default maintenance path

---

## Local Governance Files

### DB Layer Governance

- [evidence/ISSUE-744-access-control-matrix-threat-model.md](evidence/ISSUE-744-access-control-matrix-threat-model.md)
  - Repo-visible DB actor map, access matrix, and small threat model for the Postgres runtime layer, with mirror boundaries called out where relevant.
- [../runbooks/postgres_least_privilege_rls.md](../runbooks/postgres_least_privilege_rls.md)
  - Operator runbook for role/grant setup, verification, and live evidence capture.
- [access-integrity-report.md](access-integrity-report.md)
  - Access-domain integrity report for `system_config` and `security_policy_refs`.
- [audit-integrity-report.md](audit-integrity-report.md)
  - Audit-domain integrity report for `audit_trail` and `governance_events`.

### MARKET_STATE_CONTRACT_V1.md
Input contract defining the `market_state` object that BLUE services must provide to the Risk Service (`cdb_risk`) for trade decisions. Enforces fail-closed behavior: missing required fields (`return_1m`, `return_5m`, `price_change_5m`) result in `RC_002` block.

See: [MARKET_STATE_CONTRACT_V1.md](MARKET_STATE_CONTRACT_V1.md)

**Runtime Evidence**: `P1_RUNTIME_DOD_REPORT.md`, `runtime_evidence_bundle_P1.json`

### risk_events.schema.yaml
Schema specification for risk events stored in PostgreSQL. Enforced by:
- `scripts/governance/check_risk_events_schema_contract.py`
- `.github/workflows/core-guard.yml`

See INV-019 in SYSTEM_INVARIANTS.md for canonical statement.
