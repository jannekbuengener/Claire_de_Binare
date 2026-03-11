# Workspace Layout - Consolidated Canonical Structure

Status: canonical
Last Updated: 2026-03-11

## Goal

The workspace no longer depends on a separate docs repository. The productive
system is self-contained inside `Claire_de_Binare`.

## Productive Layout

```text
D:\Dev\Workspaces\Repos\
└── Claire_de_Binare\
    ├── core/
    ├── services/
    ├── infrastructure/
    ├── tests/
    ├── agents/
    ├── knowledge/
    ├── docs/
    └── .github/
```

## Optional Local Archive

Historical Docs-Hub material may exist only as local archive content inside the
working repo:

```text
Claire_de_Binare/docs/archive/docs_hub_snapshot/
```

That archive is for provenance and historical lookup only. It is not a second
source of truth.

## What Lives Where

| Artifact type | Location |
|---|---|
| code and runtime assets | `core/`, `services/`, `infrastructure/`, `tests/` |
| agent registry and roles | `agents/` |
| governance and knowledge docs | `knowledge/` |
| templates, archives, runbooks, navigation | `docs/` |
| GitHub community and workflow files | `.github/` |

## Rules

- do not rely on an external docs repo as a sibling dependency
- keep productive docs in local working-repo paths
- keep historical imports under local archive paths
- keep secrets and machine-local state outside git-tracked canon
