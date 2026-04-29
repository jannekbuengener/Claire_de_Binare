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

---

## 3. Sicherheitsmodell & Guardrails
- **Read-only Default**: Alle Befehle sind standardmäßig Read-only.
- **Dry-run Default**: Schreibfähige Commands (`export-jsonl`, optionale Datei-Ausgaben von `plan`/`snapshot`) laufen standardmäßig im Dry-run.
- **Write Opt-in**: Dateischreiben ist nur erlaubt, wenn `--apply-writes` UND ein expliziter `--output`-Pfad gesetzt sind.
- **Keine SurrealDB-Verbindung in V0**: Der Scaffold darf in V0 keine DB-Verbindung aufbauen. SurrealDB-Argumente sind für zukünftige Slices (`import-surrealdb`, `drift`) reserviert.
- **Output-Pfade**: Writes dürfen NUR unter `artifacts/` oder `temp/` erfolgen. Verboten sind absolute Pfade (z. B. führendes `/`, Laufwerkspräfixe wie `C:\`, UNC-Pfade) sowie relative Pfade, die nach Normalisierung außerhalb dieser Basispfade aufgelöst würden (Traversal über `..`). Verstöße MÜSSEN mit Exit-Code `5` stoppen.
- **No Secrets**: Der Indexer MUSS jeden Ingest-Kandidaten gegen den Secret-Scanner (`gitleaks`-Regeln) prüfen. Nicht maskierbare Treffer sind fail-closed zu behandeln (Exit-Code `5`).

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

## 5. Deterministische Identität & Hashing
- **Stabile Sortierung**: Alle `scan`-Ergebnisse MÜSSEN über den Dateipfad sortiert sein.
- **Contract-Konstante**: `schema_version = "context-indexer/v0"` ist eine feste Konstante des Vertrags und darf nicht aus CLI-Args, Environment oder Dateiinhalten abgeleitet werden.
- **Artifact Identity**: Die deterministische Identität basiert ausschließlich auf `repo_rel_path` + `content_sha256` (normalisierter Inhalt, UTF-8/LF) + `schema_version`.
- **Zeitmetadaten getrennt halten**: Ein optionales Feld wie `observed_at` darf erfasst werden, darf aber NICHT Teil der Identitäts-/Hash-Basis sein.
- **Deterministische Snapshots**: Snapshots enthalten einen Hash des Gesamtzustands der Ingestion-Welle, abgeleitet aus deterministischen Einzel-Hashes und stabil sortierten Eingaben.

---

## 6. Exit-Codes

| Code | Bedeutung |
|------|-----------|
| 0 | Erfolg |
| 1 | Validierungsfehler (Checkliste nicht erfüllt) |
| 2 | CLI Usage / Argument-Parsing-Fehler (z. B. `argparse` bei invaliden/missing Args) |
| 3 | Input-Datei nicht gefunden |
| 4 | Unsupported Format |
| 5 | Write denied (Pfad-Verstoß oder nicht maskierbarer Secret-Treffer) |
| 6 | Interner Fehler / Ingest-Anomalie |

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
- Prüfung: Abweisung von Pfad-Traversierung in `--output` (Exit-Code `5`).
