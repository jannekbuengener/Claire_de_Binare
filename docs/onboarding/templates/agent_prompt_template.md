# CDB Agent Prompt Template

Status: Template
Issue: #3238

Use this as a reusable prompt skeleton for CDB agent work. Replace placeholders
with task-specific values. Do not include credential values, private material,
or references to hidden ChatGPT/internal documents.

Docs/UI sind Orientierung, keine Autoritaet. LR bleibt NO-GO. No Live-Go. No
Echtgeld-Go.

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

- Check the target issue and matching open PRs for existing `LOCK:` comments
  before becoming the writer.
- Create a branch from current `main` only after the writer surface is clear.
- Commit only intended files.
- Open a PR with summary, changed files, validation, scope boundary,
  Safety/LR statement, and issue links.
- Post the exact `LOCK:` as the first PR comment on the associated PR before
  further push, PR update, or follow-up GitHub mutation; an issue-only status
  comment does not satisfy the PR lock requirement.
- Do not merge while required checks are red or scope is unclear.
- Comment the target issue with the PR link after PR creation.
- After merge, comment and close only if the merged diff satisfies acceptance.

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
