# [PAPER][INVESTIGATION] Market-Data-Provenance des laufenden Paper-Runs (Issue #1908)

Stand: 2026-04-24  
Scope: **Repo-backed** Investigation (fail-closed), ohne Architektur-/Plattform-Redesign.

## Kurzfazit (fail-closed)

**Aus dem Repo allein** ist der **intendierte** Runtime-Market-Data-Pfad klar:

- `cdb_ws` (RED) publiziert `market_data` nach Redis Pub/Sub, **default-source** im mexc-Pfad ist `source="mexc"`.
- `cdb_candles` (BLUE) konsumiert `market_data` und schreibt Candles in `stream.candles_1m`.
- `cdb_signal` (RED) konsumiert `market_data` und publiziert `signals` (Pub/Sub + Stream).
- `cdb_risk` (BLUE) konsumiert `stream.signals` + Allocation + Regime.
- `cdb_execution` (BLUE) ist mit `MOCK_TRADING=true` konfiguriert (Paper/Non-Live Execution).
- `cdb_paper_runner` (BLUE) subscribed `market_data/signals/orders/order_results/alerts` und loggt alles nach `logs/events/events_YYYYMMDD.jsonl`.

**Was daraus nicht folgt:** Dass der aktuell laufende 14‑Tage‑Run **tatsächlich** ausschließlich von `cdb_ws`/MEXC gespeist wird.  
Ohne runtime-nahe Evidenz (Paper-Runner JSONL oder Redis Pub/Sub Samples) bleibt die Provenance **unknown** ⇒ **evidence-invalid (fail-closed)**.

## Die Fragen aus #1908 – Antworten (repo-backed, fail-closed)

### 1) Welche exakte Market-Data-Quelle *soll* den Paper-Run speisen?

**Intendierter Pfad:** `cdb_ws` mit `WS_SOURCE=mexc_pb` (MEXC WebSocket V3 Protobuf) publiziert Redis Pub/Sub `market_data` mit `source="mexc"`.  
Repo-Evidence:
- `infrastructure/compose/compose.red.yml` setzt `WS_SOURCE: mexc_pb` und `MEXC_SYMBOL: BTCUSDT`.  
- `services/ws/mexc_v3_client.py` normalisiert Deals zu Payloads mit `source: "mexc"`.  
- `services/ws/service.py` publiziert nach Redis Topic `market_data`.

### 2) Konnte Mock-/Stub-/Fixture-/Synthetic-Market-Data in den Live-Paper-Pfad gelangen?

**Ja, als Kontaminationsrisiko ist es technisch möglich**, weil Redis Pub/Sub `market_data` ein **shared** Topic ohne Namespacing ist:

- `tests/e2e/replay_runner.py` publiziert deterministische Fixture-Ticks nach `market_data` mit `source="replay_runner"`.
- Zusätzlich existieren experimentelle/Performance-Helfer, die `market_data` publishen (z.B. unter `tools/experiments/` oder `tests/performance/`).

Wenn solche Publisher in derselben Redis-Instanz/DB laufen wie der Paper-Stack, ist die Market-Data-Provenance **kontaminiert**.

### 3) Welche Symbole/Windows/Services wären betroffen?

Repo-backed Ableitung (Intention):
- Symbol: `BTCUSDT` (compose.red: `MEXC_SYMBOL: BTCUSDT`).
- Market-Data Services/Container:
  - Producer: `cdb_ws`
  - Consumers/Side-effects: `cdb_candles`, `cdb_market`, `cdb_signal`, `cdb_paper_runner`
  - Downstream Decision/Exec: `cdb_risk`, `cdb_execution`, `cdb_db_writer`

**Konkrete Windows** (Start/End, Kontaminationszeitraum) sind **nicht** repo-ableitbar; sie müssen aus `logs/events/events_YYYYMMDD.jsonl` (oder aus Redis Samples) belegt werden.

### 4) Ist der aktuelle 14‑Tage‑Paper‑Run als Paper‑Evidence gültig?

**Ohne runtime-nahe Provenance-Evidence: nein (evidence-invalid, fail-closed).**

**Mit runtime-nahem Nachweis** (siehe „Operational Check“) kann er **evidence-valid** sein, wenn:
- `channel=market_data` Entries in `logs/events/*.jsonl` ausschließlich `source="mexc"` (oder eine explizit als „real“ ratifizierte Quelle) zeigen, und
- keine Kontaminationsquellen (`source in {"replay_runner", "stub", ...}` bzw. fehlendes `source`) auftreten.

### 5) Hat der Run nur begrenzten Wert als technische Plumbing-/Capture-Sanity?

Wenn die Provenance **unknown** oder **kontaminiert** ist: **ja**, dann bleibt maximal:
- **technical-sanity-only** für „Plumbing lebt“ (Redis→Signal→Risk→Execution→DB Writer→Paper Runner Eventlog),
- aber **nicht** als Strategie-/Paper-Evidence.

### 6) Was ist der eine nächste operative Move?

**Ein Next Move:** Provenance *hart* messen und klassifizieren, indem `logs/events/events_YYYYMMDD.jsonl` des laufenden Runs mit dem Repo-Validator ausgelesen werden:

- `python scripts/validate_paper_market_data_provenance.py --events-dir logs/events --allow-source mexc`

Ergebnis ist dann eindeutig:
- PASS ⇒ evidence-valid (nur bzgl. Market-Data-Provenance; keine PnL-Deutung)
- FAIL ⇒ evidence-invalid (oder technical-sanity-only, je nach Ziel)

## Operational Check (Evidence Capture)

### A) Minimaler Runtime-Beleg (empfohlen)

1. Stelle sicher, dass `cdb_paper_runner` läuft und `logs/events/events_YYYYMMDD.jsonl` wächst.
2. Validiere Market-Data-Provenance:
   - `python scripts/validate_paper_market_data_provenance.py --events-dir logs/events --allow-source mexc`

### B) Interpretation (fail-closed)

- **PASS**: Keine `market_data`-Events ohne `source`, keine fremden `source`-Werte.
- **FAIL**:
  - `source` fehlt ⇒ **unknown-provenance ⇒ evidence-invalid**
  - `source != mexc` (z.B. `replay_runner`, `stub`) ⇒ **contamination ⇒ evidence-invalid**

## Relevante Dateien (SSOT in diesem Slice)

- `infrastructure/compose/compose.red.yml` (WS_SOURCE / MEXC_SYMBOL)
- `services/ws/service.py`, `services/ws/mexc_v3_client.py` (Producer/Normalization)
- `tools/paper_trading/service.py` (Eventlog: `logs/events/events_YYYYMMDD.jsonl`)
- `tests/e2e/replay_runner.py` (bekannter Fixture-Publisher nach `market_data`)
- `scripts/validate_paper_market_data_provenance.py` (Validator; siehe PR)

