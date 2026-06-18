# CDB Context Refresh Runbook

**Zweck:** Zweimal woechentlich den aktuellen CDB-Repo-Kontext aus GitHub/Repo-Live-Wahrheit
in ein evidence-faehiges Context-/Brain-Paket ueberfuehren.

**Parent Epic:** [#3286](https://github.com/jannekbuengener/Claire_de_Binare/issues/3286)
**Erster operativer Slice:** [#3288](https://github.com/jannekbuengener/Claire_de_Binare/issues/3288)
**Report-only Workflow:** [#3287](https://github.com/jannekbuengener/Claire_de_Binare/issues/3287) — DIESER
**Agent Briefing Seed:** [#3290](https://github.com/jannekbuengener/Claire_de_Binare/issues/3290) — aus Context-Refresh-Artefakten
**Drift Radar:** [#3291](https://github.com/jannekbuengener/Claire_de_Binare/issues/3291) — DIESER SLICE — siehe §6
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
    v
Drift Radar (#3291, DIESER SLICE) — aus Delta + Validation + optional Briefing
    |
    v (optional, nach Drift Radar)
Lokaler append-only Brain Apply (#3289) — siehe §7
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
- Drift Radar (#3291) — DIESER SLICE — siehe §6
- Kein Onboarding (#3292) — separater Follow-up-Slice
- Keine Live-/Echtgeld-Implikation
- Keine DB-Writes

---

## 6. Drift Radar (#3291)

Der Drift Radar ist ein read-only Scanner, der stale Dokumentation und
widerspruechliche Canon-/Ledger-/GitHub-Signale sichtbar macht.

**Generator:** `tools/context/generate_context_drift_radar.py`

### Input-Artefakte

| Artefakt | Pflicht | Beschreibung |
|----------|---------|-------------|
| `context_delta.json` | Ja | Aus dem Report-Workflow (#3287) |
| `validation_report.json` | Ja | Aus dem Report-Workflow (#3287) |
| `agent_briefing_seed.json` | Optional | Aus dem Briefing-Generator (#3290) |

### Drift-Kategorien

| Kategorie | Beschreibung | Default Severity |
|-----------|-------------|-----------------|
| `canon_pointer_drift` | Canon-Pointer-Dateien (AGENTS.md, WORKING_REPO_CANON) geaendert | medium |
| `ledger_vs_github_drift` | Offene Context-/Drift-Issues im Widerspruch zum Ledger | medium |
| `lr_status_ambiguity` | LR-Status weicht von NO-GO ab | high |
| `stale_architecture_docs` | Architecture-/Knowledge-Hub-Dateien geaendert | medium |
| `stale_onboarding_docs` | Onboarding-bezogene Dateien geaendert | medium |
| `stale_agent_bootloader_instructions` | Bootloader-/Agent-Surfaces geaendert | medium |
| `workflow_check_drift` | Validation-Report blockiert/warnt | high/medium |
| `unknown_high_risk_delta` | Limitations mit Live-/Echtgeld-/Secret-Indikatoren | high |

### Output-Artefakte

| Artefakt | Format | Beschreibung |
|----------|--------|-------------|
| `stale_claims.json` | JSON | Maschinenlesbare Claims (schema_version, generated_at_utc, source_artifacts, claims, summary, degraded, limitations) |
| `impact_radar.md` | Markdown | Menschlesbarer Impact-Bericht mit allen required sections |

Optional (via `--json`):
| `impact_radar.json` | JSON | Maschinenlesbare Impact-Radar-Struktur |

### Required Fields (stale_claims.json)

| Feld | Beschreibung |
|------|-------------|
| `schema_version` | Version des Claim-Formats (`stale_claims.v1`) |
| `generated_at_utc` | ISO-8601 UTC-Zeitstempel |
| `source_artifacts` | Verwendete Input-Artefakte mit Version |
| `claims[]` | Liste der Drift-Claims |
| `claims[].claim` | Beschreibung des Drifts |
| `claims[].drift_category` | Eine der 8 Drift-Kategorien |
| `claims[].severity` | high / medium / low |
| `claims[].source_ref` | Quelle des Claims im Input |
| `claims[].current_truth_ref` | Referenz auf aktuelle Wahrheit |
| `claims[].status` | blocking / changed / open / needs_review / stale_or_unknown / warning |
| `claims[].recommended_action` | Empfohlene Massnahme |
| `claims[].blocks_brain_apply` | true/false — blockiert dieser Claim Brain Apply? |
| `summary` | Zusammenfassung (total_claims, blocking, high/medium/low severity, blocks_brain_apply) |
| `degraded` | Ob das Radar degraded lief |
| `limitations` | Bekannte Einschraenkungen |

### Required Sections (impact_radar.md)

- `Context Drift / Impact Radar` — Header mit Metadaten
- `Source Artifacts` — Verwendete Input-Quellen
- `High-Risk Drift` — Claims mit severity=high
- `Brain Apply Blockers` — Claims mit blocks_brain_apply=true
- `Stale Claims` — Alle erkannten Drift-Claims
- `Canon / Ledger / GitHub Conflicts` — Kategorisierte Konflikte
- `Workflow / Check Drift` — Validierungs-Warnungen/Blockierungen
- `Recommended Follow-up Issues` — Report-only Issue-Empfehlungen (keine Auto-Anlage)
- `Safety Boundaries` — LR/Echtgeld/Security-Grenzen
- `Limitations` — Bekannte Einschraenkungen

### Brain-Apply-Blocking Policy

High-risk Drift blockiert Brain Apply (#3289) unter folgenden Bedingungen:

| Bedingung | Grund |
|-----------|-------|
| `severity == high` | Jeder high-severity Claim blockiert vorsorglich |
| `category == lr_status_ambiguity` | LR-Status-Abweichung ist immer blocking |
| `category == unknown_high_risk_delta` | Unbekannte high-risk Deltas blockieren |
| Claim impliziert Live-Go/Echtgeld-Go | Nur LR-SSOT darf Live-Status setzen |
| Claim involviert Secrets/Orders/Fills/Positions/Risk-State | Safety-Grenze |
| Erforderliche Canon-Quelle fehlt | Unvollstaendige Basis |
| GitHub/Repo-live widerspricht Briefing/Ledger-Claim | Live-Wahrheit gewinnt |

**Verdikt:** Der Radar bewertet Brain Apply als `blocked` oder `recommended_hold`.
Brain Apply (#3289) wird hier nicht implementiert — nur der Blocker-Report.

### Exit Codes

- **0:** PASS — Radar erfolgreich generiert, keine blocking Claims
- **1:** BLOCKED — High-risk Drift erkannt, Brain Apply blockiert
- **2:** FAIL — Unerwarteter Fehler (beide Pflicht-Inputs fehlen)

### CLI-Usage

```bash
# Aus Context-Refresh-Artefakten generieren
python tools/context/generate_context_drift_radar.py \
    --delta artifacts/context_delta.json \
    --validation artifacts/validation_report.json \
    --briefing artifacts/agent_briefing_seed.json \
    --output-dir artifacts/

# Mit optionalem JSON-Output
python tools/context/generate_context_drift_radar.py \
    --delta artifacts/context_delta.json \
    --validation artifacts/validation_report.json \
    --json \
    --output-dir artifacts/

# Hilfe
python tools/context/generate_context_drift_radar.py --help
```

### Safety Boundaries

- Drift Radar ist read-only: keine DB-Writes, kein Brain Apply (#3289), kein Onboarding (#3292).
- LR bleibt NO-GO. Kein Live-Go. Kein Echtgeld-Go.
- Reports empfehlen Folge-Issues, legen sie aber nicht automatisch an.
- High-risk Drift blockiert Brain Apply, aber der Radar fuehrt keinen Apply aus.
- Keine Secrets in Outputs (Secret-Indikatoren in Inputs werden als Limitation gemeldet).
- Keine Runtime-/Docker-/Trading-Aenderungen.

---

## 7. Lokaler append-only Brain Apply (#3289)

Der lokale append-only Brain Apply ueberfuehrt ein validiertes Context Package
in ein lokales, auditiertes Ledger/Artifact. Der Apply ist immer append-only:
bestehende Records werden niemals mutiert, geloescht oder ueberschrieben.

**Tool:** `tools/context/apply_context_brain_local.py`

### Pipeline-Stellung

Der Brain Apply ist der letzte Schritt nach Schema-Validierung (#3288),
Agent Briefing Seed (#3290) und Drift Radar (#3291). Er wird nur auf bereits
validierte Packages angewendet.

### CLI-Usage

```bash
# Dry-run (Default — keine Writes)
python tools/context/apply_context_brain_local.py \
    --package artifacts/context_package.json \
    --output-dir artifacts/

# Mit Drift-Radar-Check
python tools/context/apply_context_brain_local.py \
    --package artifacts/context_package.json \
    --drift-radar artifacts/impact_radar.json \
    --output-dir artifacts/

# Expliziter Apply (append-only Writes)
python tools/context/apply_context_brain_local.py \
    --package artifacts/context_package.json \
    --apply \
    --output-dir artifacts/

# Maschinenlesbarer JSON-Output
python tools/context/apply_context_brain_local.py \
    --package artifacts/context_package.json --json

# Hilfe
python tools/context/apply_context_brain_local.py --help
```

### Exit Codes

- **0:** OK — dry-run passed, oder apply erfolgreich (auch bei Duplicate-Skip)
- **1:** BLOCKED — Precondition-Fehler, Drift-Radar blockiert, Secrets/Tags
- **2:** FAIL — unerwarteter Fehler (Datei nicht gefunden, JSON-Fehler)

### Preconditions (fail-closed)

| Bedingung | Code | Auswirkung |
|-----------|------|-----------|
| Ungueltiges oder fehlendes Package | `missing_package_id`, `missing_source_commit` | BLOCKED |
| Nicht unterstuetzte Schema-Version | `unsupported_schema_version` | BLOCKED |
| Drift Radar `blocks_brain_apply=true` | divers | BLOCKED — Drift-Risiko |
| Secret-Indikator in summary/source_path | `secret_content` | BLOCKED |
| Verbotener Tag (live-trade, echtgeld, order, fill, position) | `forbidden_tag` | BLOCKED |

### Append-only Semantik

- Der Ledger (`_brain_ledger/brain_apply_ledger.json`) ist ein JSON-Array.
- Jeder Apply-Run fuegt ein neues Element hinzu (append).
- Bestehende Elemente werden niemals veraendert, geloescht oder ueberschrieben.
- Bei identischem Package-Fingerprint (gleiche package_id + source_commit +
  sortierte record_ids) wird der Run als `skipped_duplicate` markiert und
  produziert **keine** neuen Records im Ledger.

### Ausgabe-Struktur

**Ledger-Eintrag (pro Apply-Run):**

| Feld | Beschreibung |
|------|-------------|
| `apply_run_id` | Deterministische ID aus Fingerprint + Sequence |
| `source_package_fingerprint` | SHA-256-Fingerprint des Input-Packages |
| `schema_version` | `brain_apply.v1` (fest) |
| `package_id` | Originale Package-ID aus dem Input |
| `source_path` | Absoluter Pfad der Input-Datei |
| `generated_at_utc` | ISO-8601 UTC-Zeitstempel des Apply |
| `duplicate_fingerprint` | true/false — ob identischer Fingerprint bereits existierte |
| `duplicate_of_run_id` | run_id des Original-Runs bei Duplikat |
| `status` | `applied` oder `skipped_duplicate` |
| `summary` | records_applied, records_skipped, records_blocked, total |
| `records[]` | Angewandte Records (leer bei Duplikat) |

**Ledger-Record (pro angewandtem Context-Record):**

| Feld | Beschreibung |
|------|-------------|
| `entry_id` | Deterministische ID aus Content-Hash |
| `package_record_id` | Originale record_id aus dem Package |
| `content_hash` | SHA-256 des Record-Inhalts |
| `record_type` | Record-Typ (doc_record, decision_record, etc.) |
| `source_path` | Pfad der Quelldatei |
| `summary` | Zusammenfassung des Records |

### Deterministische Fingerprints

- **Package-Fingerprint:** SHA-256 von `package_id | source_commit | sortierte_record_ids`
- **Content-Hash:** SHA-256 von kanonischem JSON der Record-Felder
  (record_id, record_type, source_path, source_commit, source_hash, confidence)
- Keine Abhaengigkeit von Wall-Clock oder Laufzeitumgebung.

### Blocking Policy

| Ausloeser | Ergebnis |
|-----------|----------|
| Package-Schema ungueltig | BLOCKED — Apply nicht moeglich |
| Drift Radar blockiert | BLOCKED — Drift-Risiko verhindert Apply |
| Secret-Indikator gefunden | BLOCKED — keine Secrets im Ledger |
| Verbotene Tags | BLOCKED — Live/Echtgeld/Trading-Content |
| Gleicher Fingerprint bereits im Ledger | SKIPPED — idempotent, keine neuen Records |
| Alles OK | APPLIED — Records in Ledger geschrieben |

### Safety Boundaries

- **Keine produktiven DB-Writes:** Nur lokales JSON-Ledger (append-only).
- **Keine SurrealDB-, MCP- oder Runtime-Mutation.**
- **Keine Secrets in Outputs:** Secret-Indikatoren werden gemeldet, aber
  keine konkreten Secret-Werte ausgegeben.
- **Keine Trading-State-Ingestion:** Live-Trade-Tags werden blockiert.
- **LR bleibt NO-GO:** Unveraendert.
- **Kein Netzwerkzugriff:** Das Tool ist komplett offline.
- **Keine `PERSIST_ALLOWED`/`MUTATION_ALLOWED` Semantik.**
- **Default: dry-run/report-only.** Nur `--apply` triggert echte Writes.

---

## 8. Safety-Grenzen (Nicht-Ziele)

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
- **#3289 Brain Apply (§7) ist implementiert:** Lokaler append-only Apply auf
  validierte Packages. Default dry-run. Keine produktiven DB/SurrealDB/MCP-Writes.
- **#3291 Drift Radar (§6) ist read-only.** Es erzeugt Reports und blockiert
  ggf. Brain Apply, fuehrt aber keinen Apply aus.
- **#3292 Onboarding Scenario bleibt zuletzt.**

---

## 9. Verwandte Issues

| Issue | Beschreibung | Status |
|-------|-------------|--------|
| #3286 | Parent Epic: Context Refresh Workflow | OFFEN |
| #3287 | Report-only GitHub Actions Workflow | ERLEDIGT (#3294) |
| #3288 | Context Package Schema + Validator | ERLEDIGT (#3293) |
| #3289 | Lokaler append-only Brain Apply | DIESER — SIEHE §7 |
| #3290 | Agent Briefing Seed | ERLEDIGT (#3295) |
| #3291 | Stale Documentation / Impact Radar | DIESES — SIEHE §6 |
| #3292 | Onboarding Scenario (bewusst zuletzt) | OFFEN — zuletzt |
