# Context Indexer CLI Contract

**Status**: Draft
**Authority**: Issue #1989 / Epic #1976
**Target**: `tools/surrealdb/context_indexer.py` (Implementation: #2045)
**Scope**: Read-only, Dry-run-first Indexing & Export

---

## 1. Zweck
Dieser CLI-Vertrag definiert die Schnittstelle für den `context_indexer`. Ziel ist es, Code- und Dokumentations-Artefakte deterministisch zu discovern, zu hashen und für den späteren Import in die SurrealDB zu exportieren (JSONL).

---

## 2. Command-Modell (v0)
Der Indexer unterstützt folgende Modi:

| Command | Zweck | Implementierungs-Status |
|---------|-------|--------------------------|
| `scan` | Discovery, Klassifizierung & Hashing (Read-only) | V0 (Prio 1) |
| `plan` | Erstellung eines Import-Plans ohne Ausführung | V0 (Prio 1) |
| `export-jsonl` | Generierung der JSONL-Artefakte für SurrealDB | V0 (Prio 2) |
| `snapshot` | Generierung eines Status-Reports | V0 (Prio 2) |
| `validate` | Validierung der Ingestion-Artefakte gegen Schema | V0 (Prio 2) |

Format-Regeln pro Command:
- `export-jsonl` produziert immer JSONL (`--format` wird hier ignoriert).
- `scan` und `validate` liefern strukturierte Console-Resultate (kein Datei-Export).
- `plan` und `snapshot` dürfen `--format` (`json`, `jsonl`, `markdown`) auswerten.

---

## 3. Sicherheitsmodell & Guardrails
- **Read-only Default**: Alle Befehle sind standardmäßig Read-only.
- **Dry-run Default**: Schreibfähige Commands (`export-jsonl`, optionale Datei-Ausgaben von `plan`/`snapshot`) laufen standardmäßig im Dry-run.
- **Write Opt-in**: Dateischreiben ist nur erlaubt, wenn `--apply-writes` UND ein expliziter `--output`-Pfad gesetzt sind.
- **Keine SurrealDB-Verbindung in V0**: Der Scaffold darf in V0 keine DB-Verbindung aufbauen. SurrealDB-Argumente sind für zukünftige Slices (`import-surrealdb`, `drift`) reserviert.
- **Output-Pfade**: Writes dürfen NUR in freigegebene `artifacts/` oder `temp/` Pfade erfolgen.
- **No Secrets**: Der Indexer MUSS jeden Ingest-Kandidaten gegen den Secret-Scanner (`gitleaks`-Regeln) prüfen.

---

## 4. Argument-Vertrag

| Argument | Beschreibung | Erforderlich? |
|----------|--------------|---------------|
| `--root` | Root-Verzeichnis des Scans (Default: `.`) | Nein |
| `--scope-config` | Pfad zur `ingestion_scope.yaml` | Ja |
| `--output` | Basis-Output-Pfad (Default: `./artifacts`) | Nein |
| `--dry-run` | Nur Simulation, keine Dateierstellung | Nein |
| `--apply-writes` | Explizites Opt-in für Dateischreiben | Nein |
| `--format` | Output-Format (`json`, `jsonl`, `markdown`) | Nein |

---

## 5. Idempotenz & Determinismus
- **Stabile Sortierung**: Alle `scan`-Ergebnisse MÜSSEN über den Dateipfad sortiert sein.
- **Hashing**: Die deterministische Identität (`content_hash`) basiert auf `sha256` des normalisierten Inhalts + Pfad.
- **Zeitmetadaten getrennt halten**: Ein optionales Feld wie `observed_at` darf erfasst werden, darf aber NICHT Teil der Identitäts-/Hash-Basis sein.
- **Deterministische Snapshots**: Snapshots enthalten einen Hash des Gesamtzustands der Ingestion-Welle, abgeleitet aus deterministischen Einzel-Hashes und stabil sortierten Eingaben.

---

## 6. Exit-Codes

| Code | Bedeutung |
|------|-----------|
| 0 | Erfolg |
| 1 | Validierungsfehler (Checkliste nicht erfüllt) |
| 2 | Unsafe Path (Schreibversuch außerhalb `artifacts/` oder `temp/`) |
| 3 | Input-Datei nicht gefunden |
| 4 | Unsupported Format |
| 5 | Interner Fehler / Ingest-Anomalie |

---

## 7. Anforderungen für Codex (#2045)
Codex MUSS den Scaffold wie folgt implementieren:
- Keine DB-Verbindung hardcoden.
- `argparse` verwenden.
- Jede Funktion muss Unit-Tests (in `tests/unit/tools/`) haben.
- Keine automatischen Repo-Mutationen.

---

## 8. Validierung (für #2045)
- `python tools/surrealdb/context_indexer.py --help`
- `python tools/surrealdb/context_indexer.py scan --scope-config ./ingestion_scope.yaml --dry-run`
- Prüfung: Werden Secrets korrekt maskiert? (Test-Case mit Fake-Secret).
