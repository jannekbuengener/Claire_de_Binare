# Decision MCP Fixtures (v1)

Diese Fixtures sind **lokal deterministisch** und **read-only**.

Scope:
- #2124 — Decision history/replay MCP tool v1 (lokale Adapter-Handler)

Guardrails:
- keine DB / keine SurrealDB / kein Netzwerk
- keine Writes
- kein Live-Go / kein Echtgeld-Go / keine LR-Aussagen
- Human-GO kann sichtbar sein, ist aber **non-authorizing**

Dateien:
- `decision_mcp_v1.json`: Shared decisions + Cases für
  - `cdb_context_decision_history`
  - `cdb_context_decision_replay`

Hinweis:
Diese Fixtures sind **kein** zweiter Bridge-Contract. Sie dienen nur als
deterministische Testdaten für lokale Handler-Tests.
