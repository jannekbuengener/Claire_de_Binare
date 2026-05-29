# SurrealDB Context Query - Local Runbook

**Status**: Draft
**Authority**: Issue #2089 / Wave 11 / Epic #1976
**Scope**: Local/dev only. Document how to query the Context Intelligence read-only layer using the context_query CLI.

This runbook is **not** a production activation guide. It does not authorize live trading, does not change Live-Readiness, and does not enable any write path to SurrealDB.

---

## 1. Purpose and Scope

This runbook describes how to use the Wave-11 Context Query CLI (`tools/surrealdb/context_query.py`) to perform read-only queries against the Context Intelligence data layer.

Use cases:
- Search artifacts and documentation chunks
- Query code symbols and import references
- Trace dependency edges
- Explain source/evidence for context records
- View snapshot, drift, and audit information

Out of scope for this runbook:

- Production SurrealDB activation
- Any write operations (CREATE, UPDATE, DELETE, etc.)
- Trading-state, risk, execution, governance, or runtime state
- Live-trading, Live-Readiness, or Echtgeld authorization
- MCP bridge, Agent-Briefing engine, or vector search

---

## 2. Non-Goals (Anti-Criteria)

This runbook explicitly does **not** establish or imply any of the following:

- No production default. The query CLI never writes to any SurrealDB instance.
- No write path. All queries are SELECT-only; write operations are denied.
- No trading-state access. Queries against trading, risk, execution tables are forbidden.
- No Live-Readiness change. LR verdict remains **NO-GO** independent of this runbook.
- No memory write. The CLI never writes to Memory (Nexus).
- No Echtgeld implication. This runbook does not authorize real trading.

---

## 3. Prerequisites

### 3.1 Local SurrealDB Instance (Optional)

For actual query execution against real data, a local SurrealDB instance is required:

```bash
# Start local SurrealDB (example)
docker run --rm -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root
```

**Note**: The CLI includes a NoopQueryAdapter that returns empty results without network connectivity, useful for testing/validation without a live DB.

### 3.2 Local Config

Create the local working copy from the checked-in example:

```bash
make context-query-config-init
```

This validates the read-only example config and creates the gitignored
`infrastructure/config/surrealdb/context_query.local.yaml` file if it is missing.
Edit only local endpoint/auth-mode settings if needed. Do not put secrets into
this config; root credentials stay in `SURREALDB_ENV` under the local secrets
directory.

---

## 4. CLI Location

```
tools/surrealdb/context_query.py
```

---

## 5. Available Commands

### 5.1 classify

Classify a SurrealQL statement (read-only check).

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    classify --statement "SELECT * FROM doc_chunk"
```

### 5.2 find-artifact

Search repo_artifact table.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    find-artifact --source-path src/ --file-type python
```

### 5.3 find-doc

Search doc_chunk table.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    find-doc --query "authentication" --source-path docs/
```

### 5.4 find-symbol

Search code_symbol table.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    find-symbol --name MyClass --symbol-type class
```

### 5.5 show-symbol

Show a single symbol by ID.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    show-symbol --symbol-id symbol-123
```

### 5.6 find-imports / show-imports-for-artifact

Search import_reference table.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    find-imports --module json

python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    show-imports-for-artifact --source-hash abc123...
```

### 5.7 trace

Trace dependency edges.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    trace --target-ref mymodule --direction upstream --depth 5
```

### 5.8 explain-source

Explain source/evidence for a context record.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    explain-source --artifact-id artifact-123

python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    explain-source --chunk-id chunk-456
```

### 5.9 show-snapshot / show-drift / show-audit

View snapshot, drift, and audit reports.

```bash
python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    show-snapshot --run-id run-123

python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    show-drift --status blocking

python -m tools.surrealdb.context_query \
    --config infrastructure/config/surrealdb/context_query.local.yaml \
    show-audit --run-id run-123
```

---

## 6. Output Formats

### 6.1 JSON (Default)

```bash
python -m tools.surrealdb.context_query \
    --config ... --format json \
    find-artifact --source-path src/
```

### 6.2 Text

```bash
python -m tools.surrealdb.context_query \
    --config ... --format text \
    find-artifact --source-path src/
```

### 6.3 Markdown

```bash
python -m tools.surrealdb.context_query \
    --config ... --format markdown \
    find-artifact --source-path src/
```

**Output Contract**: See `docs/surrealdb/context-query-output-contract.md` for detailed JSON schema.

---

## 7. Guardrails

### 7.1 Read-Only Enforcement

- All queries are validated through a statement classifier
- WRITE operations (CREATE, INSERT, UPDATE, DELETE, etc.) are denied
- Forbidden tables include: orders, fills, positions, balances, pnl, risk_state, execution_state, governance_event, governance_decision, governance_state

### 7.2 No-Network Mode

The CLI includes a NoopQueryAdapter that never opens network sockets, useful for testing/validation without a live DB.

### 7.3 Config Validation

The local config must:
- Have `schema_version: context-query-local/v0`
- Have `read_only: true`
- Have `mode.read_only: true`
- Have `mode.surrealdb_write: forbidden`
- Have `mode.surrealdb_apply: forbidden`

---

## 8. Validation Commands

### 8.1 Run Tests

```bash
python -m pytest tests/unit/surrealdb/test_context_query*.py -q
```

### 8.2 Run Lint

```bash
ruff check tools/surrealdb/context_query.py tests/unit/surrealdb/
```

### 8.3 Check Formatting

```bash
black --check tools/surrealdb/context_query.py tests/unit/surrealdb/
```

---

## 9. Troubleshooting

### 9.1 "config is required" Error

Most commands require a config file. Use `--config` flag:

```bash
python -m tools.surrealdb.context_query --config path/to/config.yaml <command>
```

### 9.2 "WRITE_DENIED" Error

The query attempted a non-SELECT operation or accessed a forbidden table. Review your query.

### 9.3 No Results

- Verify the local SurrealDB is running and accessible
- Check that context data has been imported
- Use `--include-tombstoned` to include deleted records

### 9.4 Network Error

If using the NoopQueryAdapter (default), no network is used. For real queries, ensure the SurrealDB URL in config is correct.

---

## 10. References

- Context Query Output Contract: `docs/surrealdb/context-query-output-contract.md`
- Context Import Runbook: `docs/runbooks/surrealdb_context_import.md`
- Example Config: `infrastructure/config/surrealdb/context_query.local.example.yaml`

---

## 11. Clearances and Verdict

| Item | Status |
|------|--------|
| LR Verdict | NO-GO (unchanged) |
| Board Stage | trade-capable (unchanged) |
| Echtgeld | Not authorized |
| Write Path | Disabled |
| Memory Write | Not authorized |