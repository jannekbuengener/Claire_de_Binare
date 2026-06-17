# CDB Context Refresh Runbook

**Zweck:** Zweimal woechentlich den aktuellen CDB-Repo-Kontext aus GitHub/Repo-Live-Wahrheit
in ein evidence-faehiges Context-/Brain-Paket ueberfuehren.

**Parent Epic:** [#3286](https://github.com/jannekbuengener/Claire_de_Binare/issues/3286)
**Erster operativer Slice:** [#3288](https://github.com/jannekbuengener/Claire_de_Binare/issues/3288)
**Naechster Slice (Brain Apply):** [#3289](https://github.com/jannekbuengener/Claire_de_Binare/issues/3289) — benoetigt validiertes Package aus #3288

**LR-Status:** `NO-GO`
**Board-Stage:** `trade-capable` — orthogonal zum LR-System, keine Live-Implikation

---

## 1. Context Package Schema

Das maschinenlesbare Schema definiert die Struktur und Sicherheitsgrenzen eines
Context Packages, bevor ein Brain-Apply (#3289) moeglich wird.

**Schema-Datei:** `tools/context/schemas/context_package.schema.json`
**Validator:** `tools/context/validate_context_package.py`

### Package-Struktur

```json
{
  "package": {
    "package_id": "cdb-context-package-<YYYY-MM-DD>-<seq>",
    "package_type": "context_package",
    "created_at": "<ISO-8601 UTC>",
    "source_commit": "<SHA>",
    "source_repo": "Claire_de_Binare",
    "records": []
  },
  "meta": {
    "version": "1.0",
    "validator_ref": "tools/context/validate_context_package.py",
    "schema_ref": "tools/context/schemas/context_package.schema.json",
    "safety_boundaries": {
      "lr_status": "NO-GO",
      "board_stage_is_live_go": false,
      "real_money_go": false,
      "productive_db_writes_allowed": false,
      "secrets_in_outputs_allowed": false,
      "trading_state_ingestion_allowed": false
    }
  }
}
```

### Mindestfelder je Record

Jeder Record im Package MUSS alle folgenden Felder enthalten
(Validierung erfolgt fail-closed durch das Schema):

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `record_id` | string | Eindeutige ID innerhalb des Packages |
| `record_type` | string (enum) | Einer der erlaubten Record-Typen (s.u.) |
| `repo` | string | Repo-Identifier |
| `source_path` | string | Relativer Dateipfad im Quell-Repo |
| `source_commit` | string | Git-Commit-SHA |
| `source_hash` | string | Content-Hash (z.B. SHA-256 hex) |
| `observed_at` | string (date-time) | ISO-8601 UTC-Beobachtungszeitpunkt |
| `confidence` | string (enum) | high, medium, low, unverified |
| `supersedes` | string or null | Referenz auf supersedierten Record |
| `tags` | string[] | Kategorisierungs-Tags |
| `summary` | string | Menschlesbare Zusammenfassung |
| `evidence_refs` | object[] | Evidence-Referenzen (ref + source) |

### Erlaubte Record-Typen

- `doc_record` — Dokumentationseintrag
- `code_snapshot` — Code-Snapshot
- `decision_record` — Entscheidungsrecord
- `evidence_record` — Evidence-Record
- `claim_record` — Claim-Record (benoetigt canon_read_evidence)
- `memory_record` — Memory-Record
- `dependency_edge` — Dependency-Edge
- `context_package_ref` — Referenz auf anderes Context Package

### Safety Boundaries (im Meta-Objekt verankert)

- `lr_status` ist fix `NO-GO` — nur LR-SSOT kann das aendern
- `board_stage_is_live_go` ist fix `false`
- `real_money_go` ist fix `false`
- `productive_db_writes_allowed` ist fix `false`
- `secrets_in_outputs_allowed` ist fix `false`
- `trading_state_ingestion_allowed` ist fix `false`

---

## 2. Fail-Closed Validator

Der Validator prueft ein Context Package auf zwei Ebenen:

### Ebene 1: Schema-Validierung (JSON Schema)

- Struktur, erforderliche Felder, erlaubte Record-Typen, Typkorrektheit
- Auch zusaetzliche unbekannte Felder werden blockiert (`additionalProperties: false`)

### Ebene 2: Stop Rules (zusaezlich zur Schema-Validierung)

| Regel | Ausloeser | Ergebnis |
|-------|-----------|----------|
| Secret-Indikator | `api_key`, `secret`, `password`, `token` u.a. in `summary` oder `source_path` | BLOCKED |
| Orders/Fills/Positions | `order data`, `fill status`, `position update`, `live-risk-state` in `summary` | BLOCKED |
| Live/Echtgeld-Claim | `live_or_echtgeld_claim` ohne gueltige LR-SSOT-Referenz | BLOCKED |
| Fehlende Canon-Read-Evidence | `claim_record` ohne `canon_read_evidence` | BLOCKED |
| Fehlende Evidence-Refs | Record mit leerem `evidence_refs` | BLOCKED |

### Validierungsergebnis

- **PASS:** Exit-Code 0, keine Fehler
- **BLOCKED:** Exit-Code 1, agentenlesbare + maschinenlesbare Fehlerausgabe
- **FAIL:** Exit-Code 2, unerwarteter Fehler (Datei nicht gefunden, JSON-Parse-Fehler)

### CLI-Usage

```bash
# Package validieren (Datei)
python tools/context/validate_context_package.py pfad/zum/package.json

# Package validieren (stdin)
python tools/context/validate_context_package.py --stdin < package.json

# Maschinenlesbare JSON-Report-Ausgabe
python tools/context/validate_context_package.py package.json --json

# Hilfe
python tools/context/validate_context_package.py --help
```

---

## 3. Workflow (Uebersicht)

```
Repo live lesen (#3287)
    |
    v
Delta-Paket bauen (Context Package)
    |
    v
Package validieren (#3288) ← dieses Schema/Validator
    |
    v (nur bei PASS)
Lokaler append-only Brain Apply (#3289)
    |
    v
Agent Briefing (#3290) / Drift Report (#3291)
```

---

## 4. Safety-Grenzen (Nicht-Ziele)

- **Report/Validation only:** Dieses Schema und der Validator fuehren keinen
  Brain Apply durch. Das ist Scope von #3289.
- **Keine produktiven DB-Writes:** Context Packages sind read-only Artefakte.
  Sie schreiben nicht in SurrealDB, PostgreSQL oder Redis.
- **Keine Secrets-Ingestion:** Secret-Patterns werden blockiert. Keine
  Secret-Werte erscheinen in Fehlerausgaben oder Reports.
- **Keine Trading-State-Ingestion:** Orders, Fills, Positions, Live-Risk-State
  sind blockiert.
- **LR bleibt NO-GO:** Weder Board-Stage `trade-capable` noch ein validiertes
  Context Package autorisieren Live-Kapital oder Echtgeld-Trading.
- **Keine Runtime-Aenderung:** Kein Docker-, Compose-, Runtime- oder
  BLUE/RED-Stack-Eingriff.
- **Kein MCP-Mutation:** Context Packages werden nicht automatisch in MCP-Tools
  oder SurrealDB-Verbindungen eingespielt.

---

## 5. Verwandte Issues

| Issue | Beschreibung | Status |
|-------|-------------|--------|
| #3286 | Parent Epic: Context Refresh Workflow | OFFEN |
| #3287 | Report-only GitHub Actions Workflow | OFFEN |
| #3288 | Context Package Schema + Validator | DIESES |
| #3289 | Lokaler append-only Brain Apply | OFFEN |
| #3290 | Agent Briefing Resolver | OFFEN |
| #3291 | Stale Documentation / Impact Radar | OFFEN |
| #3292 | Onboarding Scenario (bewusst zuletzt) | OFFEN |
