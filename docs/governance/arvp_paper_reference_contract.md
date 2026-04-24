# ARVP Paper-Reference-Contract (v1) — Vergleichsbasis für Replay-vs-Paper

**Status:** Kanonischer Contract (Issue `#1901`)  
**Scope:** Repo-backed Definition *welche* Paper-Referenz ARVP später vergleichen darf (kein Vergleich, keine Calibration).  
**Repo-Stand (Befundbasis):** 2026-04-24  

---

## 0. Ziel (und harte Nicht-Ziele)

**Ziel:** Einen *minimalen, belastbaren, fail-closed* Vertrag definieren, was im Repo als **Paper-Reference** gilt, gegen die eine spätere Replay-vs-Paper Comparison (ARVP Layer §4.9) vergleichen darf.

**Nicht-Ziele (Guardrails):**
- Kein Replay-vs-Paper-Vergleich (keine Matching-/Diff-Logik).
- Keine Calibration-Logik.
- Kein Umbau der Paper-Runtime / DB-Architektur / Ledger-Refactor.
- Keine LR-/Live-/Capital-Semantik.

---

## 1. Befund (repo-true): Welche paper-nahen Artefakte gibt es heute?

### 1.1 Vergleichsrelevante, auditierbare Quellen (tauglich als Reference-Quelle)

**A) PostgreSQL `correlation_ledger` (append-only Audit Trail, Phase 8C)**
- Schema: `infrastructure/database/migrations/006_correlation_phase8c.sql`
- Charakter: append-only, idempotent (`event_pk`), millisekundenbasierter Zeitanker (`timestamp_ms`), payload-gestützt.
- Erwartete Event-Typen: `SIGNAL`, `DECISION`, `ORDER`, `FILL`.
- Verknüpfung: `correlation_id` als Chain-Root (aus `signal_id`), plus `order_id` / `fill_id` (für ORDER/FILL).
- Paper-Indikator (repo-true): `order_id`-Prefix `paper_...` (siehe `services/execution/paper_trading.py`).

**Bewertung:** Das ist die einzige heute im Repo klar auditierbare, chain-fähige und timestamp_ms-getriebene Quelle, die *gleichzeitig* die Paper-Execution-Kette abbilden kann (inkl. ORDER/FILL), ohne auf „Best-Effort“-Zeitstempel-Fallbacks angewiesen zu sein.

### 1.2 Paper-nahe Quellen (nur informativ / nicht canonical comparison-grade)

**B) PostgreSQL Tabellen `signals`, `orders`, `trades`, `positions`, `portfolio_snapshots`**
- Schema: `infrastructure/database/schema.sql`
- Writer: `services/db_writer/db_writer.py`

Repo-true Grenzen, die sie **nicht** comparison-grade als *kanonische* Referenz machen:
- **Strategie-Provenance ist nicht spaltenstabil:** `strategy_id` ist in `orders`/`trades`/`portfolio_snapshots` nicht als Spalte vorhanden; ggf. nur indirekt in `metadata` (nicht garantierbar, nicht enforced).
- **Timestamps können „weich“ werden:** `convert_timestamp()` in `services/db_writer/db_writer.py` fällt bei `None`/invalid auf `utcnow()` zurück → erzeugt nicht-auditierbare Zeitstempel (vergleichsgefährlich).
- **Trade↔Order Link ist nicht robust:** `trades.order_id` wird im DB-Writer-Pfad nicht gesetzt; korrekte Chain-Rekonstruktion ist darüber nicht fail-closed möglich.

**Bewertung:** Nützlich für Betriebs-/Summary-Reports und grobe Checks, aber nicht als kanonische Paper-Reference für Replay-vs-Paper-Comparison geeignet.

**C) Paper Runner Event-Logs (JSONL)**
- Writer: `tools/paper_trading/service.py`
- Artefakte: `logs/events/events_YYYYMMDD.jsonl` (pro Zeile: `timestamp` (wall-clock), `channel`, `event`)

Repo-true Grenzen:
- File-local, nicht zentral versioniert/gebündelt.
- `timestamp` ist *recorded-at* (Runner wall-clock), nicht zwingend Event-Time.
- Keine idempotente, DB-backed Ledger-Semantik.

**Bewertung:** Debug-/Forensik-Quelle, aber nicht canonical comparison-grade.

---

## 2. Der Contract: Was ist die kanonische Paper-Referenz für ARVP?

### A. Vergleichseinheit (primär)

**Primäre kanonische Einheit:** **`paper_reference_window`** (Strategy Window)

**Definition:** Ein explizites, UTC-basiertes Zeitfenster `[start_ts_ms_utc, end_ts_ms_utc]` für genau `(strategy_id, symbol)`, für das eine Paper-Referenz aus dem **`correlation_ledger`** extrahiert wurde.

**Begründung (repo-true):**
- Es gibt heute **keine** robuste, repo-backed „Paper Run ID“ bzw. „Session ID“, die als Vergleichseinheit dienen könnte.
- `correlation_ledger` ist append-only über die Laufzeit und eignet sich natürlich für **Window-Slices**.
- ARVP selbst arbeitet ebenfalls window-orientiert (Dataset windows, 1m canvas) → passt ohne Wunscharchitektur.

Sekundäre Einheit (optional, abgeleitet):
- **`paper_reference_chain`** = die vollständige Event-Chain pro `correlation_id` innerhalb eines Windows (wird aus `paper_reference_window` abgeleitet; nicht primär).

---

### B. Pflichtfelder (comparison-grade)

Ein `paper_reference_window` ist **comparison-grade**, wenn *alle* folgenden Bedingungen erfüllt sind:

#### B1) Window-Header (Pflicht)
- `contract_version`: `"arvp_paper_reference_window.v1"`
- `strategy_id`: non-empty string
- `symbol`: non-empty string
- `start_ts_ms_utc`: integer (`> 0`)
- `end_ts_ms_utc`: integer (`> start_ts_ms_utc`)
- `paper_selector`: Objekt, das die Paper-Selektion **explizit** fail-closed macht:
  - `paper_order_id_prefix`: `"paper_"` (v1)

#### B2) Ledger-Events (Pflicht)
Für das Window muss eine Menge von `correlation_ledger`-Events enthalten sein, die mindestens folgende Felder *pro Event* haben:
- `event_pk` (idempotency key; non-empty string)
- `correlation_id` (non-empty string)
- `event_type` ∈ `{SIGNAL, DECISION, ORDER, FILL}`
- `symbol` (muss dem Window-Header entsprechen)
- `timestamp_ms` (integer, **UTC event-time**, siehe Timestamp-Semantik)
- `payload` (JSON object; muss mindestens liefern:)
  - `strategy_id` (non-empty string; muss dem Window-Header entsprechen)

Zusätzliche Pflichtfelder abhängig vom `event_type` (fail-closed):
- `SIGNAL`: `signal_id` muss gesetzt sein.
- `DECISION`: `signal_id` und `decision_id` müssen gesetzt sein.
- `ORDER`: `signal_id`, `decision_id`, `order_id` müssen gesetzt sein.
- `FILL`: `signal_id`, `decision_id`, `order_id`, `fill_id` müssen gesetzt sein.

#### B3) Paper-Chain Qualifikation (Pflicht)
Damit ein Event-Set als **Paper** gilt:
- Es muss **mindestens ein `ORDER`-Event** geben, dessen `order_id` vorhanden ist und `order_id` mit `paper_` beginnt.
- Alle `FILL`-Events, die in die Paper-Referenz aufgenommen werden, müssen `order_id` enthalten und ebenfalls `paper_`-präfixiert sein.

**Fail-closed:** Wenn diese Qualifikation nicht erfüllt ist, ist das Window **nicht comparison-grade** (siehe Validity Rules).

---

### C. Timestamp-Semantik (kritisch, fail-closed)

#### C1) Relevante Timestamps (Pflicht für Vergleich)
Für jeden Reference-Event ist `timestamp_ms` der **einzige** comparison-relevante Zeitanker.

**Semantik:** `timestamp_ms` ist **event-time (UTC)**, nicht „recorded-at“.

#### C2) Normalisierung
- `timestamp_ms` wird als Unix epoch milliseconds in UTC interpretiert.
- Keine lokalen Zeitzonen, keine naive Timestamps.

#### C3) Informative Zeitfelder (nicht vergleichsrelevant)
`created_at` (DB default NOW()) oder File-Log `timestamp` (paper_runner wall-clock) sind **nur** informative Audit-/Debug-Felder und **dürfen nicht** als Match-/Vergleichszeit verwendet werden.

#### C4) Fail-closed Kriterien (Zeit)
Ein Event ist **nicht comparison-grade**, wenn:
- `timestamp_ms` fehlt oder nicht parsebar ist.
- `timestamp_ms` außerhalb `[start_ts_ms_utc, end_ts_ms_utc]` liegt.

Ein Window ist **nicht comparison-grade**, wenn:
- die Menge der qualifizierenden Paper-Events (ORDER/FILL) nach Filterung leer ist, oder
- Events nur über recorded-at/wall-clock zu datieren wären.

---

### D. Provenance (Pflicht)

Damit die Paper-Referenz auditierbar bleibt, muss ein `paper_reference_window` folgende Provenance-Felder enthalten:

#### D1) Source-Anchor (Pflicht)
- `source_table`: `"public.correlation_ledger"` (v1 fix)
- `source_query_intent`: text (kurz, deterministisch; z.B. „select events by symbol+strategy_id+timestamp_ms window; qualify paper via order_id prefix“)

#### D2) Extract-Context (Pflicht)
- `extracted_at_utc`: ISO-8601 UTC timestamp (recorded-at; **nicht** Vergleichszeit)
- `extracted_by`: identifier string (z.B. service/script name; v1 frei, aber non-empty)

Optional (wenn repo-backed verfügbar, sonst weglassen):
- `code_commit`: git commit SHA (7–40 hex) der Extractor-Version.
- `config_snapshot_ref`: pointer auf eine repo-backed Config-Snapshot-Quelle (falls später eingeführt; v1 optional).

---

### E. Validity / Invalidity Rules (fail-closed)

#### E1) Gültig (comparison-grade), wenn:
- Header-Pflichtfelder vollständig sind.
- Alle aufgenommenen Events die Pflichtfelder erfüllen (inkl. `payload.strategy_id`).
- Paper-Qualifikation erfüllt ist (mindestens ein `ORDER` mit `paper_` + konsistente `FILL`-OrderIDs).
- Timestamp-Semantik erfüllt ist (event-time via `timestamp_ms`).

#### E2) Ungültig (nicht comparison-grade), wenn (Auszug, nicht weich interpretieren):
- `strategy_id` nicht durchgängig im `payload` vorhanden ist (oder nicht dem Header entspricht).
- `timestamp_ms` fehlt/invalid ist oder nur recorded-at verfügbar wäre.
- `order_id`/`fill_id` Pflichtbedingungen für Paper-ORDER/FILL nicht erfüllbar sind.
- Das Set nur aus `signals/orders/trades` Tabellen rekonstruiert werden könnte (keine `correlation_ledger` Basis).

#### E3) Nur informativ (darf gespeichert/angezeigt, aber nicht verglichen werden)
- `portfolio_snapshots` (Equity/Exposure) ohne chain-fähige Execution-Event-Semantik.
- DB-Writer `trades`/`orders` Rows ohne belastbare strategy_id + ohne chain-link.
- Paper Runner JSONL Logs als Debug-Fallback.

---

## 3. Konkrete repo-backed Quelle (SSOT) für v1

**SSOT für Paper-Reference v1:** `public.correlation_ledger` (PostgreSQL).

**Paper-Selektion v1:** `order_id LIKE 'paper_%'` (für qualifizierende ORDER/FILL Chains).

**Hinweis:** Der Contract definiert *was* comparison-grade ist; er definiert **nicht**, wie ein Exporter implementiert wird.

---

## 4. Restgrenzen (bewusst nicht gelöst in #1901)

- Kein Export-/Bundle-Writer für `paper_reference_window` (das ist Folgearbeit; #1902 kann darauf aufsetzen).
- Keine Replay↔Paper Matching-Regeln (Mapping von Replay-Fills/Orders auf Paper-Chains).
- Keine Drift-/Calibration-Algorithmen.
- Keine Nachbesserung der DB-Writer Tabellenmodelle (`orders/trades` etc.).
