# SurrealDB Local Context Runtime — Stack Contract

Status: `context-infra-only` | Scope: Local Development | Live-Readiness: NO-GO (unrelated to this runtime)

> **SurrealDB Local Runtime is Context Infrastructure — not a Live/Trading Go.**
>
> Starting or stopping `cdb_surrealdb` has zero effect on live-readiness, LR-status,
> real-money trading, BLUE/RED runtime, or any risk-/execution-path.

---

## 1. Docker Requirement

**Yes — Docker must be running.**

The `cdb_surrealdb` container is managed via Docker Compose.

---

## 2. What Runs Permanently

| Component | Container | Note |
|-----------|-----------|------|
| SurrealDB server | `cdb_surrealdb` | Only permanent process in this stack |

That is the complete list. No other container is part of the local Context stack.

---

## 3. Why Are There No More Containers?

The Context Intelligence tools (`context_indexer`, `context_importer`, `context_query`) are
**one-shot job runners**, not daemon processes. They run, do their work, and exit.
They are never meant to be running containers.

---

## 4. One-Shot Tools (not containers)

These scripts connect to `cdb_surrealdb` and exit when done:

| Tool | Path | Purpose |
|------|------|---------|
| Context Indexer | `tools/surrealdb/context_indexer.py` | Build/refresh the context index |
| Context Importer | `tools/surrealdb/context_importer.py` | Import context documents |
| Context Query | `tools/surrealdb/context_query.py` | Query the context store |

Run them manually when needed. They are not auto-started by the compose stack.

---

## 5. Network & Port

| Item | Value |
|------|-------|
| Local dev port | `127.0.0.1:8010 → 8000` (via `surrealdb-dev.yml` overlay) |
| Internal port | `8000` (inside container) |
| Network | `cdb_network` (external — must pre-exist) |

The port `8010` is used on localhost to avoid collision with `cdb_ws` which binds `127.0.0.1:8000`.

---

## 6. Volume

| Item | Value |
|------|-------|
| Named volume | `surrealdb_data` |
| Driver | `local` |
| Purpose | Persistent SurrealDB data storage |

The volume persists across container restarts. `context-down` does not destroy it.

---

## 7. Compose Files

| File | Role |
|------|------|
| `infrastructure/compose/surrealdb.yml` | Base stack definition — container, volume, network, healthcheck |
| `infrastructure/compose/surrealdb-dev.yml` | Dev overlay — adds `127.0.0.1:8010:8000` port binding |

Always use both files together for local development:

```bash
docker compose \
  -f infrastructure/compose/surrealdb.yml \
  -f infrastructure/compose/surrealdb-dev.yml \
  up -d
```

Or use the canonical operator shortcut (see Section 9):

```bash
make context-up
```

---

## 8. Environment / Secrets

| Item | Value |
|------|-------|
| Env file | `${SECRETS_PATH}/SURREALDB_ENV` |
| Default path (Linux/Mac) | `~/Documents/.secrets/.cdb/SURREALDB_ENV` |
| Default path (Windows) | `%USERPROFILE%\Documents\.secrets\.cdb\SURREALDB_ENV` |
| Template (in repo) | `infrastructure/config/surrealdb/SURREALDB_ENV.example` |

The real env file lives **outside the repository**. Never commit it. The template file contains
only `REDACTED` placeholders.

Required fields:

```
SURREAL_USER=<local_user>
SURREAL_PASS=<local_password>
```

Use `make context-env-check` to verify the env file without exposing any values.

---

## 9. Operator Commands

```bash
make context-env-check      # Verify env/secrets guard (no secret output)
make context-up             # Start cdb_surrealdb sidecar (runs env-check first)
make context-status         # Container/volume/port status (no secret output)
make context-logs           # Tail cdb_surrealdb logs (last 50 lines)
make context-down           # Stop cdb_surrealdb sidecar (BLUE/RED untouched)
make context-restart        # context-down then context-up
```

### Schema Workflow (Issue #2395)

```bash
make context-schema-apply   # Apply context_intelligence_v0.surql to local DB
make context-schema-check   # Verify all v0 tables exist (graceful fail if offline)
make context-reset-local    # DESTRUCTIVE: clear all context-intelligence data
```

**Schema apply** (`context-schema-apply`):

- Reads `infrastructure/surrealdb/context_intelligence_v0.surql`
- Connects to `http://127.0.0.1:8010` (local dev port — hard-guarded)
- Target namespace/database: `cdb_context_local` / `cdb_context_intel`
- Runs `DEFINE TABLE ...` statements (idempotent — safe to re-apply)
- Requires `cdb_surrealdb` running (`make context-up` first)
- No trading/live tables are touched

**Schema check** (`context-schema-check`):

- Queries `INFO FOR DB` and compares against the 18 expected v0 tables
- Exits 0 if all tables present or if container is offline (graceful)
- Exits 1 if tables are missing — prints which ones
- No secret output

**Local reset** (`context-reset-local`):

- **DESTRUCTIVE**: clears all record data in context-intelligence tables
- Schema definitions (`DEFINE TABLE`) are preserved — only records are deleted
- Hard guard: only executes against `127.0.0.1` / `localhost`
- Hard guard: `--confirm` flag required (prevents accidental execution)
- Trading/live/risk/governance tables (`orders`, `fills`, `positions`, etc.) are
  explicitly forbidden and never touched
- LR-Go remains NO-GO; this operation has no effect on live-readiness

Scripts: `tools/surrealdb/local_schema_apply.py`, `local_schema_check.py`, `local_reset.py`

---

## 10. What Is NOT Part of This Runtime

The following are explicitly **outside** the SurrealDB local context stack:

| Item | Reason |
|------|--------|
| Trading Runtime | Separate BLUE stack (`compose.blue.yml`) |
| Live Execution | Separate BLUE service (`cdb_execution`) |
| Real Money / Auto-Trade | Requires explicit LR-Go + Human Gate |
| Live-Readiness (LR-Go) | Governed by `docs/live-readiness/` — independent |
| Remote / Production DB | Never touched by local compose stack |
| BLUE stack (Postgres, Redis, Risk, Execution, …) | Started via `make docker-up` — separate |
| RED stack (Signal, WS, Grafana, …) | Started via `make docker-up` — separate |
| MCP daemon (v1) | Not implemented in this version; decided separately if needed |
| Schema apply | One-shot operation, not part of this bootstrap |
| Context import | One-shot via `context_importer.py`, not auto-started |
| Pipeline smoke | Out of scope for local runtime bootstrap |

---

## 11. Relationship to Epics

| Issue | Role | State |
|-------|------|-------|
| #1976 | CDB Context Intelligence System — Ledger Anchor | OPEN (remains open) |
| #2391 | Local Runtime Epic | OPEN (remains open) |
| #2392 | This contract document | Closed via PR |
| #2393 | One-command startup (Makefile targets) | Closed via PR |
| #2394 | Env/secrets guard | Closed via PR |
| #2395 | Local schema apply and reset workflow | Closed via PR |

---

## 12. Invariants

- `cdb_surrealdb` is the only permanent container in this stack.
- No secrets or credential values are ever printed by any `make context-*` target or helper script.
- `context-down` never stops BLUE or RED runtime containers.
- `context-up` always runs `context-env-check` first.
- `context-schema-apply` and `context-schema-check` only connect to `127.0.0.1:8010` (local-dev port).
- `context-reset-local` requires `--confirm` and never touches trading/live/risk/governance tables.
- This runtime has no effect on live-readiness verdict.
