# High Voltage (`agents/HV/`)

Dokumentation zur **High-Voltage Multi-Agent Engine** — experimenteller/isolierter Scope, nicht der produktive CDB-Runtime-Pfad.

## Scope

| Dokument | Thema |
|---|---|
| [`HIGH_VOLTAGE_ENGINE_ARCHITECTURE.md`](HIGH_VOLTAGE_ENGINE_ARCHITECTURE.md) | Architektur |
| [`HIGH_VOLTAGE_MULTI_AGENT_ENGINE.md`](HIGH_VOLTAGE_MULTI_AGENT_ENGINE.md) | Multi-Agent-Orchestrierung |
| [`HIGH_VOLTAGE_ENGINE_DOCKER_STACK.md`](HIGH_VOLTAGE_ENGINE_DOCKER_STACK.md) | Docker-Stack |
| [`HIGH_VOLTAGE_ENGINE_TESTING.md`](HIGH_VOLTAGE_ENGINE_TESTING.md) | Tests |
| [`HIGH_VOLTAGE_ENGINE_GOVERNANCE.md`](HIGH_VOLTAGE_ENGINE_GOVERNANCE.md) | Governance |

## SSOT boundary

| Thema | Kanon |
|---|---|
| Produktiver Agent-Betrieb | [`agents/AGENTS.md`](../AGENTS.md) |
| BLUE+RED Trading-Stack | [`infrastructure/compose/README.md`](../../infrastructure/compose/README.md) |
| Live-Readiness | [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../../docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md) (**NO-GO**) |

HV-Docs beschreiben keinen LR-Go und ersetzen keine operativen Runbooks unter [`docs/runbooks/`](../../docs/runbooks/).

## Related

- [`agents/prompts/README.md`](../prompts/README.md) — Prompt-Vorlagen
- [`agents/AGENTS.md`](../AGENTS.md)
