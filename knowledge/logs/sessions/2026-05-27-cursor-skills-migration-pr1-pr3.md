# Session Log — 2026-05-27: Cursor Skills Migration (PR 1–3)

## Scope

OpenCode → Codex (`.codex/cdb_skills/`) → Cursor (`.cursor/skills/`) migration for all 17 CDB repo skills, delivered in three PRs. No runtime, trading, secrets, or LR changes.

Status surfaces remain separated:

- Repo/engineering ledger: `CURRENT_STATUS.md`
- Board stage: `docs/runbooks/CONTROL_REGISTER.md` — `trade-capable`
- Live-readiness: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — **NO-GO**

## Merged (repo-backed)

| PR | Wave | Merge commit | Content |
|----|------|--------------|---------|
| #2653 | PR 1 — Session foundation | `f3308489` | `.gitignore` hygiene (`.system/`, `Anthropic-Cybersecurity-Skills/`); 4 skills: `cdb-control-intake`, `cdb-session-start`, `cdb-session-close`, `cdb-issue-to-session-plan`; `CLAUDE.md` + `AGENTS.md` |
| #2654 | PR 2 — Governance & validation | `d0e90efe` | 4 skills + gatekeeper `references/` (3 files): `cdb-shadow-validation`, `cdb-contract-evidence-gatekeeper`, `cdb-drift-reconcile`, `cdb-ci-cd-guard`; `AGENTS.md` |
| #2655 | PR 3 — Domain & ops | `87459c47` | Final 9 skills: `cdb-trading-core`, `cdb-risk-governance`, `cdb-exchange-adapters`, `cdb-backtest-engine`, `cdb-docs-ops`, `cdb-operator`, `ctb-docker-stack`, `gh-address-comments`, `gh-fix-ci`; `AGENTS.md` complete Cursor paths |

**Coverage after #2655:** 17/17 OpenCode CDB skills in Codex + Cursor.

## Hygiene / lessons

- Local `.codex/cdb_skills/` contains ignored skill-pack drift (`jMerta/`, `skillforge/`, `mockexchange/`, nested `scripts/`/`assets/`/`references/`). **Never** use `Copy-Item -Recurse` from `.codex/` — source is **only** `.opencode/skills/<skill>/SKILL.md` (+ OpenCode `references/` when present).
- Pre-commit gate: `git status --short --ignored .codex/cdb_skills .cursor/skills`
- Codex paths need `git add -f` when local `.git/info/exclude` ignores `/.codex/`
- Cursor frontmatter: Wave 2+3 skills use `disable-model-invocation: true`; `cdb-session-start` / `cdb-session-close` remain without it (PR 1 rule)

## Validation evidence

- All three PRs: CI SUCCESS, policy-gate SUCCESS, mergeState CLEAN
- PR 3: 9/9 Codex SKILL.md byte-identical to OpenCode; 9/9 Cursor skills with `disable-model-invocation: true`
- 19 files per PR 3 diff; no secrets, no DB/runtime/trading scope

## Local-only (not committed)

- `infrastructure/config/surrealdb/context_query.local.yaml` — operator local config; stays untracked

## Operating rule (session outcome)

Adopted for future agents: **work on concrete PR/Issue number; exhaust diagnostics first, ask only at governance gates** (merge, risky push, issue-close, scope expansion, secret/live/trading/LR risk, red CI without safe fix path).

## Recommended next levers

1. Optional: Cursor rule or `AGENTS.md` snippet codifying autonomy level above
2. Optional: document local `.git/info/exclude` `/.codex/` pitfall for contributors
3. `codex-primary-runtime` remains in skill table without OpenCode port (not in 17-skill set)

## Session close metadata

- **Branch at close**: `main` @ `87459c47`
- **Working tree**: only untracked `context_query.local.yaml`
- **Status**: erledigt (migration PR 1–3 landed on main)
