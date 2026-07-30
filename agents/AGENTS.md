# AGENTS

Status: Canonical
Scope: Claire de Binare repository

Diese Datei ist die kanonische Agenten-Registry fuer das Claire de Binare
repository `Claire_de_Binare`. Code, Infrastruktur und Dokumentation werden
ausschliesslich in diesem Repository gepflegt.

## Read Order

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `docs/meta/REPOSITORY_CANON.md`
6. `CURRENT_STATUS.md`
7. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
8. `docs/runbooks/CONTROL_REGISTER.md`
9. `agents/OPEN_CODE_AGENTS.md` — OpenCode Agent Shared Contract (Brain Evidence Gate fuer OpenCode Agents)

`knowledge/CDB_KNOWLEDGE_HUB.md` ist keine Pflichtlektuere mehr. Die Datei ist
eine historische Referenz fuer Dezember 2025 und darf nicht als aktueller
Status-, Decision- oder Handoff-Canon verwendet werden.

## Cursor Subagents

`.cursor/agents/` is the **Cursor IDE subagent surface** — operational helper
roles invoked as `/cdb-<name>`. This is **discovery and delegation only**; it
does not create a new authority tier. Session Lead, Human Gate, and
`knowledge/governance/CDB_AGENT_POLICY.md` remain authoritative.

| Item | Path |
| --- | --- |
| Pack README | `.cursor/agents/README_CDB_CURSOR_SUBAGENTS.md` |
| Shared contract | `.cursor/agents/_CDB_SUBAGENT_CONTRACT.md` |
| Subagent files | `.cursor/agents/cdb-*.md` |

**Parent agent enforcement:** The invoking parent must enforce Jannek GO,
session-start, Single-Writer LOCK (when issue-scoped), Brain Evidence (when
scope requires), and scope limits before any subagent write or GitHub mutation.
Subagents return evidence to the parent; they do not own delivery.

**Readonly policy:** only `cdb-ci-debugger`, `cdb-context-intelligence-engineer`,
`cdb-docs-canon-maintainer`, and `cdb-implementation-engineer` have
`readonly: false` in frontmatter — **technical capability only**, not
autonomous write permission. Effective writes require GO + session-start + LOCK
(when issue-scoped). All other subagents are read-only regardless of user phrasing.

**GitHub writes:** Subagent-related GitHub mutations (PR create/update, issue
comments, labels, review actions, merges, branch deletes, workflow dispatch) are
**`gh` CLI only**. MCP/GitHub API/connectors: read/inspect/dry-run unless a
separate explicit GO lifts a named action.

**Zone A vs Write-Zone:** Read-only discovery (repo reads, `gh view/list`) is
allowed without GO. Commits, pushes, and GitHub mutations are Write-Zone per
`CDB_AGENT_POLICY.md` §4. On conflict, **`CDB_AGENT_POLICY.md` wins** (see
shared contract § Zone A vs Write-Zone).

Invocation: `/cdb-<name>` (e.g. `/cdb-governance-gatekeeper`).

`/cdb-pr-steward` ist der read-only Routing-Helper. Er MUSS den kanonischen
`cdb-pr-router` ausführen und Evidence plus Routing-Entscheidung liefern, bevor
der Parent einen Branch, Worktree oder PR erzeugt. Er besitzt den PR nicht und
führt keine Writes aus.

Related surfaces (not subagents): `.cursor/skills/` (session skills),
`.opencode/skills/` (OpenCode), `.claude/skills/` (Claude Code), `.codex/cdb_skills/` (Codex).

Root surface matrix: [`docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md`](../docs/onboarding/AGENT_ROOT_SURFACE_MATRIX.md) —
versionierte Root-Flächen für `.claude/`, `.codex/`, `.cursor/`, `.gemini/`, `.opencode/`, `.vscode/`.

## Canonical Domains

- `agents/`
  - Gemeinsame Agenten-Entrypoints und lokale Agenten-Navigation.
- `.cursor/agents/`
  - Cursor subagent definitions (helper roles; shared contract required).
- `docs/skills/cdb-pr-router/SKILL.md`
  - Read-only PR-routing gate before Session-Plan and work-surface creation.
- `knowledge/governance/`
  - Kanonische Governance-, Policy- und Invariant-Dokumente.
- `knowledge/`
  - Aktive Knowledge-Dokumente und historische Referenzflächen; kein pauschaler Status-Canon.
- `knowledge/testing/`
  - Test-First Processing Contract, Testarten-Atlas, MockExchange-Muster,
    Skill-Valley-Upgrade-Plan. Einstieg: `knowledge/testing/README.md`.
- `.github/`
  - GitHub-Community-, Template- und Maintainer-Artefakte.
- `docs/`
  - Navigation, Runbooks, Archive und abgeleitete Views.

## Status Surfaces

- `CURRENT_STATUS.md`
  - Autoritative Quelle fuer aktuellen Repo-, Main-, Test- und Arbeitsstatus.
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
  - Autoritative Quelle fuer operativen Go/No-Go-Status und Echtgeld-Blocker.
- `docs/runbooks/CONTROL_REGISTER.md`
  - Autoritative Quelle fuer aktuellen Board-/Stage-Status und operativen Fokus im Control Board.
- `PROJECT_STATUS.md`, `knowledge/CURRENT_STATUS.md`
  - Historische Snapshots; keine aktuelle repo-weite oder operative Wahrheit.

## Current Project Reality

- `Claire_de_Binare` ist die einzige kanonische Quelle.
- Aktuelle Board-Stage ist `trade-capable` (ratifiziert 2026-04-08 via Issue `#1492`).
- Diese Board-Stage ist orthogonal zum LR-System; `LR-050` bleibt `NO-GO` und autorisiert kein Live-Kapital.

## Operating Rules

- `AGENTS.md` im Repo-Root ist nur ein Pointer auf diese Datei.
- Agenten und Tools muessen Pfade innerhalb von `Claire_de_Binare` verwenden.
- Stage-/Board-Aussagen und LR-Go/No-Go-Aussagen muessen strikt getrennt bleiben.
- Eine Board-Stage darf nie als implizite Live-Freigabe oder Strategie-Validierung interpretiert werden.
- Das lokale Archiv `docs/archive/` enthaelt historische Einzelartefakte und ist kein zweiter Canon.

## Context Brain Preflight Gate

Jeder Agenten-Prompt MUSS vor Repo-Reads einen **Context Brain Preflight** versuchen.
Repo-Fallback ist nur nach belegtem Fehlversuch erlaubt.

### Evidence-Felder (Pflicht)

```text
context_brain_attempted: true
context_brain_used: true | false
context_available: true | false
repo_fallback_used: true | false
repo_fallback_reason: none | unavailable | stale | contradictory | insufficient_evidence | missing_record | tool_blocked
context_tool_status: available | partial | blocked | absent
context_trust_level: high | medium | none
records_found: <count> | none
```

### Fallback-Klassifikationsmatrix

Welcher `repo_fallback_reason` bei welchem tatsächlichen Tool-Zustand korrekt ist:

| Tool-Status | Trust-Level | Records Found | Korrekter `repo_fallback_reason` |
|---|---|---|---|
| `available` | `high` | >=1 | `none` (kein Fallback nötig) |
| `available` | `none` | 0 | `insufficient_evidence` |
| `available` | `medium` | 0 | `missing_record` |
| `available` | `none` | >=1 (stale) | `stale` |
| `available` | `any` | widersprüchlich | `contradictory` |
| `partial` | `none` | 0 | `insufficient_evidence` |
| `blocked` | `none` | 0 | `tool_blocked` |
| `absent` | `none` | 0 | `unavailable` |

**Härteregel:** `repo_fallback_reason=unavailable` ist NUR erlaubt, wenn der
Context-Brain-Tool-Zugang wirklich fehlt (Tool nicht importierbar, nicht aufrufbar,
nicht im aktiven MCP-Surface). Ein verfügbares Tool, das kein Trust oder keine
Records liefert, ist **nicht** `unavailable`.

### Regeln

1. **Context Brain / Context-DB / MCP-Context ist der verpflichtende erste
   Aufloesungsversuch** fuer Bootloader-, Read-Order-, Governance- und Kontext-Briefing.
2. Repo ist nur Fallback, wenn Context Brain:
   - nicht verfuegbar ist (`unavailable`),
   - stale wirkt (`stale`),
   - widerspruechlich ist (`contradictory`),
   - keine belegbare Tool-/Query-/Record-Evidence liefert (`insufficient_evidence`),
   - die benoetigte Information dort nicht belastbar aufloesbar ist (`missing_record`),
   - oder die MCP-Tools blockiert sind (`tool_blocked`).
3. Bei `repo_fallback_used=true` MUSS der Agent den konkreten Grund dokumentieren.
4. Keine DB-backed Claims ohne Tool-/Query-/Record-Evidence.
5. Context Brain / MCP-Ergebnisse autorisieren **keine** automatischen Code-,
   Issue- oder Write-Aktionen; Human-GO erforderlich.
6. `context_brain_used=true` nur mit echter Tool-/Query-/Record-Evidence.
   Context Briefing, session memory oder caller-supplied metadata allein
   sind keine DB-backed Evidence.
7. Falsche Fallback-Klassifikation (z. B. `unavailable` bei verfügbarem Tool mit
   keinem Trust oder keinen Records) löst `HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED` aus und blockiert
   den weiteren Workflow bis zur Korrektur.
8. Lokale Context-Refresh-/Brain-Apply-Artefakte aus #3287-#3291 sind als
   repo-backed Brain-Evidence-Kandidaten zu prüfen, wenn Context Tools keine
   Records liefern.

## Brain Evidence Gate

For sessions whose scope includes **Strategy, Runtime, Module, Service, Contract,
Context, SurrealDB, MCP tools, DB-backed Memory, or Evidence**, every agent
MUST output the following block **before any plan**:

```text
## Brain Evidence
brain_source: surrealdb-local | in_memory | repo-only | unavailable
brain_status: used | partial | not-used | blocked
tools_or_queries:
  - <Tool/Command/Query>
records_or_results:
  - <Record-ID/Count/Source/Hash, falls vorhanden>
repo_crosscheck:
  - <Datei/Pfad/Symbol/Commit>
impact_on_plan:
  - <Was dadurch anders geplant wurde>
limitations:
  - <Was nicht bewiesen ist>
context_brain_attempted: true
context_brain_used: true | false
context_available: true | false
repo_fallback_used: true | false
repo_fallback_reason: none | unavailable | stale | contradictory | insufficient_evidence | missing_record | tool_blocked
context_tool_status: available | partial | blocked | absent
context_trust_level: high | medium | none
records_found: <count> | none
```

### Field Logic

- `brain_source=surrealdb-local`: Brain-Claims sind erlaubt, aber nur mit
  Tool-/Query-/Record-Evidence.
- `brain_source=in_memory`: Nur Fixture/Noop/In-Memory-Kontext; keine DB-backed
  Brain-Claims.
- `brain_source=repo-only`: Klar `brain-not-used` melden.
- `brain_source=unavailable`: Klar `blocked` oder `repo-only fallback` melden.
- `context_brain_attempted`: IMMER `true` — der Preflight-Versuch ist Pflicht.
- `context_brain_used`: `true` nur wenn echte Tool-/Query-/Record-Evidence vorliegt.
  Context Briefing, session memory oder caller-supplied metadata allein sind
  keine DB-backed Evidence.
- `repo_fallback_used`: `true` wenn nach Preflight auf Repo-Reads zurueckgefallen wurde.
- `context_available`: `true` nur bei `context_trust_level >= MEDIUM`. Bei `false`:
  kein nutzbarer Context; Agent muss auf GitHub/Repo-Fallback ausweichen oder HOLD.
- `repo_fallback_reason`: Exakter Grund fuer Repo-Fallback (Enum). Siehe
  Fallback-Klassifikationsmatrix oben: `unavailable` ist NUR bei echt fehlendem
  Tool-Zugang erlaubt, nicht bei keinem Trust oder keinen Records.
- `context_tool_status`: Tatsaechlicher Status des Context-Brain-Tools nach
  Preflight-Versuch.
- `context_trust_level`: Agenten-sichtbares Trust-Niveau. Nur `high` und `medium`
  sind nutzbar (usable context trust floor = MEDIUM). `none` bedeutet kein nutzbarer Context.
- `records_found`: Anzahl der gefundenen Records (0 bei `none`).

### Default posture (SSOT)

Kanonische Policy: [`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`](../knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md)
(`read_only_context_brain = conditional`, Issue #2775).

- Default bis echte Context-/DB-/MCP-Evidence: `brain_source=repo-only`,
  `brain_status=not-used`.
- `in_memory` / Noop: read-only Helper/Bundle erlaubt, **keine** DB-backed Claims.
- `surrealdb-local`: nur mit Adapter-/Tool-/Query-/Record-Evidence; caller-supplied
  `brain_source` / `metadata.source` sind keine Evidence (GitHub issue #2638).

### Source priority (when resolving context)

Higher wins; fail-closed when lower layers conflict:

1. **Live GitHub** — issues, PRs, checks, branches, comments
2. **Repo files** — governance, code, contracts, runbooks
3. **SurrealDB context package** — only with guarded adapter + record evidence
4. **Ledger / status snapshots** — e.g. `CURRENT_STATUS.md` (not live truth)
5. **Fallback** — explicit limitations; do not invent DB-backed claims

### Rules

- No plan may claim Memory/Evidence/Decision consideration without
  record/tool/query evidence. Structured claim envelope:
  [`docs/contracts/context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md`](../docs/contracts/context_tooling/DB_RECORD_EVIDENCE_CONTRACT.md)
  (validator: `tools/surrealdb/db_record_evidence_contract.py`, Issue #2851).
- Strategy/Runtime/Module work MUST distinguish `repo-only` from brain-backed.
- `context.briefing` / `briefing.session_context` is read-only working/session
  memory (`session_only=true`); not persistent DB memory; see
  `agents/OPEN_CODE_AGENTS.md` for handoff mapping.
- **Context trust floor:** `usable_context_trust_minimum = MEDIUM`.
  Nur `context_trust_level=HIGH` oder `MEDIUM` sind nutzbar.
  `none` = `context_available=false` — kein DB-backed Claim, kein "Repo-Brain used",
  Agent muss GitHub/Repo-Fallback oder HOLD. Interne Diagnose (LOW/BLOCKED) bleibt
  im Trust-Service-SSOT, ist aber keine operative Agentenoption.
- Post-#3449: `cdb_context_briefing` enrichment check ist Pflicht vor Brain-Claim.
  Ohne evidence_records/claim_records/decision_events/memory_records keine Brain-Nutzung.
  - `brain_source=repo-only` + `brain_status=not-used` bei leerem Briefing → `context_available=false`.
  - `brain_source=in_memory` bei Inline-Records; max `context_trust_level=MEDIUM`.
  - `context_trust_level=HIGH` nur mit `record_source=surrealdb-local` + Record-IDs + kein stale/disputed/blocking.
- Context Brain / MCP read results do **not** authorize automatic code changes,
  issue creation, or writes — parent agent and Jannek GO still required.
- `PERSIST_ALLOWED=False` and `MUTATION_ALLOWED=False` remain defaults on `main`;
  no productive SurrealDB writes from agent surfaces without separate explicit GO.
- `CURRENT_STATUS.md` is a ledger, not live truth.
- GitHub/Repo/Live evidence wins over Brain/CIS claims.
- Board-Stage `trade-capable` is not Live-Go.
- LR remains NO-GO.
- Falsche Fallback-Klassifikation (z. B. `unavailable` bei verfügbarem Tool mit
  keinem Trust oder keinen Records) löst `HOLD_BOOTLOADER_EVIDENCE_MISCLASSIFIED` aus. Der Workflow
  muss bis zur Korrektur blockiert bleiben.

## Repository Canon

Die verbindliche Canon-Matrix steht in `docs/meta/REPOSITORY_CANON.md`.
