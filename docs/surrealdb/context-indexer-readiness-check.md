# Context Indexer Implementation Preconditions

**Status**: Draft
**Authority**: Issue #2044 / Epic #1976
**Target**: `tools/surrealdb/context_indexer.py` (Implementierungsslice #2045)
**Scope**: Read-only, Dry-run-first Indexing

---

## 1. Zweck
Dieses Dokument dokumentiert die Voraussetzungen und offene Gates für die spätere Implementierung #2045. Es ersetzt kein separates Implementierungs-Go und keinen menschlichen Review.

---

## 2. Gate-Checkliste (Pre-Implementation)

| # | Anforderung | Validierungs-Methode | Status |
|---|-------------|----------------------|--------|
| R1 | CLI-Vertrag (#1989) ist landed | Review `docs/surrealdb/context-indexer-cli-contract.md` | LANDED |
| R2 | Handoff-Guide (#2040) ist landed | Review `docs/surrealdb/context-agent-handoff.md` | LANDED |
| R3 | Scope-Config-Format definiert | Review `ingestion_scope.yaml` Muster | LANDED |
| R4 | Keine DB-Runtime-Verbindung | Code-Review-Gate | PENDING |
| R5 | Read-only/Dry-run-first Default | Code-Review-Gate | PENDING |

---

## 3. Implementierungs-Guardrails für #2045

Die spätere Implementierung muss folgende Bedingungen erfüllen:
1. **Kein DB-Write**: Die Implementierung enthält keine SurrealDB-Schreiblogik (außer explizites Exportieren in JSONL-Files).
2. **Keine Secrets**: Der Indexer darf keine Secret-Inhalte exportieren. Treffer müssen maskiert oder als "blocked"/"omitted" markiert werden.
3. **Deterministische Identität**: Hashing basiert auf normalisiertem Inhalt + repo-relativem Pfad + stabiler Schema-/Contract-Version. Timestamp darf nie Input für den Hash sein.
4. **Output-Struktur**: Writes erfolgen NUR nach `artifacts/context-indexer/` oder `tmp/context-indexer/`. Writes außerhalb führen zu `5 write denied`.

---

## 4. Validierungsplan für #2045

Die spätere Implementierung muss folgende Tests erfolgreich bestehen:

1. `python tools/surrealdb/context_indexer.py --help`
2. `python tools/surrealdb/context_indexer.py scan --scope-config ./ingestion_scope.yaml --dry-run`
3. **Determinismus-Test**: Zweimaliger Scan auf gleichem Commit muss identische Hashes liefern.
4. **Sicherheits-Test**: Scan einer Datei mit Secret muss dieses maskieren.
5. **Path-Traversal-Test**: Scan mit `--output ../../etc/passwd` muss mit Exit-Code 5 stoppen.

---

## 5. Handoff
Dieser Readiness-Check dokumentiert Voraussetzungen und offene Gates für #2045. Er ersetzt kein separates Implementierungs-Go und keinen menschlichen Review.
