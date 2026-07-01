# Agent Onboarding Readiness

Status: Onboarding surface (informational)
Scope: Onboarding orientation for new agents and new developers only

## Purpose

Agent Onboarding Readiness is an optional, read-only orientation check that tells
a new agent or a fresh clone whether this repo can be **cold-started**,
**understood**, and **validated for a small change** without guesswork.

It exists so that a first-time actor gets an honest picture of onboarding
friction. It is **informational only**: it is not a CI gate, not a merge gate,
and not an automatic blocker. The primary output is a short list of concrete
**Top fixes**, not a pass/fail verdict.

This surface complements the canonical onboarding entrypoint
([`../../tools/onboarding_orchestrator.py`](../../tools/onboarding_orchestrator.py))
and the visual start map
([`DEVELOPER_VISUAL_START_HERE.md`](DEVELOPER_VISUAL_START_HERE.md)). It does not
replace the bootloader ([`../../AGENTS.md`](../../AGENTS.md) ->
[`../../agents/AGENTS.md`](../../agents/AGENTS.md)) or any governance canon.

## What it checks

Four independent read-only reviews, each producing its own informational score
and its own problem list:

| Check | Question it answers |
|---|---|
| CLI compatibility scan | What is the deterministic, heuristic repo signal from the external scanner? |
| Startup review | Can a cold agent bootstrap and start the repo within a fixed time budget? |
| Validation review | Can an agent verify a small change without an unnecessarily heavy loop? |
| Docs reliability review | Do the documented setup and run paths reliably match reality? |

The reviews are read-only. They inspect repo surfaces (README, scripts,
toolchain files, test/lint paths, onboarding docs) and, where safe, try the most
likely path. Standard local prerequisites (for example Docker or a local
database) count as friction, not failure.

## Score model (informational)

The readiness score is a blended orientation number, never a gate:

- `Agent Compatibility Score`: final blended orientation score.
- `Deterministic Compatibility Score`: raw score from the external CLI scanner.
- `Startup Compatibility Score`, `Validation Loop Score`, `Docs Reliability Score`:
  the three behavioral checks.

Blend used for orientation only:

```text
workflow = round(mean(startup, validation, docs))
Agent Compatibility Score = round((deterministic * 0.7) + (workflow * 0.3))
```

Rules for reading the score:

- The score never blocks a commit, PR, merge, or onboarding step.
- The **Top fixes** list is the real deliverable; treat the number as context.
- Environment problems must not be scored as repo defects (see below).

## Optional external scanner

The deterministic layer uses the published `agent-compatibility` npm package. It
is **not** bundled or vendored into this repo, and this slice does **not** add
any npm dependency, `package.json`, or lockfile entry.

Run it on demand (optional):

```bash
npx -y agent-compatibility@0.1.7 .
npx -y agent-compatibility@0.1.7 --json .
```

The canonical pin is **`0.1.7`** (verified via `npm view agent-compatibility version`
at documentation time). Use this exact version for reproducible
`Deterministic Compatibility Score` results on the same repo commit.

### Version pinning

Pinning keeps onboarding readiness comparable and auditable:

- Same repo commit + same pinned scanner version → stable, comparable scores.
- Score changes are easier to attribute to repo changes vs. upstream tool drift.
- The scanner remains **optional**; pinning does not make it a CI gate or
  required check.

**Deliberate upgrade** (maintainer or docs slice, not automatic):

1. Run `npm view agent-compatibility version` (read-only; needs npm/network).
2. Update this file and the onboarding surface pointers that echo the command.
3. Open a focused docs PR; note the old and new pin in the PR body.
4. If npm/network is unavailable (`ENV_UNAVAILABLE`), do not guess a version —
   hold the pin update until a version can be verified.

Known limitations:

- The scanner is **heuristic**. It surfaces likely friction; it is not a full
  quality verdict on the codebase.
- If Node, npm, or network access is missing, the scan is `ENV_UNAVAILABLE`.
  This is a tool-environment gap and **must not** be reported as a repo defect
  or used to penalize the repository. Fall back to the three behavioral reviews
  and say plainly that the deterministic scan was unavailable.

## The four-review pack (described, docs-only)

This slice documents the review pack; it does **not** create new
`.cursor/agents/*` subagent files. If these reviews are run, they run read-only.

| Review | Role | Mode |
|---|---|---|
| `compatibility-scan-review` | Runs the external scanner and reports the raw deterministic score plus its main problems. | read-only |
| `startup-review` | Attempts a cold bootstrap and reports where the startup path breaks down. | read-only |
| `validation-review` | Judges whether a scoped validation loop exists for a small change. | read-only |
| `docs-reliability-review` | Follows the documented setup path and reports where docs drift from reality. | read-only |

Each review returns a plain-text report: one score line, a short summary, and a
`Problems` list. Deterministic and behavioral findings are folded into a single
prioritized `Top fixes` list. None of the reviews runs in the background and
none performs writes.

## Routing and boundary

Short routing for a new agent or a fresh clone:

```text
new agent / fresh clone  ->  onboarding entrypoint  ->  Agent Onboarding Readiness (optional)
```

Boundary versus the audit surface:

- **Onboarding (this surface)** is the *entry* experience: can I start, understand,
  and validate a small change? It is orientation for first-time actors.
- **[`cdb-repository-auditor`](../../.cursor/agents/cdb-repository-auditor.md)** is an
  *audit* role: a deeper, read-only repository audit for maintainers. It is not
  the onboarding entrypoint, and Agent Onboarding Readiness does not replace it.

## Safety boundaries

- Read-only by default: no file writes, no GitHub writes, no branch or PR
  creation, no runtime, Docker, DB, or MCP mutation, no secrets.
- Informational only: no CI gate is activated and no score blocks any step.
- LR remains NO-GO. SSOT: [`../live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md).
- Board stage `trade-capable` is Board/Stage context, not a Live-Go. See
  [`../runbooks/CONTROL_REGISTER.md`](../runbooks/CONTROL_REGISTER.md).
- No Echtgeld-Go.

## Non-goals

- No replacement of the onboarding orchestrator, the bootloader, or governance canon.
- No new active truth outside existing onboarding surfaces.
- No npm install, `package.json`, or lockfile change, and no scanner vendoring.
- No automatic scoring, blocking, or gating of any workflow.
