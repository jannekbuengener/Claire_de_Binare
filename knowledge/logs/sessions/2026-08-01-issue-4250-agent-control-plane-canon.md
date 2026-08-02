# Session 2026-08-01 — Issue #4250 Agent Control Plane Canon

## Scope
Delivery-only Canon für provider-neutrale CDB Agent Control Plane (#4250 / parent #4249).

## Status
`DONE_SLICE_ADDED_TO_BATCH_PR`

## GitHub
- PR: https://github.com/jannekbuengener/Claire_de_Binare/pull/4286
- Head: `e6d6f83b33a1801d56eef83c927dbec7067b4afa`
- Branch: `batch/agent-skills-issue-4250`
- Router: `CREATE_NEW_BATCH_PR` / lane `agent-skills`

## Delivered
- `knowledge/governance/CDB_AGENT_CONTROL_PLANE.md`
- Pointers in `knowledge/governance/README.md`, `agents/AGENTS.md`, `AGENTS.md`

## Validation
- validate_readme_links OK
- validate_onboarding_docs OK
- git diff --check clean
- pr_routing validate-pr-body PASS (after ledger status fix to SLICE_DELIVERED)

## Boundaries
- LR NO-GO; no merge; no cdb-local-ci publish; no #4251+ implementation
- GitHub Workflow Control Plane untouched

## Brain Evidence
repo-only / not-used; context tools available; trust none; insufficient_evidence fallback

## Correction 2026-08-01 (P1 review on PR #4286)

Do not read the original "Canon" delivery claim as owner-ratified binding
policy. Live P1 threads `PRRT_kwDOQUkXUM6VqrHK` /
`PRRT_kwDOQUkXUM6VqrHL` required demotion:

- `CDB_AGENT_CONTROL_PLANE.md` status → **Proposal / Pending Owner Canonization**
- Truth/Authority order corrected so Constitution/Governance/Policies outrank
  GitHub live state; live state remains SSOT only for operational facts within
  those bounds
- Pointers in README/`AGENTS.md`/`agents/AGENTS.md` aligned

Rationale: `CDB_AGENT_POLICY.md` Zone D forbids agent modification of
canonical policies; `#4202` exception creates no precedent; issue `#4250` alone
is not a policy amendment.
