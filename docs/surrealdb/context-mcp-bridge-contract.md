# SurrealDB Context MCP Bridge Contract

**Issue**: #2022  
**Status**: Contract Defined  
**Date**: 2026-05-05  
**Agent**: OpenCode (Gemini Session)

## Zweck

Dieser Vertrag definiert die MCP-Bridge Für den SurrealDB Context Layer. Agenten greifen über MCP-kompatible Tools zu, ohne Tabellen direkt zu kennen.

## Nicht-Ziele

- Kein Tool schreibt Repo-Dateien
- Kein Tool gibt Live-Go
- Kein Tool triggert Runtime-Aktionen
- Kein Tool nutzt Memory als alleinige Wahrheit
- Keine SurrealDB-Query-Implementierung (nur Contract)

## MCP-Tool-Grenze

### Registry-Truth (origin/main)

**Source of Truth** dafür, welche Tool-IDs aktuell *dispatchbar/exposed* sind, ist `origin/main` (insb. `tools/mcp/registry.py` und `tools/mcp/context_bridge.py`).

Dieses Dokument ist ein **docs-only Contract**: es definiert Ziel-/Konventionsnamen und Guardrails, aber es behauptet **nicht**, dass nicht-registrierte Aliase heute schon aufrufbar sind.

Aktuell auf `origin/main` exposed Tool-IDs:

- `context.search`
- `context.package`
- `context.trace`
- `context.explain_source`
- `context.show_snapshot`
- `context.show_audit`
- `context.readiness`
- `context.self_explain`
- `context.briefing`
- `context.stop_resolver`
- `context.required_reads`
- `cdb_context_briefing` (Alias für `context.briefing`)
- `cdb_context_impact`

### Ziel-Aliase (`cdb_context_*`) für #2022

Die folgenden `cdb_context_*` Namen sind die **Ziel-/Contract-Aliase** gemäß #2022.

**Wichtig:** Nur Aliase, die oben als *aktuell exposed* gelistet sind, sind heute dispatchbar. Alle anderen Einträge sind **target/future** und erst nach Registry-/Bridge-Wiring erreichbar.

| Target Alias | Zweck | Internes Ziel (Handler/Tool-ID) | Status auf `origin/main` |
|---|---|---|---|
| `cdb_context_search` | Kontext-Wissensbasis durchsuchen | `context.search` | target/future (not yet exposed as alias) |
| `cdb_context_package` | Kontext-Artefakte für Handoff verpacken | `context.package` | target/future (not yet exposed as alias) |
| `cdb_context_trace` | Entscheidungs-/Event-Lineage verfolgen | `context.trace` | target/future (not yet exposed as alias) |
| `cdb_context_evidence_resolve` | Evidence-Referenzen auflösen | (vorgesehen) `context.evidence_resolve` | target/future (handler not present on `origin/main`) |
| `cdb_context_decision_history` | Historische Entscheidungen abrufen | (follow-up) `cdb_context_decision_history` | target/future (not in `origin/main` context bridge) |
| `cdb_context_memory_get` | Agent Memory State abrufen | (follow-up) `context.memory_get` | target/future (handler not present on `origin/main`) |
| `cdb_context_memory_write_intent` | Memory write intent gate (dry-run) | `cdb_context_memory_write_intent` | dry-run exposed (#2704) |
| `cdb_context_impact` | Auswirkungen einer Entscheidung bewerten | `cdb_context_impact` | currently exposed |
| `cdb_context_briefing` | Strukturiertes Briefing generieren | `cdb_context_briefing` (Alias für `context.briefing`) | currently exposed |

Hinweis zu `cdb_context_decision_replay`: nicht Teil des Pflichtumfangs von #2022; ggf. Follow-up-Scope (z. B. #2124), aber nicht Bestandteil dieses PR.

## Request-Modell

Alle Tools akzeptieren ein JSON-Objekt. Das Feld `tool` ist dabei **eine aktuell exposed Tool-ID** (siehe oben) oder ein **target/future Alias**, sofern/ sobald dieser registriert ist.

```json
{
  "tool": "<tool-id>",
  "parameters": {
    // tool-spezifische Parameter (siehe v1 Contracts)
  }
}
```

## Response-Modell

```json
{
  "tool": "<tool-id>",
  "status": "ok | error",
  "result": {
    // tool-spezifische Ergebnisse
  },
  "metadata": {
    "query_time_ms": 0,
    "source": "noop_adapter | surrealdb",
    "read_only": true
  }
}
```

## Evidence-/Decision-/Memory-Bezuege

- `cdb_context_evidence_resolve`: Verweist auf Evidence-IDs aus `docs/surrealdb/context-tool-contracts-v1.md`
- `cdb_context_decision_history`: Verweist auf Decision Events aus Ledger
- `cdb_context_memory_get`: Verweist auf Agent Memory (namespace-scoped)

## Trust-/Freshness-/Source-Felder

Alle Ergebnisse enthalten:

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `confidence` | float [0.0, 1.0] | Vertrauen in Ergebnisqualität |
| `source_ref` | string | Interne Referenz Für Audit |
| `timestamp` | ISO8601 | Erstellungszeitpunkt der Quelle |
| `age_ms` | integer | Alter der Evidence in Millisekunden |
| `warnings` | string[] | Warnungen (z.B. "stale evidence") |

## Error-Modell

Spezifisches Error-Modell Für #2022:

| Error Code | Bedeutung | Trigger |
|------------|-------------|--------|
| `no evidence` | Keine Evidence Für Anfrage gefunden | Leere Ergebnismenge bei Evidence-Queries |
| `stale evidence` | Evidence überschreitet Age-Limit | `evidence_age_ms` > `max_age_ms` Threshold |
| `contradictory evidence` | Widerspruechliche Evidence erkannt | Confidence-Score < 0.5 bei Konflikt |
| `source unavailable` | Quellsystem nicht erreichbar | Adapter-Fehler, Timeout |
| `permission denied` | Tool oder Parameter nicht erlaubt | `PermissionGuard` blockiert Anfrage |
| `partial result` | Ergebnis unvollständig | Teilweise Timeouts, truncated results |

### Error Response Schema

```json
{
  "tool": "cdb_context_<name>",
  "status": "error",
  "error": {
    "code": "no evidence | stale evidence | contradictory evidence | source unavailable | permission denied | partial result",
    "message": "string",
    "details": {
      "query": "string",
      "age_ms": 0,
      "confidence": 0.0
    }
  }
}
```

## Security-/Privacy-Grenzen

- Keine Secrets in Tool-Responses
- Keine Trading-State-Informationen (Orders, Positions, Risk)
- Keine persönlichen Daten ohne explizite Freigabe
- Source-Refs muessen Git-Hash oder deterministische IDs sein

## Determinismus-/Audit-Anforderungen

- Alle Tool-Aufrufe muessen über `context.briefing` oder `context.readiness` initiiert werden
- Source-Refs muessen reproduzierbar sein (Git-Hash, Event-ID)
- Decision Events muessen geloggt werden (via Ledger)
- Keine nicht-deterministischen Ergebnisse ohne `warnings`

## Auth-/Permission-Annahmen

1. **Read-Only Default**: Alle Tools sind `read_only: true` registriert
2. **Three-Layer Defense** (`tools/mcp/permission_guard.py`):
   - Registry Gate: Schreibende Tools werden registration blockiert
   - Execute Gate: `read_only` + Input Gate vor Handler-Dispatch
   - Input Gate: Mutation-Keywords in Parametern blockiert
     - Exemption: Structural read-only context tools that must carry governance or readiness terms as data are exempt from mutation-keyword scanning per `permission_guard.py`, currently: `context.readiness`, `context.briefing`, `cdb_context_briefing`, `cdb_context_impact`.
     - Die Exemption gewährt NICHT write authority; diese Tools bleiben read-only und durchlaufen weiterhin Allowlist und Handler-Grenze.
3. **Keine GitHub-Writes**: CDB-MCP bleibt Gatekeeper Für Repo/GitHub
4. **Keine SurrealDB-Writes**: Tools nutzen `NoopQueryAdapter` (in-memory) oder read-only SurrealDB-Adapter
5. **Namespace-Isolation**: Memory-Tools sind auf `agent_id` + Namespace beschränkt

## Beispiel-Requests

### cdb_context_search

```json
{
  "tool": "cdb_context_search",
  "parameters": {
    "query": "risk governance",
    "limit": 10,
    "filters": {
      "source_types": ["decision", "evidence"],
      "date_from": "2026-01-01T00:00:00Z"
    }
  }
}
```

### cdb_context_briefing

```json
{
  "tool": "cdb_context_briefing",
  "parameters": {
    "focus_areas": ["issue-2022", "mcp-bridge"],
    "depth": "detailed",
    "include_recent_decisions": true
  }
}
```

## Beispiel-Responses

### Erfolg (ok)

```json
{
  "tool": "cdb_context_search",
  "status": "ok",
  "result": {
    "results": [
      {
        "id": "decision-123",
        "type": "decision",
        "title": "MCP Bridge Contract Defined",
        "summary": "Contract for SurrealDB Context MCP Bridge",
        "source_ref": "commit:abc123",
        "confidence": 1.0,
        "warnings": []
      }
    ]
  },
  "metadata": {
    "query_time_ms": 0,
    "source": "noop_adapter",
    "read_only": true
  }
}
```

### Fehler (error - no evidence)

```json
{
  "tool": "cdb_context_evidence_resolve",
  "status": "error",
  "error": {
    "code": "no evidence",
    "message": "No evidence found for given IDs",
    "details": {
      "query": "evidence-999",
      "confidence": 0.0
    }
  }
}
```

### Fehler (error - permission denied)

```json
{
  "tool": "cdb_context_trace",
  "status": "error",
  "error": {
    "code": "permission denied",
    "message": "Tool requires read-only permission",
    "details": {
      "violation": "forbidden_keyword detected in parameters"
    }
  }
}
```

## Akzeptanzkriterien Für #2022

- [x] MCP-Bridge ist als Vertrag beschrieben (dieses Dokument)
- [x] Tools abstrahieren SurrealDB-Tabellen (`cdb_context_*` Namen)
- [x] Kein Tool triggert Repo-/GitHub-/Runtime-Writes (Read-Only Default)
- [x] Bestehender CDB-MCP bleibt Gatekeeper Für Repo/GitHub (siehe Abschnitt 11)
- [x] Input-/Output-Schemas gemappt (Request/Response-Modell)
- [x] Read-only Defaults definiert (Abschnitt 9)
- [x] Error Handling definiert (Abschnitt 7 - 6 Error Codes)
- [x] Auth-/Permission-Annahmen dokumentiert (Abschnitt 10)
- [x] Verhältnis zu bestehendem CDB-MCP dokumentiert (Abschnitt 11)

## Verhältnis zu bestehendem CDB-MCP

- **CDB-MCP** (`tools/mcp/`): Gatekeeper Für Repo/GitHub-Operationen (read-only)
- **Context MCP Bridge**: Separater Layer Für SurrealDB Context Intelligence (read-only)
- **Trennung**: Context Tools duerfen keine Repo/GitHub-Writes triggern
- **CDB-MCP Priority**: Bei Repo-bezogenen Anfragen bleibt CDB-MCP autoritativer
- **Context Bridge**: Für Knowledge Graph, Evidence Fabric, Decision Context zustaendig

## Anschlussfaehigkeit an spätere Issues

- **#2018** (Agent Briefing): `cdb_context_briefing` liefert Struktur Für Briefing-Modell
- **#2020** (Evidence Resolution): `cdb_context_evidence_resolve` implementiert Evidence Contract
- **#2025** (Contradiction Detection): `contradictory evidence` Error unterstuetzt Detection
- **#2026** (Stale Knowledge): `stale evidence` Error + `age_ms` Feld unterstuetzt Detection
- **#2027** (Scope Drift): `cdb_context_impact` liefert Impact-Assessment
- **#2028** (Knowledge Quality): `confidence` Feld + `warnings` unterstuetzt Scoring
- **#2030** (Architect Signal): `cdb_context_trace` liefert Signal-Lineage
- **#2031** (Self-Explanation): `cdb_context_briefing` + `cdb_context_memory_get` unterstuetzt Explanation
- **#2122** (Briefing Enrichment): `cdb_context_briefing` kann erweitert werden

## LR-Status

**LR bleibt NO-GO**.

Dieser Contract ist documentation-only. Er bewirkt keine:
- Live-Trading-Freigabe
- Risk-Controls-Änderung
- Execution-Verhalten-Änderung
- LR-Status-Änderung

## Geänderte Dateien

- `docs/surrealdb/context-mcp-bridge-contract.md` (neu)

## Referenzen

- Parent: #2014
- Epic: #1976
- Depends on: #2017 (CLOSED), #2018 (OPEN), #2019 (CLOSED)
- Tool Contracts v1: `docs/surrealdb/context-tool-contracts-v1.md`
- Tool Contracts v0: `docs/surrealdb/context-tool-contracts-v0.md`
- MCP Access Runbook: `docs/runbooks/surrealdb_context_mcp_access.md`
- CDB-MCP: `tools/mcp/context_bridge.py`, `tools/mcp/permission_guard.py`
