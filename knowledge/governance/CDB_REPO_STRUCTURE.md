---
relations:
  role: policy
  domain: governance
  upstream:
    - knowledge/governance/CDB_CONSTITUTION.md
    - knowledge/governance/CDB_GOVERNANCE.md
  downstream:
    - knowledge/CDB_KNOWLEDGE_HUB.md
    - docs/meta/WORKING_REPO_CANON.md
  status: canonical
  tags: [repo, structure, canonical, consolidated]
---
# CDB_REPO_STRUCTURE

Version: 2.0
Status: canonical

## 1. Goal

Define the binding structure of the consolidated `Claire_de_Binare` repository.
Runtime assets and canonical docs now live together in one repo to avoid
split-brain and broken navigation.

## 2. Active Repository Model

There is one productive repository:

- `Claire_de_Binare` for code, infrastructure, tests, agents, governance,
  knowledge, navigation docs, templates, and evidence

The former external docs repository is retired as a productive source.
Historical material may survive only as local archive content inside this
repository.

## 3. Active Top-Level Zones

| Path | Purpose |
|---|---|
| `core/`, `services/`, `infrastructure/`, `tests/` | runtime and verification |
| `agents/` | agent registry, roles, and supporting docs |
| `knowledge/` | knowledge hub, governance-adjacent docs, evidence, roadmap |
| `docs/` | navigation, templates, archives, runbooks, derived views |
| `.github/` | issue templates, community docs, workflows |
| selected root files | concise entrypoints only |

## 4. Archive Rule

Historical Docs-Hub material belongs under local archive paths such as:

- `docs/archive/docs_hub_snapshot/`
- `docs/archive/github/`

Archive content is not canonical by default and must not be used as the
standard navigation path.

## 5. Working Constraints

- no active default path may require an external docs repository
- do not reintroduce a second canonical repo
- when merging duplicates, prefer local active paths and archive the rest
- keep root entrypoints concise; long-form material belongs in `knowledge/` or `docs/`
