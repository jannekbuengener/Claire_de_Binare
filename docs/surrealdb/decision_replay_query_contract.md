# Decision Replay Query Contract (v1)

**Issue**: #2012
**Status**: Contract Defined (history-only, non-authorizing)
**Date**: 2026-05-05
**Scope**: SurrealDB Context Intelligence (CIS) — Decision Graph & Replay explanation

## Zweck

Decision Replay beantwortet **Erklärungsfragen** zu Decisions:

- Warum galt Decision X (damals)?
- Welche Decision ist **aktuell** für Topic Y?
- Was hat eine Decision superseded oder invalidated?
- Welche Evidence-/Claim-Refs sind beteiligt (inkl. **unresolved** Lücken)?
- Welche Unsicherheiten wurden explizit dokumentiert?

**Nicht-Ziel / Guardrail**: Replay ist **keine Freigabe**. Es erzeugt kein Live-Go, kein Echtgeld-Go und keine LR-Aussage. Human-GO-Felder werden als **Daten** angezeigt, aber niemals als Autorisierung interpretiert.

## Beziehung / Abgrenzung

- **#2118** liefert die Decision-History-Basis (read-only Query, current/superseded/invalidated Trennung).
- **#2119** implementiert den Replay Builder als Consumer dieses Contracts (nicht in #2012).
- **#2124** implementiert MCP Tools als Adapter (nicht in #2012).
- **#2116** Evidence Lookup und **#2117** Claim Resolution sind separate Resolver; Replay darf unresolved refs nur **sichtbar** machen.
- **#2126** Cross-cutting Tests/Fixtures sind separat; #2012 ist ein Contract-Doc-Slice.

## Inputs (Request)

### Gemeinsame Felder

- `mode` (string, required): siehe Query-Modi
- `limit` (int, optional, default: 50, max: 500)
- `date_range` (object, optional): Filter/Replay-Zeitfenster (siehe unten)

### Selektoren (optional je Modus)

- `decision_id` (string)
- `topic` (string)
- `scope` (string)
- `artifact` (string)
- `status` (string)

### Date Range (optional)

`date_range` ist ein **Filter**, keine Implementierungspflicht für Time-Travel-Runtime.

```json
{
  "from": "ISO8601 (optional)",
  "to": "ISO8601 (optional)",
  "at": "ISO8601 (optional, mutually exclusive to from/to)"
}
```

Semantik:
- Wenn `at` gesetzt ist: Replay bezieht sich auf den Zustand „als ob“ der Knowledge-Stand bis zu diesem Zeitpunkt betrachtet wird (best-effort; darf Warnung liefern, falls nicht möglich).
- Wenn `from/to` gesetzt ist: Replay darf Entscheidungen außerhalb des Fensters ausfiltern; wenn dadurch Ketten brechen, muss das als Warning sichtbar werden.

## Query-Modi (Request.mode)

Minimaler Contract für #2012 (Builder folgt in #2119):

1. `replay_by_decision_id` (requires: `decision_id`)
2. `replay_current_for_topic` (requires: `topic`)
3. `replay_superseded_for_topic` (requires: `topic`)
4. `replay_by_scope` (requires: `scope`)
5. `replay_by_artifact` (requires: `artifact`)
6. `replay_by_status` (requires: `status`)
7. optional: `replay_at_time` (requires: `topic` oder `decision_id` + `date_range.at`)

## Outputs (Response)

Replay liefert **zwei Formen**:
- **agent-readable JSON** (stabiler Schema-Contract)
- **human-readable Summary** (text/markdown), die das JSON nicht widerspricht

### Agent-readable JSON Schema (v1)

```json
{
  "schema_version": "decision-replay-query/v1",
  "query": {
    "mode": "replay_by_decision_id",
    "decision_id": "dec-002",
    "topic": null,
    "scope": null,
    "artifact": null,
    "status": null,
    "date_range": null,
    "limit": 50
  },
  "decision_summary": {
    "decision_id": "dec-002",
    "title": "string",
    "status": "accepted|proposed|parked|superseded|invalidated|unknown",
    "scope": "string",
    "topics": ["string"],
    "created_at": "ISO8601|null",
    "agent": "string",
    "human_go": {
      "present": true,
      "value": true,
      "note": "string|null"
    },
    "uncertainty": "string|null"
  },
  "current_status": {
    "bucket": "current|superseded|invalidated",
    "current_decision_id": "string|null",
    "as_of": "ISO8601|null"
  },
  "decision_chain": [
    {
      "decision_id": "string",
      "bucket": "current|superseded|invalidated",
      "created_at": "ISO8601|null",
      "superseded_by": "string|null",
      "invalidated_by": "string|null"
    }
  ],
  "supersession_chain": [
    { "from": "dec-001", "to": "dec-002", "relation": "supersedes" }
  ],
  "evidence_chain": {
    "refs": ["ev-001", "ev-missing-001"],
    "resolved": [],
    "unresolved": ["ev-missing-001"]
  },
  "claim_chain": {
    "refs": ["cl-001", "cl-missing-001"],
    "resolved": [],
    "unresolved": ["cl-missing-001"]
  },
  "stop_conditions": [],
  "warnings": ["string"],
  "approval_semantics": {
    "history_only": true,
    "no_approval": true,
    "no_live_go": true,
    "no_echtgeld_go": true,
    "note": "Replay explains only. This output does not grant approval or authorize live capital."
  }
}
```

### Required Semantics (fail-closed, audit-friendly)

- **Current vs superseded vs invalidated** muss klar unterscheidbar sein.
- **Unresolved evidence/claims** dürfen nicht verschwinden:
  - `refs` zeigt *alle* referenzierten IDs.
  - `unresolved` zeigt IDs, die ohne #2116/#2117 nicht auflösbar sind.
- **Human-GO** ist sichtbar, aber non-authorizing:
  - `approval_semantics` muss explizit „no_live_go/no_echtgeld_go“ setzen.
- **Broken chains** (fehlendes `superseded_by` Target, date_range Filter bricht Kette) müssen als Warning erscheinen.

## Human-readable Output (Beispiel, komprimiert)

```text
Decision Replay (history-only)
- mode: replay_by_decision_id
- decision: dec-002 (accepted) topic:a
- bucket: current
- human_go: present=true value=true (data only; NOT an authorization)
- evidence refs: ev-002, ev-missing-001 (unresolved: ev-missing-001)
- claim refs: cl-001, cl-missing-001 (unresolved: cl-missing-001)
- chain: dec-001 -> dec-002
- warnings: unresolved refs present
```

## Minimalbeispiel (Fixture-orientiert, ohne Datenkopie)

Orientierung an der lokalen #2118 Fixture-Struktur:
- `tests/fixtures/surrealdb/decision_history/decisions_v1.json`

Minimalfall:
- `dec-001` superseded_by `dec-002`
- `dec-002` current, enthält missing evidence/claim refs
- Human-GO sichtbar als `human_go_note`, aber `approval_semantics.no_live_go=true`

## Warning / Error Semantics (nicht abschließend)

- `missing_decision`: decision_id existiert nicht
- `ambiguous_topic`: topic matcht mehrere disjunkte chains
- `unresolved_evidence_refs_present`: unresolved evidence refs existieren
- `unresolved_claim_refs_present`: unresolved claim refs existieren
- `broken_supersession_chain`: chain edge verweist auf unknown decision_id
- `invalidated_decision`: replay target ist invalidated (sichtbar, nicht kaschieren)
- `date_range_out_of_history`: requested date window nicht abbildbar

## Validation Notes

- Dieser Contract ist Doku-only. Keine Runtime-/DB-/MCP-Implementierung.
- Für Konsistenz mit #2118 soll bei Änderungen immer die #2118 Unit-Suite grün bleiben:
  - `pytest -v tests/unit/surrealdb/test_decision_history_query_v1.py`

## Non-Goals (explizit)

- Kein Replay Builder (#2119)
- Kein MCP Tool (#2124)
- Kein Evidence Lookup (#2116)
- Kein Claim Resolution (#2117)
- Keine produktive SurrealDB-Queries, keine DB-Writes, keine Runtime-/Docker-Änderungen
- Keine Live-/LR-/Echtgeld-Autorisierung
