# Security Documentation (`docs/security/`)

Security triage, CodeQL/Trivy readouts, und Alert-Inventar — **kein** Live-Go-Signal.

## Core runbooks

| Doc | Purpose |
|---|---|
| [`TRIAGE_RUNBOOK.md`](TRIAGE_RUNBOOK.md) | Alert triage, dismiss rules, workflow modes |
| [`code-scanning-alert-inventory.md`](code-scanning-alert-inventory.md) | CodeQL inventory (Python) |
| [`TRIVY_TRIAGE_1651.md`](TRIVY_TRIAGE_1651.md) | Trivy cluster notes |

## Readouts

- [`readouts/`](readouts/) — dated security-alert readout snapshots (e.g. 2026-05-05, 2026-05-10)

## GitHub epic

- Issue **#2289** — Security Alert Readout (automation + ledger comments)

## Related

- [`.github/workflows/security-scan.yml`](../../.github/workflows/security-scan.yml)
- [`.github/workflows/security-alert-readout.yml`](../../.github/workflows/security-alert-readout.yml)
- [`docs/runbooks/README.md`](../runbooks/README.md)

## SSOT boundary

Security posture dokumentiert Risiken und Triage; autorisiert kein Live-Trading. LR **NO-GO**.
