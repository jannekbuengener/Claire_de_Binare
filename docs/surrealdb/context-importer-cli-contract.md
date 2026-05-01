# Context Importer CLI Contract

**Status**: Draft (Scaffold + Local Config + JSONL Validation + Import Plan + Dry-run Reconcile Slice)
**Authority**: Issue #2068 + #2069 + #2070 + #2071 + #2072 / Wave 10 Parent #2067 / Epic #1976
**Target**: `tools/surrealdb/context_importer.py`
**Scope**: CLI scaffold plus explicit local config validation, read-only JSONL validation, deterministic import plan generation, and dry-run reconcile against explicit read-only existing-record fixtures — no default SurrealDB connection, no SurrealDB writes.

---

## 1. Zweck

Dieser Vertrag beschreibt die CLI-Oberflaeche fuer den zukuenftigen
Context-Import-Pfad (JSONL-Artefakte aus dem Context Indexer nach SurrealDB).
In #2068 wurde ausschliesslich das Scaffold geliefert: Argument-Parsing,
Help-Text, Default-Verhalten und Safety-Gates. #2069 ergaenzt eine explizite
lokale Config-Lade- und Validierungsschicht fuer
`infrastructure/config/surrealdb/context_import.local.example.yaml`.
Die JSONL-Validation fuer `validate-jsonl` ist in #2070 read-only implementiert.
#2071 ergaenzt `plan --input-dir`: validierte JSONL-Artefakte werden zu einem
  deterministischen, DB-unabhaengigen Importplan geroutet. #2072 ergaenzt
  `dry-run --input-dir`: der Plan wird gegen einen expliziten read-only
  Existing-Records-Zustand reconciled. Apply, Audit und Rollback-Plan gehoeren
  weiterhin zu separaten Folge-Slices.

---

## 2. Command-Modell (v0)

| Command | Zweck (Endziel) | Aktuelles Verhalten |
|---|---|---|
| `validate-jsonl` | JSONL-Artefakte gegen Schema pruefen | Read-only Validation, Exit `0` ohne Blocking Findings, Exit `1` mit Blocking Findings |
| `plan` | Importplan aus JSONL-Artefakten berechnen | Mit `--input-dir`: deterministic candidate import plan, Exit `0` oder `1`; ohne `--input-dir`: Scaffold-Stub |
| `dry-run` | End-to-End-Lauf ohne Schreiben | Mit `--input-dir`: dry-run reconcile gegen leeren oder expliziten Existing-Records-Zustand, Exit `0` oder `1`; ohne `--input-dir`: Scaffold-Stub |
| `apply` | Schreiben nach SurrealDB | Hart geblockt: Exit `5` (`WRITE_DENIED`) |
| `audit` | Audit-Trail-Export | Stub: `scaffold-ack`, Exit `0` |
| `rollback-plan` | Rollback-Plan generieren | Stub: `scaffold-ack`, Exit `0` |

`apply` existiert als Subcommand und auch als globales Flag `--apply`. Beide
Pfade fuehren in #2068 zu Exit-Code `5`. Die Tests bestaetigen das als
hartes Sicherheitsnetz; das Verhalten darf erst durch einen expliziten
Folge-Slice (Apply-Implementation) entfernt werden.

---

## 3. Sicherheitsmodell und Guardrails

- **Read-only Default**: Alle nicht implementierten Subcommands sind Stubs, die
  nur eine deterministische JSON-Antwort drucken. `validate-jsonl` liest lokale
  JSONL-Dateien, validiert sie und bleibt ohne SurrealDB-Zugriff. `plan --input-dir`
  nutzt dieselbe Validation und erzeugt nur lokale Plan-Ausgabe.
- **Dry-run Default**: Ohne explizites `--apply` ist `dry_run = true`.
- **Apply hart geblockt**: `--apply` und `apply` exit `5` (`WRITE_DENIED`).
- **Keine Default-SurrealDB-Verbindung**: `--surreal-url`, `--namespace`,
  `--database` werden geparsed, aber nie fuer Netzwerkzugriff verwendet.
  `dry-run --input-dir` nutzt ausschliesslich `--existing-records` als lokale
  read-only Boundary oder einen leeren Existing-State.
- **Output-Pfad-Whitelist**: `--report-output` muss unter `artifacts/`
  oder `temp/` liegen. Absolute Pfade (`/...`, `C:\...`, UNC) und
  Traversal (`..`) werden mit Exit `5` verworfen. `validate-jsonl` schreibt
  nur bei explizitem `--report-output`; `plan --input-dir` schreibt nur bei
  explizitem `--report-output`; andere Subcommands schreiben nichts.
- **Config nur explizit**: `--config` wird nur geladen, wenn der Pfad explizit
  uebergeben wird. Ohne `--config` laeuft der Scaffold weiter ohne Config.
- **Config fail-closed**: `allow_apply_default` muss `false` sein; Trading-
  State-Tabellen und Governance-Mirror-Tabellen duerfen nicht in
  `allowed_tables` erscheinen und muessen in `forbidden_tables` enthalten sein.
- **Keine Secrets in Beispiel-Config**:
  `infrastructure/config/surrealdb/context_import.local.example.yaml` enthaelt
  nur lokale Platzhalter. Reale Credentials muessen aus `SECRETS_PATH` oder
  der Laufzeitumgebung kommen, nicht aus dieser YAML.
- **Secret-Redaction**: Findings melden secret-like Inhalte nur mit Code und
  Pfad/Zeile; erkannte Werte werden nicht in Reports oder stdout echoed.
- **Kein Apply-/Audit-/Rollback-Verhalten**: jeweils eigene Folge-Slices.
  Reconcile in #2072 bleibt dry-run-only und erzeugt nur Reports.

---

## 4. Argument-Vertrag (pro Subcommand)

| Argument | Default | Pflicht? | Verhalten im Scaffold |
|---|---|---|---|
| `--input-dir` | `None` | fuer `validate-jsonl` ja; fuer implementierten `plan` ja | lokales JSONL-Verzeichnis lesen/validieren; `plan` erzeugt daraus einen Importplan; andere Subcommands ignorieren es |
| `--surreal-url` | `""` | nein | nicht verwendet |
| `--namespace` | `None` | nein | nicht verwendet |
| `--database` | `None` | nein | nicht verwendet |
| `--run-id` | `None` | nein | `validate-jsonl` prueft optional auf einheitlichen Run; andere Subcommands parsen nur |
| `--config` | `None` | nein | explizite lokale YAML laden und validieren, kein Write |
| `--report-output` | `None` | nein | Whitelist-Check; `validate-jsonl` und `plan --input-dir` schreiben Report nur wenn explizit gesetzt |
| `--existing-records` | `None` | nein | nur fuer `dry-run --input-dir`; lokale JSON-Datei mit Existing-Records-Fixture, kein DB-Client |
| `--dry-run` | `False` (Default-Verhalten ist dennoch dry-run) | nein | redundant; explizit erlaubt |
| `--apply` | `False` | nein | `True` ⇒ Exit `5` |
| `--format` | `json` | nein | `json` / `jsonl` / `markdown` |

---

## 4.1 Lokaler Config-Vertrag (#2069)

Kanonische Beispiel-Datei:

```text
infrastructure/config/surrealdb/context_import.local.example.yaml
```

Erwartete Felder:

| Feld | Pflicht? | Vertrag |
|---|---|---|
| `schema_version` | ja | muss `context-import-local/v0` sein |
| `surreal_url` | ja | nicht-leerer String, nur validiert/echoed |
| `namespace` | ja | nicht-leerer String, nur validiert/echoed |
| `database` | ja | nicht-leerer String, nur validiert/echoed |
| `auth_mode` | ja | `none` / `root` / `scope`; Beispiel nutzt `none` |
| `timeout` | ja | positiver Integer |
| `allow_apply_default` | ja | muss `false` sein |
| `allowed_tables` | ja | nicht-leere Liste nur fuer Context-Intelligence-Tabellen |
| `forbidden_tables` | ja | muss Trading-State- und Governance-Mirror-Tabellen enthalten |

Explizit blockierte Tabellen fuer `allowed_tables`:

```text
orders, fills, positions, balances, pnl, risk_state, execution_state,
governance_event, governance_decision, governance_state
```

Diese Tabellen muessen in `forbidden_tables` stehen. Ueberschneidungen zwischen
`allowed_tables` und `forbidden_tables` sind ungueltig.

---

## 5. Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg / Scaffold acknowledged oder `validate-jsonl` ohne Blocking Findings |
| 1 | Validierungsfehler mit Blocking Findings |
| 2 | CLI-Usage / argparse-Fehler |
| 3 | Input-/Config-Datei nicht gefunden |
| 4 | Unsupported Format (defensiv; argparse faengt das frueher) |
| 5 | Write denied (Pfad-Verstoss ODER Apply im Scaffold) |
| 6 | Interner Fehler |

---

## 5.1 Existing-Records-Fixture-Vertrag (#2072)

`dry-run --input-dir` kann optional einen vorhandenen DB-Zustand als lokale
JSON-Fixture lesen:

```json
{
  "records": [
    {
      "table": "doc_page",
      "record_id": "doc_page:page-id",
      "payload_hash": "lowercase-sha256-hex",
      "schema_version": "context-importer/v0"
    }
  ]
}
```

Alternativ darf die Datei direkt eine Liste solcher Records enthalten. Statt
`payload_hash` kann ein objektfoermiges `payload` angegeben werden; der Importer
berechnet dann denselben deterministischen SHA-256-Hash wie beim Importplan.

Guardrails:

- Die Fixture ist eine mockbare read-only Boundary; kein SurrealDB-Client wird
  geoeffnet.
- Doppelte `record_id`-Werte in Existing-Records-Fixtures sind ungueltig und
  werden fail-closed als deterministischer Input-Error abgelehnt. Es gibt keine
  stille Ueberschreibung und keine Last-one-wins-Semantik.
- Tabellen muessen in der Context-Importer-Allowlist liegen und duerfen nicht in
  `orders`, `fills`, `positions`, `balances`, `pnl`, `risk_state`,
  `execution_state` oder Governance-Mirror-Tabellen liegen.
- `schema_version` darf fehlen oder `context-importer/v0` sein. Andere Werte
  erzeugen `schema_mismatch` als Blocking Finding.

---

## 6. Antwort-Schema

Erfolgsantwort (Subcommand-Stub):

```json
{
  "schema_version": "context-importer/v0",
  "command": "<subcommand>",
  "status": "scaffold-ack",
  "dry_run": true,
  "apply_requested": false,
  "surrealdb_connection": "disabled",
  "config_loaded": false,
  "implemented": false,
  "note": "scaffold only; ..."
}
```

`validate-jsonl`-Antwort:

```json
{
  "schema_version": "context-importer/v0",
  "command": "validate-jsonl",
  "status": "passed",
  "dry_run": true,
  "apply_requested": false,
  "surrealdb_connection": "disabled",
  "implemented": true,
  "input_dir": "artifacts/context-index/run",
  "run_id": "run-id-or-null",
  "artifact_counts": {"repo_artifacts": 1},
  "validation": {
    "blocking_count": 0,
    "warning_count": 0,
    "info_count": 0,
    "finding_count": 0
  },
  "findings": []
}
```

Bei Blocking Findings ist `status` `blocked` und Exit-Code `1`. Findings
enthalten nur `severity`, `code`, `message`, optional `artifact`, `line` und
`source_path`; erkannte secret-like Werte werden nicht ausgegeben.

`plan --input-dir`-Antwort (#2071):

```json
{
  "schema_version": "context-importer/v0",
  "command": "plan",
  "run_id": "run-id-or-null",
  "input_dir": "artifacts/context-index/run",
  "status": "planned",
  "dry_run": true,
  "apply_requested": false,
  "surrealdb_connection": "disabled",
  "implemented": true,
  "actions": [
    {
      "action": "create",
      "table": "doc_page",
      "record_id": "doc_page:page-id",
      "artifact": "doc_pages",
      "source_ref": "docs/example.md",
      "depends_on": [],
      "reason": "validated JSONL record; DB-independent candidate create",
      "payload_hash": "sha256-hex"
    }
  ],
  "warnings": [],
  "counts": {
    "actions": 1,
    "warnings": 0,
    "tables": 1,
    "validation_findings": 0
  },
  "table_counts": {"doc_page": 1},
  "action_counts": {"create": 1},
  "has_blocking_validation_findings": false,
  "validation_summary": {
    "blocking_count": 0,
    "warning_count": 0,
    "info_count": 0,
    "finding_count": 0
  },
  "import_order": ["repo_artifact", "doc_page", "doc_section"]
}
```

Plan-Vertrag:

- `plan` ist DB-unabhaengig: es liest keinen SurrealDB-Zustand und fuehrt keinen
  Reconcile gegen bestehende Records aus.
- Ohne Blocking-Validation-Findings erzeugt jeder neue validierte Record eine
  `create`-Candidate-Action. Innerhalb derselben Eingabe doppelte `record_id`s
  werden deterministisch als `skip` markiert (First occurrence wins).
- `update` und `tombstone` sind strukturell reserviert, werden in #2071 aber
  nicht erzeugt, weil dafuer DB-/State-Vergleich oder explizite Tombstone-
  Artefakte erforderlich waeren.
- Bei Blocking-Validation-Findings ist `status` `blocked`, `actions` ist leer,
  `has_blocking_validation_findings` ist `true`, und Exit-Code ist `1`.
- `payload_hash` ist ein stabiler SHA-256 ueber den JSONL-Record mit sortierten
  Keys; er enthaelt keine SurrealDB-State- oder Secret-Werte.
- `--format json` gibt das vollstaendige Plan-Objekt aus. `--format markdown`
  ist diff-freundlich fuer Review. `--format jsonl` gibt eine Summary-Zeile plus
  je eine Zeile pro Action/Warning aus.

`dry-run --input-dir`-Antwort (#2072):

```json
{
  "schema_version": "context-importer/v0",
  "command": "dry-run",
  "status": "reconciled",
  "dry_run": true,
  "apply_requested": false,
  "surrealdb_writes": "disabled",
  "existing_records_source": "empty",
  "counts": {
    "creates": 1,
    "skips": 0,
    "update_candidates": 0,
    "tombstone_candidates": 0,
    "blocking": 0,
    "warnings": 0
  },
  "actions": [],
  "findings": []
}
```

Reconcile-Vertrag:

- `record_missing` wird als `create` berichtet.
- `record_same` wird als `skip` berichtet.
- `record_changed` wird als `update_candidate` berichtet.
- `record_removed_from_snapshot` wird als `tombstone_candidate` berichtet.
- `schema_mismatch` wird als Blocking Finding berichtet.
- `forbidden_table` wird als Blocking Finding berichtet.
- Importplan-Actions mit `action: skip` bleiben im Reconcile `skip`, sofern
  keine Table-Policy- oder Schema-Safety-Blockade fuer denselben Record vorliegt.
- Wenn ein Plan fuer dieselbe `record_id` bereits eine fruehere Action enthaelt,
  erzeugen nachfolgende Plan-`skip`-Duplikate keine zweite Reconcile-Action und
  keine kuenstlichen create/update-Candidates.
- Plan-Warnings behalten beim Mapping in Reconcile-Findings ihre urspruengliche
  Severity; `warning` bleibt `warning`, `blocking` bleibt `blocking`.
- In blocked-plan Reconcile-Reports werden Plan-Warnings als Reconcile-Findings
  gespiegelt und nicht zusaetzlich als `warnings` doppelt gezaehlt.
- `counts.blocking` und `counts.warnings` bleiben getrennt: Blocking Findings
  oder blocking Plan-Warnings erhoehen nicht `counts.warnings`.
- Tombstones bleiben Kandidaten; kein Hard Delete und kein Apply-Verhalten.
- Blocking JSONL-/Plan-Findings blockieren auch den Reconcile-Report fail-closed
  mit Exit-Code `1`.

Artifact-zu-Table-Routing in #2071:

| JSONL-Artefakt | Ziel-Tabelle |
|---|---|
| `repo_artifacts.jsonl` | `repo_artifact` |
| `doc_pages.jsonl` | `doc_page` |
| `doc_sections.jsonl` | `doc_section` |
| `doc_chunks.jsonl` | `doc_chunk` |
| `code_symbols.jsonl` | `code_symbol` |
| `import_references.jsonl` | `import_reference` |
| `test_cases.jsonl` | `test_case` |
| `config_references.jsonl` | `config_reference` |
| `doc_code_links.jsonl` | `doc_code_link` |
| `dependency_edges.jsonl` | `dependency_edge` |

Die ersten fuenf Tabellen plus `dependency_edge` sind in
`infrastructure/surrealdb/context_intelligence_v0.surql` belegt. Die vier
Indexer-spezifischen Referenz-/Test-/Config-/Doc-Link-Tabellen werden in #2071
als import-plan-Ziele gefuehrt, aber nicht produktiv erstellt oder geschrieben.

Validierte JSONL-Artefakte:

```text
repo_artifacts.jsonl, doc_pages.jsonl, doc_sections.jsonl, doc_chunks.jsonl,
code_symbols.jsonl, import_references.jsonl, test_cases.jsonl,
config_references.jsonl, doc_code_links.jsonl, dependency_edges.jsonl
```

Validierung umfasst:

- JSONL-Syntax und Objekt-Records.
- Artefakt-spezifische Pflichtfelder.
- `schema_version == context-indexer/v0`.
- Einheitlichen bzw. per `--run-id` erwarteten `run_id`.
- `sha256`-Hashformate fuer Hash-Felder.
- Relative, nicht traversierende `source_path`-Werte.
- Trading-/Runtime-State-Pfadteile als Blocking Finding.
- Cross-References fuer `source_hash`, Page/Section/Chunk/Symbol-Verweise.
- Secret-like Keys/Werte als Blocking Finding ohne Wert-Echo.

Wenn `--config` gesetzt ist, wird die Antwort um `config_loaded: true` und ein
`config`-Objekt mit den validierten lokalen Config-Feldern erweitert. Das
Objekt ist Audit-/Debug-Ausgabe fuer lokale Entwicklung; es darf keine Secrets
enthalten.

Fehlerantwort:

```json
{
  "schema_version": "context-importer/v0",
  "status": "error",
  "error": "WRITE_DENIED",
  "message": "..."
}
```

`schema_version` ist Vertragskonstante (`context-importer/v0`) und wird
weder aus CLI-Args noch aus der Umgebung abgeleitet.

---

## 7. Anforderungen fuer Folge-Slices

- Folge-Slices duerfen das `validate-jsonl`-Antwort-Schema erweitern, aber
  `schema_version`, `command`, `status`, `dry_run`, `apply_requested`,
  `surrealdb_connection`, `validation` und `findings` muessen erhalten bleiben.
- Die Apply-Implementierung muss den Hard-Block ersetzen, NICHT lediglich
  umgehen, und muss zwingend einen Two-Step-Gate (`--apply`
  + zusaetzliche explizite Bestaetigung) bewahren.
- Jeder Slice, der eine SurrealDB-Verbindung einfuehrt, muss
  `surrealdb_connection` korrekt setzen und mindestens einen Test
  liefern, der den Connection-Pfad explizit verifiziert.
- Jeder Slice, der Secrets oder Authentifizierung nutzt, muss die
  Beispiel-Config secret-frei halten und echte Credentials ausserhalb der
  versionierten YAML laden.

---

## 8. Nicht-Ziele

#2071 aendert diese Nicht-Ziele nur fuer `plan --input-dir`: Die
Plan-Berechnung ist implementiert, bleibt aber read-only und DB-unabhaengig.
Dry-run-Reconcile, Apply, Audit und Rollback-Plan bleiben Nicht-Ziele.

- Keine SurrealDB-Verbindung.
- Kein SurrealDB-Write.
- Kein Apply-Verhalten aus validierten JSONL-Artefakten.
- Keine Dry-run-Reconcile-/Apply-/Audit-/Rollback-Logik.
- Keine Aenderung an Trading-, Risk-, Execution-, Secrets- oder
  Live-Readiness-Pfaden.
- Kein Echtgeld-/Live-Enable.
