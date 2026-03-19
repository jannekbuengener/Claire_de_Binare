# Optional Agno Storage Adapter

Purpose: provide a very small, explicitly optional storage path for `memory` and
`knowledge` records without changing the repo's default Graphiti/Ollama memory
overlay.

## Scope

- Optional only: nothing in the default repo runtime imports or requires this.
- Limited to `memory` and `knowledge`.
- Filesystem-backed local helper for maintainers or external Agno-side tooling.
- Not a revival of the old `cdb_autoclaude` / AutoCloud work.

## Location

- Adapter: `infrastructure/scripts/agno_storage_adapter.py`
- Default storage root: `.cdb_local/agno_storage`
- Override: `AGNO_STORAGE_ROOT` or `--root`

## Usage

Initialize the storage layout:

```powershell
python infrastructure/scripts/agno_storage_adapter.py init
```

Write a memory record:

```powershell
python infrastructure/scripts/agno_storage_adapter.py put `
  --kind memory `
  --key daily-note `
  --content "Risk review completed"
```

Write a knowledge record from a file:

```powershell
python infrastructure/scripts/agno_storage_adapter.py put `
  --kind knowledge `
  --key redis-runbook `
  --content-file infrastructure/docs/QUICK_START.md
```

List stored records:

```powershell
python infrastructure/scripts/agno_storage_adapter.py list
```

Read one record:

```powershell
python infrastructure/scripts/agno_storage_adapter.py get `
  --kind memory `
  --key daily-note
```

## Boundaries

- No compose wiring.
- No Agno package dependency in the default path.
- No trading/runtime state.
- No support for arbitrary extra scopes beyond `memory` and `knowledge`.
