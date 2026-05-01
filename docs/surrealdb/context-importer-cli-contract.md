# Context Importer CLI Contract

**Status**: Draft (Scaffold + Local Config + JSONL Validation + Import Plan + Dry-run Reconcile + Gated Local-Dev Apply + Tombstones Slice)
**Authority**: Issue #2068 + #2069 + #2070 + #2071 + #2072 + #2073 + #2074 / Wave 10 Parent #2067 / Epic #1976
**Target**: `tools/surrealdb/context_importer.py`
**Scope**: CLI scaffold plus explicit local config validation, read-only JSONL validation, deterministic import plan generation, dry-run reconcile against explicit read-only existing-record fixtures, and a **gated local-dev apply pipeline with a mockable adapter boundary** (default in-memory adapter, no production SurrealDB activation, no default network) that performs tombstone-only deletions via an injectable clock. The real SurrealDB adapter is **explicitly out-of-scope** in this slice.

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
| `apply` | Schreiben nach SurrealDB | Gated local-dev only: erfordert `--apply` + `--apply-mode local-dev` + `--config` + `--input-dir` + `--run-id`. Default-Adapter ist in-memory ohne Netz. Real-SurrealDB-Adapter ist explizit out-of-scope. Ohne vollstaendige Gates Exit `5` (`WRITE_DENIED`). |
| `audit` | Audit-Trail-Export | Stub: `scaffold-ack`, Exit `0` |
| `rollback-plan` | Rollback-Plan generieren | Stub: `scaffold-ack`, Exit `0` |

`apply` existiert als Subcommand und auch als globales Flag `--apply`. Auf
allen Nicht-`apply`-Subcommands fuehrt `--apply` weiterhin zu Exit `5`. Auf
dem `apply`-Subcommand ist `--apply` notwendig, aber nicht hinreichend; ohne
`--apply-mode local-dev`, ohne `--config`, ohne `--input-dir` oder ohne
`--run-id` wird Exit `5` zurueckgegeben. Der Default-Adapter ist eine
mockbare in-memory Boundary; ein realer SurrealDB-Adapter ist nicht
implementiert und nicht ueber die CLI selektierbar.

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
- **Kein Apply-/Audit-/Rollback-Verhalten**: Audit und Rollback bleiben
  Folge-Slices. Reconcile in #2072 bleibt dry-run-only. Apply in #2073/#2074
  ist auf `--apply-mode local-dev` mit dem in-memory Adapter beschraenkt; es
  oeffnet keinen produktiven SurrealDB-Pfad und schreibt keine Trading- oder
  Governance-Tabellen.
- **No production SurrealDB activation**: Es existiert kein realer SurrealDB-
  Adapter in diesem Slice (`real_surrealdb_adapter_available = false`).
- **Tombstone-only deletions**: Es gibt keinen Hard-Delete; der Default-Adapter
  exponiert keine `delete`/`apply_delete`-API.

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
| `--apply` | `False` | nein | Notwendig, aber nicht hinreichend fuer `apply`; auf jedem anderen Subcommand ⇒ Exit `5` |
| `--apply-mode` | `None` | fuer `apply` ja | Nur `local-dev` ist erlaubt; argparse rejects andere Werte. Ohne diesen Mode bleibt `apply` Exit `5` |
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

### Effective Apply-Table-Policy

Beim `apply`-Pfad gilt eine strikt restriktive, fail-closed Tabellen-Policy:

```text
allow_effective  = ALLOWED_CONTEXT_IMPORT_TABLES ∩ config.allowed_tables
forbid_effective = FORBIDDEN_CONTEXT_IMPORT_TABLES ∪ config.forbidden_tables
```

Regeln:

- Eine Tabelle wird nur angewendet, wenn sie in `allow_effective` ist und nicht
  in `forbid_effective`.
- `config.allowed_tables` ist restriktiv, niemals dekorativ: eine Tabelle, die
  global erlaubt waere, der Operator aber bewusst aus `config.allowed_tables`
  entfernt hat, wird beim Apply blockiert. Es gibt keinen Fallback auf die
  globale Allow-Liste.
- `config.allowed_tables` darf die globale Allow-Liste niemals erweitern.
  Eine Tabelle, die nicht in `ALLOWED_CONTEXT_IMPORT_TABLES` steht, bleibt
  blockiert, auch wenn der Operator sie in `config.allowed_tables` aufnimmt.
- Forbidden schlaegt Allowed: jede Quelle (global oder config) reicht aus, um
  eine Tabelle zu blocken.
- Block-Findings nennen Tabelle und Grund, leaken aber keine Payload-,
  Hash- oder Secret-Werte.

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

## 5.2 Gated Local-Dev Apply (#2073)

`apply --apply --apply-mode local-dev --config <yaml> --input-dir <dir> --run-id <id>`
fuehrt eine **gated local-dev apply pipeline** gegen eine **mockable adapter
boundary** aus. Default ist der `InMemoryContextApplyAdapter`; **no production
SurrealDB activation**, kein Default-Netzwerk-Connect.

Gates (alle muessen erfuellt sein, sonst Exit `5`):

- `--apply` gesetzt.
- `--apply-mode local-dev` gesetzt (argparse erlaubt nur `local-dev`).
- `--config <yaml>` zeigt auf eine valide lokale Config (siehe §4.1).
- `--input-dir <dir>` enthaelt validierbare JSONL-Artefakte (siehe §4).
- `--run-id <id>` ist gesetzt.
- Config-`surreal_url` host ist `127.0.0.1`, `::1` oder `localhost`.
- Reconcile-Report enthaelt keine Blocking Findings (sonst Exit `1`).

Adapter-Vertrag:

| Property | Vertrag |
|---|---|
| Default-Adapter | `InMemoryContextApplyAdapter`; `adapter_kind = "in-memory"` |
| Netzwerk | nie geoeffnet; `surrealdb_connection = "in-memory-no-network"` |
| `apply_create(table, record_id, payload)` | Pflicht |
| `apply_update(table, record_id, payload)` | Pflicht |
| `apply_tombstone(table, record_id, payload)` | Pflicht; payload muss `TOMBSTONE_REQUIRED_FIELDS` enthalten |
| `delete` / `apply_delete` / `hard_delete` | **darf nicht existieren** |
| Reale SurrealDB-Verbindung | nicht implementiert; `real_surrealdb_adapter_available = false` |

Reconcile-zu-Apply-Mapping:

| Reconcile-Action | Apply-Op |
|---|---|
| `create` | `create` |
| `update_candidate` | `update` |
| `tombstone_candidate` | `tombstone` |
| `skip` | dropped (no apply op) |

Per-Op-Fehler des Adapters werden als `failed`-Result gesammelt und brechen
die Pipeline nicht ab. Die CLI mappt:

- Blocking Findings ⇒ Exit `1`.
- Mindestens ein `failed` ⇒ Exit `6`.
- Mindestens ein `blocked` (Table-Policy zur Apply-Zeit) ⇒ Exit `5`.
- Sonst Exit `0`.

Determinismus:

- Operationen sind nach `(op_kind, table, record_id)` deterministisch sortiert.
- Bei identischer Eingabe und identischem `ClockProvider` ist der gesamte
  Apply-Report byte-identisch.
- Es werden keine Payload-Werte oder Secrets in den Report geleakt; nur
  `payload_hash` (sha256), Tabelle und Record-ID.

---

## 5.3 Tombstone-Semantik (#2074)

Tombstones sind die **einzige** Form der Loeschung in dieser Pipeline. Es gibt
keinen Hard Delete und keine Adapter-Delete-API.

Pflichtfelder im Tombstone-Payload (`TOMBSTONE_REQUIRED_FIELDS`):

| Feld | Vertrag |
|---|---|
| `tombstoned` | `true` (`false` wird vom Adapter als `ApplyAdapterError` abgelehnt) |
| `tombstoned_at` | reales ISO8601-UTC mit trailing `Z`, erzeugt aus dem injizierbaren `ClockProvider` (`core.utils.clock`); kein Sentinel-Marker, kein `<run-derived>` |
| `tombstone_reason` | Default `record_removed_from_snapshot` |
| `last_seen_run_id` | Run-ID des letzten Sees-Snapshots oder `null` |
| `superseded_by` | reserviert; in v0 immer `null` |

Verhalten:

- `tombstone_candidate` aus `dry-run` reconcile wird in `apply` zu einer
  Tombstone-Op gegen den Default-Adapter.
- Der Adapter ueberschreibt das Original-Record nicht; es bleibt erhalten und
  bekommt die Tombstone-Felder dazu.
- Original-Record-Felder werden auch dann erhalten, wenn das Record nicht
  ueber einen vorhergehenden `apply_create`/`apply_update` im selben Adapter-
  Prozess liegt: enthaelt der `--existing-records`-Eintrag ein `payload`-Objekt,
  wird dieses verbatim (ohne Envelope-Steuerschluessel wie `payload_hash`,
  `schema_version`, `table`, `record_id`, `id`, `__line`) in die Tombstone-
  Payload uebernommen und von der Tombstone-Metadata (`tombstoned`,
  `tombstoned_at`, `tombstone_reason`, `last_seen_run_id`, `superseded_by`)
  sowie den Identitaetsfeldern (`table`, `record_id`, `run_id`, `payload_hash`)
  ueberlagert. Liefert der Eintrag nur einen `payload_hash`-String, bleibt die
  Tombstone-Payload bei der deterministischen Minimalform. Die uebernommenen
  Felder werden ausschliesslich an den Adapter weitergereicht und nie in
  Reports oder Result-Detailtexten serialisiert.
- `tombstoned_at` wird ausschliesslich aus dem injizierten `ClockProvider`
  erzeugt; `datetime.now()`/`datetime.utcnow()` darf im Apply-Pfad nicht
  benutzt werden. `FixedClock` liefert byte-identische Reports.
- Re-Emergenz (Record taucht nach Tombstone wieder im Snapshot auf) wird in
  v0 nur informativ als `note: re-emerged_after_tombstone` markiert; es gibt
  keine Untombstone-Semantik.

Per-Tabelle gilt das fuer alle in §6 gerouteten Tabellen, getestet
explizit fuer `doc_page`, `doc_chunk`, `code_symbol` und `dependency_edge`.

---



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
- Die Apply-Implementierung in #2073/#2074 ersetzt den frueheren Hard-Block
  fuer das `apply`-Subcommand durch einen mehrstufigen Gate
  (`--apply` + `--apply-mode local-dev` + `--config` + `--input-dir`
  + `--run-id` + lokaler Host + Reconcile ohne Blocking Findings). Auf allen
  Nicht-`apply`-Subcommands bleibt `--apply` ⇒ Exit `5`. Ein zukuenftiger
  realer SurrealDB-Adapter darf diesen Gate nicht aufweichen.
- Jeder Slice, der eine SurrealDB-Verbindung einfuehrt, muss
  `surrealdb_connection` korrekt setzen und mindestens einen Test
  liefern, der den Connection-Pfad explizit verifiziert.
- Jeder Slice, der Secrets oder Authentifizierung nutzt, muss die
  Beispiel-Config secret-frei halten und echte Credentials ausserhalb der
  versionierten YAML laden.

---

## 8. Nicht-Ziele

#2071 aendert diese Nicht-Ziele nur fuer `plan --input-dir`. #2073/#2074
aendern sie nur fuer `apply` im gated local-dev Modus mit der mockable
adapter boundary; ein realer SurrealDB-Adapter ist explizit out-of-scope.
Audit und Rollback-Plan bleiben Nicht-Ziele.

- Keine produktive SurrealDB-Verbindung (`real_surrealdb_adapter_available = false`).
- Kein Default-Netzwerk-Connect; in-memory adapter ist Default.
- Kein Hard Delete; nur Tombstones.
- Kein Apply ausserhalb von `--apply-mode local-dev` mit lokalem Host.
- Kein Schreiben in Trading-, Risk-, Execution- oder Governance-Mirror-Tabellen.
- Keine Audit-/Rollback-Logik.
- Keine Aenderung an Trading-, Risk-, Execution-, Secrets- oder
  Live-Readiness-Pfaden.
- Kein Echtgeld-/Live-Enable.
