# Context Importer CLI Contract

**Status**: Draft (Scaffold + Local Config Slice)
**Authority**: Issue #2068 + #2069 / Wave 10 Parent #2067 / Epic #1976
**Target**: `tools/surrealdb/context_importer.py`
**Scope**: CLI scaffold plus explicit local config validation — no SurrealDB connection, no writes, no JSONL parsing.

---

## 1. Zweck

Dieser Vertrag beschreibt die CLI-Oberflaeche fuer den zukuenftigen
Context-Import-Pfad (JSONL-Artefakte aus dem Context Indexer nach SurrealDB).
In #2068 wurde ausschliesslich das Scaffold geliefert: Argument-Parsing,
Help-Text, Default-Verhalten und Safety-Gates. #2069 ergaenzt eine explizite
lokale Config-Lade- und Validierungsschicht fuer
`infrastructure/config/surrealdb/context_import.local.example.yaml`.
Jede echte Logik (JSONL-Validation, Plan-Berechnung, Apply, Audit,
Rollback-Plan) gehoert weiterhin zu separaten Folge-Slices.

---

## 2. Command-Modell (v0, Scaffold)

| Command | Zweck (Endziel) | Verhalten in #2068 |
|---|---|---|
| `validate-jsonl` | JSONL-Artefakte gegen Schema pruefen | Stub: `scaffold-ack`, Exit `0` |
| `plan` | Diff JSONL ↔ SurrealDB berechnen | Stub: `scaffold-ack`, Exit `0` |
| `dry-run` | End-to-End-Lauf ohne Schreiben | Stub: `scaffold-ack`, Exit `0` |
| `apply` | Schreiben nach SurrealDB | Hart geblockt: Exit `5` (`WRITE_DENIED`) |
| `audit` | Audit-Trail-Export | Stub: `scaffold-ack`, Exit `0` |
| `rollback-plan` | Rollback-Plan generieren | Stub: `scaffold-ack`, Exit `0` |

`apply` existiert als Subcommand und auch als globales Flag `--apply`. Beide
Pfade fuehren in #2068 zu Exit-Code `5`. Die Tests bestaetigen das als
hartes Sicherheitsnetz; das Verhalten darf erst durch einen expliziten
Folge-Slice (Apply-Implementation) entfernt werden.

---

## 3. Sicherheitsmodell und Guardrails

- **Read-only Default**: Alle Subcommands sind Stubs, die nur eine
  deterministische JSON-Antwort drucken.
- **Dry-run Default**: Ohne explizites `--apply` ist `dry_run = true`.
- **Apply hart geblockt**: `--apply` und `apply` exit `5` (`WRITE_DENIED`).
- **Keine SurrealDB-Verbindung**: `--surreal-url`, `--namespace`,
  `--database` werden geparsed, aber nie verwendet. Die Antwort enthaelt
  immer `surrealdb_connection: "disabled"`.
- **Output-Pfad-Whitelist**: `--report-output` muss unter `artifacts/`
  oder `temp/` liegen. Absolute Pfade (`/...`, `C:\...`, UNC) und
  Traversal (`..`) werden mit Exit `5` verworfen. Der Scaffold schreibt
  selbst nichts.
- **Config nur explizit**: `--config` wird nur geladen, wenn der Pfad explizit
  uebergeben wird. Ohne `--config` laeuft der Scaffold weiter ohne Config.
- **Config fail-closed**: `allow_apply_default` muss `false` sein; Trading-
  State-Tabellen und Governance-Mirror-Tabellen duerfen nicht in
  `allowed_tables` erscheinen und muessen in `forbidden_tables` enthalten sein.
- **Keine Secrets in Beispiel-Config**:
  `infrastructure/config/surrealdb/context_import.local.example.yaml` enthaelt
  nur lokale Platzhalter. Reale Credentials muessen aus `SECRETS_PATH` oder
  der Laufzeitumgebung kommen, nicht aus dieser YAML.
- **Keine JSONL-Validation-Logik**: gehoert zu Folge-Slice.
- **Keine Plan-/Audit-/Rollback-Logik**: jeweils eigene Folge-Slices.

---

## 4. Argument-Vertrag (pro Subcommand)

| Argument | Default | Pflicht? | Verhalten im Scaffold |
|---|---|---|---|
| `--input-dir` | `None` | nein | nicht gelesen |
| `--surreal-url` | `""` | nein | nicht verwendet |
| `--namespace` | `None` | nein | nicht verwendet |
| `--database` | `None` | nein | nicht verwendet |
| `--run-id` | `None` | nein | nur geparsed |
| `--config` | `None` | nein | explizite lokale YAML laden und validieren, kein Write |
| `--report-output` | `None` | nein | Whitelist-Check, kein Write |
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
| 0 | Erfolg / Scaffold acknowledged |
| 1 | Validierungsfehler (reserviert; im Scaffold nicht ausgeloest) |
| 2 | CLI-Usage / argparse-Fehler |
| 3 | Input-/Config-Datei nicht gefunden |
| 4 | Unsupported Format (defensiv; argparse faengt das frueher) |
| 5 | Write denied (Pfad-Verstoss ODER Apply im Scaffold) |
| 6 | Interner Fehler |

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

- `validate-jsonl`-Implementierung darf das Antwort-Schema erweitern,
  aber `schema_version`, `command`, `status`, `dry_run`,
  `apply_requested`, `surrealdb_connection` muessen erhalten bleiben.
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

## 8. Nicht-Ziele in #2068

- Keine SurrealDB-Verbindung.
- Kein SurrealDB-Write.
- Keine JSONL-Validierung.
- Keine Plan-/Apply-/Audit-/Rollback-Logik.
- Keine Aenderung an Trading-, Risk-, Execution-, Secrets- oder
  Live-Readiness-Pfaden.
- Kein Echtgeld-/Live-Enable.
