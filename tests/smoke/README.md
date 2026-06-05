# Smoke tests (`tests/smoke/`)

Minimale Sanity-Checks (MCP-Runtime, Pipeline-Smoke). Schnell, aber nicht vollständige CI-Abdeckung.

## Marker

- `@pytest.mark.smoke` wo gesetzt
- MCP-Runtime: in CI oft ausgeschlossen via `-k "not test_mcp_time_server_runtime"`

## Commands

```bash
pytest -v tests/smoke/
pytest -q -k "not test_mcp_time_server_runtime"   # CI-äquivalent
```

## Container

| Test | Stack |
|---|---|
| `test_mcp_runtime.py` | MCP-Deps lokal; kein BLUE+RED für Basis-Smoke |
| Pipeline-Smoke | Siehe jeweilige Testdatei |

## Related

- [`mcp_navpack_working_repo/ENTRYPOINTS.yaml`](../../mcp_navpack_working_repo/ENTRYPOINTS.yaml) — MCP smoke contract
- [`tools/validate_mcp_config.py`](../../tools/validate_mcp_config.py)
- [`tests/README.md`](../README.md)
