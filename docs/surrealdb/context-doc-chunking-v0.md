# CDB Context Intelligence — Documentation Chunking Model v0

**Status**: Draft (Issue #1988)
**Authority**: Issue #1988 / Parent #1985 / Epic #1976
**Dependencies**: #1980 (ontology), #1981 (core schema: doc_page, doc_section, doc_chunk)
**Guardrail**: trade-capable is NOT a Live-Readiness-Go; Live-Readiness remains NO-GO.

---

## 1. Purpose

This document defines the chunking model for documentation in the CDB Context
Intelligence System. It specifies how `doc_page`, `doc_section`, and `doc_chunk`
records relate, how Markdown documents are split into semantically meaningful
chunks, and how chunk context is preserved for downstream retrieval.

This is a **contract specification**, not an implementation. No runtime
chunking, no import pipeline, no SurrealDB writes are authorized.

---

## 2. Non-Goals

- No runtime chunking execution
- No import pipeline or SurrealDB write
- No chunking of archive, log, artifact, or excluded roots (per ingestion scope)
- No chunking of code files (code symbols use separate extraction)
- No chunking of binary files or non-text artifacts
- No vector embedding generation (deferred to retrieval layer)
- No runtime, compose, or service changes
- No trading state, no live/echtgeld go

---

## 3. Object Hierarchy

### 3.1 Three-Level Model

```
doc_page
  └── doc_section (1:N)
        └── doc_chunk (1:N)
```

| Object | Scope | Identity | Example |
|---|---|---|---|
| `doc_page` | One Markdown file | `page_id` | `docs/surrealdb/README.md` |
| `doc_section` | One heading-scoped section | `section_id` | "## 3. Object Hierarchy" in this document |
| `doc_chunk` | One token-bounded content block | `chunk_id` | A ~500-token paragraph group |

### 3.2 Object Boundaries

| Rule | Description |
|---|---|
| One file = one `doc_page` | No multi-file pages, no page splitting |
| One heading = one `doc_section` | Every `#` / `##` / `###` etc. creates a section |
| Sections are hierarchical | `heading_path` captures the full path: `["## 1. Purpose"]` |
| Chunks split sections | Long sections create multiple chunks; short sections may share chunks |
| Code blocks are NOT separate chunks | Inline code blocks stay with their section context |

### 3.3 Section Hierarchy

The `heading_path` array captures the full breadcrumb:

```
# Title                    → heading_path: ["Title"]
## Section A               → heading_path: ["Title", "Section A"]
### Subsection A.1          → heading_path: ["Title", "Section A", "Subsection A.1"]
```

The `heading` field stores the current level's heading text without `#` markers:
```
heading: "Subsection A.1"    (not "### Subsection A.1")
```

The `section_index` field stores the 0-based position within the parent:

```
page
├── section_index: 0  →  "## First Section"
├── section_index: 1  →  "## Second Section"
└── section_index: 2  →  "## Third Section"
```

---

## 4. Chunking Rules

### 4.1 Chunk Size Parameters

| Parameter | Default | Description |
|---|---|---|
| `chunk_max_tokens` | 500 | Soft maximum tokens per chunk |
| `chunk_min_tokens` | 50 | Minimum tokens to form a standalone chunk |
| `chunk_overlap_tokens` | 0 | No overlap in v0 (simpler, deterministic) |
| `heading_min_level` | 1 | Minimum heading level to split on (# = 1) |
| `heading_max_level` | 6 | Maximum heading level to split on (###### = 6) |

### 4.2 Chunk Splitting Algorithm

```
1. Parse document into section tree (headings → sections)
2. For each section:
   a. If section token count ≤ chunk_max_tokens:
      → Create one chunk with full section content
   b. If section token count > chunk_max_tokens:
      → Split at paragraph boundaries (double newline)
      → Each chunk ≤ chunk_max_tokens
      → Last chunk may be smaller but ≥ chunk_min_tokens
      → If last chunk < chunk_min_tokens, merge into previous chunk
3. Chunks from a section are sequential (chunk_index: 0, 1, 2, ...)
```

### 4.3 Token Counting

Tokens are estimated, not precisely counted. The estimator uses a simple
word-based heuristic:

```
tokens_estimate = ceil(len(content.split()) * 1.3)
```

This is a conservative over-estimate that accounts for punctuation and special
characters. It does NOT use a real tokenizer (no LLM dependency in v0).

### 4.4 Code Block Handling

Code blocks (``` ``` ```) within Markdown are NOT split:

| Rule | Description |
|---|---|
| Code blocks stay intact | A code block is never split across chunks |
| Code block in header | Code blocks before the first heading belong to an implicit preamble section |
| Code block with language | Language annotation is preserved in chunk content |
| Code block exceeds max | If a single code block > `chunk_max_tokens`, it gets its own chunk regardless of limit |

### 4.5 Table Handling

Markdown tables are treated as atomic units:

| Rule | Description |
|---|---|
| Tables stay intact | A table is never split across chunks |
| Small table | Table < chunk_max → included in current chunk |
| Large table | Table > chunk_max → gets its own chunk |
| Table with surrounding text | Table is chunked with preceding text if total ≤ chunk_max |

### 4.6 List Handling

| Rule | Description |
|---|---|
| Ordered/unordered lists | Treated as paragraphs; split at list item boundaries |
| Nested lists | Entire nested list stays in one chunk if possible |
| Long lists | Individual top-level items may be split into separate chunks |

### 4.7 YAML Frontmatter Handling

| Rule | Description |
|---|---|
| Frontmatter is NOT chunk content | Stripped before chunking |
| Frontmatter metadata → doc_page fields | `title` mapped from frontmatter `title` if present |
| `---` delimiters | YAML between `---` markers at file start only |
| No frontmatter | No special handling; entire file treated as content |

### 4.8 Inline Content Handling

| Element | Behavior |
|---|---|
| **Bold** / *Italic* | Kept as-is in chunk content |
| `inline code` | Kept as-is |
| [Links](url) | Kept as-is (`[text](url)` format) |
| ![Images](url) | Kept as reference; alt text preserved |
| HTML comments (`<!-- -->`) | Stripped before chunking |
| Blockquotes (`>`) | Treated as regular paragraphs |
| Horizontal rules (`---`, `***`) | Treated as paragraph separators |

---

## 5. Chunk Identity and Cross-Referencing

### 5.1 Chunk Identification

```
chunk_id = sha256(page_id + ":" + section_id + ":" + chunk_index)
```

This ensures:
- Deterministic chunk_id (same page + section + index = same id)
- Reproducible across rebuilds
- No dependency on content (content may change, chunk_id stays)

### 5.2 Chunk References

| Field | Target | Description |
|---|---|---|
| `page_ref` | `doc_page` | Back-reference to the page |
| `section_ref` | `doc_section` | Back-reference to the section |
| `chunk_index` | — | Sequential position within the section |

### 5.3 Source Consistency

| Field | Purpose |
|---|---|
| `source_hash` | Hash of the source page file (matches `doc_page.source_hash`) |
| `content_hash` | Hash of the chunk's text content (for change detection) |

On re-ingestion:
```
if chunk.content_hash != stored.content_hash:
    → chunk content changed
    → update chunk, increment source_hash
    → old chunks NOT deleted (immutable history)
```

---

## 6. Stale Chunk Rules

### 6.1 Staleness Detection

A chunk is stale when:

| Condition | Detection |
|---|---|
| Source page hash changed | `chunk.source_hash != doc_page.source_hash` |
| Chunk content changed | `chunk.content_hash` differs from recomputed |
| Section removed | `section_id` no longer exists in current parse |
| Page deleted | `page_id` no longer exists in current repo |

### 6.2 Staleness Handling

| Action | Description |
|---|---|
| Mark stale | Create `stale_context` record (per #1981 schema) |
| Do NOT delete | Chunks are immutable history |
| Flag for retrieval | Retrieval layer can filter stale chunks |
| Link old→new | If a replacement page/section exists, link via `supersedes` |

---

## 7. CDB-Specific Terms

The following terms from the CDB Ontology v0 (`context-ontology-v0.yaml`) are
recognized during chunking and flagged for special retrieval treatment:

| Ontology Concept | Detection Pattern | Example |
|---|---|---|
| `Human GO` | `Human-GO`, `Human GO`, `human_go` | "requires Human-GO" |
| `No-Go` | `NO-GO`, `No-Go`, `no-go` | "Live-Readiness remains NO-GO" |
| `Governance Gate` | `Governance Gate`, `governance_gate` | "passing the governance gate" |
| `Decision Contract` | `Decision Contract`, `decision_contract` | "per decision contract v1" |
| `Evidence Fabric` | `Evidence Fabric`, `evidence_fabric` | "query the evidence fabric" |
| `Live-Readiness` | `Live-Readiness`, `LR-` | "LR-AUDIT-STATUS" |
| `Scope Drift` | `Scope Drift`, `scope_drift` | "scope drift detected" |
| `Stop Condition` | `STOP`, `Stop Condition` | "STOP if check fails" |

Detection does NOT modify chunk content. Detected terms are stored as metadata
for retrieval boosting, not as content annotations.

---

## 8. Ingested Document Scope

Chunking applies only to documents within allowed roots as defined in
`docs/surrealdb/context-ingestion-scope.md`.

| Root | Chunking | Notes |
|---|---|---|
| `docs/` | Yes | Excluding `docs/archive/` |
| `knowledge/` | Yes | Governance and operating docs |
| `agents/` | Yes | Agent registry and rules |
| `README.md` (root) | Yes | Repo entry points |
| `docs/archive/` | No | Excluded (historical, not canonical) |
| Core/services/tests | No | Not documentation (code extraction only) |
| Logs/artifacts | No | Excluded (runtime artifacts) |

### Conditional Chunking

Files in conditional roots (`core/`, `services/`, `tests/`,
`infrastructure/compose/`) are NOT chunked by default. Only files under explicit
allowed documentation roots are chunked.

---

## 9. Output Structure

Each chunking run produces structured output aligned with the schema:

```json
{
  "doc_page": {
    "page_id": "sha256(path@commit)",
    "source_path": "docs/surrealdb/README.md",
    "source_commit": "abc123",
    "source_hash": "sha256:...",
    "title": "SurrealDB Documentation",
    "doc_format": "markdown"
  },
  "doc_sections": [
    {
      "section_id": "sha256(page_id:section_index)",
      "page_ref": "doc_page:<page_id>",
      "heading": "Purpose",
      "heading_path": ["SurrealDB Documentation", "Purpose"],
      "section_index": 0,
      "span_start_line": 3,
      "span_end_line": 15
    }
  ],
  "doc_chunks": [
    {
      "chunk_id": "sha256(page_id:section_id:0)",
      "page_ref": "doc_page:<page_id>",
      "section_ref": "doc_section:<section_id>",
      "chunk_index": 0,
      "content": "Full text of the chunk...",
      "content_hash": "sha256:...",
      "tokens_estimate": 320,
      "source_hash": "sha256:..."
    }
  ]
}
```

---

## 10. Example Walkthrough

### 10.1 Input Document

```markdown
---
title: Test Document
---

# Overview

This is the overview section. It describes the system at a high level.

## Details

Here are the implementation details. This section includes:

- Item one
- Item two
- Item three

### Sub-details

More granular information about specific components.

## API Reference

The API provides the following endpoints:

| Endpoint | Method | Description |
|---|---|---|
| `/status` | GET | Health check |
| `/trade` | POST | Place trade |
```

### 10.2 Parse Result

```
doc_page
  page_id: sha256("docs/test.md@abc123")
  title: "Test Document"  (from frontmatter)
  
doc_section 0: heading="Overview", heading_path=["Test Document", "Overview"]
doc_section 1: heading="Details", heading_path=["Test Document", "Overview", "Details"]
doc_section 2: heading="Sub-details", heading_path=["Test Document", "Overview", "Details", "Sub-details"]
doc_section 3: heading="API Reference", heading_path=["Test Document", "API Reference"]

doc_chunk for section 0:
  chunk_index: 0, tokens_estimate: ~50
  content: "This is the overview section. It describes the system at a high level."

doc_chunk for section 1+2:
  chunk_index: 0, tokens_estimate: ~80
  content: "Here are the implementation details. This section includes:\n\n- Item one\n- Item two\n- Item three\n\n### Sub-details\n\nMore granular information about specific components."

doc_chunk for section 3:
  chunk_index: 0, tokens_estimate: ~60
  content: "The API provides the following endpoints:\n\n| Endpoint | Method | Description |\n|---|---|---|\n| `/status` | GET | Health check |\n| `/trade` | POST | Place trade |"
```

Note: The long example is for illustration only. No actual trading-related
content would be chunked (per ingestion scope guardrails).

---

## 11. Guardrails

- No chunking of files in excluded roots (`docs/archive/`, `logs/`, `artifacts/`)
- No chunking of secrets or sensitive metadata
- `sensitive_metadata` classified files use metadata-only extraction, not full chunking
- `forbidden` classified files are excluded entirely (per ingestion scope)
- No chunking of binary or non-text files
- No runtime chunking execution authorized by this document
- Chunk content MUST NOT contain secrets
- All chunking is deterministic and replay-verifiable

---

## 12. Validation Checklist

- [ ] Three-level hierarchy (page → section → chunk) is defined
- [ ] Chunk size parameters are specified (max 500, min 50, overlap 0)
- [ ] Splitting algorithm is deterministic
- [ ] Token estimation heuristic is documented
- [ ] Code block handling rules are specified
- [ ] Table handling rules are specified
- [ ] Frontmatter handling rules are specified
- [ ] Inline content handling is documented
- [ ] Chunk identity formula is deterministic
- [ ] Stale chunk detection and handling is specified
- [ ] CDB-specific term recognition list is defined
- [ ] Ingested document scope is aligned with ingestion-scope.md
- [ ] Output structure matches schema fields
- [ ] No secrets in scope
- [ ] No chunking of excluded roots
- [ ] No runtime execution authorized

---

## Provenance / Sources

- **Issue**: #1988
- **Parent**: #1985
- **Epic**: #1976
- **Dependencies**: #1980 (ontology), #1981 (core schema)
- **Referenced documents**:
  - `infrastructure/surrealdb/context_intelligence_v0.surql` (doc_page, doc_section, doc_chunk schemas)
  - `docs/surrealdb/context-ontology-v0.yaml` (CDB concepts for term recognition)
  - `docs/surrealdb/context-ingestion-scope.md` (allowed/excluded roots)
  - `docs/surrealdb/context-artifact-identity-v0.md` (hash rules, idempotency)
  - `docs/surrealdb/context-relationship-vocabulary-v0.md` (supersedes, contains)
  - `docs/surrealdb/context-intelligence-namespace-layout.md` (field conventions)
