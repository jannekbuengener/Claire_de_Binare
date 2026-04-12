# cdb-daily-delta-triage — Unit Notes

## Status rationale

`active` — scheduled 4× per week (Tue/Wed/Fri/Sun 06:20 UTC). This is the lightest
automated triage touchpoint in the control-plane cluster; it keeps signal flowing
between the weekly digest and post-merge scanner without manual effort.

## Critical runtime dependency

`docs/runbooks/CONTROL_REGISTER.md` is **not** advisory documentation for this unit —
it is a **runtime file dependency**. The triage script receives the path as a CLI
argument (`--register-file`) and reads it directly.

This distinction is explicit in the manifest under `dependencies.required_files`.
The validator path-checks this file; if it is moved or deleted, the manifest will
fail validation (and the workflow will fail at runtime).

## Bounded issue creation

The triage script has a hard bound of **max 1 follow-up issue per run**. This is an
explicit guard against issue-creation storms. The manifest documents this under
`mutation_surfaces.issues`.

## Gold-im-Keller context

Part of the #1633 Gold-im-Keller cluster alongside the post-merge scanner. These
two workflows together form the automated signal-propagation backbone feeding #1445.
The daily triage adds time-boxed scheduling; the post-merge scanner adds event-driven
coverage.

## Fail posture

`fail_closed` — if the triage script cannot read the Control Register or encounters
an unhandled error, the workflow fails closed. This is intentional: a triage run
that cannot read its configuration should not silently produce empty results.

## Schedule note

Runs Tue/Wed/Fri/Sun. Deliberately skips Monday (start-of-week overload) and
Saturday (low signal). Thursday is also skipped; this may be worth revisiting if
signal density increases.

## Caveats

- If CONTROL_REGISTER.md is restructured, the triage script's parsing logic may
  need updating alongside the manifest.
- The `actions: read` permission is required for the script to query recent workflow
  run statuses as part of the delta signal.

## Related issues

- #1445: Target cockpit (indirect consumer of follow-up issues)
- #1633: Workflow audit (Gold-im-Keller cluster)
- #1644: This collection-layer entry
- #1642: Future drift-scan workflow (will reference this schedule cadence)
