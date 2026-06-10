# ARVP Probe Layer Spec

**Version:** 1.0
**Status:** Canonical
**Issue:** #3110
**Parent:** #3102 (Campaign Supervisor Umbrella)
**Manifest Contract:** docs/runbooks/arvp_campaign_supervisor_manifest_state_machine.md

---

## 1. Purpose

The read-only probe layer provides deterministic, structured health and
state checks for the ARVP Campaign Supervisor. Each probe returns a
machine-readable JSON object without mutating any runtime, database,
or configuration surface.

## 2. Output Schema

Every probe returns:

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `ok` \| `warn` \| `blocked` \| `unavailable` |
| `evidence` | dict | Probe-specific result data |
| `observed_at_utc` | string | ISO-8601 UTC timestamp |
| `limitations` | string[] | Known edge cases or constraints |
| `no_mutation` | bool | Always `true` |

Status semantics:
- `ok`: Expected conditions met
- `warn`: Degraded but not blocking
- `blocked`: Campaign cannot proceed
- `unavailable`: Probe cannot execute

## 3. Probe Catalog

| # | Probe | CLI Flag | Dependency | Windows? |
|---|-------|----------|------------|----------|
| 1 | Host | `--host` | PowerShell, WMI | Yes only |
| 2 | Docker | `--docker` | Docker CLI | Yes |
| 3 | Safety | `--safety` | Docker CLI | Yes |
| 4 | DB Readonly | `--db` | psycopg2 or pg_isready | Yes |
| 5 | Candles | `--candles` | psycopg2 | Yes |
| 6 | correlation_ledger | `--ledger` | psycopg2 | Yes |
| 7 | Regime | `--regime` | HTTP or Docker CLI | Yes |

## 4. CLI Usage

```bash
# All probes
python tools/arvp_probe_layer.py --all

# Single probe
python tools/arvp_probe_layer.py --host
python tools/arvp_probe_layer.py --docker
python tools/arvp_probe_layer.py --safety
python tools/arvp_probe_layer.py --db
python tools/arvp_probe_layer.py --candles
python tools/arvp_probe_layer.py --ledger
python tools/arvp_probe_layer.py --regime

# Ledger with campaign start filter
python tools/arvp_probe_layer.py --ledger \
  --campaign-start "2026-06-11T08:00:00Z"

# Custom docker targets
python tools/arvp_probe_layer.py --docker \
  --docker-targets cdb_execution cdb_regime cdb_risk
```

## 5. Integration with Campaign Supervisor (#3111)

The polling loop (#3111) calls `arvp_probe_layer.py` as a subprocess
at each monitoring cycle. Output is parsed as JSON array of probe
results. The supervisor classifies overall campaign health from the
aggregate statuses.

## 6. Safety Boundaries

| Boundary | Status |
|----------|--------|
| No Live-Go | Confirmed |
| No Echtgeld-Go | Confirmed |
| No productive DB writes (SELECT only) | Confirmed |
| No Docker/compose mutation | Confirmed |
| No runtime config changes | Confirmed |
| No strategy parameter changes | Confirmed |
| No secrets in output | Confirmed |
| No synthetic evidence | Confirmed |
