# CDB Testing Knowledge

Status: active local index

This folder contains CDB testing guidance and planning maps. It is knowledge,
not executable test code.

## Current Entries

| File | Purpose |
|---|---|
| `TEST_HARNESS_V1.md` | Historical test execution guide and local command map. |
| `PAPER_TRADING_TEST_REQUIREMENTS.md` | Early P0 paper-trading scenario requirements. |
| `PERFORMANCE_BASELINES.md` | Draft latency and throughput baseline targets. |
| `MOCKEXCHANGE_CDB_TEST_MAP.md` | Active map for turning MockExchange reference patterns into CDB-native tests. |
| `TEST_FIRST_PROCESSING_CONTRACT.md` | Active contract: test metadata standard, 15 test types, SurrealDB knowledge model, processing pipeline. |
| `SKILL_VALLEY_TEST_UPGRADE_PLAN.md` | Active plan: 8 skill rules agents must learn before scaling tests. |

## Scanner

`tools/test_metadata_scanner.py` — read-only CDB Test-First Metadata Scanner.

Aktueller Pilot-Block: `tests/unit/validation/test_profitability_evidence_packet_assembler.py`
(`CDB-PILOT-001`).

**Zweck:** Findet 15-field Metadatenbloecke in Python-Testdateien, validiert
Pflichtfelder und gibt ein JSON-Artefakt aus — Vorstufe zum SurrealDB-Import.

**read-only Grenze:** Der Scanner schreibt nur in die explizit per `--output`
angegebene Datei. Kein DB-Zugriff, kein Netzwerk, keine Mutation ausserhalb
der Output-Datei.

**Nutzung:**
```bash
# Stdout
python -m tools.test_metadata_scanner tests/

# Datei
python -m tools.test_metadata_scanner tests/ --output artifacts/test-metadata.json

# Einzelfile
python -m tools.test_metadata_scanner tests/unit/validation/test_profitability_evidence_packet_assembler.py
```

**Exit-Codes:**
- 0: alle Bloecke gueltig (oder keine gefunden)
- 1: Validierungsfehler (fehlende Pflichtfelder)
- 2: Usage-/Parse-Fehler (keine Python-Dateien)

**SurrealDB-Export:** `surrealdb_export: true` markiert genau einen
Metadatenblock als exportfreigegeben fuer das JSON-Artefakt des Scanners. Im
JSON erscheint das als Block-Feld und im Report als
`"surrealdb_export_ready"`-Zaehler. Das ist kein SurrealDB-Write und keine
Import-Freigabe; ein spaeterer Importer bleibt ein eigener Slice.

## Import-Bundle-Builder

`tools/test_metadata_import_bundle.py` — read-only SurrealDB-ready Import-Bundle-Builder.

**Zweck:** Transformiert das JSON des Scanners in ein deterministisches,
SurrealDB-kompatibles Import-Bundle. Nur Blöcke mit `is_valid: true` und
`surrealdb_export: true` werden übernommen. Kein DB-Zugriff, kein Netzwerk,
keine Mutation.

**Record-Format:**
- `record_type: test_case` (aligniert mit `TEST_FIRST_PROCESSING_CONTRACT.md`)
- `record_id` aus `source_file` + `test_id` (deterministisch, stabil)
- `content_hash` per `canonical_hash()` aus `core/replay/canonical_json.py`
- `pilot_id` wird aus `test_id` abgeleitet (Pattern: `cdb-test-pilot-NNN`)
- `metadata` enthält alle Scanner-Felder unverändert

**Nutzung:**
```bash
# Pipe aus Scanner
python -m tools.test_metadata_scanner tests/ --output artifacts/scanner-report.json
python -m tools.test_metadata_import_bundle artifacts/scanner-report.json

# Datei
python -m tools.test_metadata_import_bundle artifacts/scanner-report.json --output artifacts/import-bundle.json

# Stdin
python -m tools.test_metadata_scanner tests/ | python -m tools.test_metadata_import_bundle -
```

**Exit-Codes:**
- 0: valides Bundle erzeugt
- 1: keine exportierbaren Blöcke oder Validierungsfehler
- 2: Parse-/Usage-Fehler

**Path-Sicherheit:** Absolute Pfade (Windows-Laufwerkbuchstabe oder führender
Schrägstrich) werden fail-closed abgelehnt.

## Guardrail

Testing knowledge does not authorize runtime, Docker, exchange, database, or
live-capital actions. LR remains NO-GO unless the canonical live-readiness SSOT
states otherwise.
