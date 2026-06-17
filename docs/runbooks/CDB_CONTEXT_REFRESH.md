# CDB Context Refresh Runbook

**Zweck:** Zweimal woechentlich den aktuellen CDB-Repo-Kontext aus GitHub/Repo-Live-Wahrheit
in ein evidence-faehiges Context-/Brain-Paket ueberfuehren.

**Parent Epic:** [#3286](https://github.com/jannekbuengener/Claire_de_Binare/issues/3286)
**Erster operativer Slice:** [#3288](https://github.com/jannekbuengener/Claire_de_Binare/issues/3288)
**Report-only Workflow:** [#3287](https://github.com/jannekbuengener/Claire_de_Binare/issues/3287) — DIESER
**Agent Briefing Seed:** [#3290](https://github.com/jannekbuengener/Claire_de_Binare/issues/3290) — aus Context-Refresh-Artefakten
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

## 3. Report-only Workflow

Der GitHub Actions Workflow `.github/workflows/cdb-context-refresh-report.yml`
erzeugt zweimal pro Woche einen report-only Context Refresh Report.

### Schedule

| Tag | UTC | Europe/Berlin (CEST) | Europe/Berlin (CET) |
|-----|-----|---------------------|---------------------|
| Montag | 08:00 UTC | 10:00 | 09:00 |
| Donnerstag | 08:00 UTC | 10:00 | 09:00 |

Zusaetzlich ist `workflow_dispatch` fuer manuelle Ausfuehrungen moeglich.

### Permissions

- `contents: read`, `issues: read`, `pull-requests: read`, `actions: read`
- **Keine** write-Permissions
- **Keine** Secrets-Referenzen
- **Keine** Runtime-/Docker-Kommandos

### Artefakte

| Artefakt | Format | Beschreibung |
|----------|--------|-------------|
| `context_delta.json` | JSON | Maschinenlesbares Delta (Schema, Ref-Info, Open Issues/PRs, geaenderte Canon-Pfade, Safety-Boundaries, Limitations) |
| `context_refresh_summary.md` | Markdown | Menschlesbare Zusammenfassung (Timestamp, Schedule-Erklaerung UTC vs Berlin, Issue/PR-Kontext, Validator-Ergebnis, Safety-Grenzen) |
| `validation_report.json` | JSON | Validator-Selbsteinschaetzung (PASS / PASS_WITH_LIMITATIONS / BLOCKED, blocked_reasons, warnings, artifact_paths) |

### Report-Generator

Der Workflow nutzt `tools/context/generate_context_refresh_report.py` (Python, stdlib only).
Das Script sammelt lokale Git-Informationen und ruft `gh` fuer GitHub Issue/PR-Daten ab.

**Fail-closed:** Bei fehlenden Git-Refs oder nicht verfuegbarem `gh` erzeugt das Script
einen degraded Report mit Limitations, aber hartem Exit-Code 1 bei Core-Data-Fehlern.

### Safety Boundaries

- Report-only: keine DB-Writes, kein Brain Apply (#3289), keine Runtime-Aenderung.
- LR bleibt NO-GO. Kein Live-Go. Kein Echtgeld-Go.
- validation_report.json ist ein Selbst-Report des Generators, kein Context-Package-Validator (#3288).
- context_delta.json hat kein `records`-Feld und ist kein validiertes Context Package.

---

## 4. Pipeline (Gesamtuebersicht)

```
Repo live lesen (#3287, dieser Workflow)
    |
    v
Delta-Paket bauen (context_delta.json + validation_report.json)
    |
    v
Agent Briefing Seed (#3290) — aus 3 Artefakten
    |
    v (optional, nach Briefing)
Lokaler append-only Brain Apply (#3289) — spaeter
    |
    v
Drift Report (#3291) — spaeter
```

---

## 5. Agent Briefing Seed (#3290)

Das Agent Briefing Seed erzeugt aus den drei Context-Refresh-Artefakten
(`context_delta.json`, `context_refresh_summary.md`, `validation_report.json`)
einen kompakten, evidence-faehigen Kontext-Snapshot fuer schnelleren Agentenstart.

**Generator:** `tools/context/generate_agent_briefing_seed.py`

### Output-Artefakte

| Artefakt | Format | Beschreibung |
|----------|--------|-------------|
| `agent_briefing_seed.json` | JSON | Maschinenlesbarer Briefing-Seed (schema_version, brain_evidence_status, recommended_read_order, new_merges, open_context_prs/issues, changed_canon_files, new_evidence_files, stale_claims, stop_conditions, safety_boundaries, limitations) |
| `agent_briefing_seed.md` | Markdown | Menschlesbare Zusammenfassung mit allen required sections |

### CLI-Usage

```bash
# Aus Context-Refresh-Artefakten generieren
python tools/context/generate_agent_briefing_seed.py \
    --delta artifacts/context_delta.json \
    --summary artifacts/context_refresh_summary.md \
    --validation artifacts/validation_report.json \
    --output-dir artifacts/

# Ohne gh-CLI-Zugriff (nur Dateien)
python tools/context/generate_agent_briefing_seed.py \
    --delta artifacts/context_delta.json \
    --summary artifacts/context_refresh_summary.md \
    --validation artifacts/validation_report.json \
    --no-gh

# Hilfe
python tools/context/generate_agent_briefing_seed.py --help
```

### Exit Codes

- **0:** PASS — Briefing Seed erfolgreich generiert
- **1:** DEGRADED — mindestens ein Input-Artefakt fehlt oder ist unlesbar
- **2:** FAIL — unerwarteter Fehler

### Required Fields (JSON)

Das JSON-Output enthaelt folgende Pflichtfelder:

| Feld | Beschreibung |
|------|-------------|
| `schema_version` | Version des Briefing-Seed-Formats (`agent_briefing_seed.v1`) |
| `generated_at_utc` | ISO-8601 UTC-Zeitstempel |
| `source_artifacts` | Verwendete Input-Artefakte mit Version |
| `source_commit` | Git-Commit-SHA der Quelle |
| `brain_evidence_status` | Ob Brain-Evidence aus DB/Repo/nicht verfuegbar |
| `recommended_read_order` | Empfohlene Agent-Read-Reihenfolge (Primaervorschlag) |
| `new_merges` | Seit letztem Refresh gemergte PRs |
| `open_context_prs` | Offene PRs mit Kontextwirkung |
| `open_context_issues` | Offene Issues mit Kontextwirkung |
| `changed_canon_files` | Geaenderte Canon-Dateien |
| `new_evidence_files` | Neue Evidence-Dateien |
| `stale_claims` | Stale/unknown Claims aus Limitations/Warnings |
| `stop_conditions` | Safety-Stop-Conditions (built-in + aus Limitations) |
| `safety_boundaries` | Safety-Grenzen (LR NO-GO, kein Live-Go, etc.) |
| `limitations` | Bekannte Einschraenkungen |

### Required Sections (Markdown)

Das Markdown-Output enthaelt folgende Pflicht-Sections:

- `Agent Briefing Seed` - Header mit Metadaten
- `Source Artifacts` - Verwendete Input-Quellen
- `Brain Evidence Status` - Quelle und Status der Brain-Evidence
- `Recommended Read Order` - Prioritierte Lesereihenfolge
- `Context-Relevant Changes` - Canon- und Evidence-Aenderungen
- `Open PRs / Issues` - Aktuelle PRs/Issues mit Kontextwirkung
- `Stale or Unknown Claims` - Markierte Stale/Unknown Claims
- `Stop Conditions` - Safety-Stop-Conditions
- `Safety Boundaries` - LR/Echtgeld/Security-Grenzen
- `Limitations` - Bekannte Einschraenkungen

### Safety Boundaries

Das Briefing Seed enthaelt dieselben Safety-Grenzen wie das Context Package:

```json
{
  "lr_status": "NO-GO",
  "board_stage_is_live_go": false,
  "real_money_go": false,
  "productive_db_writes_allowed": false,
  "secrets_in_outputs_allowed": false,
  "trading_state_ingestion_allowed": false,
  "brain_apply_allowed": false,
  "drift_radar_allowed": false,
  "onboarding_allowed": false,
  "auto_issue_creation_allowed": false,
  "agent_authorization_allowed": false
}
```

### Evidence-Regeln

- Jeder Claim verweist auf Source/Commit/Hash, soweit die Input-Artefakte es liefern.
- Stale/unknown Claims werden explizit markiert (confidence: low/medium, marked_as: stale_or_unknown/blocking).
- Kein Briefing darf LR-/Live-/Echtgeld-Freigabe implizieren.
- Repo-/GitHub-live Claims haben Vorrang vor Ledger Claims.
- Wenn Input-Artefakte fehlen: degraded_report mit ehrlicher Statusmeldung; keine Fake-Fakten.
- Das Briefing ist **Kontext, keine Autorisierung**. Briefings duerfen nicht als Entscheidungsbefugnis interpretiert werden.

### Eingeschraenkte Scope-Grenzen

- Kein Brain Apply (#3289) — separater Follow-up-Slice
- Kein Drift Radar (#3291) — separater Follow-up-Slice
- Kein Onboarding (#3292) — separater Follow-up-Slice
- Keine Live-/Echtgeld-Implikation
- Keine DB-Writes

---

## 7. Safety-Grenzen (Nicht-Ziele)

- **Briefing Seed (#3290) ist Kontext, keine Autorisierung:** Das Agent Briefing
  Seed erzeugt einen kompakten evidence-faehigen Kontext-Snapshot. Es autorisiert
  keine Live-Trades, keine Runtime-Aenderungen und keine DB-Writes. Es ist keine
  Alternative zum Brain Apply (#3289).
- **Report/Validation only:** Dieses Schema und der Validator fuehren keinen
  Brain Apply durch. Das ist Scope von #3289. Der Workflow (#3287) ist ebenfalls
  report-only und erzeugt keine persistierenden Aenderungen.
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
- **#3289 Brain Apply ist nicht Teil dieses Workflows.** Brain Apply kommt in
  einem spaeteren Slice.
- **#3292 Onboarding Scenario bleibt zuletzt.**

---

## 8. Verwandte Issues

| Issue | Beschreibung | Status |
|-------|-------------|--------|
| #3286 | Parent Epic: Context Refresh Workflow | OFFEN |
| #3287 | Report-only GitHub Actions Workflow | DIESES |
| #3288 | Context Package Schema + Validator | ERLEDIGT (#3293) |
| #3289 | Lokaler append-only Brain Apply | OFFEN — spaeter |
| #3290 | Agent Briefing Seed | DIESES — DONE_MERGED_CLOSED |
| #3291 | Stale Documentation / Impact Radar | OFFEN — spaeter |
| #3292 | Onboarding Scenario (bewusst zuletzt) | OFFEN — zuletzt |
