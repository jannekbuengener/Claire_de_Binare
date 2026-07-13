# Community Health Audit — Issue #4005

**Task:** `cdb-execute-4005-community-health`  
**Date:** 2026-07-13  
**Base SHA:** `f9e0cb0a6025d6cb8b5843c68e3e74619f4b48f8` (`origin/main`)

---

## Brain Evidence

```text
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - cdb_context_briefing (task_id: cdb-execute-4005-community-health)
  - gh api community/profile (before)
  - gh issue/pr live queries
  - git worktree safety checks
records_or_results:
  - briefing operator_trust_level=LOW; records_found=none
  - community profile before: health=100%, CoC key=other, license=MIT
repo_crosscheck:
  - README.md, CODE_OF_CONDUCT.md, CONTRIBUTING.md, .github/SECURITY.md, LICENSE
impact_on_plan:
  - Repo/GitHub live as SSOT; no DB-backed claims
limitations:
  - Post-merge community profile re-check required after PR merge
context_brain_attempted: true
context_brain_used: false
context_available: false
repo_fallback_used: true
repo_fallback_reason: insufficient_evidence
context_tool_status: available
context_trust_level: none
records_found: none
```

---

## GitHub Community Profile (before)

| Field | Value |
|-------|-------|
| health_percentage | 100 |
| code_of_conduct | present (`key: other`) |
| contributing | present |
| license | MIT |
| security policy | `.github/SECURITY.md` (not in community profile API fields) |

---

## Ist-/Soll-Matrix

| Surface | Before | After |
|---------|--------|-------|
| README Community links | missing | `## Community & Governance` with 4 links |
| CODE_OF_CONDUCT | CC 2.0, `buengener@gmail.com` | CC 3.0, `modusmono.dev@gmail.com` |
| CONTRIBUTING | #3994/#3995 base only | + dedupe, worktree, merge policy, agents/MCP, security |
| SECURITY | placeholders, SLAs, `dev` supported | `main` only, no SLAs, live measures |
| LICENSE | MIT 2024–2026 | unchanged |
| Contract test | none | `tests/unit/docs/test_community_health_contract.py` |

---

## Dedupe vs #3994 and #3995

**Preserved:**
- CONTRIBUTING § README Link Convention
- `make readme-links-guard` / `make onboarding-docs-guard`
- Setup, test, lint, safety/LR sections
- Shared `tools/markdown_link_utils.py` (reused in contract test)

**Not duplicated:**
- No second link engine
- No full agent governance copy (pointer to `agents/AGENTS.md` only)
- No root `SECURITY.md`

---

## Contributor Covenant

| Item | Value |
|------|-------|
| Version | 3.0 |
| Official source | https://www.contributor-covenant.org/version/3/0/code_of_conduct/ |
| Official markdown | https://www.contributor-covenant.org/version/3/0/code_of_conduct/code_of_conduct.md |
| Project-specific header | German Claire de Binare context **outside** covenant text |
| Security note | Outside covenant text → `.github/SECURITY.md` |
| Filled template field | Reporting contact: `modusmono.dev@gmail.com` |
| Attribution | CC BY-SA 4.0 block retained verbatim |

---

## Contact Reconcile

| Item | Value |
|------|-------|
| Old active contact | `buengener@gmail.com` (CODE_OF_CONDUCT) |
| Placeholder removed | `[Security contact - add your email]` (SECURITY) |
| New canonical contact | `modusmono.dev@gmail.com` |
| Active files updated | README (indirect), CODE_OF_CONDUCT, CONTRIBUTING, .github/SECURITY.md |

**Historical (unchanged):**
- `docs/archive/docs_hub_snapshot/meta/legacy/CODE_OF_CONDUCT.md`
- `docs/archive/docs_hub_snapshot/meta/github/SECURITY.md`

---

## Security Policy Changes

**Removed:**
- `dev` as supported version
- Response SLAs (24h/72h/weekly/7-14-30 days)
- `Security Lead: TBD`
- M7/M8/M9 roadmap placeholders
- "Trivy planned" (Trivy workflows exist)

**Added/updated:**
- Supported: `main` only
- Coordinated disclosure without fixed timelines
- Live-verified measures table (Gitleaks, CodeQL, Trivy, Dependabot, GitHub secret scanning/push protection)
- Out-of-scope section (no live/echtgeld implication)

**PVR:** Not enabled or claimed.

---

## Non-goals and Safety Boundaries

- No runtime, trading, ARVP, DB, MCP, Docker, or infra changes
- No LR/board/live/echtgeld decision changes
- No worktree/branch cleanup (#4006)
- No issue-template redesign
- LR remains NO-GO

---

## Handoff to #4006

Worktree `Claire_de_Binare__docs-4005-community-health` and branch
`docs/4005-community-health-reconcile` remain for operator cleanup under #4006.

---

## Validation (local)

Recorded at implementation time in PR body and CI.
