# Optional Canonical Docs RAG Adapters

Purpose: provide a small, explicitly optional RAG path for documentation in the
Claire de Binare repository without changing the default runtime or memory overlay.

## Scope

- Canonical docs only.
- Optional only: nothing in the default repo runtime imports these adapters.
- No dependency on LangChain or LlamaIndex unless you explicitly request those
  adapter surfaces.
- Not a revival of the old `cdb_autoclaude` / AutoCloud work.

## Location

- Adapter: `infrastructure/scripts/canonical_docs_rag_adapter.py`
- Repository detection:
  - local Claire de Binare repository canon (`docs/meta/REPOSITORY_CANON.md`)
  - optional explicit `--repository` path
- Default source roots:
  - `docs/meta/REPOSITORY_CANON.md` in the Claire de Binare repository
  - `knowledge/`
  - `agents/`
  - `docs/meta/`

## Usage

Preview JSONL-ready chunks without writing a file:

```powershell
python infrastructure/scripts/canonical_docs_rag_adapter.py preview
```

Export the canonical docs corpus as JSONL:

```powershell
python infrastructure/scripts/canonical_docs_rag_adapter.py `
  export-jsonl `
  --out .cdb_local\canonical_docs_rag.jsonl
```

Probe the LangChain surface if the package is installed:

```powershell
python infrastructure/scripts/canonical_docs_rag_adapter.py preview --adapter langchain
```

Probe the LlamaIndex surface if the package is installed:

```powershell
python infrastructure/scripts/canonical_docs_rag_adapter.py preview --adapter llamaindex
```

## Boundaries

- No compose wiring.
- No automatic indexing job.
- No vector database.
- No external repository or archive fallback.
- No effect on the default Graphiti/Ollama path.
- Only canonical-docs / RAG preparation and adapter surfaces.
