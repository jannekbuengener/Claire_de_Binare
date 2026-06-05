# CDB Context MCP Server (`tools/mcp/`)

Stdio-MCP-Server für read-only Context Intelligence Tools (ContextBridge + PermissionGuard).

## Start

```bash
python -m tools.mcp.server
```

Kanonische Config: `claire-de-binare.mcp.json` (Repo-Root); Cursor: `.cursor/mcp.json`.

Validierung:

```bash
make mcp-config-validate
# oder
python tools/validate_mcp_config.py tests/fixtures/mcp_smoke_config.json
```

## Guardrails

- Default: in-memory/noop adapter — kein SurrealDB/Docker nötig zum Start.
- DB-backed mode: explizit per `adapter_config_path` pro Tool-Call.
- Keine Writes, kein Schema-Apply, keine Remote-DB-URLs durch Agenten.
- LR **NO-GO** — Tool-Output autorisiert keine Live-Orders.

## Layout

| File | Rolle |
|---|---|
| `server.py` | MCP stdio entry |
| `context_bridge.py` | Bridge + tool dispatch |
| `registry.py` | Tool registry |
| `permission_guard.py` | Fail-closed permissions |
| `*_tools.py` | Tool implementations |

## Tests

- `tests/unit/tools/mcp/` — contract/unit
- `tests/smoke/test_mcp_runtime.py` — runtime smoke (CI slice may exclude)

## Canonical References

- [`docs/runbooks/surrealdb_context_mcp_access.md`](../../docs/runbooks/surrealdb_context_mcp_access.md)
- [`agents/templates/README.md`](../../agents/templates/README.md)
- [`docs/surrealdb/README.md`](../../docs/surrealdb/README.md)
