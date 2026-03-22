---
relations:
  role: doc
  domain: knowledge
  upstream: []
  downstream: []
---
# Defines rules for operational procedures.

## Where to write / Where not to write
*   **Write here:** Rules, guidelines, and instructions for system operation, maintenance, and incident response.
*   **Do NOT write here:** Agent-specific policies (use `agents/policies/`), canonical governance policies (use `knowledge/governance/`).

## Key entrypoints
*   `LIVE_TRADING_RUNBOOK.md` - canonical operator runbook for live-trading cutover and rollback.

## Canonical path rule
*   Active operating rules and operator procedures belong in `knowledge/operating_rules/`.
*   If a same-purpose document also exists directly under `knowledge/`, that copy must be only a pointer, deprecated shell, or clearly historical note.
*   `docs/live-readiness/` remains the canonical status and evidence surface for the current live-readiness verdict; this directory holds the operating procedure.
