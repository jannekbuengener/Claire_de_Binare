# Context Intelligence — Wave 21 Completion Gates

**Status**: Draft
**Authority**: Issue #2205 / Epic #1976
**Scope**: Planungs- und Governance-Audit für Wave 21

---

## 1. Zweck
Dieses Dokument definiert die Abschlusskriterien für Wave 21 (Cross-cutting Hardening, Search, CI & Operations). Da Wave 21 eine Planungs- und Governance-Welle ist, liegt der Fokus auf der Existenz und Qualität der entsprechenden Strategiepapiere.

---

## 2. Guardrails (Anti-Kriterien)
Wave 21 gilt als **nicht** abgeschlossen, wenn:
- Produktive SurrealDB-Instanzen ohne separates GO aktiviert wurden.
- Trading-Runtime-Code verändert wurde.
- Secrets oder Trading-Daten in das Context-System eingeflossen sind.
- Provider-Zwang für Embeddings eingeführt wurde (Embeddings müssen optional bleiben).

---

## 3. Gate-Checkliste (MUSS)

Wave 21 ist abgeschlossen, wenn folgende Artefakte im Repo existieren und den Anforderungen entsprechen:

### 3.1 Suche & Retrieval
- [ ] **Vector Search Decision**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§2).
- [ ] **Fulltext Tuning Design**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§3).

### 3.2 Performance & Hardening
- [ ] **Scale Validation Plan**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§4).
- [ ] **Protective Hardening Plan**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§5).

### 3.3 Operations & CI
- [ ] **CI Integration Plan**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§6).
- [ ] **Backup/Restore Strategy**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§7).

### 3.4 Governance
- [ ] **Doc & Decision Governance Cadence**: Dokumentiert in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` (§8).

---

## 4. Validierung
Die Validierung erfolgt durch:
1. **Statische Review** der in `docs/surrealdb/context-wave21-cross-cutting-hardening.md` getroffenen Entscheidungen gegen die Anforderungen der Issues #2198–#2204.
2. **Git Diff Prüfung**: Sicherstellung, dass keine unautorisierten Code-Änderungen enthalten sind.

---

## 5. Handoff
Nach Abschluss von Wave 21 ist das Context Intelligence System konzeptionell vollständig gehärtet und bereit für die finale Integration in den Agent-Betrieb.
