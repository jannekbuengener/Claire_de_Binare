# Session Log — 2026-07-05 #3742 Readonly Access Hold

**Scope:** Document #3742 HOLD_READONLY_ACCESS_UNAVAILABLE; evidence doc + PR.

**Base:** `origin/main` @ `782ab3f3`

## Delivered

- `scripts/arvp_3742_natural_paper_window_inventory.py` (readonly inventory script)
- `docs/evidence/arvp_natural_paper_window_bank_readonly_feasibility_3742.md`
- `CURRENT_STATUS.md` HOLD line for #3742

## Validation

- `ruff check scripts/arvp_3742_natural_paper_window_inventory.py` — PASS
- Script run — exit 1, `HOLD_READONLY_ACCESS_UNAVAILABLE` (cdb_readonly auth fail)
- No credentials in diff

## Boundaries

- No DB mutation, no Docker/runtime/replay
- #3742 stays OPEN
- LR NO-GO unchanged

## Next

- Operator repair: `operator_create_readonly_login.sql` + `verify_privileges.sql`
- Re-run inventory script; continue #3742 data feasibility slice

## Merge closeout (2026-07-05)

- PR #3744 **MERGED** (squash) @ `5f7d33fd`
- Branch `docs/arvp-3742-readonly-access-hold` deleted
- #3742 **OPEN**; #1900 **OPEN**
- LR **NO-GO** unchanged; §5.2.4 **NOT MET**
