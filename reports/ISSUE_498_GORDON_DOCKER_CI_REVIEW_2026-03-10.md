# Issue #498 Review Verdict (Current Repo State)

Date: 2026-03-10
Scope: Review current Gordon Docker setup + CI workflow claims against today's repo state.

## Claims checked

1. BLUE contains the full core set, including `cdb_db_writer` and `cdb_paper_runner`.
2. BLUE/RED setup is operable through the repo's scripts and docs.
3. CI validates or materially exercises the BLUE/RED split.

## Current verdict

### Claim 1: True today

- `infrastructure/compose/compose.blue.yml` includes both `cdb_db_writer` and `cdb_paper_runner`.
- `infrastructure/compose/SERVICE_MAPPING.md` and `infrastructure/docs/BLUE_RED_SPLIT.md` document the same BLUE membership.

### Claim 2: Partially true before this review, now clarified

- The BLUE/RED compose files and setup wrapper exist and remain the active operator path.
- The shared network helper remains in `infrastructure/scripts/setup_blue_red.ps1`.
- However, the active smoke/test path had drifted: scripts and operational docs still referenced `scripts/smoke_core_flow.py`, which is not present in the current repo.
- This review closes that drift by switching the active smoke path to the existing health-based wrapper `infrastructure/scripts/smoke_test.ps1` and by marking `reports/CORE_FLOW_E2E_SMOKE.md` as historical archived evidence rather than the current runnable gate.

### Claim 3: Not supported today

- Current E2E workflows still run the legacy compose path `infrastructure/compose/base.yml` + `infrastructure/compose/dev.yml`.
- No current GitHub Actions workflow was found that validates `compose.blue.yml` / `compose.red.yml` as the canonical CI path.
- Therefore older claims that CI already verifies the Gordon BLUE/RED split should be treated as historical or over-broad, not as the current repo contract.

## Minimal repo fix applied for review closure

- `infrastructure/scripts/setup_blue_red.ps1` now invokes the maintained health smoke wrapper instead of the missing Python script.
- `infrastructure/scripts/smoke-test.sh` was aligned with the same health-based service model.
- Active operational docs were updated to describe the current smoke path truthfully.

## Remaining limits

- This review does not retrofit CI to validate BLUE/RED compose files.
- Historical evidence files remain in place and may still describe the older core-flow smoke path as part of historical implementation context.
