# CDB Context Intelligence — Artifact Identity and Deterministic Hashing v0

**Status**: Draft (Issue #1987)
**Authority**: Issue #1987 / Parent #1985 / Epic #1976
**Dependencies**: #1981 (core schema, `repo_artifact` table)
**Guardrail**: trade-capable is NOT a Live-Readiness-Go; Live-Readiness remains NO-GO.

---

## 1. Purpose

This document defines deterministic artifact identity and hashing rules for the
CDB Context Intelligence System. It specifies how `repo_artifact` records are
identified, how content hashes are computed, and how identity is preserved
across renames, rebuilds, and re-ingestion.

This is a **contract specification**, not an implementation. No runtime hashing,
no import pipeline, no SurrealDB writes are authorized by this document.

---

## 2. Non-Goals

- No runtime hashing execution
- No import pipeline or SurrealDB write
- No hashing of secrets or sensitive files (excluded roots per ingestion scope)
- No modification of existing ledger/mirror importers
- No runtime, compose, or service changes
- No trading state, no live/echtgeld go

---

## 3. Artifact Identity Model

### 3.1 Record Identity

Each `repo_artifact` record carries two identity layers:

| Layer | Field | Format | Example |
|---|---|---|---|
| SurrealDB Record ID | implicit | `repo_artifact:<id>` | `repo_artifact:abc123` |
| Stable ID | `artifact_id` | `sha256(normalize(source_path) + "@" + source_commit)` | `a1b2c3...` |

The `artifact_id` is computed as:

```
artifact_id = sha256(normalize(source_path) + "@" + source_commit)
```

This ensures:
- Same file at same commit = same `artifact_id` (deterministic)
- Different file or different commit = different `artifact_id`
- Path changes (rename/move) = different `artifact_id` (tracked via cross-reference)

`normalize(source_path)` MUST:

- use repo-root-relative path
- use forward slashes (`/`)
- preserve case as-is
- strip leading `./`
- strip trailing `/`
- reject path traversal segments (`..`)
- reject platform-specific backslashes

`source_commit` MUST be the full lowercase 40-character Git SHA-1 commit
hash, equivalent to `git rev-parse HEAD` without `--short`. Abbreviated
SHA values (e.g. `abc123` in examples) are display-only and MUST NOT be
used in `artifact_id` computation.

### 3.2 Identity Stability Guarantees

| Operation | Behavior |
|---|---|
| Re-ingestion (same commit, same path) | Same `artifact_id`, update `observed_at` |
| Content change (new commit) | New `artifact_id` (new source_commit in hash) |
| Path rename (same content, same commit) | New `artifact_id` (path changed) |
| Path rename (new commit, no content change) | New `artifact_id`, `source_hash` unchanged |
| Content deleted from repo | No new record; existing record persists with `freshness: deleted` |

### 3.3 Cross-Reference for Renames

When a file is renamed, the old `artifact_id` and new `artifact_id` share the
same `source_hash` but differ in `source_path`. Detection:

```
rename_detected =
    (old.source_hash == new.source_hash)
    AND (old.source_path != new.source_path)
    AND (old.source_commit != new.source_commit)
```

Same `source_hash` + different path + same commit = **duplicate**, not rename
(see Section 7.1). Cross-commit boundary distinguishes rename tracking from
duplicate detection.

The old and new records are linked via `supersedes` / `superseded_by` (per
#1982 vocabulary), matching Section 7.2.

---

## 4. Hash Rules

### 4.1 Hash Types

| Hash | Algorithm | Input | Purpose |
|---|---|---|---|
| `source_hash` | SHA-256 | Raw file bytes from git blob | Detect any byte-level change |
| `normalized_hash` | SHA-256 | Normalized content (Section 5) | Cross-platform identity (ignore line ending diffs) |
| `content_hash` | SHA-256 | Content after metadata stripping | Compare semantic content across formats |

The `source_hash` field in `repo_artifact` stores the raw hash. Additional hash
types may be stored or computed on demand.

### 4.2 Integrity Algorithm

The `integrity_algo` field on `repo_artifact` documents which algorithm produced
`source_hash`. For v0:

```
integrity_algo = "sha256"
```

Future versions may extend to `sha512`, `blake3`, or other algorithms.

### 4.3 Hash Computation

```
source_hash = sha256(git_cat_file_blob(source_path, source_commit))
```

The hash is computed from the **git blob** content, not the working tree file.
This ensures the hash matches the committed version, not local modifications.

### 4.4 Hash Verification

During re-ingestion or validation:

```
current_hash = sha256(git_cat_file_blob(source_path, source_commit))
if current_hash != stored.source_hash:
    → drift detected
    → mark freshness: stale
    → create stale_context record
```

---

## 5. Normalization Rules

Normalization transforms file content into a canonical form before computing
`normalized_hash`. This eliminates non-semantic differences (line endings,
trailing whitespace) that don't affect content meaning.

### 5.1 Normalization Pipeline

| Step | Operation | Example |
|---|---|---|
| 1 | Decode to UTF-8 | Bytes → Unicode |
| 2 | CRLF → LF | `\r\n` → `\n` |
| 3 | Strip trailing whitespace | `"line   "` → `"line"` |
| 4 | Normalize final newline | Ensure exactly one trailing `\n` |
| 5 | Encode to UTF-8 bytes | Unicode → Bytes |

### 5.2 Encoding Handling

| Encoding | Behavior |
|---|---|
| UTF-8 | Direct (no conversion) |
| UTF-8 BOM | Strip BOM, treat as UTF-8 |
| UTF-16 LE/BE | Convert to UTF-8 |
| Latin-1 / Windows-1252 | Convert to UTF-8 |
| Unknown / binary | Compute `source_hash` from raw git blob bytes; mark `mime_type` accordingly; skip `normalized_hash` and `content_hash` |

### 5.3 Frontmatter Handling

YAML frontmatter (delimited by `---`) is treated as metadata:

```
normalized_content = content_without_frontmatter
metadata = parse_frontmatter_as_yaml()
```

- `source_hash` includes frontmatter (full file integrity)
- `content_hash` excludes frontmatter (semantic content only)
- Frontmatter-only changes (title, date, tags) produce different `source_hash` but same `content_hash`

### 5.4 File-Specific Normalization

| File Type | Additional Rules |
|---|---|
| Markdown (`.md`) | Strip HTML comments (`<!-- -->`) before content_hash |
| YAML (`.yaml`, `.yml`) | Parse and re-serialize (canonical YAML) |
| JSON (`.json`) | Parse and re-serialize (sorted keys, no whitespace) |
| Python (`.py`) | Strip shebang, encoding declaration, docstring for content_hash |
| SurrealQL (`.surql`) | Strip `--` comments for content_hash |
| TOML (`.toml`) | Raw bytes only; no semantic normalization in v0 |
| Other | Raw bytes only; `source_hash` only |

---

## 6. Artifact Type Classification

The `artifact_type` field on `repo_artifact` classifies the artifact for
downstream processing.

### 6.1 Type Taxonomy

| Type | Description | Example |
|---|---|---|
| `source_code` | Executable code file | `services/risk/service.py` |
| `documentation` | Markdown documentation | `docs/surrealdb/README.md` |
| `configuration` | Config file (YAML, JSON, TOML) | `infrastructure/compose/compose.blue.yml` |
| `schema` | Schema definition | `infrastructure/surrealdb/context_intelligence_v0.surql` |
| `test` | Test file | `tests/unit/risk/test_risk_service.py` |
| `governance` | Governance/policy document | `knowledge/governance/CDB_CONSTITUTION.md` |
| `script` | Shell/PowerShell script | `tools/backup_all.ps1` |
| `ontology` | Ontology definition | `docs/surrealdb/context-ontology-v0.yaml` |
| `contract` | Contract/specification | `docs/contracts/market_data.schema.json` |
| `runbook` | Operational runbook | `docs/runbooks/CONTROL_REGISTER.md` |
| `other` | Unclassified | — |

### 6.2 Classification Rules

Priority order (path-prefix beats extension when both match):

1. Path-prefix overrides:
   - `tests/` or `test/` → `test`
   - `.github/` or `knowledge/governance/` → `governance`
   - `docs/runbooks/` → `runbook`
   - `docs/contracts/` → `contract`
   - `docs/surrealdb/` with `.yaml` / `.yml` (ontology) → `ontology`
   - `infrastructure/surrealdb/` with `.surql` → `schema`
   - `infrastructure/` with `.yml` / `.yaml` / `.json` / `.toml` → `configuration`
2. Extension / content fallback:
   - `.py` → `source_code`
   - `.md` → `documentation`
   - `.yml` / `.yaml` / `.json` / `.toml` → `configuration`
   - `.surql` → `schema`
   - shebang or `.ps1` / `.sh` / `.bash` → `script`
3. Final fallback:
   - Uncertain → `other`

Classification is deterministic and replayable. No probabilistic classification
in v0.

---

## 7. Duplicate and Rename Handling

### 7.1 Duplicate Detection

A duplicate exists when two files have the same `source_hash` at the same commit:

```
artifact_a.source_hash == artifact_b.source_hash
AND artifact_a.source_path != artifact_b.source_path
AND artifact_a.source_commit == artifact_b.source_commit
```

Duplicates are recorded but not deduplicated — each path gets its own record.
The relationship is noted via `related_to`.

### 7.2 Rename Tracking

A rename is confirmed when a file moves from one path to another across
commits with unchanged content, AND the old path no longer exists in the
newer commit tree (delete evidence). If the old path still exists with the
same hash, the event is a **copy** (duplicate lineage), not a rename.

```
artifact_v1.source_path != artifact_v2.source_path
AND artifact_v1.source_hash == artifact_v2.source_hash
AND artifact_v1.source_commit != artifact_v2.source_commit
AND NOT exists_in_commit(artifact_v1.source_path, artifact_v2.source_commit)
```

The old record is not deleted. Both records persist, linked via `supersedes` /
`superseded_by` (per #1982 vocabulary). Cross-commit copies with an existing
original path create `related_to` links, not `supersedes`.

### 7.3 Deletion Detection

When a file exists at commit N but not at commit N+1:

```
→ mark freshness: "deleted"
→ do NOT delete the record (immutable history)
```

---

## 8. Rebuild and Idempotency

### 8.1 Idempotency Guarantee

Re-running ingestion on the same commit MUST produce:
- Same `artifact_id` values
- Same `source_hash` values
- Same `normalized_hash` values
- Same `content_hash` values
- Same record count

No random, time-based, or environment-dependent values may influence identity.

### 8.2 Rebuild Behavior

| Scenario | Behavior |
|---|---|
| Full rebuild (drop + re-ingest) | Identical records, same IDs, same hashes |
| Incremental rebuild (new commit only) | New records for changed files; existing records untouched |
| Partial rebuild (path filter) | Only filtered paths re-ingested; ids match full rebuild |

### 8.3 Idempotency Validation

```
for each ingested artifact:
    compute artifact_id from (source_path, source_commit)
    assert artifact_id == stored.artifact_id
    compute source_hash from git blob
    assert source_hash == stored.source_hash
```

---

## 9. Integration with `repo_artifact` Schema

The schema `repo_artifact` in `context_intelligence_v0.surql` provides:

| Field | This Document | Schema Alignment |
|---|---|---|
| `artifact_id` | Section 3.1 | ✅ `TYPE string` |
| `source_path` | Section 3.2 | ✅ `TYPE string` |
| `source_commit` | Section 3.1 | ✅ `TYPE string` |
| `source_hash` | Section 4.1 | ✅ `TYPE string` |
| `integrity_algo` | Section 4.2 | ✅ `TYPE string` |
| `size_bytes` | — | ✅ `TYPE int` |
| `mime_type` | Section 5.2 | ✅ `TYPE string` |
| `artifact_type` | Section 6 | ✅ `TYPE string` |
| `observed_at` | Section 3.2 | ✅ `TYPE datetime` |
| `freshness` | Section 3.2, 7.3 | ✅ `TYPE string` |
| `confidence` | — | ✅ `TYPE float` |

No schema changes are required. This document operationalizes the existing fields.

---

## 10. Guardrails

- No hashing of files in excluded roots (`.git/`, `.venv/`, `logs/`, `artifacts/`, `docs/archive/`)
- No hashing of secrets, credentials, or sensitive metadata
- `sensitive_metadata` and `forbidden` classified files are excluded (per ingestion scope)
- No runtime hashing execution authorized by this document
- No modification of existing ledger or mirror importers
- All hashing is deterministic and replay-verifiable
- `source_hash` MUST use git blob content, not working tree

---

## 11. Example Walkthrough

### 11.1 Markdown File

**File**: `docs/surrealdb/README.md` at commit `abc123`

```
artifact_id   = sha256("docs/surrealdb/README.md@abc123")  → "d4e5f6..."
source_path   = "docs/surrealdb/README.md"
source_commit = "abc123"
source_hash   = sha256(git blob bytes)                      → "a1b2c3..."
integrity_algo = "sha256"
artifact_type = "documentation"
size_bytes    = 1234
mime_type     = "text/markdown"
```

### 11.2 Normalized Hash Example

**Raw content** (CRLF, trailing spaces):
```
# Title\r\n\r\nContent line  \r\n
```

**Normalized content** (LF, no trailing spaces):
```
# Title\n\nContent line\n
```

```
source_hash     = sha256(raw_bytes_with_crlf)     → "x1y2z3..."
normalized_hash = sha256(normalized_bytes)        → "a1b2c3..."
content_hash    = sha256("Content line\n")        → "m1n2o3..."
```

### 11.3 Rename Detection

| Commit | Path | source_hash | artifact_id |
|---|---|---|---|
| `abc123` | `docs/old/readme.md` | `a1b2c3...` | `sha256(docs/old/readme.md@abc123)` |
| `def456` | `docs/new/readme.md` | `a1b2c3...` | `sha256(docs/new/readme.md@def456)` |

Same `source_hash`, different path → rename detected. Link old and new via
`supersedes` relationship.

### 11.4 YAML File

**File**: `infrastructure/compose/compose.blue.yml` at commit `abc123`

```
artifact_id   = sha256("infrastructure/compose/compose.blue.yml@abc123")  → "f7a8b9..."
source_path   = "infrastructure/compose/compose.blue.yml"
source_commit = "abc123"
source_hash   = sha256(git blob bytes)                                     → "c3d4e5..."
integrity_algo = "sha256"
artifact_type = "configuration"
size_bytes    = 2847
mime_type     = "application/x-yaml"
```

### 11.5 Python File

**File**: `services/risk/service.py` at commit `abc123`

```
artifact_id   = sha256("services/risk/service.py@abc123")  → "b2c3d4..."
source_path   = "services/risk/service.py"
source_commit = "abc123"
source_hash   = sha256(git blob bytes)                      → "e5f6a7..."
integrity_algo = "sha256"
artifact_type = "source_code"
size_bytes    = 6412
mime_type     = "text/x-python"
```

### 11.6 JSON File

**File**: `docs/contracts/market_data.schema.json` at commit `abc123`

```
artifact_id   = sha256("docs/contracts/market_data.schema.json@abc123")  → "a9b0c1..."
source_path   = "docs/contracts/market_data.schema.json"
source_commit = "abc123"
source_hash   = sha256(git blob bytes)                                    → "d2e3f4..."
integrity_algo = "sha256"
artifact_type = "contract"
size_bytes    = 1533
mime_type     = "application/json"
```

---

## 12. Validation Checklist

- [ ] `artifact_id` formula is deterministic and documented
- [ ] All hash types (source, normalized, content) are defined
- [ ] Normalization pipeline steps are specified
- [ ] Encoding handling rules are specified
- [ ] Frontmatter handling rules are specified
- [ ] File-type-specific rules are documented
- [ ] Artifact type taxonomy covers all expected types
- [ ] Duplicate detection logic is specified
- [ ] Rename tracking logic is specified
- [ ] Idempotency guarantee is explicit
- [ ] Integration with `repo_artifact` schema is verified
- [ ] No secrets in scope
- [ ] No runtime execution authorized
- [ ] No trading state in scope

---

## Provenance / Sources

- **Issue**: #1987
- **Parent**: #1985
- **Epic**: #1976
- **Dependencies**: #1981 (core schema)
- **Referenced documents**:
  - `infrastructure/surrealdb/context_intelligence_v0.surql` (repo_artifact schema)
  - `docs/surrealdb/context-ingestion-scope.md` (excluded roots, sensitivity classes)
  - `docs/surrealdb/context-relationship-vocabulary-v0.md` (supersedes, related_to)
  - `docs/surrealdb/context-intelligence-namespace-layout.md` (hash field conventions)
  - `infrastructure/config/surrealdb/ownership.yaml` (drift rules, source_hash requirement)
