# Optional Canonical Docs RAG Adapters

Purpose: provide a very small, explicitly optional RAG path for the canonical
documentation workspace
LangChain and LlamaIndex without changing the repo's default runtime or memory
overlay.

## Scope

- Canonical docs only.
- Optional only: nothing in the default repo runtime imports these adapters.
- No dependency on LangChain or LlamaIndex unless you explicitly request those
  adapter surfaces.
- Not a revival of the old `cdb_autoclaude` / AutoCloud work.

## Location

- Adapter: `infrastructure/scripts/docs_hub_rag_adapter.py`
- Default docs workspace detection:
  - local working repo canon (`docs/meta/WORKING_REPO_CANON.md`)
  - `--docs-hub`
  - `DOCS_HUB_PATH`
  - local `docs/archive/docs_hub_snapshot/` as legacy fallback
- Default source roots:
  - `docs/meta/WORKING_REPO_CANON.md` in the working repo
  - `DOCS_HUB_INDEX.md`, `index.yaml`, `cdb_docs_index.yaml` in the local archive snapshot
  - `knowledge/`
  - `agents/`
  - `meta/` or `docs/meta/`

## Usage

Preview JSONL-ready chunks without writing a file:

```powershell
python infrastructure/scripts/docs_hub_rag_adapter.py preview
```

Export the canonical docs corpus as JSONL:

```powershell
python infrastructure/scripts/docs_hub_rag_adapter.py `
  export-jsonl `
  --out .cdb_local\docs_hub_rag.jsonl
```

Probe the LangChain surface if the package is installed:

```powershell
python infrastructure/scripts/docs_hub_rag_adapter.py preview --adapter langchain
```

Probe the LlamaIndex surface if the package is installed:

```powershell
python infrastructure/scripts/docs_hub_rag_adapter.py preview --adapter llamaindex
```

## Boundaries

- No compose wiring.
- No automatic indexing job.
- No vector database.
- No effect on the default Graphiti/Ollama path.
- Only canonical-docs / RAG preparation and adapter surfaces.
