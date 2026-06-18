# Onboarding / README / Navigation Audit (#3227)

Status: Evidence
Issue: #3227
Parent: #3226
Date: 2026-06-16
Scope: Docs / onboarding / navigation / repo-brain discoverability only

## Executive Summary

- Repo-backed inventory found `79` active non-archive `README.md` surfaces, `4` active `index.md` surfaces, `3` active onboarding markdown files, `1` active navpack `ENTRYPOINTS.yaml`, `1` active `CHEATSHEET.md`, and `2` active `AGENTS.md` bootloader surfaces.
- The active front door is `README.md`, but it does not send a new developer into a clean developer-first chain. It routes first into control/status surfaces and omits direct pointers to `DEVELOPER_ONBOARDING.md` and `docs/index.md` as the primary setup path (`README.md:36-44`).
- `DEVELOPER_ONBOARDING.md` and `CONTRIBUTING.md` are active-file surfaces with stale guidance: direct secret-display commands, non-canonical test/lint guidance, and historical status references (`DEVELOPER_ONBOARDING.md:170-180`, `DEVELOPER_ONBOARDING.md:282-289`, `DEVELOPER_ONBOARDING.md:509-596`, `CONTRIBUTING.md:9-12`, `CONTRIBUTING.md:91-122`).
- `knowledge/content/ONBOARDING_QUICK_START.md` and `knowledge/content/ONBOARDING_LINKS.md` behave as duplicate legacy onboarding packs in the live tree. They contain multiple missing-path references and should not remain implicit active truth (`knowledge/content/ONBOARDING_QUICK_START.md:76-90`, `knowledge/content/ONBOARDING_LINKS.md:24-35`, `knowledge/content/ONBOARDING_LINKS.md:71-95`).
- Repo Brain / Context Intelligence onboarding assets exist and are healthy as tooling, but they are not visible enough in the first-line onboarding flow. The read-only doctor exists in `Makefile:400-402`, `tools/surrealdb/context_onboarding_doctor.py`, and `tests/unit/surrealdb/test_context_onboarding_doctor.py`, but the primary onboarding surfaces do not route a developer to it.
- No runtime, Docker, live-trading, LR, DB-write, or code-behavior changes were made in this issue.

## Scope

Deep-audited mandatory surfaces:

- `README.md`
- `.github/README.md`
- `DEVELOPER_ONBOARDING.md`
- `docs/index.md`
- `CONTRIBUTING.md`
- `services/README.md`
- `tests/README.md`
- `tools/README.md`
- `infrastructure/compose/README.md`
- `docs/surrealdb/README.md`
- `knowledge/content/ONBOARDING_QUICK_START.md`
- `knowledge/content/ONBOARDING_LINKS.md`
- `mcp_navpack_working_repo/ENTRYPOINTS.yaml`
- `mcp_navpack_working_repo/CHEATSHEET.md`
- `Makefile`
- `tools/surrealdb/context_onboarding_doctor.py`
- `tests/unit/surrealdb/test_context_onboarding_doctor.py`

Adjacent discovery surfaces read for routing context:

- `AGENTS.md`
- `agents/AGENTS.md`
- `agents/OPEN_CODE_AGENTS.md`
- `mcp_navpack_working_repo/README.md`
- `docs/runbooks/README.md`
- `docs/live-readiness/README.md`
- `docs/meta/WORKING_REPO_CANON.md`
- `CURRENT_STATUS.md`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`

Repo-wide inventory counts used for prioritization:

| Surface family | Total incl. archive | Active / non-archive |
|---|---:|---:|
| `README.md` | 105 | 79 |
| `index.md` | 4 | 4 |
| `*ONBOARDING*.md` | 5 | 3 |
| `ENTRYPOINTS.yaml` | 6 | 1 |
| `CHEATSHEET.md` | 1 | 1 |
| `AGENTS.md` | 3 | 2 |

## Live Evidence

Git / GitHub start truth:

| Check | Result |
|---|---|
| `git fetch origin --prune` | OK |
| `git branch --show-current` before branching | `main` |
| `git rev-parse HEAD` vs `git rev-parse origin/main` | identical: `59e2db587d2e27ab7a4380bbb6631add7b2c4ae1` |
| `git status -sb` before branching | clean tracked state; unrelated untracked dirs present: `.opencode/plans/`, `docs/decisions/` |
| `gh issue view 3227` | `OPEN` |
| `gh issue view 3226` | `OPEN` |
| `gh pr list --search "3227" --state all --limit 20` | no PR found |
| `gh pr list --state open --limit 20` | only open PRs seen were unrelated dependabot PRs `#3204`-`#3207` |
| `gh issue list --state open --search "onboarding OR README OR docs index OR repo brain OR context doctor" --limit 50` | open chain confirmed: `#3226`, `#3227`, `#3228`, `#3229`, `#3230`, `#3231`, `#3232`, `#3233` |

Relevant GitHub-live signals:

- `#3226` already defines the child-issue chain `#3227`-`#3233` in a live comment.
- `#1445` contains prior post-merge discovery-surface-drift signals for this exact area:
  - comment `4633271121`: drift observation against `README.md`, `services/README.md`, `mcp_navpack_working_repo/ENTRYPOINTS.yaml`, `mcp_navpack_working_repo/CHEATSHEET.md`
  - comment `4633810579`: drift observation against `docs/index.md`, `docs/runbooks/README.md`, `mcp_navpack_working_repo/ENTRYPOINTS.yaml`, `mcp_navpack_working_repo/CHEATSHEET.md`

## Bootloader Evidence

Bootloader chain resolved repo-backed before GitHub mutation:

| Surface | Evidence |
|---|---|
| `AGENTS.md` | root pointer only; points to `agents/AGENTS.md` (`AGENTS.md:9-26`) |
| `agents/AGENTS.md` | canonical 10-step read order present and complete (`agents/AGENTS.md:10-22`) |
| `knowledge/governance/CDB_AGENT_POLICY.md` | Write-Zone and single-writer rules read before any write (`knowledge/governance/CDB_AGENT_POLICY.md:125-213`) |
| `docs/meta/WORKING_REPO_CANON.md` | SSOT split and working-repo canon confirmed (`docs/meta/WORKING_REPO_CANON.md:28-57`) |
| `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | LR verdict confirmed `NO-GO` (`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md:11-18`) |
| `docs/runbooks/CONTROL_REGISTER.md` | Board stage confirmed `trade-capable`, orthogonal to LR (`docs/runbooks/CONTROL_REGISTER.md:3-7`, `docs/runbooks/CONTROL_REGISTER.md:21-31`) |
| `agents/OPEN_CODE_AGENTS.md` | OpenCode routing and Brain-Evidence / MCP capability rules confirmed (`agents/OPEN_CODE_AGENTS.md:28-43`) |

Canonical read-order entries were all present:

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md`

## Brain Evidence

```text
## Brain Evidence
brain_source: repo-only
brain_status: not-used
tools_or_queries:
  - read AGENTS.md
  - read agents/AGENTS.md
  - read knowledge/governance/CDB_CONSTITUTION.md
  - read knowledge/governance/CDB_GOVERNANCE.md
  - read knowledge/governance/CDB_AGENT_POLICY.md
  - read knowledge/governance/SYSTEM_INVARIANTS.md
  - read knowledge/CDB_KNOWLEDGE_HUB.md
  - read docs/meta/WORKING_REPO_CANON.md
  - read CURRENT_STATUS.md
  - read docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md
  - read docs/runbooks/CONTROL_REGISTER.md
  - read agents/OPEN_CODE_AGENTS.md
  - grep Read Order / Brain Evidence / section 4
records_or_results:
  - No verified SurrealDB-local/context-package record evidence used.
  - Full agents/AGENTS.md read order resolved repo-backed with all 10 entries present.
  - CDB_AGENT_POLICY.md section 4 read repo-backed before write-zone actions.
repo_crosscheck:
  - AGENTS.md -> agents/AGENTS.md
  - agents/AGENTS.md:10-22, 103-172
  - knowledge/governance/CDB_AGENT_POLICY.md:125-213
  - docs/meta/WORKING_REPO_CANON.md:28-57
  - docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md:11-18
  - docs/runbooks/CONTROL_REGISTER.md:3-7, 21-31
impact_on_plan:
  - Context/Repo Brain claims stay repo-backed only.
  - GitHub live state overrides CURRENT_STATUS.md where they differ.
  - This issue remains evidence-only; no onboarding fixes in-scope.
limitations:
  - No verified SurrealDB-local adapter/query/record evidence proving DB-backed Context Brain use.
  - No DB-backed onboarding-memory inventory was proven; repo and GitHub remain the authoritative sources.
```

## Audit Matrix

| Surface | Primary status | Current role | Audit finding | Follow-up issue |
|---|---|---|---|---|
| `AGENTS.md` | `active` | root bootloader pointer | Correct local pointer; should remain pointer-only (`AGENTS.md:9-26`) | none |
| `agents/AGENTS.md` | `active` | canonical bootloader / read order | Complete and current; already exposes Brain Evidence Gate (`agents/AGENTS.md:10-22`, `agents/AGENTS.md:103-172`) | none |
| `README.md` | `active` | GitHub landing page / repo front door | Canon-safe status framing, but not developer-first. No direct link to `DEVELOPER_ONBOARDING.md` or `docs/index.md` in the primary entry chain (`README.md:36-44`) | `#3228` |
| `.github/README.md` | `active` | control-plane explainer | Useful support doc, but count claims are stale: file states `65` workflow defs / `66` tracked files / `67` workflows, while directory listing shows `69` entries incl. `labels.json` => `68` workflows (`.github/README.md:32-49`, `.github/README.md:88-119`) | `#3230` |
| `DEVELOPER_ONBOARDING.md` | `stale` | long-form developer setup guide | Routes through active files near the end, but contains secret-display commands, non-canonical test/lint guidance, and historical references like `PROJECT_STATUS.md` (`DEVELOPER_ONBOARDING.md:170-180`, `DEVELOPER_ONBOARDING.md:282-289`, `DEVELOPER_ONBOARDING.md:509-596`) | `#3229` |
| `docs/index.md` | `active` | shortest docs landing page | Concise and mostly clean, but it omits any direct developer-setup pointer to `DEVELOPER_ONBOARDING.md` and does not expose Repo Brain / Context doctor from the landing page (`docs/index.md:6-49`) | `#3230` |
| `CONTRIBUTING.md` | `stale` | contribution rules | Diverges from repo canon: `Python 3.11+`, `flake8`, generic `pytest tests/`, heavy `pre-commit` framing instead of current `ruff`/repo test slice (`CONTRIBUTING.md:9-12`, `CONTRIBUTING.md:91-122`) | `#3229` |
| `services/README.md` | `active` | service-tree index | Clean local index; good boundary language; low direct onboarding risk (`services/README.md:1-37`) | `#3230` only if README graph is adjusted |
| `tests/README.md` | `active` | test taxonomy | Good CI/local split and LR boundary; low risk (`tests/README.md:22-48`) | `#3230` only if README graph is adjusted |
| `tools/README.md` | `active` | repo-wide PowerShell index | Good runtime/tool index, but it does not expose `make context-doctor` or the Context onboarding doctor as a developer-facing preflight (`tools/README.md:16-60`) | `#3231`, `#3232` |
| `infrastructure/compose/README.md` | `active` | compose canon explainer | Good runtime/CI split; acts as supporting infra doc, not first onboarding step (`infrastructure/compose/README.md:22-65`) | `#3230` only if README graph is adjusted |
| `docs/surrealdb/README.md` | `active` | Context / SurrealDB doc index | Good operator index, but it hides the developer preflight path: no mention of `make context-doctor` or `context_onboarding_doctor.py` (`docs/surrealdb/README.md:5-45`) | `#3231`, `#3232` |
| `knowledge/content/ONBOARDING_QUICK_START.md` | `duplicate` | legacy onboarding pack in live tree | Duplicate onboarding surface with active-tree placement, but it routes to multiple missing or non-canonical docs (`knowledge/content/ONBOARDING_QUICK_START.md:13-31`, `knowledge/content/ONBOARDING_QUICK_START.md:73-90`, `knowledge/content/ONBOARDING_QUICK_START.md:129-135`) | `#3229` |
| `knowledge/content/ONBOARDING_LINKS.md` | `duplicate` | legacy consolidated links pack | Duplicate surface with many broken or stale paths (`docs/CONTRACTS.md`, `docs/TEST_HARNESS_V1.md`, `docs/PATCHSET_PLAN_345.md`, `docs/services/`, `docs/architecture/`, `docs/workflows/`, `docs/services/WS_SERVICE_RUNBOOK.md`) (`knowledge/content/ONBOARDING_LINKS.md:24-35`, `knowledge/content/ONBOARDING_LINKS.md:71-95`, `knowledge/content/ONBOARDING_LINKS.md:120-127`, `knowledge/content/ONBOARDING_LINKS.md:143-183`) | `#3229`, `#3230` |
| `mcp_navpack_working_repo/README.md` | `active` | navpack summary | Useful meta-surface, but still routes step 3 to stale `DEVELOPER_ONBOARDING.md` and does not surface the bootloader-first developer chain (`mcp_navpack_working_repo/README.md:13-24`) | `#3230`, `#3231` |
| `mcp_navpack_working_repo/ENTRYPOINTS.yaml` | `stale` | machine-readable read order | Active surface, but expected signal for compose still says `base/dev fragments`, and the minimal bundle omits `docs/surrealdb/README.md`, `tools/README.md`, `tests/README.md`, and any doctor surface (`mcp_navpack_working_repo/ENTRYPOINTS.yaml:24-26`, `mcp_navpack_working_repo/ENTRYPOINTS.yaml:71-83`) | `#3230`, `#3231`, `#3232` |
| `mcp_navpack_working_repo/CHEATSHEET.md` | `stale` | human nav quickref | Routes developers straight into stale `DEVELOPER_ONBOARDING.md` and still lacks any `context-doctor` / Repo Brain preflight pointer (`mcp_navpack_working_repo/CHEATSHEET.md:5-10`, `mcp_navpack_working_repo/CHEATSHEET.md:25-49`) | `#3230`, `#3231`, `#3232` |
| `Makefile` | `active` | command surface | Canonical place where `context-doctor` is already exposed (`Makefile:111`, `Makefile:400-402`); strong active tooling evidence | `#3232` only if help text or neighboring targets need onboarding refinement |
| `tools/surrealdb/context_onboarding_doctor.py` | `active` | read-only onboarding preflight | Healthy supporting tool: no secret output, LR `NO-GO` note preserved, next-action prioritization is conservative (`tools/surrealdb/context_onboarding_doctor.py:66-72`, `tools/surrealdb/context_onboarding_doctor.py:312-344`, `tools/surrealdb/context_onboarding_doctor.py:448-478`, `tools/surrealdb/context_onboarding_doctor.py:541-554`) | `#3232` |
| `tests/unit/surrealdb/test_context_onboarding_doctor.py` | `active` | safety regression for doctor | Good evidence that the doctor redacts secrets and stays fail-closed (`tests/unit/surrealdb/test_context_onboarding_doctor.py:292-338`) | `#3232` |

## GitHub README Priority Finding

Finding: `README.md` is the highest-impact onboarding surface because it is the repo landing page on GitHub, but its current canonical entry chain is control-first rather than developer-first.

Evidence:

- `README.md:36-44` sends readers to `CONTROL_REGISTER`, GitHub issue `#1445`, `CURRENT_STATUS.md`, LR status, canon doc, and `agents/AGENTS.md`.
- The same README does not directly send a new developer to `DEVELOPER_ONBOARDING.md`, `docs/index.md`, `CONTRIBUTING.md`, or the Context onboarding doctor.
- Because GitHub renders the root README by default, this is the most important surface to repair first.

Consequence:

- `#3228` should be the first high-impact README/front-door fix.

## Repo Brain / Context Intelligence Onboarding Finding

Finding: Repo Brain / Context Intelligence onboarding assets exist, but they are not visible enough in the active developer flow.

Positive evidence:

- Bootloader / Brain Evidence policy is explicit in `agents/AGENTS.md:103-172`.
- OpenCode routing explicitly references Brain Evidence and MCP capability rules in `agents/OPEN_CODE_AGENTS.md:30-43`.
- `docs/surrealdb/README.md` is a valid context/MCP index (`docs/surrealdb/README.md:5-45`).
- `Makefile` exposes `make context-doctor` (`Makefile:111`, `Makefile:400-402`).
- The doctor itself is secret-safe and tested (`tools/surrealdb/context_onboarding_doctor.py`, `tests/unit/surrealdb/test_context_onboarding_doctor.py`).

Gap evidence:

- `README.md` does not mention the brain/context path (`README.md:36-44`).
- `docs/index.md` exposes `docs/surrealdb/README.md`, but not a developer-facing context preflight path (`docs/index.md:10-21`).
- `DEVELOPER_ONBOARDING.md` never points to `make context-doctor` or `docs/surrealdb/README.md`.
- `tools/README.md` does not mention the doctor at all (`tools/README.md:16-60`).
- `docs/surrealdb/README.md` also omits the doctor and preflight entry.

Consequence:

- `#3231` should make the Repo Brain / Context path explicit in the front-door chain.
- `#3232` should expose the already-existing doctor tooling in that chain.

## Secret-Output-Risk Finding

Finding: `DEVELOPER_ONBOARDING.md` contains commands that intentionally print or inline secret material into terminal history / shell substitution.

Evidence:

- `DEVELOPER_ONBOARDING.md:170-180` explicitly instructs `cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD` / `Get-Content ...REDIS_PASSWORD`.
- `DEVELOPER_ONBOARDING.md:282-289` uses `redis-cli -a $(cat ~/Documents/.secrets/.cdb/REDIS_PASSWORD)` inline.
- `DEVELOPER_ONBOARDING.md:579` keeps `View secret` in the quick reference table.

Counter-evidence of the safer pattern already available:

- `tools/surrealdb/context_onboarding_doctor.py` defines forbidden output substrings and redacts sensitive text (`tools/surrealdb/context_onboarding_doctor.py:66-72`, `tools/surrealdb/context_onboarding_doctor.py:541-554`).
- `tests/unit/surrealdb/test_context_onboarding_doctor.py:292-338` asserts secret values never appear in JSON or text output.

Consequence:

- `#3229` should remove the secret-printing guidance from human onboarding docs.
- `#3232` should promote a no-secret-output validation path instead of raw secret viewing.

## Broken / Stale Path Finding

High-confidence missing-path or stale-path examples:

| Surface | Broken or stale target | Result |
|---|---|---|
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/CONTRACTS.md` | missing |
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/TEST_HARNESS_V1.md` | missing |
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/PATCHSET_PLAN_345.md` | missing |
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/services/` | missing |
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/architecture/` | missing |
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/workflows/` | missing |
| `knowledge/content/ONBOARDING_LINKS.md` | `docs/services/WS_SERVICE_RUNBOOK.md` | missing |
| `knowledge/content/ONBOARDING_QUICK_START.md` | `docs/CONTRACTS.md` | missing |
| `knowledge/content/ONBOARDING_QUICK_START.md` | `docs/TEST_HARNESS_V1.md` | missing |
| `knowledge/content/ONBOARDING_QUICK_START.md` | `docs/PATCHSET_PLAN_345.md` | missing |
| `knowledge/content/ONBOARDING_QUICK_START.md` | `docs/services/<SERVICE>_RUNBOOK.md` | stale pattern; subtree absent |
| `knowledge/content/ONBOARDING_QUICK_START.md` | `docs/security/SECRET_LEAK_RESPONSE.md` | missing |
| `DEVELOPER_ONBOARDING.md` | `PROJECT_STATUS.md` as service overview | historical snapshot, not current SSOT |
| `.github/README.md` | workflow-count claims | stale detail, paths themselves resolve |
| `mcp_navpack_working_repo/ENTRYPOINTS.yaml` | compose expected signal says `base/dev` | stale expectation against current compose canon |

## Recommended Execution Order For #3228-#3233

Recommended order:

1. `#3228` — restore `README.md` as a developer-usable GitHub landing page.
2. `#3230` — reconcile `docs/index.md`, navpack routing, and the README graph across support surfaces.
3. `#3229` — reconcile `DEVELOPER_ONBOARDING.md`, `CONTRIBUTING.md`, and demote/retire duplicate onboarding packs under `knowledge/content/`.
4. `#3231` — add the explicit Repo Brain / Context Intelligence developer path across front-door docs.
5. `#3232` — expose and, if needed, extend the one-command onboarding doctor path around existing `context-doctor` tooling.
6. `#3233` — codify link and entrypoint validation only after the intended active graph is settled.

Dependency rationale:

- `#3228` is first because GitHub users see root `README.md` before any other surface.
- `#3230` should lock the active graph before deeper content repair, because navpack and docs index currently route traffic into stale surfaces.
- `#3229` should then repair the long-form setup content and duplicate onboarding packs.
- `#3231` and `#3232` should build on the repaired front-door graph, not compete with it.
- `#3233` should validate the final intended chain, not preserve today's stale one.

## Suggested File Ownership By Follow-up Issue

| Issue | Recommended primary file set |
|---|---|
| `#3228` | `README.md` |
| `#3229` | `DEVELOPER_ONBOARDING.md`, `CONTRIBUTING.md`, `knowledge/content/ONBOARDING_QUICK_START.md`, `knowledge/content/ONBOARDING_LINKS.md` |
| `#3230` | `docs/index.md`, `.github/README.md`, `services/README.md`, `tests/README.md`, `tools/README.md`, `infrastructure/compose/README.md`, `docs/surrealdb/README.md`, `mcp_navpack_working_repo/README.md`, `mcp_navpack_working_repo/ENTRYPOINTS.yaml`, `mcp_navpack_working_repo/CHEATSHEET.md` |
| `#3231` | `README.md`, `docs/index.md`, `DEVELOPER_ONBOARDING.md`, `tools/README.md`, `docs/surrealdb/README.md`, `mcp_navpack_working_repo/ENTRYPOINTS.yaml`, `mcp_navpack_working_repo/CHEATSHEET.md` |
| `#3232` | `Makefile`, `tools/surrealdb/context_onboarding_doctor.py`, `tests/unit/surrealdb/test_context_onboarding_doctor.py`, plus supporting discoverability pointers in `tools/README.md` and `docs/surrealdb/README.md` |
| `#3233` | CI / validator surfaces that enforce the repaired active graph; likely new or updated validation scripts/tests/workflows rather than direct content fixes in this audit issue |

## Stop / Non-Scope Boundaries

- No README, onboarding, navpack, or tooling fixes were implemented here beyond this evidence document.
- No runtime, Docker, stack, live-trading, paper-trading, exchange, LR, or safety-policy behavior was changed.
- No productive DB or memory writes were performed.
- No secret values were read into the evidence document.
- `CURRENT_STATUS.md` was treated as ledger only, not as live GitHub truth.
- Board stage `trade-capable` was not treated as LR-Go.

## Restunsicherheiten

- This audit intentionally deep-read the required high-priority surfaces, not all `79` active non-archive `README.md` files line-by-line.
- The navpack / onboarding graph almost certainly has more secondary cleanup candidates in subtree READMEs; they were inventory-counted but not all individually classified here.
- The exact future validation mechanism for `#3233` was not designed here; this audit only shows where the drift exists.
- The local worktree contained unrelated untracked surfaces before this issue branch (`.opencode/plans/`, `docs/decisions/`); they were excluded from scope.

## Verdict

Audit verdict: `PASS_FOR_EVIDENCE`

Recommended handoff verdict for the issue chain:

- `#3227` can close once this evidence doc is merged.
- Follow-up work should proceed in the recommended order above.
