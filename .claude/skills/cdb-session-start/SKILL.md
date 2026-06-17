---
name: cdb-session-start
description: >
  Enforce a fail-closed session start for Claire_de_Binare repo work. Use when
  any agent must begin implementation, planning, or triage work in the working
  repo. Verifies Git truth before any other action, detects risky starting
  conditions such as stale local main, dirty worktree, gone-upstream branches,
  or branch-local state mistaken for merged truth, verifies issue state against
  GitHub, then delegates control-context reading to cdb-control-intake. Produces
  a verified execution surface and a conservative go/no-go gate before any repo
  change is made.
---

# CDB session start

Establish a verified, fail-closed starting state before any repo work begins.

## Inputs

- Session goal, issue number, or user request.
- Working repo at `D:\Dev\Workspaces\Repos\Claire_de_Binare`.
- Access to git CLI and GitHub CLI (`gh`).

## Workflow

1. Verify Git truth before reading anything else:

   ```bash
   git fetch origin main
   git rev-parse --abbrev-ref HEAD          # which branch am I on?
   git status                               # clean or dirty?
   git log --oneline origin/main..HEAD      # commits above main?
   ```

   Interpret the output:
   - If HEAD is on a named branch that is not `main`: confirm whether this branch
     has a known purpose or is leftover. If unclear, treat as stale and do not
     use it as the work surface.
   - If the worktree is dirty (unstaged or staged changes): stop and identify what
     the changes are and whether they belong to the current task.
   - If local `main` is behind `origin/main`: do not start branching from stale
     local main; use `origin/main` as the base explicitly.
   - If the branch has commits above `origin/main` with no corresponding open PR:
     surface this as an unreported delivery candidate before continuing.

2. Detect risky starting conditions and apply the gates below before any planning:

   | Condition | Gate |
   |---|---|
   | Dirty worktree with unknown changes | STOP — identify origin, stash or resolve |
   | Local main behind origin/main | Do not start from stale local main; refresh or use origin/main explicitly |
   | Gone upstream branch (remote deleted, local present) | Mark stale; do not build on it |
   | Old local worktree from a prior session | Do not read as implicit active progress |
   | Branch-local commits presented as merged truth | Verify via `gh pr list --state merged` |
   | Auto-merge enabled on repo during closure-sensitive work | State `Closes #N` vs `Refs #N` explicitly |

3. Verify issue state — not just issue prose:

   ```bash
   gh issue view <N>                                         # open or closed? labels?
   gh pr list --search "Closes #<N>" --state merged         # already landed?
   ```

   Determine:
   - Is the target issue still open, or was it closed (possibly prematurely)?
   - Does a merged PR already deliver what the issue asks for?
   - Is the issue superseded by a related issue that is now the active delivery
     vehicle?
   - Was a prior closure valid, or should the issue be reopened?

   If the issue is already closed and no reopening is justified, stop and report
   the session as pre-empted rather than inventing new work.

4. Run `cdb-control-intake` to rebuild the control context:

   Do not continue past this point without the output of `cdb-control-intake`.
   The Git truth checks in steps 1-3 do not replace the control-context read; they
   precede it.

5. Brain Evidence Gate (scope-abhängig):

   If the session scope includes **Strategy, Runtime, Module, Service, Contract,
   Context, SurrealDB, MCP tools, DB-backed Memory, or Evidence**, output the
   Brain Evidence block from `agents/AGENTS.md` § Brain Evidence Gate **before
   any plan**.

   The block MUST contain all fields (`brain_source`, `brain_status`,
   `tools_or_queries`, `records_or_results`, `repo_crosscheck`, `impact_on_plan`,
   `limitations`) with honest values.

   **No plan may claim Memory/Evidence/Decision consideration without
   record/tool/query evidence.**

   If the block is missing or incomplete:
   - STOP.
   - Report which fields are missing or which values are unsubstantiated.
   - Do not proceed to implementation planning.

   Reference: `agents/AGENTS.md` § Brain Evidence Gate;
   default posture SSOT: `knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`
   (#2775). Until verified MCP/DB evidence: `brain_source=repo-only`,
   `brain_status=not-used`. `PERSIST_ALLOWED=False` / `MUTATION_ALLOWED=False`
   on `main`; Context Brain output does not authorize writes or issue creation.

6. MCP Capability Resolution Gate (conditional):

   When the session scope includes Context, SurrealDB, MCP tools, ContextBridge,
   or DB-backed agent memory, verify capability before any implementation or
   tool-dependent planning.

   **Capability beats assumption.** Repo presence is not MCP availability. A tool
   counts as available only if the active MCP surface exposes it and invocation
   dispatches a real handler.

   | # | Check | Pass criterion |
   |---|---|---|
   | 1 | Active inventory | Tool appears in the active MCP tool list |
   | 2 | No `unknown_tool` | Tool call does not return `unknown_tool` |
   | 3 | No `not_implemented` | Tool call does not return `not_implemented` |
   | 4 | Real dispatch | Handler returns real behavior |
   | 5 | Read-only contract | `metadata.read_only == true` where applicable |
   | 6 | Explicit DB opt-in | DB-backed mode requires explicit `adapter_config_path` |
   | 7 | Fail-closed boundaries | Remote DB URLs and write/admin statements are rejected |

   If any check fails:
   - STOP.
   - Report the exact missing layer.
   - Do not adopt raw/external SurrealDB MCP as a shortcut.
   - Propose only the smallest CDB-native read-only slice after Human-GO.
   - LR remains NO-GO. No Echtgeld-Go.

   Reference: `docs/runbooks/surrealdb_context_mcp_access.md` § 1.5.

7. Create a clean execution surface:

   Once steps 1-6 are complete and no gate has fired, create the working surface:
   - Branch from current `origin/main` (never from stale local main).
   - Clean worktree confirmed.
   - Explicit target issue identified and open.
   - Scope stated: what is IN, what is OUT.
   - Closure semantics confirmed: `Closes #N` (full delivery) vs. `Refs #N`
     (partial or scoped delivery).

## Fail-Closed Rules

- If `git fetch origin main` fails, stop and report the session as blocked.
- If the worktree is dirty and the changes cannot be attributed, stop.
- If local main is stale and the correct base cannot be confirmed, stop.
- If the target issue cannot be read via `gh issue view`, stop.
- If `cdb-control-intake` cannot be completed, stop.
- If any of the risky conditions in step 2 cannot be resolved, stop and report
  what remains unresolved before any file is touched.
- If the Brain Evidence Gate block is missing or incomplete for a relevant
  scope, stop and report which fields are missing or unsubstantiated.
- If MCP capability cannot be verified for a Context/SurrealDB tool in scope,
  stop and report the missing layer instead of implementing or calling around it.

## Output

Return the result in this structure:

```md
Git-Wahrheit
- Branch:
- Worktree:
- Commits ueber origin/main:
- Risky conditions gefunden: ja / nein -- <Detail>

Issue-Wahrheit
- Issue #N: offen / geschlossen
- Merged PR gefunden: ja / nein -- <PR-Nummer oder keiner>
- Bewertung: gueltige Startbasis / pre-empted / Klaerungsbedarf

Control-Snapshot (via cdb-control-intake)
- Board stage:
- LR verdict:
- Weekly focus:

Brain Evidence (nur bei relevantem Scope)
- brain_source:
- brain_status:
- tools_or_queries:
- records_or_results:
- repo_crosscheck:
- impact_on_plan:
- limitations:

Arbeitsflaeche
- Branch:
- Scope:
- Closure-Semantik:
- Gate: go | no-go -- <Grund wenn no-go>
```

## Anti-Patterns

- Do not read control docs or the target issue before verifying Git state.
- Do not assume local main is current without an explicit fetch.
- Do not treat branch-local commits as merged truth.
- Do not start work on a dirty worktree without identifying the changes.
- Do not use `git add .` at any point during session start.
- Do not mark the gate as `go` when any of the fail-closed conditions is unresolved.
- Do not invent reviewer, approver, or merge-authority roles; this is a
  solo-maintainer repo.
- Do not treat repo presence of MCP files, registry entries, or `tools/mcp/server.py`
  as proof that a tool is callable through the active MCP surface.
