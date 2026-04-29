# Context Intelligence CLI Contract

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
- **Dry-run Default**: Aktionen, die Schreibvorgänge (Output-Files) auslösen, erfordern `--dry-run` oder explizite Pfad-Zuweisung.
- **Keine SurrealDB-Verbindung in V0**: Der Scaffold darf in V0 keine DB-Verbindung aufbauen. SurrealDB-Argumente sind für zukünftige Slices (`import-surrealdb`, `drift`) reserviert.
- **Output-Pfade**: Writes dürfen NUR in freigegebene Pfade unter `artifacts/context-indexer/` oder `tmp/context-indexer/` erfolgen. Absolute Pfade oder Pfad-Traversierung (`../`, `/`) sind verboten. Writes außerhalb erlaubter Pfade MÜSSEN mit Exit-Code `5 write denied` stoppen.
- **No Secrets**: Der Indexer darf keine Secret-Inhalte exportieren. Treffer gegen bekannte Secret-Patterns (basierend auf Projekt-Gitleaks-Regeln) müssen maskiert oder als "blocked"/"omitted" im Artefakt markiert werden. Bestehende CI-Validierungsflächen (wie Gitleaks) dienen als ergänzende Sicherheitsinstanz; der Indexer agiert bei unmaskierbaren Treffern "fail-closed".

---

## 4. Argument-Vertrag

| Argument | Beschreibung | Erforderlich? |
|----------|--------------|---------------|
| `--root` | Root-Verzeichnis des Scans (Default: `.`) | Nein |
| `--scope-config` | Pfad zur `ingestion_scope.yaml` | Ja |
| `--include` | Zusätzliche Inklusionsmuster (glob) | Nein |
| `--exclude` | Zusätzliche Exklusionsmuster (glob) | Nein |
| `--commit` | Git-Commit-Hash zur Referenzierung | Nein |
| `--output` | Basis-Output-Pfad (Default: `./artifacts/context-indexer`) | Nein |
| `--dry-run` | Nur Simulation, keine Dateierstellung | Nein |
| `--format` | Output-Format (`json`, `jsonl`, `markdown`) | Nein |

*Hinweis: `--scope` wurde nicht implementiert, um Eindeutigkeit zum Scope-Management durch die zentrale `ingestion_scope.yaml` zu wahren.*

---

## 5. Deterministische Identität & Hashing
- **Stabile Sortierung**: Alle `scan`-Ergebnisse MÜSSEN über den Dateipfad sortiert sein.
- **Artifact Identity**: Identität basiert ausschließlich auf einer stabilen Kombination aus: `repo_rel_path` + `content_sha256` (normalisierter Inhalt) + `schema_version`.
- **Zeitstempel**: Zeitstempel (`observed_at`) sind Snapshot-/Report-Metadaten und dürfen **nicht** Bestandteil der Identity (Hash) sein.
- **Normalisierung**: Vor dem Hashing sind Zeilenenden (LF) und Encodings (UTF-8) deterministisch zu normalisieren.

---

## 6. Exit-Codes

| Code | Bedeutung |
|------|-----------|
| 0 | Erfolg |
| 1 | Validierungsfehler (Checkliste nicht erfüllt) |
| 2 | Unsafe Path (Schreibversuch außerhalb zulässiger Pfade) |
| 3 | Input-Datei nicht gefunden |
| 4 | Unsupported Format |
| 5 | Write denied (Secret-Treffer oder Pfad-Verstoß) |
| 6 | Interner Fehler / Ingest-Anomalie |

---

## 7. Acceptance Criteria für spätere Implementierung (#2045)
Die spätere Implementierung (#2045) muss:
- Keine DB-Verbindung hardcoden.
- `argparse` verwenden.
- Jede Funktion muss Unit-Tests (in `tests/unit/tools/`) haben.
- Keine automatischen Repo-Mutationen.

---

## 8. Validierung (für #2045)
- `python tools/surrealdb/context_indexer.py --help`
- `python tools/surrealdb/context_indexer.py scan --scope-config ./ingestion_scope.yaml --dry-run`
- Prüfung: Werden Secrets maskiert? (Test-Case mit Fake-Secret).
- Prüfung: Determinismus (zweimaliger Scan auf gleichem Commit muss identische Hashes liefern).
- Prüfung: Abweisung von Pfad-Traversierung in `--output` (Exit-Code 5).
