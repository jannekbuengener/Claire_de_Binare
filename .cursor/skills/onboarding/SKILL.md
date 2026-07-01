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
It routes first to `tools/onboarding_orchestrator.py`, which produces the
read-only CDB Onboarding status card before any optional next step.

**This is a session-skill / command-skill, not a subagent.**

## Default Invocation

```text
/onboarding
```

Equivalent default config:

```yaml
mode: default
writes: disabled
github_writes: disabled
lr: NO-GO
```

Expected initial output:

```text
=== CDB Onboarding ===
Status: PASS | SETUP_WARN | BLOCKED
State: STATUS_ONLY | SETUP_CONFIRMATION_PENDING | SETUP_REQUIRED | DRY_RUN_COMPLETE | BLOCKED
check_scope: onboarding_status_default | onboarding_status_check_only
allowed_next_actions: <machine-readable list>
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

1. **Primary route:** `python -m tools.onboarding_orchestrator`
2. **Bootloader:** `AGENTS.md` -> `agents/AGENTS.md` -> full Read Order.
3. **Context Brain Preflight:** `context_brain_attempted=true` required before repo reads.
4. **Live Checks (evidence-pflichtig):** `git fetch`, `gh issue view`, `gh pr list` — Ergebnisse dokumentieren. Ohne diese Kommandos: "GitHub-/Check-Live nicht geprüft."
5. **Optional next steps only after the status card:** role-specific tour,
   doctor/validator, or first-issue sandbox.
6. **Final Verdict:** CDB Onboarding status card with explicit state and allowed next actions.
   The two-option setup prompt appears only when `State: SETUP_CONFIRMATION_PENDING`.

## Agent Response Guardrails

### Response Contract (required fields)

- Report only `Status`, `State`, warnings, `allowed_next_actions`, `check_scope`, and `skipped_checks`.
- Include **Evidence-Abgrenzung**: was wurde geprüft, was nicht (siehe Wording Contract).
- Include **Safety-Grenzen**: LR NO-GO, kein Live-Go, kein Echtgeld-Go.

### Wording Contract (Evidence-Abgrenzung)

- **Ohne ausgeführte git/gh/check-Kommandos**:
  "Repo-/Canon-Prüfung durchgeführt; GitHub-/Check-Live nicht geprüft."
- **Mit Live-Kommandos**:
  "GitHub-/Repo-Live geprüft: <konkrete Kommandos und Ergebnis>."
- **CURRENT_STATUS.md** → Engineering-Ledger, nicht Live-Wahrheit.
- **LR-SSOT** → `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
- **trade-capable** → Board-/Stage-Kontext, kein Live-Go.
- **Invarianten** → "Zentrale Sicherheitsgrenzen erkannt."

### Verbotene Phrasen

- "Live-Wahrheit geprüft: Ja" (nur mit konkreten Kommandos erlaubt)
- "trade-capable ist deaktiviert" / "trade-capable ist aktiviert"
- "alle systemischen Invarianten erfasst" / "vollständige Live-Wahrheit geprüft"
- "CURRENT_STATUS.md ist Live-Wahrheit"
- "trade-capable erlaubt Live" / "trade-capable ist Live-Go"
- Freie Management-Zusammenfassung ohne Evidence-Abgrenzung

### Weitere Regeln

- Do not invent or renumber options.
- Do not offer setup execution after `--mode check-only`.
- If a doctor output is partial, say that it is a partial check.
- Board-Stage nie als Schalter oder Freigabe darstellen.
- Vollständigkeitsclaims nach Teilreads vermeiden.

## Referenced V2 Surfaces

| Surface | Purpose |
|---------|---------|
| `AGENTS.md` | Root pointer -> canonical agent registry |
| `agents/AGENTS.md` | Read Order, Brain Evidence Gate, Context Brain Preflight Gate |
| `agents/OPEN_CODE_AGENTS.md` | OpenCode shared contract, skill routing |
| `tools/onboarding_orchestrator.py` | **Single smart entrypoint** (status card + verdict) |
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
- **Do not start `cdb-session-start` or `onboarding_doctor` as the primary path for onboarding intent.**
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

## Run the Orchestrator

If the user says `/onboarding`, `onboarding`, `onboarding durchführen`, `mach onboarding`,
`fresh agent onboarding`, or equivalent, run:

Guided rehearsal intent (`onboarding rehearsal`, `guided rehearsal`, `rehearsal mode`,
`generalprobe`, `tu so als waere ich neuer entwickler`, `reisefuehrer`,
`nicht staendig fragen`, `realitaetsnah simulieren`, `onboarding als test-szenario`):
run `python -m tools.onboarding_simulation --mode guided-rehearsal --role developer`.
Guided rehearsal ist kein Setup-GO und kein Live-Go. Mutierende Schritte werden nur simuliert.
**Nach guided-rehearsal-Lauf:** KEINE Anschlussfrage, keine Einladung, kein "Wenn du willst...".
Keine nummerierten Nachfolgemenues (1/2/3).
Der letzte Ausgabe-Absatz MUSS ein Abschluss sein: Status, ein naechster empfohlener Schritt, STOP.

```bash
# Default: status card
python -m tools.onboarding_orchestrator

# JSON output
python -m tools.onboarding_orchestrator --format json

# Check-only mode
python -m tools.onboarding_orchestrator --mode check-only

# PowerShell front door
.\tools\cdb.ps1 onboarding
```

Do not create `.env`, initialize secrets, initialize context, write reports, create issues, or run Docker unless the user explicitly selects a next option after the status card.

Optional next steps after explicit user selection:

```bash
# Agent role, first-issue dry-run
python -m tools.onboarding_simulation

# Developer role
python -m tools.onboarding_simulation --role developer

# Check-only mode (no simulated PR)
python -m tools.onboarding_simulation --mode check-only

# JSON output
python -m tools.onboarding_simulation --format json

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

## External Documentation Lookup

When onboarding orientation mentions external tools or agent surfaces:
- Load `cdb-external-docs` for a complete list of external documentation references.
- Look up `docs/external-docs/index.md` for links to OpenCode, Cursor, Codex, Claude, Gemini docs.
- Relevant for new agents: Agent Surfaces section, GitHub Docs, MCP / Context docs.
- If internet is unavailable, reference local `docs/external-docs/index.md` and `AGENTS.md`.

## Agent Onboarding Readiness

Optional, informational readiness orientation for new agents and fresh clones.
Canonical description: [`../../../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md`](../../../docs/onboarding/AGENT_COMPATIBILITY_READINESS.md).

- Four read-only checks: CLI compatibility scan, startup review, validation review, docs reliability review.
- Score is informational only: no CI gate, no merge gate, no automatic blocker. The primary output is a prioritized Top-fixes list.
- The external scanner `npx -y agent-compatibility@0.1.7 .` is optional and not bundled; missing Node/npm/network is `ENV_UNAVAILABLE` and must not be scored as a repo defect.
- Boundaries unchanged: LR remains NO-GO, `trade-capable` is not Live-Go, no Echtgeld-Go.

## Non-Goals

- No Live-Go.
- No Echtgeld-Go.
- No runtime, Docker, trading, strategy, LR, productive DB, SurrealDB, or MCP mutation.
- No replacement of existing CDB subagents.
- No broad onboarding rewrite.
- No new active truth outside existing Onboarding V2 surfaces.
