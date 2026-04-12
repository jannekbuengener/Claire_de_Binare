# cdb-post-merge-followup-scanner — Unit Notes

## Status rationale

`active` — this workflow auto-fires on every merged PR via `pull_request: types: [closed]`
(with a guard for `github.event.pull_request.merged == true`). It is part of the
core post-merge automation layer identified in the #1633 Gold-im-Keller candidates.

## Operational role

After each PR merge, this scanner:
1. Reads the merged PR content
2. Applies the CDB control-followup prompt
3. Posts a structured analysis comment to #1445 (the weekly cockpit issue)

This makes #1445 the living record of all post-merge follow-up signals without
requiring manual triggering.

## Shared dependency with cdb-control-followup-classifier

Both units share `.github/prompts/cdb-control-followup.prompt.yml`. A change to
that prompt will affect both automated and manual paths.

## Fail posture

`report_only` — if the scanner fails (e.g., GitHub Models API down, prompt error),
it does not block the PR or the branch. The failure is visible in the Actions log
but has no hard gate effect. This is intentional to avoid blocking merges on an
analysis step.

## Permission note

This unit requires `pull-requests: read` in addition to the standard `issues: write`
and `models: read`. This is the one permission that distinguishes it from the
classifier unit.

## Caveats

- Only fires for merged PRs (not closed-without-merge); the guard ensures this.
- Does not create issues; only comments on #1445.
- Manual dispatch is available for re-running the analysis on a specific PR SHA.

## Related issues

- #1445: Target comment surface (weekly cockpit)
- #1633: Workflow audit (Gold-im-Keller candidate)
- #1644: This collection-layer entry
