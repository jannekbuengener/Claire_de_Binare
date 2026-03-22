# Working Repo Canon

Status: Canonical
Issue: #1140

## Decision

Das Working Repo `Claire_de_Binare` ist der produktive Standardpfad fuer aktive
Agenten-, Governance-, Knowledge-, Template- und Navigationsdokumentation.

Das alte Docs-Hub-Material ist nur noch:
- read-only Legacy-Archiv
- historische Importquelle
- kein produktiver Canon

## Canon Matrix

| Domain | Canonical Path |
| --- | --- |
| Agent registry | `agents/AGENTS.md` |
| Governance / policy | `knowledge/governance/` |
| Knowledge hub | `knowledge/` |
| GitHub templates / community docs | `.github/` |
| Navigation / runbooks / archive | `docs/` |
| Root entrypoints | `README.md`, `AGENTS.md`, `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md`, `CURRENT_STATUS.md`, `PROJECT_STATUS.md` |

## Status SSOT Rule

Status im Working Repo ist absichtlich rollenspezifisch und nicht in einer
einzigen generischen "Current Status"-Datei gebuendelt.

| Status class | Canonical source | Rule |
| --- | --- | --- |
| Operational / live-readiness status | `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` | Autoritative Quelle fuer aktuellen Go/No-Go-Status und operative Live-Readiness-Blocker |
| Working repo / engineering status | `CURRENT_STATUS.md` | Autoritative Quelle fuer aktuellen Repo-, Main-, Test- und aktiven Arbeitsstatus |
| Historical implementation / audit snapshots | `PROJECT_STATUS.md`, `knowledge/CURRENT_STATUS.md` | Nur punktuelle historische Snapshots; keine aktuelle operative oder repo-weite Wahrheit |
| Evidence / milestone / governance reports | z. B. `governance-audit-2026-01-15.md`, `CODEX_RUN_REPORT.md`, `docs/governance/status/` | Nachweis-, Audit- oder Milestone-Artefakte; nicht-kanonisch fuer aktuellen Gesamtstatus |

## Status Usage Rules

- `README.md` bleibt Front Door und darf Status nur zusammenfassen oder auf die
  jeweilige kanonische Quelle verweisen.
- Statusdateien mit historischem oder sekundaerem Charakter muessen ihren
  Status-Typ explizit kennzeichnen.
- Neue Reports, Pass-Reports oder Audit-Snapshots duerfen scope-lokale Findings
  dokumentieren, aber nicht als aktuelle repo-weite Wahrheit auftreten.

## Internal Redirect Map

| Legacy entrypoint | Local target |
| --- | --- |
| `AGENTS.md` | `agents/AGENTS.md` |
| `CDB_CONSTITUTION.md` | `knowledge/governance/CDB_CONSTITUTION.md` |
| `CDB_GOVERNANCE.md` | `knowledge/governance/CDB_GOVERNANCE.md` |
| `LEGACY_FILES.md` | `docs/archive/LEGACY_FILES.md` |
| `ORCHESTRATOR_PACK_144.md` | `docs/archive/ORCHESTRATOR_PACK_144.md` |
| `DOCS_MOVED_TO_DOCS_HUB.md` | this file |

## Repo Rules

- Navigation, guards and scripts must prefer local repo paths.
- References to the retired external docs repo are legacy-only and must not be the default path.
- Pointer files may exist at root for discoverability, but they must resolve internally.
- Status-bearing docs must declare whether they are `operational`, `working-repo`, `historical snapshot`, or `scoped evidence` whenever ambiguity is plausible.
- No secondary file may override or restate the current repo-wide operational verdict independently of the canonical live-readiness source.

## Legacy Archive

Local archive path:
- Path: `docs/archive/docs_hub_snapshot/`
- Use: historical comparison, audit provenance
- Do not treat it as the default edit target
