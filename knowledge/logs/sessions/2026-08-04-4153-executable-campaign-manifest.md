# Session 2026-08-04 — #4153 Executable Campaign Manifest (Manifest-only)

## Status

`DONE_EXECUTABLE_CAMPAIGN_MANIFEST_ADDED_TO_PR` (pending push/PR at log write time)

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

Bootloader-Fallback: `CDB.LOADER_V3.0.md` / „Claire MCP Server-9“ nicht auflösbar;
kanonische Governance + Context MCP + Live-GitHub/Repo verwendet.

## Ratification SSOT

- Issue comment: `5175526900`
- Status: `DONE_4153_PARAMETER_GRID_RATIFIED`
- Expansion: `BASELINE_PLUS_OFAT_WITH_BOUNDED_INTERACTIONS`
- Variants: 21 (1+3+2+4+3+4+4)
- Runs: 819
- CDB-021: OUT
- Strategy: `primary_breakout_v1`
- Correctness baseline: `301bc757be7cb4162db6db114a5c445f2aca392f`

## Delivered

- Schema v1.1: `docs/contracts/cdb_sensitivity_experiment_manifest.v1.1.schema.json`
- Canonical manifest: `config/arvp/sensitivity_campaign_4153_v1.json`
- Grid/expansion: `tools/arvp_vacation/sensitivity_campaign_grid.py`
- Preflight verdict: `READY_FOR_REPLAY_SENSITIVITY_CAMPAIGN`
- Repo preflight: `READY_FOR_REPLAY_SENSITIVITY`
- SHA binding: `correctness_baseline_sha` + ancestor check (no self-referential PR commit hash)

## Boundaries

- No campaign runs
- No merge / no `cdb-local-ci`
- LR=`NO-GO`
- #4153/#4147/#4152 remain open
