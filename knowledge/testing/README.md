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
| `TEST_FIRST_METADATA_PILOT.md` | Pilot: Test-First-Metadatenblock in `tests/unit/validation/test_profitability_evidence_packet_assembler.py` — Proof-of-Concept fuer SurrealDB-Export-faehige Metadaten. |

## Scanner

`tools/test_metadata_scanner.py` — read-only CDB Test-First Metadata Scanner.

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

**SurrealDB-Export:** `surrealdb_export: true` wird im JSON sichtbar als
`"surrealdb_export_ready"`-Zaehler. Dieser Scanner schreibt noch nicht nach
SurrealDB — er bereitet nur den Export vor.

## Guardrail

Testing knowledge does not authorize runtime, Docker, exchange, database, or
live-capital actions. LR remains NO-GO unless the canonical live-readiness SSOT
states otherwise.
