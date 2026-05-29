# AGENTS

Status: Canonical
Scope: Working Repo

Diese Datei ist die kanonische Agenten-Registry fuer das Working Repo `Claire_de_Binare`.
Sie ersetzt die alte Split-Repo-Annahme, nach der Agenten- und Governance-Doku standardmaessig
in einem separaten externen Doku-Repo gesucht wurde.

## Read Order

1. `knowledge/governance/CDB_CONSTITUTION.md`
2. `knowledge/governance/CDB_GOVERNANCE.md`
3. `knowledge/governance/CDB_AGENT_POLICY.md`
4. `knowledge/governance/SYSTEM_INVARIANTS.md`
5. `knowledge/CDB_KNOWLEDGE_HUB.md`
6. `docs/meta/WORKING_REPO_CANON.md`
7. `CURRENT_STATUS.md`
8. `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
9. `docs/runbooks/CONTROL_REGISTER.md`
10. `agents/OPEN_CODE_AGENTS.md` — OpenCode Agent Shared Contract (Brain Evidence Gate fuer OpenCode Agents)

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

Related surfaces (not subagents): `.cursor/skills/` (session skills),
`.opencode/skills/` (OpenCode), `.codex/cdb_skills/` (Codex).

## Canonical Domains

- `agents/`
  - Gemeinsame Agenten-Entrypoints und lokale Agenten-Navigation.
- `.cursor/agents/`
  - Cursor subagent definitions (helper roles; shared contract required).
- `knowledge/governance/`
  - Kanonische Governance-, Policy- und Invariant-Dokumente.
- `knowledge/`
  - Kanonische Knowledge-Hub- und Decision-Hub-Dokumente.
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

- Working Repo bleibt der produktive Canon fuer Agenten-, Governance-, Knowledge- und Navigationsdoku.
- Aktuelle Board-Stage ist `trade-capable` (ratifiziert 2026-04-08 via Issue `#1492`).
- Diese Board-Stage ist orthogonal zum LR-System; `LR-050` bleibt `NO-GO` und autorisiert kein Live-Kapital.

## Operating Rules

- `AGENTS.md` im Repo-Root ist nur ein Pointer auf diese Datei.
- Agenten und Tools sollen standardmaessig lokale Pfade im Working Repo verwenden.
- Stage-/Board-Aussagen und LR-Go/No-Go-Aussagen muessen strikt getrennt bleiben.
- Eine Board-Stage darf nie als implizite Live-Freigabe oder Strategie-Validierung interpretiert werden.
- Das lokale Archiv `docs/archive/docs_hub_snapshot/` ist nur noch ein optionaler historischer Rueckgriff.
- Externe Docs-Repo-Pfade sind kein produktiver Default mehr.

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
```

### Field Logic

- `brain_source=surrealdb-local`: Brain-Claims sind erlaubt, aber nur mit
  Tool-/Query-/Record-Evidence.
- `brain_source=in_memory`: Nur Fixture/Noop/In-Memory-Kontext; keine DB-backed
  Brain-Claims.
- `brain_source=repo-only`: Klar `brain-not-used` melden.
- `brain_source=unavailable`: Klar `blocked` oder `repo-only fallback` melden.

### Rules

- No plan may claim Memory/Evidence/Decision consideration without
  record/tool/query evidence.
- Strategy/Runtime/Module work MUST distinguish `repo-only` from brain-backed.
- `CURRENT_STATUS.md` is a ledger, not live truth.
- GitHub/Repo/Live evidence wins over Brain/CIS claims.
- Board-Stage `trade-capable` is not Live-Go.
- LR remains NO-GO.

## Legacy Note

Die fruehere Docs-Hub-Struktur bleibt als Archiv referenzierbar, ist aber nicht mehr
die autoritative Quelle fuer laufende Arbeit in diesem Repo. Die aktuelle Canon-Matrix
steht in `docs/meta/WORKING_REPO_CANON.md`.
