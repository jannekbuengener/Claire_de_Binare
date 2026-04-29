# Context Indexer Implementation Readiness Check (v0)

**Status**: Draft
**Authority**: Issue #2044 / Epic #1976
**Target**: `tools/surrealdb/context_indexer.py` (Codex Implementation #2045)
**Scope**: Read-only, Dry-run-first Indexing

---

## 1. Zweck
Dieses Dokument stellt sicher, dass alle Voraussetzungen für den Implementierungsslice #2045 durch Codex erfüllt sind. Es dient als "Pre-Flight Check" für die Scaffold-Erstellung.

---

## 2. Gate-Checkliste (Pre-Implementation)

| # | Anforderung | Validierungs-Methode | Status |
|---|-------------|----------------------|--------|
| R1 | CLI-Vertrag (#1989) ist landed | Review `docs/surrealdb/context-indexer-cli-contract.md` | YES |
| R2 | Handoff-Guide (#2040) ist landed | Review `docs/surrealdb/context-agent-handoff.md` | YES |
| R3 | Scope-Config-Format definiert | Review `ingestion_scope.yaml` Muster | YES |
| R4 | Keine DB-Runtime-Verbindung im Scaffold | Code-Review-Gate (Codex-Check) | PENDING |
| R5 | Read-only/Dry-run-first Default | Code-Review-Gate (Codex-Check) | PENDING |

---

## 3. Implementierungs-Guardrails für Codex (#2045)

Die Implementierung darf NUR erfolgen, wenn folgende Bedingungen erfüllt sind:
1. **Kein DB-Write**: Die Implementierung enthält keine SurrealDB-Schreiblogik (außer explizites Exportieren in JSONL-Files).
2. **Keine Secrets**: Der Indexer darf keine Secrets extrahieren; bei Treffern "fail-closed" oder maskieren.
3. **Deterministische Identität**: Hashing basiert nur auf Inhalt + Pfad (kein Timestamp!).
4. **Output-Struktur**: Writes erfolgen NUR nach `./artifacts/context-indexer/` oder `./tmp/context-indexer/`.

---

## 4. Validierungsplan für Codex (#2045)

Sobald Codex den Scaffold in `tools/surrealdb/context_indexer.py` implementiert hat, MUSS Codex folgende Tests erfolgreich ausführen:

1. `python tools/surrealdb/context_indexer.py --help` (Muss den vollen Vertrag aus #1989 widerspiegeln)
2. `python tools/surrealdb/context_indexer.py scan --dry-run` (Scannt den Root ohne Schreibzugriff)
3. **Determinismus-Test**: Zweimaliger Scan des `core/`-Verzeichnisses auf dem gleichen Git-Commit muss identische File-Hashes erzeugen.
4. **Sicherheits-Test**: Scan einer Test-Datei mit einem Fake-Secret muss dieses im Output maskieren.
5. **Path-Traversal-Test**: Scan mit `--output ../../etc/passwd` MUSS mit Exit-Code 5 stoppen.

---

## 5. Handoff
Dieser Readiness-Check ist das "Go" für Codex #2045, sofern die PRs zu #1989 und #2040 gemergt sind.
