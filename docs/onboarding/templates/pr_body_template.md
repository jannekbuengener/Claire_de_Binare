# PR Body Template: CDB Docs / Onboarding Slice

## Summary

- `<what changed>`
- `<why it is scoped to this issue>`
- `<what remains out of scope>`

## Changed Files

- `<path>` - `<purpose>`
- `<path>` - `<purpose>`

## Validation

- [ ] `git diff --check`
- [ ] `ruff check .`
- [ ] `<issue-specific docs/link/safety checks>`

## Scope Boundary

- Docs/onboarding only.
- No real GUI or web app.
- No runtime, Docker, service, strategy, risk, execution, trading, LR, productive
  DB, or memory-write changes.
- No credential values or private operator material.

## Safety/LR

- LR bleibt NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- Docs/UI sind Orientierung, keine Autoritaet.
- `CURRENT_STATUS.md` is a ledger, not GitHub live truth.

## Issue Links

Refs #`<issue-number>`

Related: `<parent or sibling issues>`
