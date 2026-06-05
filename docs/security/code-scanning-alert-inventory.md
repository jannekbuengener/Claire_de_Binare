# Code-Scanning Alert Inventory

> **Stand:** 2026-05-15T00:14 CEST (UTC+2)
> **Basis:** Issue [#2289](https://github.com/jannekbuengener/Claire_de_Binare/issues/2289)
> **Kontext:** Slice 1 abgeschlossen via PR [#2486](https://github.com/jannekbuengener/Claire_de_Binare/pull/2486) — `f634ab38`
> **Scope Guard:** Dieses Dokument ist Arbeitsbasis für Fix-Slices. Es ist kein Live-Readiness-Verdikt, keine Echtgeld-/Trading-Freigabe und kein LR-Go/No-Go. LR-Status bleibt NO-GO gemäß `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.

---

## 1. Executive Summary

| Metrik | Wert |
|--------|------|
| Offene Alerts gesamt | **895** |
| CodeQL | **58** |
| Trivy | **837** |
| Unique Trivy-CVEs | **95** |
| CodeQL warning-level (handlungsrelevant) | **2** |
| Trivy error-severity (CDB-Services) | **105** |

**Wichtigste Erkenntnisse:**

- **Slice 1 abgeschlossen:** PR #2486 gemergt, CodeQL-main-run erfolgreich.
  `services/ws/mexc_proto_gen/**` hat 0 offene CodeQL-Alerts.
  CodeQL gesamt von 92 → 58 (−34): Proto-Gen-Rauschen eliminiert.
- **2 CodeQL warnings** in produktivem Code erfordern Analyse, bevor Note-Level-Rauschen priorisiert wird.
- **Trivy-Masse** (837 Alerts, 95 CVEs) ist strukturell bekannt: alle 8 CDB-Service-Images teilen dieselbe Basis (`python:3.11-slim-trixie`), 7 Images × ~14 error-CVEs. Fixability unvollständig aus API ableitbar — als TBD markiert.
- **Third-party Trivy** (141 Alerts): Grafana und Prometheus tragen eigene CVE-Cluster. Keine CDB-Code-Änderung möglich, nur Image-Bump.

---

## 2. Abfrage-Basis

```bash
# Alle offenen Alerts, alle Tools, paginiert
gh api "repos/jannekbuengener/Claire_de_Binare/code-scanning/alerts?state=open&per_page=100&page=N"

# Issue und PR
gh issue view 2289 --json number,title,state,labels,updatedAt,url
gh pr view 2486 --json number,state,mergedAt,mergeCommit,url
```

**Einschränkungen:**
- `fixedVersion` / Fixability ist nicht direkt aus der Code-Scanning-API abrufbar; muss aus Trivy-Advisory-Details einzeln geprüft werden.
- `fixed`-State-Übergänge in GitHub sind asynchron; Proto-Gen-Alerts zeigen noch nicht `state=fixed`, sind aber aus `state=open` verschwunden — valider Beweis.
- `TRIAGE_RUNBOOK.md` und `TRIVY_TRIAGE_1651.md` in diesem Verzeichnis dokumentieren Trivy-Dismiss-Prozesse aus dem Vorgänger-Epic (#1649/#1651).

---

## 3. Gesamtzahlen

### Nach Tool

| Tool | Alerts |
|------|--------|
| CodeQL | 58 |
| Trivy | 837 |
| **Gesamt** | **895** |

### CodeQL nach Severity

| Severity | Alerts |
|----------|--------|
| ⚠️ warning | 2 |
| note | 56 |

### Trivy nach Severity

| Severity | CDB-Services | Third-Party | Gesamt |
|----------|-------------|-------------|--------|
| error (Critical/High) | 105 | 52 | 157 |
| warning (Medium) | 521 | 82 | 603 |
| note (Low) | 70 | 7 | 77 |
| **Gesamt** | **696** | **141** | **837** |

---

## 4. CodeQL-Cluster

### 4.1 ⚠️ Warning-Level — Handlungspflicht (Prod-Code)

| Alert-ID | Rule | Datei | Kategorie | URL |
|----------|------|-------|-----------|-----|
| #4286 | `py/redundant-comparison` | `services/risk/service.py` | service-prod | [Link](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4286) |
| #4285 | `py/implicit-string-concatenation-in-list` | `tools/mcp/context_bridge.py` | tools | [Link](https://github.com/jannekbuengener/Claire_de_Binare/security/code-scanning/4285) |

**Root-Cause-Hypothesen:**
- `#4286`: `balance_usdt > 0`-Vergleich in Risk Service könnte invariant true sein — potenzieller Logik-Bug auf dem Order-Pfad. Bedarf Code-Lektüre vor Fix.
- `#4285`: Zwei benachbarte String-Literale in einer Liste ohne Komma könnten versehentlich konkateniert werden. Python-Fallstrick.

### 4.2 Note-Level — Prod-Code (`services/`, `core/`)

| Alert-ID | Rule | Datei |
|----------|------|-------|
| #4111 | `py/unused-global-variable` | `services/validation/strategy_replay_runner.py` |
| #4110 | `py/unused-global-variable` | `services/execution/service.py` |
| #4148 | `py/unused-import` | `core/replay/dataset_provider.py` |

### 4.3 Note-Level — Tools (17 Alerts)

| Rule | Anzahl | Dateien |
|------|--------|---------|
| `py/unused-import` | 10 | `tools/surrealdb/trust_summary.py` (×2), `tools/mcp/context_evidence_memory_tools.py`, `tools/misc/verlosung/validate_persistence.py`, `tools/paper_trading/service.py`, `tools/paper_trading/email_alerter.py`, `tools/surrealdb/context_stop_resolver.py`, `tools/surrealdb/context_self_explanation.py`, `tools/surrealdb/context_required_reads.py`, `tools/research/portfolio_manager.py` |
| `py/unused-global-variable` | 3 | `tools/surrealdb/context_stop_resolver.py` (×2), `tools/surrealdb/context_impact_radar.py` |
| `py/unused-local-variable` | 2 | `tools/mcp/context_bridge.py` (#4055, #4054) |
| `py/empty-except` | 1 | `tools/mcp/context_evidence_memory_tools.py` (#4415) |
| `py/implicit-string-concatenation-in-list` | 1 | `tools/mcp/context_bridge.py` (#4285) ← **warning** |

### 4.4 Note-Level — Infrastructure / Scripts (8 Alerts)

| Rule | Anzahl | Dateien |
|------|--------|---------|
| `py/unused-import` | 7 | `infrastructure/scripts/generate_shadow_digest.py`, `reconcile_positions.py`, `verify-persistence.py`, `verify-ollama.py`, `verify-graphiti.py`, `scripts/validate_paper_market_data_provenance.py`, `scripts/drills/lr041_redis_postgres_failure_runner.py` |
| `py/unused-local-variable` | 1 | `infrastructure/scripts/lr040_soak_gate_eval.py` |

### 4.5 Note-Level — GitHub Scripts (3 Alerts)

| Rule | Anzahl | Dateien |
|------|--------|---------|
| `py/unused-import` | 3 | `.github/scripts/control_plane_validate.py`, `.github/scripts/post_merge_followup_scanner.py` (×2) |

### 4.6 Note-Level — SDK (5 Alerts, historical)

> **Historical:** `cdb_agent_sdk/` was removed from the repo (PR #2994). Agent skills now live under `.codex/cdb_skills/`, `.cursor/skills/`, and `.opencode/skills/`. Alert paths below refer to the former package layout at scan time.

| Rule | Anzahl | Dateien (historical paths) |
|------|--------|---------|
| `py/unused-import` | 5 | `cdb_agent_sdk/src/cdb_agent_sdk/main.py` (×3), `cdb_agent_sdk/tests/test_agents.py`, `cdb_agent_sdk/tests/test_agent.py` |

### 4.7 Note-Level — Tests / Fixtures (21 Alerts)

| Rule | Anzahl | Dateien (Auswahl) |
|------|--------|---------|
| `py/unused-local-variable` | 14 | `tests/unit/risk/test_service.py`, `test_contract_enforcement.py`, `test_context_bridge.py` (×3), `test_replay_reporter.py`, `test_replay_report_builder.py`, `test_dataset_provider.py`, `test_lr021_export_redis.py`, `test_lr040_soak_gate_eval.py`, `test_dual_write_evidence_gate.py`, `test_backlog_curation.py`, `test_smoke_pipeline.py`, `test_baseline_measurements.py` |
| `py/unused-import` | 5 | `tests/fixtures/surrealdb/context_graph/sample_module.py` (×4), `tests/unit/db_writer/test_service.py` |
| `py/unused-global-variable` | 1 | `tests/unit/validation/test_replay_reporter.py` |
| `py/mixed-returns` | 1 | `tests/fixtures/db_fixtures.py` (#4262) |

---

## 5. Trivy-Cluster

### 5.1 CDB-Service-Images (696 Alerts)

Alle 8 CDB-Services basieren auf `python:3.11-slim-trixie` (SHA-pinned). CVEs replizieren sich über alle Images.

| Image | Total | error | warning | note |
|-------|-------|-------|---------|------|
| `library/cdb_allocation` | 94 | 14 | 70 | 10 |
| `library/cdb_market` | 94 | 14 | 70 | 10 |
| `library/cdb_regime` | 94 | 14 | 70 | 10 |
| `library/cdb_risk` | 94 | 14 | 70 | 10 |
| `library/cdb_signal` | 94 | 14 | 70 | 10 |
| `library/cdb_ws` | 94 | 14 | 70 | 10 |
| `library/cdb_execution` | 92 | 14 | 68 | 10 |
| `library/cdb_db_writer` | 40 | 7 | 33 | 0 |

**Top error-CVEs (CDB, Auswahl):**

| CVE | Alerts | Severity |
|-----|--------|----------|
| CVE-2025-69720 | ×32 | error |
| CVE-2026-29111 | ×16 | error |
| CVE-2026-4878 | ×8 | error |
| CVE-2026-42010/42011 | ×7 each | error |
| CVE-2026-3833/33845/33846/27135/7598 | ×7 each | error |

**Root Cause:** OS-Pakete in `python:3.11-slim-trixie` (`libssh2`, `libkrb5`, `gnutls`, `libcap` u.a.) tragen CVEs. Fixability: **TBD** — muss per CVE einzeln geprüft werden. `trivy.yml` nutzt `ignore-unfixed: true` im SARIF-Upload; historische Alerts ohne Fix-Version können trotzdem offen bleiben.

### 5.2 Third-Party Images (141 Alerts)

| Pfad | Total | error | warning | note |
|------|-------|-------|---------|------|
| `usr/share/grafana/bin/grafana` | 40 | 19 | 20 | 1 |
| `grafana/grafana` | 35 | 0 | 29 | 6 |
| `bin/prometheus` | 13 | 8 | 5 | 0 |
| `usr/share/grafana/bin/grafana-cli` | 13 | 7 | 6 | 0 |
| `usr/share/grafana/bin/grafana-server` | 13 | 7 | 6 | 0 |
| `bin/promtool` | 10 | 6 | 4 | 0 |
| `usr/local/bin/gosu` | 9 | 5 | 4 | 0 |
| pip packages (3 entries) | 7 | 0 | 7 | 0 |
| `library/postgres` | 1 | 0 | 1 | 0 |

Fix-Strategie: Image-Bump in Compose-Dateien. Kein CDB-Quellcode-Fix möglich.

### 5.3 Fixability-Status

| Kategorie | Einschätzung |
|-----------|-------------|
| CDB-Service-CVEs mit Fix-Version verfügbar | **TBD** — Einzelprüfung nötig |
| CDB-Service-CVEs ohne Fix (upstream) | **TBD** |
| Third-party CVEs (Grafana/Prom) | **TBD** — Grafana/Prom Release-Notes prüfen |
| pip-Pakete | Wahrscheinlich per `pip install --upgrade` fixbar |

---

## 6. Priorisierte Fix-Slices

| Slice | Status | Ziel | Alerts | Risiko | Erwarteter Impact |
|-------|--------|------|--------|--------|-------------------|
| **Slice 1** | ✅ **DONE** (PR #2486) | CodeQL proto-gen exclusion (`mexc_proto_gen/**`) | −34 CodeQL | Niedrig | 92→58 CodeQL-Alerts |
| **Slice 2** | 🔲 Bereit | `py/redundant-comparison` → `services/risk/service.py` | 1 (⚠️ warning) | Mittel — Risk-Service-Prod-Code | Schließt potenziellen Logik-Bug im Order-Pfad |
| **Slice 3** | 🔲 Bereit | `py/implicit-string-concatenation-in-list` → `tools/mcp/context_bridge.py` | 1 (⚠️ warning) | Niedrig — Tools-Code | Bereinigt zweiten warning, sauberer CodeQL-Stand |
| **Slice 4** | 🔲 Nach Slice 2+3 | CodeQL note-level cleanup (tests/sdk/infrastructure/tools) | ~50 (note) | Sehr niedrig | Signifikante Rauschreduktion; evtl. weitere `paths-ignore` oder Einzel-Fixes |
| **Slice 5** | 🔲 Komplex | Trivy CDB-Service base image — neue `python:3.11-slim-trixie` SHA | ~696 (anteilig) | Mittel — Dockerfile-Änderung, alle 8 Services | Reduziert error-CVEs soweit upstream fix verfügbar |
| **Slice 6** | 🔲 Komplex | Trivy third-party images (Grafana/Prometheus) in Compose-Dateien | ~141 | Mittel — Stack-Bump | Schließt dritte CVE-Gruppe |
| **Slice 7** | 🔲 Nur nach extra GO | `.trivyignore` / Dismiss-Prozess für no-fix-upstream CVEs | TBD | Niedrig — rein dokumentarisch | Rauschen entfernen, kein echter Fix |

**Empfohlene Reihenfolge:** Slice 2 → Slice 3 → Slice 4 → Slice 5/6 (parallel planbar) → Slice 7

---

## 7. Parked / Blocked

- **Trivy error-CVEs ohne upstream Fix:** Unbestimmt bis Slice 5 / Einzelprüfung. Nicht dismissbar ohne dokumentierten Grund und Re-Evaluation-Datum.
- **Grafana/Prometheus third-party CVEs:** Blockiert auf upstream Releases. Kein CDB-Code-Fix möglich.
- **`py/mixed-returns` (#4262, `tests/fixtures/db_fixtures.py`):** Test-Fixture, niedrige Priorität — parken bis Slice 4.
- **`py/empty-except` (#4415, `tools/mcp/context_evidence_memory_tools.py`):** Defensives Coding-Pattern — Needs Review, ob echter Bug oder bewusstes Catch-All.
- **`pip-24.0` / `pip-25.3` Alerts:** pip selbst in images — wahrscheinlich fixbar durch Basis-Image-Bump, aber nicht isoliert adressierbar.

---

## 8. Dismissal-Regeln

Referenz: [`docs/security/TRIAGE_RUNBOOK.md`](TRIAGE_RUNBOOK.md) §2 Triage-Entscheidungslogik und §4 Dismiss-Cluster.

Zusätzliche Regeln für diesen Epic (#2289):

1. **Kein Dismissal ohne dokumentierten Grund** (Klasse + Root-Cause-Begründung).
2. **Kein Massendismissal** ohne explizites GO und separaten PR.
3. **Re-Evaluation-Datum** erforderlich bei jedem Dismissal (max. 6 Monate).
4. **Trivy no-fix-upstream:** Dismissal nur nach Einzelnachweis, dass kein Fix-Release existiert.
5. **CodeQL false-positive:** Erst nach Code-Lektüre und schriftlicher Begründung im PR-Body.
6. **Dismissal erst nach extra GO** — kein Dismissal in Fix-Slices ohne separate Freigabe.

---

## 9. Restunsicherheiten

- **Trivy-Fixability:** Nicht vollständig aus der Code-Scanning-API ableitbar. `fixed_at` und Advisory-Details erfordern Einzelabfragen oder externe CVE-Datenbank.
- **`ignore-unfixed: true` in `trivy.yml`:** Neuere Scans sollten keine no-fix-Alerts mehr hochladen — trotzdem sind historische Alerts aus älteren Scans noch offen. Konsequenz: echte Anzahl adressierbarer Trivy-CVEs ist kleiner als 837.
- **`py/redundant-comparison` (#4286):** Ob echter Logik-Bug oder False Positive ist erst nach Code-Lektüre entscheidbar. Slice 2 beginnt mit Read-only-Analyse.
- **CodeQL `fixed`-State:** Asynchron — Proto-Gen-Alerts noch nicht als `state=fixed` sichtbar, aber aus offener Liste verschwunden. Kein Handlungsbedarf.
- **CDB-Service-Image-SHA:** Aktuell SHA-gepinnt in Dockerfiles (`python:3.11-slim-trixie@sha256:...`). Ob eine neuere SHA verfügbar ist und welche CVEs sie löst: TBD für Slice 5.
