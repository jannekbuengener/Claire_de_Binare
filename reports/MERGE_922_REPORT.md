## Merge 922 Report

Status: `BLOCKED (no merge performed)`

- PR URL: `https://github.com/jannekbuengener/Claire_de_Binare/pull/922`
- PR state: `OPEN`
- mergedAt: `null`
- mergeCommit: `null`
- mergeStateStatus: `BLOCKED`
- mergeable: `MERGEABLE`

Gate checks completed:
- Checks green (required): `ci (Unit/Integration + Lint gesammelt)` = `pass`
- Docs-only verified: all 4 changed files are under `docs/governance/status/2026-02-24/`
- File types verified: only `.md`, `.csv`, `.json`
- PR body auto-close keyword scan: none found (`Related: #749` only)

Merge command attempted (failed safely):
- `gh pr merge 922 -R jannekbuengener/Claire_de_Binare --squash --delete-branch --match-head-commit dab785561eaf3b57db4c602613ce726bffdcd388`

GitHub response:
- `base branch policy prohibits the merge`

Likely blocker:
- `main` branch protection has `required_conversation_resolution: true`
- PR remains blocked until the policy condition is satisfied (e.g. unresolved review conversation(s))

Notes:
- No `--admin` merge was used.
- No issue edits, label/state changes, or code changes were performed in this step.
