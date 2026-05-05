# Validation Plan Generator v1 — Contract

**Issue:** #2109
**Epic:** #1976
**Parent Wave:** Welle 13 (#2103–#2114)
**Depends on:** #2108 (Impact Radar v1)
**Prepares:** #2111 (Impact Radar MCP Tool), #2112 (Tests and Fixtures)
**Status:** Implemented (`tools/surrealdb/context_validation_plan.py`)
**Schema Version:** 1.0.0

## 1. Purpose

The Validation Plan Generator consumes the output of the Impact Radar v1
(`ImpactReport` or its `to_payload()` dict) and produces a concrete,
agent-readable `ValidationPlan`. The plan translates impact analysis into
actionable validation steps while maintaining all hard guardrails.

## 2. Domain Model

### 2.1 ValidationPlanInput

| Field           | Type                | Description                                 |
|-----------------|---------------------|---------------------------------------------|
| `impact_report` | `ImpactReport\|None` | Direct ImpactReport reference               |
| `payload`       | `dict\|None`         | `to_payload()` dict from ImpactReport       |

Exactly one of `impact_report` or `payload` must be provided. Both `None` or
both non-`None` raise `ValueError`.

### 2.2 ValidationPlan

| Field                    | Type                   | Description                                          |
|--------------------------|------------------------|------------------------------------------------------|
| `plan_id`                | `str`                  | Deterministic SHA256-derived ID                      |
| `required_checks`        | `tuple[str, ...]`      | Checks that must pass before proceeding              |
| `suggested_tests`        | `tuple[str, ...]`      | Suggested test suites/functions to run               |
| `docs_to_review`         | `tuple[str, ...]`      | Documentation paths that need review                 |
| `evidence_to_collect`    | `tuple[str, ...]`      | Evidence artifacts to collect                        |
| `commands_to_consider`   | `tuple[str, ...]`      | Commands suggested (never auto-run)                  |
| `manual_review_needed`   | `bool`                 | Whether manual/Human-GO review is required           |
| `blocking_preconditions` | `tuple[str, ...]`      | Blocking conditions from impact analysis             |
| `success_criteria`       | `tuple[str, ...]`      | Conditions that define validation success            |
| `stop_conditions`        | `tuple[dict, ...]`     | Stop conditions propagated from ImpactReport         |
| `schema_version`         | `str`                  | Schema version (`1.0.0`)                             |

### 2.3 Required Checks

Derived from:
- Impact level (`blocking`/`high`/`medium`)
- Gate risks (`governance_touched`, `risk_surface_touched`, etc.)
- Blocking preconditions
- Blocking stop conditions (`severity: blocking`)

### 2.4 Success Criteria

Derived from:
- Impact level → appropriate validation depth
- Confidence level (`low`/`medium`/`high`) → data quality requirements
- Gate risks → governance/secrets/contract/live-readiness coverage
- Presence of artifacts/symbols/tests/docs → verification requirements
- Presence/absence of stop conditions

### 2.5 Action Classification

| Category              | Auto-Run | Human-GO Required | Example                              |
|-----------------------|----------|-------------------|--------------------------------------|
| `required_checks`     | No       | Yes               | "Blocking impact — seek Human-GO"    |
| `suggested_tests`     | No       | No                | "test_clock"                         |
| `commands_to_consider`| **Never**| **N/A**           | "pytest -v tests/"                   |
| `docs_to_review`      | No       | No                | "docs/surrealdb/readme.md"           |
| `blocking_preconditions` | No   | Yes               | "Secrets surface touched — verify"   |
| `success_criteria`    | No       | No                | "All suggested tests passing"        |

**Commands are suggestions only.** The generator never auto-executes anything.
Read-only, dry-run, and Human-GO-sensitive actions are explicitly distinguished.

## 3. Determinism Guarantee

`build_validation_plan()` is a pure function:
- Same inputs → same outputs (identical `plan_id`, identical field contents).
- No randomness, no timestamps, no external state.
- No DB, network, filesystem, GitHub, or MCP calls.
- No command execution.

## 4. Compatibility

- Accepts `ImpactReport` directly (attribute-based access via `to_payload()`).
- Accepts plain `dict` payload for MCP tool wrapping (#2111).
- Same input via either path produces the identical `ValidationPlan`.

## 5. Guardrails

- No DB write. No command auto-run. No GitHub write from generator.
- No runtime, trading, live, or Echtgeld implication.
- Blocking preconditions from impact are always propagated.
- Stop conditions are always propagated.
- `manual_review_needed` is always visible.

## 6. Testing

- `tests/unit/surrealdb/test_context_validation_plan.py`
- Covers: empty input, low/medium/high/blocking impact levels, all gate risks,
  success criteria derivation, stop condition propagation, command-as-suggestion
  semantics, full-impact-radar-to-plan pipeline.
- All tests marked `@pytest.mark.unit`.
- No Docker, no runtime, no secrets required.
