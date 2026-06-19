# CDB Always-On Evidence Harvester v1

**Status:** Draft contract surface for #3346  
**Mode:** Docs only  
**Parent:** #3345  
**Live-Readiness:** NO-GO  
**Runtime Impact:** none

## Purpose

This document defines the canonical design for an always-on evidence backbone for
ARVP and profitability research.

The goal is continuous, background, paper-only evidence collection so that
coverage gaps are detected early instead of being discovered late in ad hoc
campaigns. This directly addresses the failure mode behind #3343/#3344: the
system should not wait for a one-off research slice to notice that valid natural
paper windows are missing.

## Non-Purpose

This slice is not:

- a trading system
- a live enablement path
- a LR progress claim
- a scheduler implementation
- a collector implementation
- a DB mutation path

## Core Model

The harvester operates on three evidence layers:

- **Raw evidence**: directly observed inputs such as candles, market-data
  provenance markers, paper-run logs, and stream/metrics observations
- **Derived evidence**: computed summaries such as coverage ratios, regime
  coverage, volatility windows, paper-chain counts, and signal density
- **Decision evidence**: human-reviewed or issue-anchored conclusions such as
  blockers, stop conditions, or readiness notes

Only raw evidence is input truth. Derived evidence is explanatory. Decision
evidence is governance output.

## Data Classes

The harvester must cover at least these data classes:

- candles
- market data provenance
- regime coverage
- volatility windows
- paper chains
- strategy signal density
- gaps and blockers

## Read Surfaces

The design assumes read-only observation of existing surfaces:

- Postgres read-only access for evidence lookup when available in later slices
- paper runner logs / event logs
- Redis streams and metrics only if later implementation explicitly allows them

The design does **not** require DB write access. Any append-only evidence table
would need a separate future issue with explicit permission.

## Write Surfaces

Allowed outputs for this slice are local or repo-backed artifacts only:

- Markdown summaries
- JSON snapshots
- issue comments

Forbidden in this slice:

- DB writes
- runtime actions
- secrets output
- trading, risk, or execution actions

## Artifact Contract

The harvester should produce two canonical artifact shapes:

1. **Daily JSON snapshot**
2. **Daily Markdown summary**

Minimum snapshot metrics:

- candle coverage
- market-data provenance status
- regime coverage
- volatility-window coverage
- paper-chain count
- strategy signal density
- gap list with severity
- blocker list with severity
- freshness / last-seen timestamps

Optional rolling status may be emitted for operator visibility, but it must not
replace the daily artifact pair.

## Safety Boundaries

- LR remains NO-GO.
- `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- No execution mutation.
- No order placement.
- No risk override.
- No secrets read or output.
- No automatic Docker or runtime start in the scheduler slice unless a later
  issue explicitly approves it.

## Gap Detection

The harvester must treat these as first-class evidence gaps:

- stale feed
- missing candles
- missing regime coverage
- zero paper chains
- provenance contamination
- missing or stale signal density

Gap detection exists to surface blocked evidence early, not to auto-fix it.

## Sequencing

Implementation order for the child issues is fixed:

1. `#3347` collector
2. `#3348` scheduler
3. `#3349` snapshot
4. `#3350` alerts
5. `#3351` validation

`#3346` must close before any implementation slice starts.

## Why Always-On

Always-on collection prevents the #3343-style late discovery problem by keeping
coverage, provenance, and gap signals continuously visible. That changes the
evidence model from campaign snapshots to a durable background ledger.

## Stop Conditions

Stop the slice if any of the following becomes true:

- a design claim requires live trading semantics
- the harvester starts to imply LR or Echtgeld readiness
- the design needs a runtime start, scheduler deployment, or Docker action
- the design requires DB mutation to be honest
- the design cannot keep raw, derived, and decision evidence separate

## Relationship To Neighbor Issues

- `#3345` is the parent issue tree anchor.
- `#3347` defines the passive collector.
- `#3348` defines local background scheduling.
- `#3349` defines the daily snapshot artifact contract.
- `#3350` defines evidence-gap escalation.
- `#3351` proves 24h dry collection without trading side effects.
- `#1900` remains the ARVP north-star anchor.
- `#2985` remains the separate live roadmap.
- `#2977` remains BLOCKED and is not changed here.
- `#3343/#3344` provide the motivation for continuous evidence collection.

## Validation

For this docs-only slice, validation means:

1. the document is linked from the `#3346` PR
2. the design distinguishes raw, derived, and decision evidence
3. the safety boundaries remain explicit and fail-closed
4. the sequencing to `#3347`-`#3351` is explicit
5. the document contains no secrets, DB writes, or runtime actions

This document does not prove that the harvester exists. It defines the contract
that future implementation slices must satisfy.
