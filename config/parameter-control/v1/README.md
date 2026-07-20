# Parameter Control Policy v1

Machine-readable control surface for Claire de Binare parameter changes.

## Files

- `CDB_PARAMETER_CONTROL_POLICY.json` — canonical policy body with 56 indexed rules.
- `CDB_PARAMETER_CONTROL_POLICY.schema.json` — JSON Schema for structural validation.
- `CDB_PARAMETER_CONTROL_POLICY.yaml` — stable YAML discovery pointer to the canonical JSON file; the policy body is intentionally not duplicated.

## Resolution

Each compact rule follows `rule_fields` and resolves references through the top-level `names`, `classes`, `decisions`, `paths`, and `evidence` tables.

Context codes:

- `r` — replay
- `p` — paper
- `u` — runtime
- `l` — live
- `d` — docs
- `t` — tests

## Safety

The policy is default-deny. Unknown parameters, missing evidence, and live context are denied. Stage-A, Stage-B, OOS, stress, risk, and live boundaries remain frozen unless a separate canonical governance decision explicitly supersedes this candidate policy.

This folder does not authorize runtime, database, MCP, live, or real-money actions.

Refs: #4147, #4148.
