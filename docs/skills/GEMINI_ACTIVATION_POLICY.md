# CDB Gemini Activation Policy (`.gemini/skills/`)

Status: active governance policy (docs-only; no activation)

Registry anchor: [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) §5, §15.

## Purpose

This document defines when `.gemini/skills/` is **not** used as a CDB domain-skill
mirror and which explicit gates are required if Gemini domain-skill activation is
ever requested later.

**This policy is documentation only.** It does not:

- activate, copy, or deploy CDB domain skills to `.gemini/`
- authorize runtime, Docker, DB, MCP, or API changes
- change LR status (remains **NO-GO**)
- imply Live-Go or Echtgeld authorization
- treat Board stage `trade-capable` as Live-Go

## Default posture (fail-closed)

`.gemini/skills/` is a **restricted surface**, not part of the standard CDB
domain-skill mirror set.

| Rule | Meaning |
| --- | --- |
| No automatic mirror | CDB domain/workflow skills in `docs/skills/` are **not** mirrored to `.gemini/` |
| No implicit activation | Presence of a skill on OpenCode/Cursor/Codex/Claude does **not** justify Gemini deployment |
| Uncertainty → stop | If surface intent, adapter type, or registry entry is unclear, **do not** deploy to `.gemini/` |
| Drift guard out of scope | `tools/validate_skill_surface_mirror.py` explicitly excludes `.gemini/skills/` — absence from the guard is **not** permission to add skills silently |

Normal CDB domain skills live on:

1. **Canon:** `docs/skills/<name>/SKILL.md`
2. **Active adapters:** OpenCode, Cursor, Codex, Claude (see Registry §4)

Gemini remains outside that mirror loop unless a separate, explicit activation
slice passes all gates below.

## Currently allowed Gemini surface

As of Registry §5 (2026-07-01), only these **curated** skills are deployable under
`.gemini/skills/`:

| Skill | Role on Gemini |
| --- | --- |
| `cdb-external-docs` | External documentation lookup for agent tasks |
| `surrealdb-python` | Curated SurrealDB Python guidance (not full canon mirror) |
| `surrealdb-vector` | Curated SurrealDB vector guidance |
| `surrealql` | Curated SurrealQL guidance |

Characteristics of the allowed set:

- **Onboarding / reference oriented** — supports Gemini bootloader and external-docs
  workflows, not full CDB session/trading/risk operator loops
- **Not body-mirrored** — `.gemini/skills/` copies are **not** `mirrored-from-canon`
  adapters; they may differ from `docs/skills/` canon by design
- **Not counted** in the 97-adapter mirror inventory (Registry §16)
- **Tracked separately** in Registry §5 as *eingeschränkt* (restricted)

Repo root surface (`.gemini/README.md`, `onboarding.md`, `settings.json`) handles
Gemini IDE configuration and onboarding routing — not domain-skill mirroring.

Related but distinct: local user Gemini runtime paths under `~/.gemini/` are
outside this repo policy and are not activated by repo changes.

## What is explicitly NOT on Gemini

The following must **not** be copied or activated on `.gemini/skills/` without
passing the activation gates:

- CDB session/workflow skills (`cdb-session-start`, `cdb-session-close`,
  `cdb-control-intake`, `cdb-operator`, `cdb-issue-to-session-plan`, …)
- CDB trading/risk/validation skills (`cdb-trading-core`, `cdb-risk-governance`,
  `cdb-shadow-validation`, `cdb-backtest-engine`, …)
- CDB governance/CI skills (`cdb-ci-cd-guard`, `cdb-contract-evidence-gatekeeper`,
  `cdb-drift-reconcile`, `cdb-docs-ops`, `cdb-github-api-ops`, …)
- Infrastructure/ops skills (`ctb-docker-stack`, `gh-fix-ci`, `gh-address-comments`)
- Any skill solely because it exists on another adapter surface

Rationale: Gemini in CDB is a **limited IDE surface** for onboarding and curated
reference skills. Full operator/session skill packs would duplicate governance
surfaces without a proven Gemini-specific need and would bypass the canon mirror
model.

## Future activation gates (all required)

If a future slice proposes adding a **CDB domain skill** (or new domain-skill
category) to `.gemini/skills/`, **every** gate below must pass before any file
lands on `.gemini/`:

### 1. Dedicated issue with explicit scope

- Title clearly states Gemini activation intent (not docs-only policy)
- Lists exact skill names and **non-goals** (no blanket mirror, no runtime GO)
- Deduped against open `[SKILLS]` / surface issues
- Human Plan-GO for the activation slice — policy documentation alone is insufficient

### 2. Surface decision recorded in Registry

- Update [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) §5 with:
  - skill name(s)
  - adapter type (`adapted`, `alias`, or exceptional `mirrored` with documented reason)
  - rationale why Gemini needs this skill and other surfaces are insufficient
- Anti-pattern check: Registry §Anti-Patterns must remain satisfied

### 3. Adapter contract defined

- Document whether the Gemini copy is:
  - **curated/adapted** (expected for Gemini today), or
  - **mirrored-from-canon** (exceptional; requires strong justification)
- Header block per Registry §7 if treated as a registered adapter; otherwise
  explicit *non-mirror curated* entry in §5
- No silent divergence from canon without `adapted` documentation

### 4. Skill-Meta review (when applicable)

- For skills with governance/evidence expectations, review
  [`SKILL_META_SCHEMA.md`](SKILL_META_SCHEMA.md) (`META.yaml`, `evals.json`)
- Meta artifacts stay **canon-only** unless a separate decision says otherwise
- Activation slice cites meta completeness or documented waiver

### 5. Drift validation plan

- Confirm impact on `tools/validate_skill_surface_mirror.py` (Gemini remains
  excluded unless validator scope is explicitly extended in its own slice)
- Run drift guard after any canon change that might affect related skills
- Document how Gemini curated copies will be reconciled (manual review cadence or
  future validator extension — not assumed)

### 6. Safety and authority boundaries

- Reconfirm LR **NO-GO**, no MCP mutations, no productive DB writes
- Gemini activation does not grant GitHub write, merge, or Live-Go authority
- `CDB_AGENT_POLICY.md` and session skills remain authoritative on all surfaces

### 7. Non-goals restated in PR

- PR body must include: Delivered, Validation, Non-goals, Safety Boundaries,
  Remaining uncertainty
- PR must **not** claim full surface parity with OpenCode/Cursor/Codex/Claude
  unless that is explicitly scoped and delivered

## Decision checklist (quick reference)

Use this before any `.gemini/skills/` domain-skill change:

```
[ ] Dedicated activation issue exists and is approved
[ ] Registry §5 updated with skill + adapter type + rationale
[ ] Adapter contract (curated vs mirrored) documented
[ ] Skill-Meta reviewed or waiver documented
[ ] Drift/validation plan documented; validate_skill_surface_mirror.py run if canon touched
[ ] Safety boundaries unchanged (LR NO-GO, no runtime/MCP/DB GO)
[ ] PR non-goals explicit; no blanket mirror implied
```

If any box is unchecked → **HOLD**; do not deploy to `.gemini/`.

## Relationship to other documents

| Document | Relationship |
| --- | --- |
| [`SKILL_SURFACE_REGISTRY.md`](SKILL_SURFACE_REGISTRY.md) | SSOT for surfaces; §5 lists restricted Gemini set |
| [`SKILL_META_SCHEMA.md`](SKILL_META_SCHEMA.md) | Meta contract for canon skills |
| [`CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md`](CDB_SURREALDB_SKILLS_RULES_ACTIVATION.md) | Historical SurrealDB slice; Gemini stayed inactive |
| [`.gemini/README.md`](../../.gemini/README.md) | Gemini root surface onboarding/config |
| [`GEMINI.md`](../../GEMINI.md) | Gemini bootloader (repo root) |
| [`docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md`](../onboarding/AGENT_ROOT_SURFACE_MATRIX.md) | Root surface allowlist |

## Anti-patterns

- Do **not** mirror all `docs/skills/` canon skills to `.gemini/` for "parity"
- Do **not** add domain skills because Gemini agents "might need them someday"
- Do **not** treat `.gemini/skills/` presence as registry approval without §5 entry
- Do **not** bypass Human-GO with a docs-only PR that copies skill bodies
- Do **not** conflate local `~/.gemini/skills` with repo `.gemini/skills/` policy

## Remaining gaps (intentional)

- No automated validator for `.gemini/skills/` curated copies vs canon
- No Gemini rule surface equivalent to `.cursor/rules/` (see SurrealDB activation doc)
- Full operator skill pack on Gemini is **undecided** and **not planned** by default

Follow-up slices may address validator hardening or Registry §15 `done` finalization
separately; they are out of scope for this policy document.
