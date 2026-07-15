# ARVP Signal Runtime Rebuild/Recreate Review (#3976)

**Status:** Review complete (docs-only)  
**Date:** 2026-07-10  
**Source PR:** [#3974](https://github.com/jannekbuengener/Claire_de_Binare/pull/3974)  
**Related chain:** [#3956](https://github.com/jannekbuengener/Claire_de_Binare/pull/3956), [#3961](https://github.com/jannekbuengener/Claire_de_Binare/pull/3961), [#3971](https://github.com/jannekbuengener/Claire_de_Binare/pull/3971)  
**Active runtime notice:** [#3982](https://github.com/jannekbuengener/Claire_de_Binare/issues/3982) OPEN — no runtime mutation in this review

## Verdict

**Rebuild/recreate IS required** before any new telemetry or natural-paper observation can be treated as code-fresh, whenever `services/signal/` or its Dockerfile changed on `main` since the last image build.

PR #3974 added `ARG/ENV CDB_SOURCE_SHA` to `services/signal/Dockerfile`. Without rebuild + container recreate, running containers may carry stale Python code while reporting a missing or outdated `CDB_SOURCE_SHA` marker — producing false telemetry (historical `signal_id` collision / false-zero risk documented in #3967, fixed in #3971).

## What changed (repo-backed)

| PR | Runtime impact | Rebuild scope |
|----|------------------|---------------|
| #3956 | `format_runtime_signal_id()`, supervisor lane counts | `cdb_signal` image |
| #3961 | `campaign_id` + block-reason ledger attribution | `cdb_signal`, `cdb_risk` (risk code path; signal is primary telemetry surface) |
| #3971 | Runtime `signal_id` preservation, insert-conflict metrics | `cdb_signal` image |
| #3974 | `CDB_SOURCE_SHA` Dockerfile marker + diag-reverify manifests | `cdb_signal` image (build-arg required) |

## Operator rule (not executed here)

1. Pin expected SHA: `git rev-parse origin/main` (or manifest `expected_source_sha`).
2. Rebuild signal images with build-arg:
   ```powershell
   $env:CDB_SOURCE_SHA = "<expected_sha>"
   docker compose -f infrastructure/compose/compose.red.yml build `
     --build-arg CDB_SOURCE_SHA=$env:CDB_SOURCE_SHA cdb_signal
   ```
3. For campaign overlays, rebuild lane services from the matching manifest compose file (example diag-reverify):
   ```powershell
   docker compose `
     -f infrastructure/compose/compose.red.yml `
     -f config/arvp/runtime_np_diag_reverify_signal_compose_override.yml `
     build --build-arg CDB_SOURCE_SHA=$env:CDB_SOURCE_SHA cdb_signal_pb1 cdb_signal_donchian
   ```
4. Recreate containers (only after explicit RUNTIME-GO):
   ```powershell
   docker compose -f infrastructure/compose/compose.red.yml up -d --force-recreate <service>
   ```
5. **HOLD gate:** Before observation, verify container env:
   ```powershell
   docker inspect <container> --format "{{range .Config.Env}}{{println .}}{{end}}" | findstr CDB_SOURCE_SHA
   ```
   If `CDB_SOURCE_SHA` ≠ expected SHA → **do not start observation**.

## Actions taken in #3976 review session

| Action | Status |
|--------|--------|
| Docker build | **Not executed** (scope boundary) |
| Container recreate | **Not executed** (scope boundary) |
| Runtime start/stop | **Not executed** (#3982 may be running) |
| Documentation reconcile | **Executed** — `ARCHITECTURE_MAP.md`, `SERVICE_CATALOG.md`, `services/signal/README.md` |

## Evidence from prior successful re-verify (#3977)

Re-verify execute [#3977](https://github.com/jannekbuengener/Claire_de_Binare/issues/3977) rebuilt signal images with `CDB_SOURCE_SHA=251faf59…` (#3971) and achieved `PASS_TELEMETRY_REVERIFIED`. Evidence: `docs/evidence/arvp_diag_telemetry_reverify_run.md`.

That proves the rebuild/recreate pattern works when applied under RUNTIME-GO; it does **not** authorize live trading.

## Future automation (recommendation only)

- Preflight tools already enforce SHA checks: `tools/arvp_diag_reverify_preflight.py`, `tools/arvp_np_telemetry_pass_preflight.py`.
- A future ops slice could add a read-only `tools/arvp_signal_image_freshness_check.py` (inspect-only, no compose up).
- No automation was implemented in this docs-only reconcile.

## Boundaries

- LR **NO-GO** unchanged
- Telemetry PASS ≠ trading promotion
- No Live/Echtgeld
- #3982 remains OPEN and untouched
