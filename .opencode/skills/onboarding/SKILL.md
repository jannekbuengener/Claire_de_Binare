---
name: onboarding
description: >
  Canonical CDB onboarding slash command for agents, developers, and docs
  maintainers. Orchestrates bootloader reads, Context Brain Preflight, live
  truth checks, role-specific tour path, onboarding doctor/validator, and
  first-issue dry-run simulation. Read-only by default. No Live-Go, no
  Echtgeld-Go, no runtime/Docker/DB/MCP mutation. Safe for fresh clones and
  first-time agent sessions.
---

# /onboarding — Canonical CDB Onboarding Slash Skill

## Purpose

`/onboarding` is the canonical, simple slash entrypoint for CDB onboarding.
It orchestrates the completed Onboarding V2 surfaces into a single, safe,
deterministic flow without inventing new truth.

**This is a session-skill / command-skill, not a subagent.**

## Default Invocation

```text
/onboarding
```

Equivalent default config:

```yaml
role: agent
mode: first-issue-dry-run
writes: disabled
github_writes: disabled
lr: NO-GO
```

Expected initial output:

```text
ONBOARDING_START
mode: first-issue-dry-run
role: Agent
writes: disabled
lr: NO-GO
```

## Optional Forms

Optional aliases exist, but `/onboarding` remains canonical:

```text
/onboarding agent       # Agent onboarding path
/onboarding developer   # Developer onboarding path
/onboarding check       # Check-only mode (no simulated PR)
/onboarding first-issue # Full first-issue dry-run (default)
```

## Orchestrated Flow

1. **Bootloader:** `AGENTS.md` -> `agents/AGENTS.md` -> full Read Order.
2. **Context Brain Preflight:** `context_brain_attempted=true` required before repo reads.
3. **Live Truth:** GitHub live + repo live before ledger.
4. **Onboarding Tour:** Role-specific path via `tools/onboarding_tour.py`.
5. **Doctor / Validator:** `tools/onboarding_doctor.py` + `tools/validate_onboarding_docs.py`.
6. **First-Issue Sandbox:** Simulate docs-only issue-to-PR workflow via
   `tools/onboarding_simulation.py` or `docs/onboarding/first_issue_sandbox.md`.
7. **Final Verdict:** `READY_FOR_REAL_FIRST_ISSUE` or `HOLD_ONBOARDING_GAP`.

## Referenced V2 Surfaces

| Surface | Purpose |
|---------|---------|
| `AGENTS.md` | Root pointer -> canonical agent registry |
| `agents/AGENTS.md` | Read Order, Brain Evidence Gate, Context Brain Preflight Gate |
| `agents/OPEN_CODE_AGENTS.md` | OpenCode shared contract, skill routing |
| `tools/onboarding_tour.py` | Role-specific read-only tour |
| `tools/onboarding_doctor.py` | Local developer setup preflight |
| `tools/validate_onboarding_docs.py` | Active onboarding docs integrity validator |
| `tools/onboarding_simulation.py` | Deterministic simulation runner (new, issue #3273) |
| `docs/onboarding/first_issue_sandbox.md` | Guided first-issue rehearsal |
| `docs/onboarding/fresh_clone_rehearsal.md` | Read-only fresh-clone path |
| `docs/onboarding/DEVELOPER_VISUAL_START_HERE.md` | Visual onboarding map |
| `docs/onboarding/cdb_glossary.md` | CDB terminology reference |
| `docs/onboarding/repo_brain_context_intelligence.md` | Repo Brain first-use guide |
| `DEVELOPER_ONBOARDING.md` | Developer setup and first PR workflow |

## Safety Boundaries

- **LR remains NO-GO** — SSOT: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **Board stage `trade-capable` is not Live-Go**
- **No Echtgeld-Go**
- **Read-only by default** — no file writes, no GitHub writes, no branch creation,
  no PR creation, no runtime/Docker/DB/MCP mutation, no secrets.
- **No subagent replacement** — `/onboarding` is a slash-skill, not a subagent.
  CDB subagents (`/cdb-governance-gatekeeper`, etc.) remain unchanged.

## HOLD Conditions

The flow produces `HOLD_ONBOARDING_GAP` if:

- `git fetch` / `gh issue view` fail
- Worktree is dirty with unknown changes
- Local main is behind origin/main
- Target issue is not readable via `gh`
- Context Brain Preflight fails without valid fallback reason
- Bootloader files are missing or unreadable
- Required checks are red and not scope-fixable
- Diff shows scope growth beyond allowed surfaces
- Secrets or LR/Live boundaries are touched

## Run the Simulation Runner

The `/onboarding` skill delegates to the deterministic simulation runner:

```bash
# Default: agent role, first-issue-dry-run mode
python -m tools.onboarding_simulation

# Developer role
python -m tools.onboarding_simulation --role developer

# Check-only mode (no simulated PR)
python -m tools.onboarding_simulation --mode check-only

# JSON output
python -m tools.onboarding_simulation --format json

# PowerShell front door
.\tools\cdb.ps1 onboarding simulate
```

## Final Restart / Tool Reload Required

**After completing onboarding, a tool restart is mandatory.**

After successful onboarding:

1. Close your current tool (Cursor, OpenCode, Claude Code / Codex, Terminal/Shell/PowerShell, IDE)
2. Reopen it / start a new session
3. Only then continue with CDB work

**Why:** Env, PATH, MCP configuration, secrets, and agent/skill definitions
may have changed during onboarding. Old sessions can have stale:
- MCP/agent configuration cached in memory
- PATH/Env values that do not reflect new setup
- Cursor/OpenCode agents that have been added after session start
- CLI/terminal sessions using stale process state

Without a restart, onboarding appears complete but tooling runs with old context,
causing phantom errors.

This applies to: **Cursor, OpenCode, Claude Code / Codex, CLI/Terminal/Shell,
PowerShell, IDEs, and editor processes.**

## Non-Goals

- No Live-Go.
- No Echtgeld-Go.
- No runtime, Docker, trading, strategy, LR, productive DB, SurrealDB, or MCP mutation.
- No replacement of existing CDB subagents.
- No broad onboarding rewrite.
- No new active truth outside existing Onboarding V2 surfaces.
