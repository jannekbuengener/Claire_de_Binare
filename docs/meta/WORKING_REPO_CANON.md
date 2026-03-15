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
| Root entrypoints | `README.md`, `AGENTS.md`, `CDB_CONSTITUTION.md`, `CDB_GOVERNANCE.md` |

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

## Legacy Archive

Local archive path:
- Path: `docs/archive/docs_hub_snapshot/`
- Use: historical comparison, audit provenance
- Do not treat it as the default edit target
