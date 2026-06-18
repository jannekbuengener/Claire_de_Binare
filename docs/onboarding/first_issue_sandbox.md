# First-Issue Sandbox

Status: docs-only guided rehearsal
Issue: #3251
Parent: #3246

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## Purpose / What this sandbox is

This sandbox is a safe, minimal rehearsal path for a new developer or agent who
wants to walk through CDB's branch, validation, PR, LOCK, required checks, merge,
and issue-close workflow without touching runtime, Docker, trading, LR, or
productive DB surfaces.

After completing this rehearsal you will have:

- created a feature branch from `main`,
- made the smallest docs-only change,
- run the scoped validation for that change,
- opened a PR with a proper body and LOCK comment,
- understood which checks must pass before merge,
- merged (or simulated merge criteria), and
- commented and closed the target issue.

The sandbox expects a **tiny docs-only issue**. If no real issue is available,
simulate one: add a sentence to `docs/onboarding/cdb_glossary.md` or
`docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`. Choose the smallest,
safest change that satisfies the rehearsal.

## Safety Boundaries

| Boundary | Rule |
|----------|------|
| **LR** | NO-GO. Never touched by this sandbox. |
| **Live-Go** | Not permitted. |
| **Echtgeld-Go** | Not permitted. |
| **Board stage** | `trade-capable` is Board context, not Live-Go. |
| **Runtime (BLUE+RED)** | No changes. |
| **Docker / Compose** | No changes. |
| **Trading / Strategy / Risk / Execution** | No changes. |
| **Productive DB writes** | No changes. |
| **MCP mutations** | No changes. |
| **SurrealDB writes** | No changes. |
| **Secrets** | No output, no display, no value in any file. |
| **Legacy pack decision** | Outside scope; handled by #3252. |
| **Scope growth** | If the diff drifts outside docs/onboarding or narrow discovery updates, stop. |

## Before starting: Bootloader and live truth

Read these surfaces before you branch. Do not treat any of them as optional.

### For humans

1. `README.md` — repo landing page and safety boundary.
2. `docs/index.md` — shortest active docs landing page.
3. `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md` — visual map for developers.
4. `docs/onboarding/cdb_glossary.md` — terminology anchor for CDB-specific terms.
5. `docs/onboarding/fresh_clone_rehearsal.md` — read-only fresh-clone path.

### For agents

1. `AGENTS.md` → `agents/AGENTS.md` (bootloader + full Read Order).
2. `knowledge/governance/CDB_AGENT_POLICY.md` section 4 (LOCK rules).
3. `docs/runbooks/CONTROL_REGISTER.md` (Board stage and operating focus).
4. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` (LR SSOT, NO-GO).
5. `agents/OPEN_CODE_AGENTS.md` (Brain Evidence Gate and gh-only writes).
6. If scope includes Strategy, Runtime, Module, Service, Contract, Context,
   SurrealDB, MCP tools, DB-backed Memory, or Evidence: emit Brain Evidence
   block before the plan.

### Live truth check (both)

```bash
git fetch origin --prune
git status -sb
git rev-parse HEAD
git rev-parse origin/main
git branch --show-current
gh issue view <issue> --json number,title,state,labels,body,comments
gh pr list --state open --limit 20
```

Stop if:
- you are not on `main`,
- local `main` differs from `origin/main`,
- the target issue is already closed,
- a matching open PR already exists with an active `LOCK:` comment by another writer,
- or scope drifts into runtime, Docker, trading, DB write, memory write, or LR changes.

**Remember**: `CURRENT_STATUS.md` is a ledger, not live truth. GitHub live + repo
live evidence wins.

## Pick or simulate a tiny docs-only issue

1. Verify the issue on GitHub live (`gh issue view`). Confirm it is OPEN and the
   scope is docs-only.
2. Read the full issue body and any linked parent/child comments.
3. If no suitable docs-only issue exists, simulate one:
   - Add a sentence to `docs/onboarding/cdb_glossary.md` that explains a term
     already used in onboarding docs.
   - Or add a clarifier to `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md`.
   - Keep the change to 1-3 lines.

## Create a feature branch or worktree

Always branch from current `main`.

```bash
git switch -c docs/<short-scope>-<issue>
```

Example: `docs/first-issue-sandbox-3251` or `docs/glossary-clarify-XXXX`.

If you prefer a dedicated worktree:

```bash
git worktree add ../cdb-sandbox-<issue> origin/main
cd ../cdb-sandbox-<issue>
```

Verify:

```bash
git status -sb
git branch --show-current
```

## Make a minimal docs-only change

Rules:
- Only edit files under `docs/onboarding/` or the discovery surfaces named in
  the issue.
- Never touch `infrastructure/`, `services/`, `core/`, `knowledge/governance/`,
  or `.github/workflows/`.
- Do not output secrets.
- Do not change `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.
- Do not change `docs/runbooks/CONTROL_REGISTER.md`.
- No opportunistic cleanup outside the issue scope.

## Run targeted validation

Validation depends on the change. For docs-only slices:

```bash
# Whitespace sanity
git diff --check

# Link integrity (if new links were added)
python -m tools.validate_onboarding_docs

# Lint (CI-required)
ruff check .

# Onboarding doctor
python -m tools.onboarding_doctor
```

If a validation failure is caused by known unrelated untracked files (e.g.
`.opencode/plans/`, `docs/decisions/`), document it as scope-fremd and do not
fix it inside the issue.

For agent-specific validation, also run:

```bash
python -m tools.onboarding_tour --role agent
python -m tools.onboarding_tour --role developer
```

## Prepare PR body

Start from the template at `docs/onboarding/templates/pr_body_template.md`.

Required sections in every PR body:

| Section | Content |
|---------|---------|
| Summary | What changed and why it is scoped to this issue. |
| Changed Files | List of paths with purpose. |
| Validation | Commands run and their results. |
| Scope Boundary | Docs/onboarding only; no runtime/Docker/trading/LR/DB changes. |
| Safety/LR | LR bleibt NO-GO. Board stage `trade-capable` is not Live-Go. No Echtgeld-Go. |
| Issue Links | `Closes #<issue>`, `Refs #<parent>`. |
| Brain Evidence | Required when scope touches module/service/contract/context surfaces. |

## Post PR LOCK

After pushing and creating the PR, the **first PR comment** must be the exact
single-writer lock. This is mandatory per `knowledge/governance/CDB_AGENT_POLICY.md`
section 4 and the definition in `docs/onboarding/cdb_glossary.md`.

**Format**:

```text
LOCK: agent=<agent-id> issue=#<issue> ts=<ISO8601> mode=single-writer
```

**Rules**:

- The `LOCK:` must be the **first PR comment**. Do not push or mutate the PR
  before posting it.
- If a `LOCK:` from another agent already exists on the PR: **HARD STOP**.
  Do not push, comment, or mutate.
- If no `LOCK:` exists but a PR already exists: do not create a second PR.
  Inspect the existing PR's comments first.
- An issue-level `START:` comment is useful for status but does **not** replace
  the required PR LOCK.

**Post via `gh` CLI**:

```bash
gh pr comment <pr-number> --body "LOCK: agent=<agent-id> issue=#<issue> ts=<ISO8601> mode=single-writer"
```

All GitHub writes (PR create, comment, merge, issue comment, labels) go through
`gh` CLI only. No MCP/GitHub API/connector writes.

## Check required checks

As defined in `docs/onboarding/cdb_glossary.md` and `.github/CONTROL_PLANE.md`:

| Check | Required? | What it validates |
|-------|-----------|-------------------|
| `ci` | **Yes** | Unit + integration tests, lint (ruff), type checks (mypy) |
| `policy-gate` | **Yes** | Governance compliance, scope violations, forbidden paths |

Non-required checks that should be green or skipped:
- `capture-intent` (non-blocking)
- `submit-pypi` (non-blocking)

Wait for both required checks to go green. If either is red: fix the issue
inside the PR scope, push, and wait again. If the failure is outside your
scope, comment on the PR and stop.

## Merge criteria

Before merging, verify:

1. Required checks `ci` and `policy-gate` are green.
2. No non-required check has a red status caused by this PR's content.
3. Diff stays inside the approved scope (docs/onboarding + narrow discovery).
4. No new `LOCK:` from another writer appeared.
5. No `CHANGES_REQUESTED` review from a blocking reviewer.
6. PR is not in draft / HOLD / BLOCKED state.
7. No secrets in the diff.
8. No LR, Live, or Echtgeld boundary touched.
9. `CURRENT_STATUS.md` is not treated as live truth in the change.

Use **squash merge** to keep a clean main history:

```bash
gh pr merge <pr-number> --squash --delete-branch
```

After merge, verify the merge SHA:

```bash
git fetch origin --prune
git rev-parse origin/main
```

## Close issue / parent comment pattern

### Close the target issue

After merge, comment on the target issue with:
- PR link and merge SHA,
- what was delivered,
- validation evidence,
- scope boundary confirmation,
- Brain Evidence (if applicable).

Then close the issue:

```bash
gh issue close <issue-number>
```

### Parent progress comment

If the issue is a child of a parent issue, add a progress comment on the parent:

```text
## Progress Update — #<child> complete

Delivered via PR #<pr> (<merge-sha-short>):
- <what changed>

Status:
- #<child> complete and merged.
- Parent #<parent> remains open for remaining children: #<next-child>.
```

Keep the parent open unless all children are done.

## Human developer path

1. Read the [CDB Glossary](cdb_glossary.md) first.
2. Follow [Fresh-Clone Rehearsal](fresh_clone_rehearsal.md) if this is your
   first checkout.
3. Pick a tiny docs-only issue or simulate one.
4. Follow this sandbox step by step. Do not skip the bootloader reads.
5. All commands in this sandbox are examples; adjust paths, issue numbers,
   and branch names to your actual task.
6. If you get stuck: stop. Re-read `docs/index.md` or ask on the issue.

## Agent path

1. Resolve the full bootloader: `AGENTS.md` → `agents/AGENTS.md` → full Read
   Order from `agents/AGENTS.md`.
2. If the scope includes Strategy, Runtime, Module, Service, Contract, Context,
   SurrealDB, MCP tools, DB-backed Memory, or Evidence: output the
   **Brain Evidence** block before the plan (see `agents/AGENTS.md` § Brain
   Evidence Gate and `agents/OPEN_CODE_AGENTS.md`).
3. Verify GitHub live state: target issue, related issues, open PRs.
   GitHub live wins over ledger state.
4. Follow this sandbox step by step. Do not skip the PR LOCK.
5. All GitHub writes go through `gh` CLI only.
6. If a matching open PR already exists with a `LOCK:` from another agent:
   **HARD STOP**. Do not push, comment, or mutate.
7. Treat `CURRENT_STATUS.md` as a ledger, not live truth.
8. `trade-capable` (Board stage) is never Live-Go.
9. LR remains NO-GO.

For more detail on the first issue-to-PR flow pattern, see the companion example
at [`examples/first_issue_to_pr_flow.md`](examples/first_issue_to_pr_flow.md).

## Common HOLD conditions

| Condition | Action |
|-----------|--------|
| Not on `main` at start | Switch to `main` and pull. Start over. |
| `main` diverged from `origin/main` | `git fetch origin --prune && git reset --hard origin/main` |
| Issue already closed | Pick a different open issue. |
| Matching open PR with active `LOCK:` by another writer | HARD STOP. Wait or ask. |
| Required check `ci` is red | Fix the issue inside PR scope. Do not expand scope. |
| Required check `policy-gate` is red | Read the failure output. Fix governance issue or stop. |
| Diff grows into runtime/Docker/trading/LR/DB scope | Revert the out-of-scope change. Commit only docs. |
| Secret value appears in diff | Revert immediately. Do not push. |
| `CURRENT_STATUS.md` treated as live truth in the change | Correct to ledger/ledger wording. |
| Opportunistic cleanup of unrelated files | Revert those changes. Keep the diff narrow. |

## What this sandbox must never touch

- `infrastructure/compose/`, `infrastructure/database/`, `infrastructure/scripts/`
- `services/`, `core/`
- `.github/workflows/`
- `knowledge/governance/`
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- `docs/runbooks/CONTROL_REGISTER.md`
- `CURRENT_STATUS.md` (except as read-only evidence)
- `docs/archive/`
- Secret files, `.env`, `SECRETS_PATH`
- Any file outside `docs/onboarding/`, `tools/`, and `tests/` that was not
  explicitly named in the issue scope

## Sources

- [`cdb_glossary.md`](cdb_glossary.md) — PR LOCK, Required Checks, CI, policy-gate
- [`fresh_clone_rehearsal.md`](fresh_clone_rehearsal.md) — read-only fresh-clone path
- [`examples/first_issue_to_pr_flow.md`](examples/first_issue_to_pr_flow.md) — companion example flow
- [`templates/pr_body_template.md`](templates/pr_body_template.md) — PR body template
- [`../index.md`](../index.md) — docs landing page
- [`DEVELOPER_VISUAL_START_HERE.md`](DEVELOPER_VISUAL_START_HERE.md) — visual developer start
- [`../../DEVELOPER_ONBOARDING.md`](../../DEVELOPER_ONBOARDING.md) — developer onboarding guide
- [`../../CONTRIBUTING.md`](../../CONTRIBUTING.md) — contribution workflow and LOCK semantics
- [`../../knowledge/governance/CDB_AGENT_POLICY.md`](../../knowledge/governance/CDB_AGENT_POLICY.md) — agent policy, LOCK rules
- [`../../docs/runbooks/CONTROL_REGISTER.md`](../../docs/runbooks/CONTROL_REGISTER.md) — Board stage
- [`../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) — LR SSOT
- [`../../CURRENT_STATUS.md`](../../CURRENT_STATUS.md) — repo/engineering ledger
- [`../../agents/AGENTS.md`](../../agents/AGENTS.md) — agent bootloader and Read Order

## Safety / LR Reminder

- **LR remains NO-GO.**
- **Board stage `trade-capable` is not Live-Go.**
- **No Echtgeld-Go.**
- **Docs/UI are orientation, not authority.**
- **`CURRENT_STATUS.md` is a ledger, not GitHub live truth.**
- **GitHub live and repo live evidence wins over Brain, memory, or ledger claims.**
