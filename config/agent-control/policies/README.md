# Agent Control Policies

`#4252` keeps authority ceilings inside
`profiles/execution_contracts/*.yaml`. Registry entries may only reduce those
permissions; they never expand Execution Contract authority.

Approval policy overlay (`#4257`):
[`approval/pr_approval.v1.yaml`](approval/pr_approval.v1.yaml) — versioned
source for `cdb.pr_approval_context.v1`. Do not embed `content_sha256` in the
YAML; the hash is computed at load time.
