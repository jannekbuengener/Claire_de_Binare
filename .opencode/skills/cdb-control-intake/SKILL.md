---
name: cdb-control-intake
description: >
  Establishes the CDB control context for a session by reading canonical control
  surfaces and producing a fail-closed operational snapshot.
---

# CDB control intake

Build the minimum reliable control snapshot before planning or implementation.

## Pflichtquellen

- `docs/runbooks/CONTROL_REGISTER.md`
- GitHub Issue `#1445` live, falls GitHub verfuegbar
- `CURRENT_STATUS.md` nur als Ledger (nicht als Live-SSOT)
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- offene PRs/Issues live, falls fuer den aktuellen Scope relevant

## Prozess (minimal)

1. Read control sources in this order:
   - `docs/runbooks/CONTROL_REGISTER.md`
   - `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
   - `CURRENT_STATUS.md`
   - GitHub `#1445` and relevant open PRs/issues live, if available
2. Separate ledger statements from live GitHub truth.
3. Produce a conservative control snapshot for the current session scope.

## Output

- Board stage
- LR verdict
- aktueller operativer Fokus
- rote Checks / Unsicherheiten
- kleinster sinnvoller naechster Slice

## Stop-Regeln

- Keine LR-/Live-/Echtgeld-Ableitung aus Board stage oder Ledger.
- Wenn Live-GitHub-Pruefung nicht verfuegbar ist: Unsicherheit explizit markieren.
- Bei widerspruechlicher Ledger-/Live-Lage: stoppen oder klar trennen und fail-closed bewerten.
