# CDB Agent Prompt Template

Status: Template
Issue: #3238

Use this as a reusable prompt skeleton for CDB agent work. Replace placeholders
with task-specific values. Do not include credential values, private material,
or references to hidden ChatGPT/internal documents.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

## PR Routing (Pflicht)

Vor Plan-Finalisierung, Branch-, Worktree- oder PR-Erstellung:

```powershell
python -m tools.pr_routing route --issue <issue-number> --agent <agent-id>
```

Der Prompt muss die Router-Ausgabe mit Ziel-PR/-Branch, Lane, Validation
Profile, Lock-State und Reason Codes enthalten. `HOLD_*` stoppt alle Writes.
Der normale Abschluss ist `DONE_SLICE_ADDED_TO_BATCH_PR`; Merge und
Issue-Closure sind kein Session-Default.

## Aufgabe

Bearbeite CDB Issue `<issue-number>`:
`<issue-title-or-url>`

## Ziel

`<one concise target outcome>`

## Scope

In scope:

- `<paths, docs, or code areas explicitly allowed>`

Out of scope:

- No real GUI or web app unless explicitly approved.
- No runtime, Docker, trading, live, LR, productive DB, or memory-write changes
  unless explicitly approved for this issue.
- No credential values or private operator material.

## Bootloader

Resolve before planning or writing:

1. `AGENTS.md`
2. `agents/AGENTS.md`
3. Full Read Order from `agents/AGENTS.md`
4. `agents/OPEN_CODE_AGENTS.md`
5. Task-specific canon and evidence docs

If a canonical file or Read Order entry is missing, stop and report it exactly.

## Brain Evidence

If scope touches Strategy, Runtime, Module, Service, Contract, Context,
SurrealDB, MCP tools, DB-backed memory, or Evidence, output this block before
any plan:

```text
## Brain Evidence
brain_source: surrealdb-local | in_memory | repo-only | unavailable
brain_status: used | partial | not-used | blocked
tools_or_queries:
  - <tool, command, query, or repo read>
records_or_results:
  - <record id, count, source, hash, or explicit none>
repo_crosscheck:
  - <file, path, symbol, commit, or issue>
impact_on_plan:
  - <what changed because of the evidence>
limitations:
  - <what is not proven>
```

No DB-backed Brain claim is allowed without real tool/query/record evidence.
GitHub live and repo evidence win over Brain or memory claims.

## Live-Checks

Run before changes:

```bash
git fetch origin --prune
git status -sb
git rev-parse HEAD
git rev-parse origin/main
git branch --show-current
gh issue view <issue-number> --json number,title,state,labels,body,comments
gh pr list --state open --limit 20
```

Add related issue/PR reads when the issue body or parent issue requires them.

Stop if:

- Repo is not on `main`.
- `main` does not equal `origin/main`.
- Target issue is closed.
- A matching open PR already exists.
- Required governance files are missing.
- Scope grows into a forbidden area.

## Arbeitsplan

1. `<small step 1>`
2. `<small step 2>`
3. `<small step 3>`

Keep the plan to the smallest correct slice. Do not add backward compatibility,
new tooling, or navigation wiring unless the issue explicitly asks for it.

## Validierung

Run the commands required by the issue, for example:

```bash
git diff --check
ruff check .
```

For docs/onboarding safety text, also run:

```bash
rg -n "Live-Go|Echtgeld-Go|LR bleibt NO-GO|Docs/UI sind Orientierung" <target-path>
```

## Issue-/PR-Regeln

- Run `cdb-pr-router` before Plan, Branch, Worktree or PR creation.
- Reuse the uniquely compatible PR; multiple candidates or lock ambiguity mean
  HOLD.
- Create a branch only after `CREATE_NEW_BATCH_PR` or `CREATE_DEDICATED_PR`.
- Commit only intended files.
- Require matching Issue-/PR-Level Locks before writing a Batch-PR.
- End a normal Slice with targeted Validation, Ledger update, Issue handoff and
  `DONE_SLICE_ADDED_TO_BATCH_PR`.
- Do not publish `cdb-local-ci`, merge or close the Issue for an intermediate
  Slice.
- Only a frozen `merge_candidate` enters Full Fast-CI, exact-SHA status and
  normal squash-merge gates. Never use `--admin` as a bypass.
- After a live-verified merge (`DONE_MERGED_CLOSED`), comment and close only
  if the merged diff satisfies acceptance. Do not re-push a remote branch
  deleted by `--delete-branch`.

## Safety

- LR bleibt NO-GO.
- Board stage `trade-capable` is not Live-Go.
- No Echtgeld-Go.
- No productive DB or memory writes without explicit separate approval.
- No credential values in logs, docs, issues, PRs, examples, or templates.
- `CURRENT_STATUS.md` is a ledger, not live truth.

## Output-Format

Return:

1. Brain Evidence Block
2. Bootloader-/Read-Order-Evidence
3. Live-Lage
4. Befund
5. Umgesetzte Schritte
6. Validierung
7. PR-/Issue-Links
8. Holds / Follow-up-Issues
9. Restunsicherheiten
10. Status
