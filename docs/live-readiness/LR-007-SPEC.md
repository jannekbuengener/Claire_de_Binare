# LR-007 Shadow Mode Validation Gate – SPEC v1.0

**Version:** 1.0
**Status:** Draft (Decision-only)
**Date:** 2026-02-07
**Scope:** Criteria-only definition (NO code, NO CI, NO implementation)
**Author:** Claude Code (Session Lead)

---

## 1. Purpose & Positioning

**Leitfrage:**
*Wann darf objektiv über Live-Readiness gesprochen werden – und wann explizit nicht?*

**LR-007 definiert:**
Das Gate zwischen Governance-Korrektheit (LR-001 bis LR-006A abgeschlossen) und operativer Vertrauenswürdigkeit (Control Layer demonstriert fail-safe Behavior über definierten Zeitraum).

**LR-007 ist NICHT:**
- Ein Implementation-Task (kein neuer Code)
- Ein CI-Gate (keine Required Checks hinzugefügt)
- Ein Live-Trading-Approval (Capital at Risk außerhalb Scope)
- Ein Performance-Tuning (Latency-Optimierung nicht Ziel)

**LR-007 IST:**
Eine deterministische, artefakt-basierte Bewertung, ob Shadow-Mode-Laufzeit die Mindeststandards für Live-Trading-Diskussion erfüllt.

---

## 2. Shadow Mode Definition

### 2.1 Scope

**Aktive Services:**
- `cdb_ws` (WebSocket Market Data Consumer)
- `cdb_candles` (Candle Aggregator)
- `cdb_regime` (Regime Classification Service)
- `cdb_allocation` (Allocation Decision Service)
- `cdb_risk` (Risk Service – Order Gating)
- `cdb_execution` (Execution Service – Order Lifecycle)
- `cdb_redis` (Stream Infrastructure)

**Stack-Identifier:**
`BLUE` (oder aktuelle Production-Shadow-Stack laut Compose-Config)

**Märkte/Paare:**
Mindestens **BTCUSDT** (1m timeframe), weitere Paare optional (dokumentiert in `shadow_mode_config.yaml`)

### 2.2 Erlaubte Outputs

**Schreib-Operationen (ALLOWED):**
- Redis Streams:
  - `stream.candles_1m` (Candle-Aggregation)
  - `stream.regime_signals` (Regime-Change-Events)
  - `stream.allocation_decisions` (Allocation-Decisions)
  - `stream.signals` (Trading Signals, mock-only)
  - `stream.orders` (Order-Lifecycle-Events, mock-only)
- Postgres Tables (Append-only):
  - `market_data` (Market-Tick-Storage)
  - `orders` (Order-History, `mock_trading=true` only)
  - `positions` (Position-Snapshots, `mock_trading=true` only)
  - `decisions` (Decision-Trace-Records via LR-006A Contract)
- Prometheus Metrics:
  - Alle Service-Metrics (Counter, Gauges, Histograms)

**Read-Only Zones:**
- Secrets (Docker Secrets, `.env` Files) → Nur via Tresor-Read, nie modify
- Configs (Service-Configs sind Read-Only nach Start)
- Exchange APIs → **Nur API-Calls erlaubt: Market-Data-Subscriptions, Account-Balance-Reads, Position-Reads**

### 2.3 Explizit Verboten (HARD FAIL)

**NO-GO während Shadow Mode:**
- Exchange Order Placement (`POST /order`) → Circuit-Breaker MUST reject
- Exchange Order Cancellation (`DELETE /order`) → Circuit-Breaker MUST reject
- Withdrawal Requests → **HARD BLOCK**, no exceptions
- Account Settings Changes → **HARD BLOCK**
- Testnet/Paper-Trading-APIs → **Erlaubt** (falls verfügbar), aber nicht Production-Exchange
- Modifikation von Config-Files (nur via PR + Merge erlaubt)

**Enforcement:**
`mock_trading=true` MUST be enforced in Execution Service Config (validiert durch LR-002 Contract Tests).

---

## 3. Entscheidende Metriken (PASS/FAIL Logic)

**Keine Zielwerte festgelegt** (diese sind Governance-Entscheidung außerhalb LR-007 Scope).
LR-007 definiert nur **Bewertungslogik** und **Kategorien**.

### 3.1 Metric Categories

#### 3.1.1 Decision Rate Metrics

**Definition:**
Messung der Service-Aktivität über Zeit.

**Metrics:**
- `regime_candles_processed_total` (Counter)
- `allocation_decisions_emitted_total` (Counter)
- `risk_orders_evaluated_total` (Counter)
- `execution_orders_processed_total` (Counter)

**Evaluation Logic:**
```
decision_rate_5m = rate(metric[5m])

PASS IF: decision_rate_5m > 0 for ≥95% of 5-minute windows
FAIL IF: decision_rate_5m == 0 for >5% of 5-minute windows (indicates stall)
```

**Rationale:**
Services MUST continuously process data. Prolonged zero-rates indicate silent failures.

#### 3.1.2 Reject Rate Metrics

**Definition:**
Anteil der abgelehnten Orders vs. genehmigte Orders.

**Metrics:**
- `risk_orders_rejected_total` (Counter, labels: `reason_code`)
- `risk_orders_approved_total` (Counter)

**Evaluation Logic:**
```
reject_rate = risk_orders_rejected_total / (risk_orders_rejected_total + risk_orders_approved_total)

PASS IF: 0.10 <= reject_rate <= 0.90 (healthy gating, not too permissive/restrictive)
FAIL IF: reject_rate < 0.05 (risk gates possibly inactive)
FAIL IF: reject_rate > 0.95 (risk gates too aggressive, system unusable)
```

**Interpretation Guidance:**
Reject-Rate ist **markt- und regimeabhängig**. Bewertung erfolgt **relativ zur Regime-Verteilung** über Shadow-Mode-Laufzeit:
- Low-Vol-Regime: Höhere Reject-Rate erwartet (weniger tradable Setups)
- High-Vol-Chaotic: Höhere Reject-Rate erwartet (Risk-Gates aktiver)
- High-Vol-Trending: Niedrigere Reject-Rate erwartet (mehr tradable Setups)

**Absolute 0.10-0.90 Bounds gelten regime-uebergreifend** (Aggregat ueber volle Validierungs-Laufzeit).
Regime-spezifische Analyse optional, aber nicht LR-007-Requirement.

**Rationale:**
Verhindert "aber im Low-Vol-Regime..."-Diskussionen. Bewertung ist Gesamt-Reject-Rate über volle Laufzeit, nicht Regime-segmentiert.

Risk Service MUST reject some orders (validates gates active), but not ALL orders (validates gates not broken).

#### 3.1.3 Risk Gate Trigger Metrics

**Definition:**
Häufigkeit von Circuit-Breaker- und Emergency-Stop-Events.

**Metrics:**
- `circuit_breaker_active` (Gauge, 0=inactive, 1=active)
- `circuit_breaker_trips_total` (Counter)
- `kill_switch_active` (Gauge, 0=inactive, 1=active)

**Evaluation Logic:**
```
PASS IF: circuit_breaker_trips_total < 3 during validation window
PASS IF: kill_switch_active == 0 for entire validation window
FAIL IF: circuit_breaker_trips_total >= 3 (indicates repeated instability)
FAIL IF: kill_switch_active == 1 for >1 minute (hard abort scenario)
```

**Rationale:**
Repeated circuit breaker trips indicate systemic instability. Kill Switch activation is manual-intervention-only and signals critical failure.

#### 3.1.4 Latency Percentiles

**Definition:**
End-to-End Latency für kritische Flows.

**Metrics:**
- `candle_processing_latency_seconds` (Histogram, p50/p95/p99)
- `regime_classification_latency_seconds` (Histogram, p50/p95/p99)
- `risk_evaluation_latency_seconds` (Histogram, p50/p95/p99)
- `order_lifecycle_latency_seconds` (Histogram, p50/p95/p99)

**Evaluation Logic:**
```
PASS IF: p95(latency_seconds) < threshold_p95 for each metric
WARN IF: p95(latency_seconds) >= threshold_p95 but < threshold_p99
FAIL IF: p99(latency_seconds) > threshold_max
```

**Thresholds:**
Not defined in LR-007 (decision left to operational team). Evaluation logic only requires thresholds exist and are documented.

**Rationale:**
Tail latencies indicate performance bottlenecks. p95 violations are warnings; p99 violations are hard fails.

#### 3.1.5 Error & Drop Rate Metrics

**Definition:**
Service-Level Error Rates (HTTP 5xx, exceptions, stream read failures).

**Metrics:**
- `http_requests_total` (Counter, labels: `status_code`)
- `stream_read_errors_total` (Counter, labels: `stream_name`)
- `service_exceptions_total` (Counter, labels: `service`, `exception_type`)

**Evaluation Logic:**
```
error_rate_5xx = rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m])

PASS IF: error_rate_5xx < 0.01 (< 1% error rate)
WARN IF: 0.01 <= error_rate_5xx < 0.05 (1-5% error rate)
FAIL IF: error_rate_5xx >= 0.05 (≥5% error rate)
```

**Stream Drop Rate:**
```
drop_rate = stream_read_errors_total / (stream_read_total + stream_read_errors_total)

PASS IF: drop_rate < 0.001 (< 0.1% drops)
FAIL IF: drop_rate >= 0.01 (≥1% drops)
```

**Rationale:**
High error rates indicate instability. Stream drops indicate data loss (unacceptable for trading system).

---

## 4. Zeit & Abbruch

### 4.1 Mindestlaufzeit

**Minimum Continuous Runtime:**
**72 Stunden** (3 Kalendertage)

> **Hinweis:** Eine fruehere Spec-Version (v1.0) forderte 30 Kalendertage.
> Diese Anforderung wurde per Maintainer-Entscheidung (2026-03-30, Issue #1347) auf 72h reduziert.
> Der aktive Gate-Contract in `live_trading_gate.py` und INV-006 war bereits 72h.

**Definition "Continuous":**
- Alle Control-Layer-Services (`cdb_candles`, `cdb_regime`, `cdb_allocation`, `cdb_risk`, `cdb_execution`) laufen ohne Restart
- Redis Streams enthalten lueckenlose Candle-Historie (keine Gaps >5 Minuten)
- WebSocket-Verbindung zu Exchange aktiv (Reconnects erlaubt, aber nicht >10% der Zeit disconnected)

**Start-Timestamp:**
Dokumentiert in `shadow_mode_start.timestamp` (ISO8601 Format, UTC)

**End-Timestamp (fruehestens):**
`shadow_mode_start.timestamp + 72 hours`

**Restart Policy:**
Jeglicher **geplanter** Restart eines Control-Layer-Services **resettet** die 72h-Uhr auf Stunde 0.

**Exception (NICHT resettet):**
- Infrastructure-Restarts (Redis, Postgres, Prometheus) → Solange Control-Layer-Services durchlaufen
- **Hotfixes mit <5 Minuten Downtime UND Post-Restart-Validierung (via Snapshot-Verify)**
  - **Maximum: 1× Hotfix pro 72h-Periode**
  - **Dokumentationspflicht:** Hotfix-Grund, Downtime, Validation-Evidence in `LR-007-HOTFIX-LOG.md`

**Bei >1 Hotfix in 72h:**
Shadow-Mode-Uhr resettet auf Stunde 0 (verhindert schleichende "kleine Fixes").

**Rationale:**
Ein Notfall-Hotfix ist akzeptabel (Production-Reality). Mehrere Hotfixes signalisieren mangelnde Stabilitaet → Shadow-Mode-Neustart erforderlich.

### 4.2 Harte Abbruchkriterien (HARD FAIL)

**Shadow Mode MUST abort sofort bei:**

1. **Kill Switch Activation:**
   `kill_switch_active == 1` für >60 Sekunden → ABORT + Incident Report

2. **Data Loss Event:**
   Stream-Gap >60 Minuten in `stream.candles_1m` → ABORT (Signal-Integrität kompromittiert)

3. **Silent Service Failure:**
   Health-Endpoint liefert HTTP 200, aber `rate(candles_processed_total[5m]) == 0` für >15 Minuten → ABORT (LR-006A Trace kann nicht erstellt werden ohne Activity)

4. **Unauthorized Order Attempt:**
   Log-Eintrag zeigt `POST /order` zu Exchange API (nicht Testnet/Mock) → **IMMEDIATE ABORT** + Security Review

5. **Secrets Leak:**
   Decision-Trace enthält Tresor-Zone-Referenz oder API-Key im Klartext → ABORT + LR-006A Violation Incident

6. **Repeated Circuit Breaker Trips:**
   `circuit_breaker_trips_total` ≥ 5 in 24h → ABORT (System instabil)

**Bei HARD FAIL:**
- Shadow Mode Status → `ABORTED`
- 72h-Zaehler → resettet auf Stunde 0
- Incident Report MUST be created (inkl. Decision Traces via LR-006A)
- LR-007 Gate bleibt **CLOSED**

### 4.3 Soft-Warnkriterien (Monitor, nicht abbrechen)

**Beobachten, aber NICHT abbrechen:**

1. **Elevated Error Rates:**
   Error-Rate 1-5% (über WARN-Schwelle, aber unter FAIL) → Monitor, keine Abort-Action

2. **Latency Spikes:**
   p95 Latency >Threshold, aber p99 <Max → Monitor, keine Abort-Action

3. **Minor Reject-Rate-Anomalien:**
   Reject-Rate 5-10% oder 85-95% für <24h → Monitor, keine Abort-Action

4. **WebSocket-Reconnects:**
   >5 Reconnects/Tag → Monitor, aber solange <10% Disconnect-Zeit, kein Abort

**Action bei Soft-Warn:**
- Log in `shadow_mode_warnings.log`
- Erwähnen in Daily-Digest (falls existiert)
- NICHT 72h-Zaehler resetten
- Keine Incident-Erstellung

---

## 5. Beweisartefakte

### 5.1 Required Evidence (PASS Criteria)

**LR-007 Gate öffnet ONLY IF folgende Artefakte existieren:**

#### 5.1.1 Shadow Mode Runtime Evidence

**Datei:** `docs/live-readiness/LR-007-RUNTIME-EVIDENCE.md`

**Inhalt (Mindestanforderungen):**
- Start-Timestamp (ISO8601 UTC)
- End-Timestamp (ISO8601 UTC, ≥72h nach Start)
- Container-Uptime-Logs (docker ps Output, zeigt keine Restarts)
- Stream-Length-Timeline (Candles-1m Wachstum, tägliche Snapshots)
- Restart-Count-Validation (RESTARTS=0 für alle Control-Layer-Services)

**Format:**
Markdown mit eingebetteten Code-Blocks (reproduzierbare Bash-Commands)

#### 5.1.2 Metrics Aggregation Report

**Datei:** `docs/live-readiness/LR-007-METRICS-REPORT.json`

**Inhalt (JSON Schema):**
```json
{
  "shadow_mode_id": "string (UUID or timestamp-based ID)",
  "start_timestamp": "ISO8601 UTC",
  "end_timestamp": "ISO8601 UTC",
  "runtime_hours": "integer (≥72)",
  "metrics": {
    "decision_rate": {
      "candles_processed_total": integer,
      "allocation_decisions_emitted_total": integer,
      "risk_orders_evaluated_total": integer,
      "decision_rate_5m_avg": float
    },
    "reject_rate": {
      "orders_rejected_total": integer,
      "orders_approved_total": integer,
      "reject_rate_pct": float
    },
    "risk_gates": {
      "circuit_breaker_trips_total": integer,
      "kill_switch_activations_total": integer,
      "max_kill_switch_duration_seconds": integer
    },
    "latency_percentiles": {
      "candle_processing_p50_ms": float,
      "candle_processing_p95_ms": float,
      "candle_processing_p99_ms": float,
      "risk_evaluation_p50_ms": float,
      "risk_evaluation_p95_ms": float,
      "risk_evaluation_p99_ms": float
    },
    "error_drop_rates": {
      "http_5xx_rate_pct": float,
      "stream_drop_rate_pct": float,
      "total_exceptions": integer
    }
  },
  "verdict": "PASS | FAIL | WARN",
  "fail_reasons": ["string array, empty if PASS"],
  "warn_reasons": ["string array"]
}
```

**Generierung:**
Via Prometheus-Query-Export oder Custom-Aggregator-Script (außerhalb LR-007 Scope).

#### 5.1.3 Decision Trace Samples (LR-006A Integration)

**Datei:** `docs/live-readiness/LR-007-DECISION-TRACES.yaml`

**Inhalt:**
Mindestens **10 Decision-Trace-Beispiele** aus Shadow-Mode-Laufzeit:
- 3x Order-Rejection-Traces (verschiedene `reason_code`)
- 3x Order-Approval-Traces
- 2x Circuit-Breaker-Trip-Traces (falls vorhanden, sonst N/A)
- 2x Regime-Change-Decision-Traces

**Format:**
LR-006A Contract Format (YAML, siehe LR-006A-EVIDENCE.md Beispiele)

**Rationale:**
Beweist, dass LR-006A Contract operational genutzt wird, nicht nur Spec-Compliance.

#### 5.1.4 Snapshot-Reproduzierbarkeit (LR-005 Integration)

**Datei:** `docs/live-readiness/LR-007-SNAPSHOT-VERIFY.md`

**Inhalt:**
- Snapshot vor Shadow-Mode-Start (`completion_snapshot_pre_lr007.json`)
- Snapshot nach Shadow-Mode-Ende (`completion_snapshot_post_lr007.json`)
- Diff-Analyse (welche LR-Tasks Changed, welche Stable)
- Git-SHA-Referenzen (Code-Version während Shadow-Mode-Laufzeit)

**Rationale:**
Sicherstellt, dass Shadow-Mode-Laufzeit auf stabiler Code-Basis stattfand (keine Breaking-Changes during runtime).

### 5.2 Reproduzierbarkeit ohne Runtime

**Anforderung:**
Alle Evidence-Artefakte MÜSSEN aus Git-Repo + Prometheus-Export rekonstruierbar sein **OHNE** erneutes Ausführen von Shadow Mode.

**Test:**
```bash
# Prüfung: Können Metrics aus historischen Prometheus-Snapshots abgerufen werden?
git show <sha>:docs/live-readiness/LR-007-METRICS-REPORT.json
cat LR-007-METRICS-REPORT.json | jq '.metrics.decision_rate'

# Prüfung: Können Decision-Traces ohne Re-Execution gelesen werden?
git show <sha>:docs/live-readiness/LR-007-DECISION-TRACES.yaml
```

**PASS IF:**
Alle Artefakte sind Git-versioniert und lesbar ohne Docker-Runtime.

---

## 6. Out-of-Scope (Explizit)

**LR-007 deckt NICHT ab:**

### 6.1 Capital at Risk

**NICHT Teil von LR-007:**
- Live-Trading-Approval (separate Governance-Entscheidung)
- Capital-Deployment-Strategie
- Exchange-Account-Funding
- Withdrawal-Policies

**Rationale:**
LR-007 validiert nur technische Stabilität, NICHT Finanz-Risiko-Management.

### 6.2 Delivery-Gate

**NICHT Teil von LR-007:**
- Code-Freeze für Shadow-Mode-Periode
- Feature-Development-Block
- PR-Merge-Restrictions

**Rationale:**
Shadow Mode ist Observe-Only. Code-Changes erlaubt, aber Shadow-Runtime resettet bei Breaking-Changes.

### 6.3 Performance-Optimierung

**NICHT Teil von LR-007:**
- Latency-Tuning (p95 Reduction)
- Throughput-Steigerung
- Memory-Footprint-Reduction

**Rationale:**
LR-007 validiert, dass System "gut genug" läuft, NICHT dass es "optimal" läuft.

### 6.4 Observability-Erweiterung

**NICHT Teil von LR-007:**
- Neue Dashboards erstellen
- Neue Alerts hinzufügen
- Loki-Log-Aggregation implementieren

**Rationale:**
LR-007 nutzt bestehende Metrics. Observability-Gaps sind separate Tasks (z.B. LR-009).

### 6.5 Human-Approval-Workflow

**NICHT Teil von LR-007:**
- Six-Eyes-Policy (separate Task: LR-008)
- Jannek-Sign-Off-Mechanism
- Multi-Stakeholder-Review

**Rationale:**
LR-007 definiert objektive Pass/Fail-Kriterien. Human-Approval-Layer ist orthogonale Governance.

---

## 7. PASS/FAIL Logic (Final Decision)

### 7.1 PASS Criteria (ALL MUST BE TRUE)

```
LR-007 PASS ⟺
  (1) runtime_hours ≥ 72
  AND (2) container_restarts == 0 (Control Layer)
  AND (3) decision_rate_5m > 0 for ≥95% of windows
  AND (4) 0.10 ≤ reject_rate ≤ 0.90
  AND (5) circuit_breaker_trips_total < 3
  AND (6) kill_switch_active == 0 (entire period)
  AND (7) error_rate_5xx < 0.05
  AND (8) stream_drop_rate < 0.01
  AND (9) NO HARD FAIL triggers (§4.2)
  AND (10) ALL Evidence Artifacts exist (§5.1)
  AND (11) ≥10 Decision Traces valid (LR-006A format)
```

### 7.2 FAIL Criteria (ANY TRIGGERS FAIL)

```
LR-007 FAIL ⟺
  (1) runtime_hours < 72
  OR (2) ANY container_restart (Control Layer)
  OR (3) ANY HARD FAIL criterion (§4.2)
  OR (4) error_rate_5xx ≥ 0.05
  OR (5) stream_drop_rate ≥ 0.01
  OR (6) decision_rate_5m == 0 for >5% of windows
  OR (7) reject_rate < 0.05 OR reject_rate > 0.95
  OR (8) MISSING Evidence Artifacts (§5.1)
```

### 7.3 WARN State (Beobachten, aber nicht blockieren)

```
LR-007 WARN ⟺
  PASS Criteria erfüllt
  BUT (1-5% error rate OR elevated latency p95 OR minor reject anomalies)
```

**Action bei WARN:**
LR-007 Gate öffnet (PASS), aber Warn-Reasons werden in `LR-007-STATE.yaml` dokumentiert für Jannek-Review.

---

## 8. Decision Point: Objektive Sprechfähigkeit

**Nach LR-007 PASS darf gesprochen werden über:**
- Live-Trading-Readiness-Discussion (NOT approval, only discussion)
- Capital-Deployment-Strategie
- Exchange-Account-Selection
- Risk-Parameter-Tuning für Production

**Nach LR-007 PASS darf NICHT gesprochen werden über:**
- Sofortiges Live-Trading (Human-Gate LR-008 fehlt noch)
- Capital-at-Risk ohne weitere Governance-Reviews
- Auto-Deployment ohne Manual-Approval

**Nach LR-007 FAIL darf NICHT gesprochen werden über:**
- Live-Trading (ANY Kontext)
- Production-Deployment
- Exchange-Account-Funding

**Klare Grenze:**
```
LR-007 PASS = "Technisch bereit für Live-Trading-Diskussion"
LR-007 FAIL = "Shadow Mode nicht erfolgreich, zurück zu Stabilisierung"
```

---

## 9. State-Transition & Integration

### 9.1 LR-007-STATE.yaml Schema

```yaml
task_id: "LR-007"
task_title: "Shadow Mode Validation Gate"
status: "PENDING | IN_PROGRESS | DONE | BLOCKED | ABORTED"
completion_timestamp: "ISO8601 UTC or null"
blocked_reason_code: "RC_B* or null"
blocked_reason_text: "string or null"
blocked_since: "ISO8601 UTC or null"

shadow_mode:
  start_timestamp: "ISO8601 UTC"
  end_timestamp: "ISO8601 UTC or null (if still running)"
  runtime_hours: integer
  verdict: "PASS | FAIL | WARN | IN_PROGRESS"

evidence_artifacts:
  - "docs/live-readiness/LR-007-RUNTIME-EVIDENCE.md"
  - "docs/live-readiness/LR-007-METRICS-REPORT.json"
  - "docs/live-readiness/LR-007-DECISION-TRACES.yaml"
  - "docs/live-readiness/LR-007-SNAPSHOT-VERIFY.md"

fail_reasons: []
warn_reasons: []
```

### 9.2 LR-004 Integration

**LR-007-STATE.yaml validiert durch:**
`lr004_completion_guard.py` (LR-004 Schema-Validator)

**State-Transition-Rules:**
- `PENDING → IN_PROGRESS`: Shadow-Mode-Start (start_timestamp gesetzt)
- `IN_PROGRESS → DONE`: 72h elapsed + ALL PASS criteria
- `IN_PROGRESS → ABORTED`: ANY HARD FAIL criterion
- `DONE → BLOCKED`: Nicht erlaubt (DONE ist final)
- `ABORTED → IN_PROGRESS`: Nach Incident-Resolution, neuer Shadow-Mode-Start

### 9.3 LR-005 Integration

**Snapshot-Generator:**
`completion_snapshot.json` enthält LR-007 Status + Verdict + Runtime-Days

**Beispiel-Snapshot-Eintrag:**
```json
{
  "task_id": "LR-007",
  "status": "IN_PROGRESS",
  "shadow_mode": {
    "runtime_hours": 48,
    "verdict": "IN_PROGRESS",
    "projected_completion": "2026-03-09"
  }
}
```

### 9.4 LR-006A Integration

**Decision-Traces:**
LR-007 Evidence MUST enthalten ≥10 Traces im LR-006A Format.

**Trace-Validation:**
- Artefakt-Referenzen valid (`git:<sha>:<path>#L<start>-L<end>`)
- Keine Secrets/Tresor-Refs
- `replay_verified: true` für mindestens 3 Traces

---

## 10. Erwartetes Ergebnis

**Dieses Dokument definiert:**

1. **Eindeutige Pass/Fail-Logik** (§7) – Keine Grauzone, kein "vielleicht"
2. **Deterministische Bewertung** (§3, §5) – Artefakt-basiert, nicht Meinungs-basiert
3. **Harte Grenzen** (§4.2) – Wann Shadow Mode abgebrochen werden MUSS
4. **Out-of-Scope-Klarheit** (§6) – Was LR-007 NICHT ist
5. **Integration mit Foundation** (§9) – LR-004/005/006A Interoperabilität

**Nach LR-007 gibt es:**
- ✅ Objektive Kriterien für Live-Readiness-Diskussion
- ✅ Kein Interpretationsspielraum (Pass/Fail eindeutig)
- ✅ Kein implizites Go (Human-Gate LR-008 fehlt noch)
- ✅ Kein technischer Drift (alle Artefakte Git-versioniert)

---

## 11. Next Steps (Decision-only, nicht Implementation)

**Nach LR-007 PASS:**

**Option A: LR-008 – Six-Eyes Policy (Human-Gate)**
Erforderlich für Live-Trading-Approval (Jannek-Sign-Off)

**Option B: LR-009 – Observability Foundation**
Dashboards + Alerts für Production-Monitoring (optional, nicht blockierend)

**Option C: LR-010 – Capital-Deployment-Strategie**
Financial-Risk-Governance (außerhalb technischer Scope)

**Nach LR-007 FAIL:**

**Zurück zu:**
- Stabilisierungs-Tasks (Incident-Resolution)
- Root-Cause-Analysis (warum Shadow Mode aborted)
- Neuer Shadow-Mode-Start nach Fixes

---

## End of LR-007 SPEC v1.0

**Governance Clarity:** ✅
**Implementation:** ❌ (out of scope)
**Technical Drift:** ❌ (specification only)
**Live Trading:** ❌ (LR-007 is NOT approval, only validation gate)

---

**Autor:** Claude Code (Session Lead)
**Review:** Ausstehend (Jannek-Approval erforderlich)
**Status:** Draft (Decision-only SPEC)
