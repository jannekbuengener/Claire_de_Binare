---
name: cdb-repo-workflow
description: Scoped CDB repo workflow for Hermes cdb-engineer — PR-Flow v1 without merge/CI publish authority.
---

# CDB repo workflow (cdb-engineer)

1. Session-start discipline: git truth → control intake → brain evidence (repo-only if context blocked).
2. Route with `python -m tools.pr_routing route --issue <N>` before branch/PR creation.
3. Deliver slices into the routed PR; expect `DONE_SLICE_ADDED_TO_BATCH_PR`.
4. Mint GitHub tokens only via `python -m tools.hermes_ops mint-token --profile cdb-engineer`.
5. Never publish `cdb-local-ci`, never `--admin` merge, never edit branch protection.
6. Windows tools only against the dedicated workspace; kill-switch fail-closed.
