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

## Local Archive

Historical evidence may exist under:

```text
Claire_de_Binare/docs/archive/
```

The archive is for provenance only and is not a second source of truth.

## What Lives Where

| Artifact type | Location |
|---|---|
| code and runtime assets | `core/`, `services/`, `infrastructure/`, `tests/` |
| agent registry and roles | `agents/` |
| governance and knowledge docs | `knowledge/` |
| templates, archives, runbooks, navigation | `docs/` |
| GitHub community and workflow files | `.github/` |

## Rules

- keep all productive docs in `Claire_de_Binare`
- keep historical imports under local archive paths
- keep secrets and machine-local state outside git-tracked canon
