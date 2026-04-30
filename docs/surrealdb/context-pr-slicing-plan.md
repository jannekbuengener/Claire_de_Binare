# Context Intelligence — PR Slicing Plan (Wave 7 -> Implementation)

**Status**: Draft
**Authority**: Issue #2042 / Parent #2034 / Epic #1976
**Scope**: Docs-only (kein Code, kein Schema-Apply, keine Runtime-Aenderung)

---

## 1. Zweck

Dieses Dokument definiert einen **sicheren, reviewbaren PR-Slicing-Plan** fuer den Uebergang von der Welle-7-Landing-Phase
zu den spaeteren Implementierungswellen.

Ziel ist:

- kleine PRs mit klarer Diff-Grenze
- eindeutige Dependencies
- klare Stop-Bedingungen
- keine Misch-PRs (Docs + Runtime + Schema in einem)

---

## 2. Grundregeln (MUSS)

- Jeder PR MUSS einen klaren Slice haben (eine eng definierte Aenderungsflaeche).
- Jeder PR MUSS eine eindeutige Issue-Referenz enthalten (z. B. `Refs #<issue>`).
- Kein PR DARF implizit Live- oder Echtgeld-Freigaben ableiten.
- Kein PR DARF Trading-State oder Secrets anfassen oder modellieren.
- Kein PR DARF die Trading-Runtime umbauen.
- Kein PR DARF produktive SurrealDB-Aktivierung als Nebeneffekt enthalten.
- Kein PR DARF `git add .` als Anweisung enthalten.

**STOPP**, wenn ein PR mehrere Slices vermischt oder Guardrails verletzt.

---

## 3. Status und Abhaengigkeiten (Live-Rule)

SSOT fuer Status ist GitHub (Issues/PRs), nicht dieses Dokument.

Abhaengigkeiten fuer die Context-Intelligence-Welle 7:

- #2035 (Architektur) — gemergt
- #2036 (Roadmap) — gemergt
- #2037 (Schema Draft) — gemergt
- #2038 (Ontology Seed) — gemergt
- #2039 (Validation Checklist) — geschlossen
- #2040 (Agent Handoff Guide) — geschlossen
- #2041 (SurrealDB docs index update) — gemergt via PR #2225
- #2042 (PR Slicing Plan) — geschlossen
- #2043 (Wave-7 Completion Gates) — geschlossen

Bereits gelandete Reconciliation-PRs:

- PR #2224 — Wave 7-A docs reconciliation — MERGED
- PR #2225 — Wave 7-B docs index update — MERGED
- PR #2226 — Wave 7-C closeout docs reconciliation — MERGED

Offen, aber fuer diesen Slice bewusst eingefroren / out of scope:

- PR #2223 — #1986 ingestion scope rebuild — OPEN / FROZEN / OUT OF SCOPE
- PR #2216 — Wave 8 readiness/readiness — OPEN / FROZEN / OUT OF SCOPE

Hinweis: Live-Status MUSS immer gegen GitHub verifiziert werden; dieses Dokument beschreibt nur den Slice-Plan.

---

## 4. Empfohlene PR-Reihenfolge (ab Wave 7)

### 4.1 Landing / Docs-Foundation (Wave 7)

Diese PRs sind docs-first und sollen einzeln landbar sein:

1. #2035: Architektur-Doku (bereits gemergt)
2. #2036: Roadmap-Doku (bereits gemergt)
3. #2037: Schema-Draft (bereits gemergt, Draft only)
4. #2038: Ontology Seed (bereits gemergt)
5. #2039: Static Validation Checklist (geschlossen)
6. #2040: Agent Handoff Guide (geschlossen)
7. #2041: SurrealDB docs index update (bereits gemergt via PR #2225)
8. #2042: PR Slicing Plan (dieses Dokument, geschlossen)
9. #2043: Wave-7 Completion Gates (geschlossen)

### 4.2 Reconciliation-Stand nach Wave 7-A / 7-B

- Wave 7-A ist ueber PR #2224 gelandet.
- Wave 7-B ist ueber PR #2225 gelandet.
- Wave 7-C ist ueber PR #2226 gelandet und hat die verbleibenden Docs-Issues #2039, #2040, #2042 und #2043 geschlossen.
- PR #2223 und PR #2216 bleiben separate, eingefrorene Arbeitsstraenge und gehoeren nicht in einen Wave-7-C-Diff.

---

## 5. Umsetzungsschnitt zu spaeteren Implementierungswellen (8+)

Implementierungswellen (8+) sollen strikt sequenziell bleiben:

- Welle 8: Indexer Scaffold + Dry-run Export Pipeline
- Welle 9: Symbol-/Graph-Extraktion
- Welle 10: Import/Reconcile/Apply (lokal, gegated)
- Welle 11: Query CLI read-only
- Welle 12: MCP Bridge read-only

Regel:

- Ein PR soll bevorzugt **nur einen** Baustein liefern (z. B. nur Hashing, nur Discovery, nur JSONL Export).

---

## 6. Kleine PR-Slices (Beispiele)

### Beispiel-Slice: "Exporter Dry-run"

- Aendert nur: Export-CLI, Export-Format, Tests
- DARF NICHT: SurrealDB-Apply, Runtime, Secrets

### Beispiel-Slice: "Schema Draft Update"

- Aendert nur: `.surql` Draft
- DARF NICHT: Migration/Apply, Runtime

---

## 7. Rollen: Gemini vs. Implementierungs-Agenten

Gemini (Audit/Review) ist besonders geeignet fuer:

- Review-Gates, Checklisten, Trust/Evidence-Pruefpunkte
- Scope-/Guardrail-Checks
- PR-Hygiene, Diff-Scope-Audits

Codex/Claude (Implementierung) sind eher geeignet fuer:

- Indexer/Exporter/Import-Pipeline
- Tests, Fixtures, Contracts
- Tooling (CLI/MCP) unter Read-only Constraints

Regel: Gemini soll keine Implementierung treiben; Implementierungsagenten muessen die Guardrails belegen.

---

## 8. Dependencies und Stop-Bedingungen (MUSS)

- Wenn eine Dependency offen ist, darf ein Slice, der diese Dependency voraussetzt, NICHT finalisiert werden.
- Wenn GitHub einen PR blockiert, darf nicht umgangen werden.
- Wenn Checks rot sind und Ursache nicht slice-intern ist: rerun, dann eskalieren.
- Wenn Diff Scope fremde Dateien enthaelt: STOPP.
- Live-Readiness bleibt `NO-GO`; kein Slice darf daraus ein Live- oder Echtgeld-Go ableiten.

---

## 9. Merge-Reihenfolge und Anti-Misch-PR-Regeln

- Docs-only PRs sollen nicht mit Runtime/Code gemischt werden.
- Schema-Draft PRs sollen nicht mit Implementation gemischt werden.
- Implementation PRs sollen nicht mit Governance/Policy-Aenderungen gemischt werden.

**STOPP**, wenn ein PR mehrere Klassen mischt.

---

## 10. Validierung pro PR (Minimal)

Jeder PR MUSS mindestens:

- `git diff --name-only` (Diff-Scope)
- `gh pr view` (mergeStateStatus, changedFiles)
- `gh pr checks` (keine pending/failed)

Docs-only PRs:

- Markdown-Review (Struktur, Guardrails, keine impliziten Freigaben)

---

## 11. Offene Restarbeit (aktuell)

- #2034: minimalen Closeout-/Ledger-Abgleich landen, damit das offene Anchor-Issue ohne Statusdrift geschlossen werden kann
- PR #2223 und PR #2216 bleiben offen, eingefroren und fuer Wave 7-C out of scope

Dieses Dokument ist kein Ersatz fuer den Live-Status in GitHub.
