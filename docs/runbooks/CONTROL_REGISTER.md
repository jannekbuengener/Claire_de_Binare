# Control Register

**Letzte Aktualisierung:** 2026-07-14 (Reconcile-Batch #4041/#4043/#4045/#4053/#4057/#4060/#4066/#4084/#4086)
**SSOT Live-Readiness:** [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md)
**Verdict:** NO-GO
**Control-Board Stage:** `trade-capable` (ratifiziert 2026-04-08 via Issue [#1492](https://github.com/jannekbuengener/Claire_de_Binare/issues/1492))

---

## Cockpit-Einstieg

1. GitHub Issue `[CONTROL] Claire de Binare — Operatives Cockpit (dauerhaft offen)` — **[#1445](https://github.com/jannekbuengener/Claire_de_Binare/issues/1445)**
   - Rebaseline 2026-05-13: [`docs/runbooks/control-cockpit/CONTROL_COCKPIT_1445_REBASELINE_2026-05-13.md`](control-cockpit/CONTROL_COCKPIT_1445_REBASELINE_2026-05-13.md)
   - Alte Kommentare sind Ledger/Telemetry, keine Live-Wahrheit.
2. GitHub Issue [#1492](https://github.com/jannekbuengener/Claire_de_Binare/issues/1492) — ratifizierter Stage-Uebergang `stability -> trade-capable`
3. [`CURRENT_STATUS.md`](../../CURRENT_STATUS.md) — Repo/Engineering-Status, Session-Ledger
4. [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](../live-readiness/LR-AUDIT-STATUS-2026-03-05.md) — Live-Readiness-Verdikt

---

## Aktueller Stage-Stand

- Board-/Projekt-Stage: `trade-capable`
- Ratifikation: 2026-04-08 via Issue `#1492`
- Guardrails bleiben unveraendert:
  - shadow/mock only
  - kein Live-Kapital
  - kein Grafana-Gate
  - keine Strategie-Validierung
  - `LR-050` bleibt `NO-GO`

---

## SSOT-Grenzen

| Quelle | Zuständigkeit |
|---|---|
| `docs/runbooks/CONTROL_REGISTER.md` | Control-Board-Cockpit, aktueller Stage-/Operating-Focus |
| `CURRENT_STATUS.md` | Repo-Stand, Session-Ledger, offene PRs |
| `LR-AUDIT-STATUS-2026-03-05.md` | Live-Readiness-Phasenstatus, Go/No-Go-Verdikt |
| `ACTIVE_ROADMAP.md` | Pointer auf beide SSoTs |

Regel: Phasen-Status nie in CURRENT_STATUS eintragen. LR-Verdikt nie aus einer Board-Stage ableiten. Board-Stage nie als implizites LR-GO lesen.

---

## Architecture Decisions

| ADR | Topic | Decision | Status |
|-----|-------|----------|--------|
| `ADR-002` | Context Intelligence Canon (`knowledge/decisions/ADR-002-context-intelligence-canon.md`, Issue #3419) | `ADOPTED` — Foundation-Reparatur (#3420–#3427) und Trust-Wave (#3449–#3459) abgeschlossen; Context Intelligence Canon ist produktiv | **accepted / adopted** |
| `#2775` | Context Brain Default Posture (`knowledge/decisions/CDB_CONTEXT_BRAIN_DEFAULT_POSTURE.md`) | `ALLOW_READONLY_CONDITIONAL` | **accepted / active** |

Hinweise:
- ADR-002 autorisiert weder Runtime- noch Live- noch DB-Write-Operationen.
- `PERSIST_ALLOWED=false` und `MUTATION_ALLOWED=false` bleiben unverändert.
- Board-Stage `trade-capable` ist orthogonal zu ADR-002.

---

## Replay-Status-Spiegelung (offline / control)

- Kanonischer Replay-Lauf: `.github/workflows/lr021_replay_smoke.yml` (on-demand + schedule), Entry-Point `make replay-shadow-run`.
- Primäre Run-Wahrheit: GitHub Actions Run + Artifact `replay-smoke-<run_id>` (inkl. `report.json`/`manifest.json`/`audit.log`).
- Spiegel-Surfaces (knapp, kein Doppel-Reporting):
  1. `#1445` (Cockpit): kompakter Pointer auf letzten relevanten Replay-Smoke (PASS/FAIL + Run/Artifact-Link).
  2. `#1784` (Paper-Control): nur wenn fuer den laufenden Paper-Betrieb operativ relevant.
  3. `#1786` (Checkpoint): optional als Einzeiler im regulaeren Checkpoint.
- Guardrail: Offline-Replay-Evidenz ist **nicht** LR-Go/No-Go und **nicht** Echtgeld-Go.
  LR-Verdikt bleibt ausschliesslich `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`.

### Standardtext fuer Replay-Status (Kommentarvorlage)

```md
### Replay Smoke (offline)
- Zeitpunkt (UTC):
- Trigger: workflow_dispatch | schedule
- Ergebnis: PASS | FAIL
- Run: <GitHub Actions Run URL>
- Artefakt: replay-smoke-<run_id>
- run_id / gate_status / deterministic_replay_ok:
- Einordnung: Offline-Replay-Evidenz; keine LR-/Live-/Echtgeld-Freigabe.
```

---

## Wiederkehrende Drift-Vektoren

| Drift-Typ | Prüfung | Kontext-Issues |
|---|---|---|
| Solo-Maintainer in SOPs | kein Mehrpersonen-Eskalationspfad in aktiven Docs | #1372 |
| Terminologie BLACK | Risk Service / cdb_risk statt BLACK | #1373, #1388 |
| Stack-Canon single-compose | compose.blue.yml + compose.red.yml | #1371 |
| Credential-host canon | operator tresor layout per runbook #1411 | #1411 |
| Runbook legacy stack_up | keine base+dev Referenz in aktiven Runbooks | #1410 |
| Discovery-Surfaces | ENTRYPOINTS.yaml / CHEATSHEET aktuell | #1413 |
| ARCHITECTURE_MAP | bei Service-Change nachziehen | #1409 |
| GitHub Actions UI Workflow-Count > Repo-Count | `state: active` in API ≠ ausführbar; gelöschte Dateien behalten historische Registrierung; platform-managed dynamic Workflows (Copilot/Dependabot/CodeQL) zählen zusätzlich; erwartet, kein Risiko | #1666 |

Kontext-Issue-Nummern sind historische Anker (alle CLOSED) — nicht als offene Aufgaben interpretieren.

---

## Governance-Anker

- **Human Gate GRANTED:** 2026-04-04
  Artefakt: `docs/evidence/reports/p5_canary/2026-04-04/decision_record.yaml`
  Gilt für: P5 prestart only — kein Echtgeld-Trading ohne erneuten expliziten Gate

---

## Aktive Infra-Workflows

| Workflow | Trigger | Zweck |
|---|---|---|
| `weekly_digest.yml` | wöchentlich | Issue-/Status-Digest |
| `weekly_digest_failure_alert.yml` | nach `weekly_digest.yml` | Failure-Eskalation als `report:weekly-fail` Issue nur bei echtem Fehler |
| `cdb-weekly-control-hygiene-classifier.yml` | Mo/Do/Fr 07:30 UTC + manuell | Weekly hygiene/reconciliation fuer `#1445`; dedupe-sicherer Wochenkommentar, branch-obsolescence Klassifikation (repo-backed) und lokaler/manual worktree-cleanup handoff; optional max 0..2 enge Follow-up-Issues |
| `cdb-daily-delta-triage.yml` | Di/Mi/Fr/So 06:20 UTC + manuell | Daily fresh-delta triage fuer `#1445`; delta-only gegen letzten Daily-Marker, optional max 0..1 enges Follow-up-Issue |
| `cdb-backlog-curation.yml` | `issues.labeled` (`task` oder gepaarte `type:*` + `scope:*` Labels) | Bounded issue-scoped Companion-Workflow fuer implementation-relevante Issues; erzeugt agent-readable JSON unter `artifacts/backlog-curation/issue-<number>.json` mit Handoff-Klassen/Budgets/Fingerprint und postet einen dedupe-sicheren Receipt-Kommentar direkt unter dem betroffenen Issue |
| `cdb-backlog-anomaly-escalation.yml` | `workflow_run` (nach `cdb-backlog-curation`) + manuell | Separate Phase-1-Eskalationslane fuer starke typed backlog-curation Anomalien; klassifiziert fail-closed (`report_only` / `follow_up_issue` / `unclear`), blockiert sensitive/private Findings fuer public auto-issueing und emittiert dedupe-safe max 0..1 Follow-up-Issue |
| `governance-audit.yml` | manuell | Governance-Audit |
| `cdb-control-followup-classifier.yml` | manuell | Human-in-the-loop Klassifikation repo-backed Control-Findings |
| `cdb-post-merge-followup-scanner.yml` | bei gemergten PRs + manuell | Repo-backed Post-Merge-Scan fuer kleine Nachzugspakete; Kommentar nach `#1445` oder enges dedupe-sicheres Follow-up-Issue; `architecture_service_catalog_drift` wird unterdrueckt fuer digest-only Image-Pin-Aenderungen (semantischer Tag unveraendert, nur `@sha256`-Digest aktualisiert — PR #1729) |
| `gemini-scheduled-triage.yml` | manuell (geparkt fail-closed) | Gemini-Triage |
| `project_reconcile_daily.yml` | täglich | Board-Reconciliation |
| `control_board_upsert.yml` | Mo 02:30 UTC | GitHub Project #8 Upsert |
| `control_board_auto_routing.yml` | manuell (geparkt fail-closed, #2772) | Per-Event-Router fuer Project #8; auto-`issues`/`pull_request`/`repository_dispatch`-Trigger bewusst entfernt, nur noch `workflow_dispatch` (druckt Parkhinweis). Board-Konsistenz laeuft ueber `control_board_upsert.yml`. |

---

## Workflow-Control-Notizen

- Dependabot Autopilot (PRs #4062, #4067): Der fail-closed Klassifikator liest normalisierte Fakten gegen die versionierte Phase-1-Allowlist. Der Broker ist **report-only**; `ELIGIBLE` autorisiert keinen Merge, `merge_authorized=false`, keine GitHub-Mutation und keine Runtime-/LR-Ableitung. Phase-1-Kill-Switch/Merge-Ausführung bleibt außerhalb dieses Control-Stands.
- `security-scan.yml` / Prometheus (PR #4083, gemergt 2026-07-14, Commit `2081d41d`): Scan-cleared Pin `prom/prometheus:v3.13.0@sha256:c6b27ea…` → `v3.13.1@sha256:3c42b892…` in Security-Matrix, Shared Base, RED und v3-Overlay synchron nachgezogen. `CVE-2026-39822` ist im validierten Kandidaten nicht mehr vorhanden; Postgres/Grafana bleiben upstream-abhaengig und unveraendert. Keine Alert-Dismissals, kein Runtime-Deploy, LR **NO-GO**.
- `security-scan.yml`: Trivy-SARIF-Uploads muessen explizit stabile Kategorien verwenden (`trivy-base-*`, `trivy-custom-*`), damit Digest-/Tag-Bumps keine neuen Code-Scanning-Baselines aufspalten. Security-Triage und Dismiss-Cluster bleiben im `docs/security/TRIAGE_RUNBOOK.md` verankert.
- `security-scan.yml` (PR #1768): Redis-Digest-Refresh — `redis:7.4.8-alpine`-Digest in `trivy-scan-base`- und `scan-base-images`-Matrix aktualisiert (digest-only, semantischer Tag unveraendert). Trivy-SARIF-Kategorie `trivy-base-redis` bleibt stabil; kein neues Security-Triage-Item.
- `security-scan.yml` (PR #2302): Postgres-Digest-Refresh — `postgres:15.17-alpine`-Digest in `trivy-scan-base`- und `scan-base-images`-Matrix aktualisiert (digest-only, semantischer Tag unveraendert). Trivy-SARIF-Kategorie `trivy-base-postgres` bleibt stabil; kein neues Security-Triage-Item.
- `security-scan.yml` (PR #2308): Revert Grafana image pin von `13.0.1-ubuntu` zurueck auf `11.4.7-ubuntu` in `trivy-scan-base`-Matrix; post-merge Trivy zeigte #2292 curl-CVEs unveraendert und 47 zusaetzliche Grafana-13/Ubuntu-24.04-Befunde. Trivy-SARIF-Kategorie `trivy-base-grafana` bleibt stabil bei `11.4.7-ubuntu`; kein LR-/Live-/Echtgeld-Impact. #2292 bleibt upstream-blocked. PR #2305 ist durch diesen Revert supersediert.
- `security-scan.yml` (PR #2544): Grafana-Base-Image in der Trivy-Matrix und in der RED-Runtime auf `grafana/grafana:12.4.3-security-02-ubuntu@sha256:089f9dbb...` aktualisiert. Trivy-SARIF-Kategorie `trivy-base-grafana` bleibt stabil; `cdb_grafana` bleibt RED-Monitoring und erzeugt kein LR-/Live-/Echtgeld-Signal.
- `emoji-bot.yml`: Kommentarinhalt aus `issue_comment` bleibt untrusted Input und darf nur ueber `env`/kontrollierte Uebergaben in Shell- oder Python-Schritte fliessen. Der Workflow ist ein Operator-Helfer, keine Evidenz- oder Freigabe-Surface. Bekannte Residual-Haertung fuer multiline-Outputs an `$GITHUB_OUTPUT` bleibt separater Folgescope und wird hier nicht ueberdehnt.
- `.github/scripts/advanced-emoji-filter.py`: Emoji-Erkennung laeuft fail-closed primaer ueber `emoji.emoji_list(...)`; die frueheren breiten Unicode-Range-Regexe wurden im CodeQL-Nachzug aus PR #1757 entfernt. Der Script bleibt ein Operator-Helper fuer Kommentarhygiene; keine LR-/Freigabe-Evidenz ableiten.
- Workflow-Permissions aus PR #1749: `.github/workflows/stale.yml` nutzt explizit `issues: write` + `pull-requests: write`, `emoji-filter.yml` fuehrt top-level `contents: read` plus job-spezifisches `contents: write`, `emoji-bot.yml` setzt fuer `help-command` explizit `issues: write`, `gemini-dispatch.yml` bleibt mit `permissions: {}` fail-closed. Diese Grants sind eng auf den jeweiligen Automationszweck begrenzt.
- Action-Dependency-Bumps (PRs #1788, #1789, #1790, #1792, 2026-04-21): Vier Dependabot-Bumps ohne operative Control-Aenderung — `actions/cache` 5.0.4→5.0.5 (`trivy.yml`, PR #1788); `actions/upload-artifact` 4.6.2→7.0.1 (alle Artifact-produzierenden Workflows inkl. aller Control-Workflows, PR #1789, SHA-gepinnt auf den Commit zu v7.0.1); `github/codeql-action` 4.35.1→4.35.2 (`gitleaks.yml`, `security-scan.yml`, `trivy.yml`, PR #1790, SARIF-Kategorien und Security-Triage-Postur unveraendert); `docker/build-push-action` 6.18.0→7.1.0 (`docker-publish.yml`, PR #1792, kein Control-Workflow). Keine Aenderung an Artifact-Upload-Semantik, SARIF-Kategorien oder Control-Surface-Verhalten.
- Action-Dependency-Bump (PR #1958, 2026-04-27): `aquasecurity/trivy-action` `876cf04`→`ed142fd` (Trivy v0.70.0) in `ci.yaml`, `security-scan.yml`, `trivy.yml`. Keine Aenderung an SARIF-Kategorien, Security-Triage-Postur oder operative Control-Logik.
- Action-Dependency-Bump (PR #2284, 2026-05-04): `github/codeql-action/upload-sarif` SHA-Refresh `95e58e9`→`e46ed2c` (4.35.2→4.35.3) in `gitleaks.yml`, `security-scan.yml`, `trivy.yml`. SARIF-Kategorien und Security-Triage-Postur unveraendert; keine operative Control-Aenderung.
- Action-Dependency-Bump (PR #2431, 2026-05-11): `github/codeql-action` SHA-Refresh `e46ed2c`→`68bde55` (4.35.3→4.35.4) in `codeql-python.yml` (`init`, `analyze`) sowie `gitleaks.yml`, `security-scan.yml`, `trivy.yml` (`upload-sarif`). Keine Aenderung an Triggern, Permissions, SARIF-Kategorien oder Security-Triage-Postur; keine operative Control-Aenderung.
- Action-Dependency-Bump (PR #2540, 2026-05-18): `github/codeql-action` SHA-Refresh `68bde55`→`9e0d7b8` (4.35.4→4.35.5) in `codeql-python.yml` (`init`, `analyze`) sowie `gitleaks.yml`, `security-scan.yml` und `trivy.yml` (`upload-sarif`). SARIF-Kategorien, Trigger und Security-Triage-Postur bleiben unveraendert; keine LR-/Live-/Echtgeld-Ableitung.
- Action-Dependency-Bump (PR #2541, 2026-05-18): GitHub App credential action SHA-Refresh `1b10c78`→`bcd2ba4` in `gemini-invoke.yml`, `gemini-review.yml`, `gemini-scheduled-triage.yml` und `gemini-triage.yml` (vollständiger Action-Pin siehe PR-Diff). Keine Aenderung an Triggern, App-Auth-Gating oder Gemini-Control-Surface-Semantik.
- `lr021_replay_smoke.yml` (PR #1834): Summary-Schritt semantisch geschaerft — `replay_execution_status` spiegelt den Workflow-/Pipeline-Pass, `gate_status` das fachliche Strategie-Gate; beide Werte sind nicht zu verwechseln und kein LR-/Live-Signal. Die gekoppelte Replay-Surface (Workflow-`workflow_dispatch` + Makefile-Target `replay-shadow-run`) wird fail-closed durch `tests/unit/scripts/test_lr021_replay_surface.py` abgesichert.
- `docs-hub-guard.yml` (PR #1968, 2026-04-27): Der Runtime-Artefakt-Guard erlaubt `docs/runbooks/evidence/*.log` explizit als runbook-nahe Evidence-Ausnahme. Generische `*.log`-Dateien ausserhalb dieses Pfads sowie `logs/`, `__pycache__/`, `.pytest_cache/`, `*.pyc` und `*.pyo` bleiben blockiert. Keine Workflow-/Runtime-/Trading-/LR-Semantik ableiten.
- `codeql-python.yml` (PR #2325): Custom CodeQL Python Security-Analyse mit `queries: security-and-quality`. Trigger: push main, PR main, weekly Monday 03:21 UTC, `workflow_dispatch`. Permissions: `security-events: write` fuer SARIF-Upload mit Kategorie `/language:python`. Ergaenzt das GitHub-native Default-CodeQL um erweiterte Security-and-Quality-Queries. Security-Triage-Postur analog zu Trivy/Gitleaks — keine neuen SARIF-Kategorien, kein LR-/Live-/Echtgeld-Signal.
- `security-alert-readout.yml` (PR #2422, gemergt 2026-05-10T19:21:21Z, Commit `3c6ea6b66e49`): `fix(security): disable direct publish in alert readout workflow` — direktes Issue-Publish (Commit-Loop fuer Artifact-Readout direkt an `#1445`) entfernt; Workflow produziert nur noch Step-Summary + Artefakt. Kein nachwirkender Schreibzugriff auf Issues im Normalbetrieb; TRIAGE_RUNBOOK.md §9 (Publish-Mode-Tabelle) entsprechend aktualisiert. Security-Triage-Postur unveraendert; kein LR-/Live-/Echtgeld-Signal.
- `security-alert-readout.yml` (PR #2424, gemergt 2026-05-10T20:45:24Z, Commit `2fbeebafeaaa`): `feat(security): add persist_via_pr mode to alert readout workflow` — zweiter Job `persist-via-pr` hinzugefuegt; laeuft nur bei `workflow_dispatch` mit `inputs.persist_via_pr=true`. Erstellt Branch `chore/security-readout/YYYY-MM-DD` von `main`, commitet Artefakt mit `[skip ci]`, pushed und oeffnet PR via `gh pr create --base main` (kein Auto-Merge). Dedupe-Guard gegen bestehende offene PRs (gleicher Branch-Name). DATE-Validation fail-closed via Regex (`^[0-9]{4}-[0-9]{2}-[0-9]{2}$`). Permissions job-scoped: `contents: write` + `pull-requests: write` nur fuer `persist-via-pr`-Job; Top-Level-Permissions bleiben `contents: read` + `security-events: read`. TRIAGE_RUNBOOK.md §9 auf persist-via-pr-Modus nachgezogen. Kein LR-/Live-/Echtgeld-Signal. Epic: #2289.
- `security-alert-readout.yml` (PR-Slice, 2026-05-13): `feat(security): comment readout results on epic #2289` — neuer Job `comment-epic` postet nach jedem Run einen kompakten Ledger-Kommentar auf Issue #2289 (Run-Metadaten, `readout_status`, `delta_status`, Artefaktpfade). Permissions job-scoped: `issues: write` nur im Kommentar-Job; Top-Level-Permissions unveraendert. Keine neuen Issues, keine Alert-Dismissals, kein Auto-Merge; Secret Scanning bleibt redacted/status-only. Kein LR-/Live-/Echtgeld-Signal.
- `gitleaks.yml` (PR #2771, gemergt 2026-06-01T18:50:28Z, Commit `0a5034911c915c97a199b9d6552fba13eecd7944`): `deps(actions): bump gitleaks/gitleaks-action from 2.3.9 to 3.0.0` — Node-24-Runtime-Nachzug fuer `gitleaks/gitleaks-action`; Inputs, Outputs und Verhalten bleiben laut Upstream unveraendert. Kein Control-Surface- oder LR-Effekt; die passende Control-Notiz ist damit nachgezogen.
- `security-alert-readout.yml` (PR #2787, gemergt 2026-06-01T23:15:48Z, Commit `033c167d88b665a6a59c145490b0ecc384c0ce0b`): `fix(workflow): stabilize comment-epic summary issue-link rendering` — `comment-epic`-Rendering wurde ueber einen robusten Python-Block gehaertet, damit die Issue-Link-Ausgabe verlaesslich bleibt. Keine Aenderung an Readout-Grenzen, Issue-Automation, Cap-Logik oder Alert-Dismissal-Postur; lediglich der Kommentarpfad ist stabilisiert.
- `architecture_service_catalog_drift` auf PR #2793 ist repo-backed false-positive: die betroffenen SQL-Migrationen `005_risk_events_idempotent.sql` und `006_correlation_phase8c.sql` wurden nur in ihren Header-Kommentaren von historischer Review-Sprache auf neutrale Notizen umgestellt. Daraus folgt kein Architektur- oder Service-Catalog-Nachzug; #2794 wird als dokumentierte False-Positive-Reconciliation behandelt.
- `copilot-setup-steps.yml` (PR #2443, gemergt 2026-05-12T23:17:55Z, Commit `c06d7ef1ad36`): Node-Setup und Node-Dependency-Installation laufen nur noch, wenn am Repo-Root ein unterstuetztes Node-Lockfile vorhanden ist (`package-lock.json`, `npm-shrinkwrap.json`, `yarn.lock`). Zweck: Copilot-Setup nicht an Repos ohne Root-Node-Lockfile scheitern lassen; zusaetzlich Node 24 statt 20 und Yarn-Fallback bei `yarn.lock`. Keine Aenderung an Runtime, Trading, LR, Security-Alert-Surfaces oder Live-Readiness; kein LR-/Live-/Echtgeld-Signal.
- `codeql-python.yml` (PR #2486, gemergt 2026-05-14T22:04:13Z, Commit `f634ab38`): CodeQL-Konfigurationsdatei hinzugefuegt — neues `.github/codeql/codeql-config.yml` mit `paths-ignore: services/ws/mexc_proto_gen/**`; in `codeql-python.yml` als `config-file` eingebunden. Proto-Gen-Rauschen eliminiert: CodeQL-Alerts von 92 → 58 (−34). SARIF-Kategorie `/language:python` unveraendert; kein neues Security-Triage-Item; kein LR-/Live-/Echtgeld-Signal. Alert-Inventur: `docs/security/code-scanning-alert-inventory.md`.
- `security-alert-readout.yml` (PR #2495, gemergt 2026-05-15T11:52:26Z, Commit `87827c00`): `feat(security): add alert readout issue automation` — neuer Job `issue-automation` hinzugefuegt; laeuft nach `security-readout`, erzeugt pro neuer hochgradiger Alert-Gruppe (severity: critical/high/error) deduplizierte GitHub-Issues mit hartem Cap von max. 10 neuen Issues pro Lauf. Dedupe fail-closed ueber Kommentar-Marker `<!-- cdb-security-new-group:<hash> -->`; GraphQL-Lookup-Fehler fuehren zu skip + exit 2 (nie fail-open). Scheduled Runs laufen produktiv im Live-Modus; `workflow_dispatch` bleibt standardmaessig Dry-run und kann explizit per `issue_automation_live=true` auf Live gesetzt werden. Permissions job-scoped: `contents: read`, `actions: read`, `issues: write` ausschliesslich im `issue-automation`-Job; Top-Level-Permissions unveraendert. `comment-epic`-Job nutzt die maschinenlesbare Automation-Summary (`created`, `deduped`, `skipped`, `capped`, `failed`, `created_issues`) fuer den #2289-Ledger-Kommentar inkl. Cap-Hinweis. Kein Auto-Close, keine Alert-Dismissals, kein Auto-Merge; Secret Scanning bleibt redacted/status-only; `comparison_skipped`-Sources ausgeschlossen. `TRIAGE_RUNBOOK.md` §10 (Issue-Automation-Vertrag, Invarianten, Dedupe-, Cap- und Reporting-Regeln) nachgezogen. Kein LR-/Live-/Echtgeld-Signal. Epic: #2289.
- `security-scan.yml` (PR #2514, gemergt 2026-05-17T18:58:11Z): Postgres- und Redis-Base-Images in `trivy-scan-base` sowie `scan-base-images` auf `postgres:15.18-alpine@sha256:df7bca00...` bzw. `redis:7.4.9-alpine@sha256:6ab0b6e7...` aktualisiert; compose-Refs (`base.yml`, `compose.blue.yml`) wurden im selben Slice synchron nachgezogen. Trivy-SARIF-Kategorien `trivy-base-postgres` und `trivy-base-redis` bleiben stabil; keine Aenderung an Triggern, Permissions, Upload-Verhalten oder Control-Surface-Semantik. Kein LR-/Live-/Echtgeld-Signal.
- `security-scan.yml` (PR #2518, gemergt 2026-05-17T19:53:10Z): Prometheus-Base-Image in `trivy-scan-base` auf `prom/prometheus:v3.11.3@sha256:e4254400...` aktualisiert; compose-Refs (`base.yml`, `compose.red.yml`, `compose.prometheus-v3.yml`) und der Runtime-Eintrag fuer `cdb_prometheus` wurden im selben Slice synchron nachgezogen. Trivy-SARIF-Kategorie `trivy-base-prometheus` bleibt stabil; keine Aenderung an Triggern, Permissions, Upload-Verhalten oder Control-Surface-Semantik. Kein LR-/Live-/Echtgeld-Signal.
- Action-Dependency-Bumps (PRs #2629–#2633, gemergt 2026-05-28): Fuenf Dependabot SHA-only Refreshes ohne operative Control-Aenderung — `docker/setup-buildx-action` 4.0.0→4.1.0 in `docker-publish.yml` (PR #2629); `docker/build-push-action` + `docker/login-action` SHA-Refreshes in `docker-publish.yml` (PRs #2630–#2631; on-disk Kommentar `# v6` bei build-push bleibt, Pin ist SHA-only); `actions/stale` 10.2.0→10.3.0 in `stale.yml` (PR #2632; Permissions unveraendert, vgl. #1749); `github/codeql-action` 4.35.5→4.36.0 in `codeql-python.yml`, `gitleaks.yml`, `security-scan.yml`, `trivy.yml` (PR #2633; SARIF-Kategorien und Security-Triage-Postur unveraendert). Keine Aenderung an Triggern, Permissions oder Control-Surface-Semantik. Kein LR-/Live-/Echtgeld-Signal.
- `ci.yml` (PR #2994, gemergt 2026-06-05T13:30:25Z, Commit `b2784ad`): Canonical PR gate wieder als `.github/workflows/ci.yml` auf self-hosted Runner `[self-hosted, cdb, docker, merge-gate]` verankert. Job `ci (Unit/Integration + Lint gesammelt)` laeuft MCP-Config-Validate (`make mcp-config-validate`), `ruff check .`, diff-scoped `black --check` (nur geaenderte `*.py`, ausgenommen `.codex/**` und `.opencode/**`) und `pytest -q -k "not test_mcp_time_server_runtime"`. Trigger: alle PRs auf `main`; Push auf `main` nur bei Pfadfiltern (`core/**`, `services/**`, `tests/**`, `infrastructure/**`, `.github/workflows/**`, `requirements*.txt`, `pyproject.toml`). `ci.yaml` bleibt frozen legacy (`push`/`workflow_dispatch` only). Im selben Slice: `cdb_agent_sdk/` aus dem Repo entfernt; repo-lokale Agent-Skills nach `.codex/cdb_skills/` und `.opencode/skills/` synchronisiert; `.gitignore` erweitert fuer embedded `.cursor/skills`-Repos. Kein LR-/Live-/Echtgeld-Signal. Follow-up: #2995.
- Action-Dependency-Bump (PR #3063, gemergt 2026-06-08T11:24:43Z, Commit `5706ff55`): `actions/checkout` SHA-Refresh 6.0.2→6.0.3 in 40 Workflow-Dateien. Keine Aenderung an Triggern, Permissions, Control-Surface-Semantik oder operativem Workflow-Verhalten. Kein LR-/Live-/Echtgeld-Signal.
- Action-Dependency-Bump (PR #3064, gemergt 2026-06-08T10:51:45Z, Commit `e9fa938a`): `github/codeql-action` SHA-Refresh 4.36.0→4.36.2 in `codeql-python.yml` (`init`, `analyze`), `gitleaks.yml`, `security-scan.yml`, `trivy.yml` (`upload-sarif`). SARIF-Kategorien, Trigger und Security-Triage-Postur bleiben unveraendert; keine operative Control-Aenderung. Kein LR-/Live-/Echtgeld-Signal.
- `security-scan.yml` (PR #3075, gemergt 2026-06-08T10:19:15Z, Commit `1041c6c2`): CVE-2026-42504 Batch-Triage — Prometheus, Promtool, Grafana, Grafana-cli, Grafana-server und embedded `gosu` in Redis/Postgres alle **UPSTREAM_BLOCKED** (kein scan-verified upstream rebuild verfuegbar). Keine Dismissals, keine false-resolved-Claims, keine Image-Pin-Aenderung im Security-Scan ausserhalb der bestehenden Matrix. Evidence-Dokument: `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3065-3070-CVE-42504_2026-06-08.md`. Residual-Security-Cluster `cve-2026-42504` wird ueber `TRIAGE_RUNBOOK.md` getracked. Kein LR-/Live-/Echtgeld-Signal.
- `ci.yml` + `policy-gate.yml` (PR #3405, gemergt 2026-06-28): **Self-Hosted Runner Security Fix** — `runs-on` von `[self-hosted, cdb, docker, merge-gate]` auf `ubuntu-latest` umgestellt. Grund: Repo ist PUBLIC → untrusted Fork-PRs koennten bösartigen Code auf dem privilegierten self-hosted Runner ausführen (Docker-Socket, NOPASSWD). `NOPASSWD:ALL` durch restriktive sudo-Regel ersetzt (nur `chown`, `mkdir`, `groupmod`, `usermod`). Runner-Doku mit Security-Notice erweitert. Merge-Gate-Checks laufen jetzt auf GitHub-hosted. Selbstgehostete Runner bleiben fuer `workflow_dispatch`/`schedule`-Jobs erhalten. Kein LR-/Live-/Echtgeld-Signal. Closes #3405.
- `security-scan.yml` (PR #3528, gemergt 2026-06-30T18:48:46Z, Commit `9a4ea814`): Redis-Base-Image semver-major `7.4.9-alpine` → `8.8.0-alpine@sha256:9d317178...` in `trivy-scan-base`, `scan-base-images` sowie Compose (`base.yml`, `compose.blue.yml`) synchron nachgezogen. Kein digest-only Bump; Trivy-SARIF-Kategorie `trivy-base-redis` bleibt stabil; keine Aenderung an Triggern, Permissions, Upload-Verhalten oder Control-Surface-Semantik. Runtime-Recreate bleibt separates Ops-Ticket #3594. Kein LR-/Live-/Echtgeld-Signal.
- `security-scan.yml` (PR #3530, gemergt 2026-06-30T19:21:22Z, Commit `7973a66f`): Postgres-Base-Image semver-major `15.18-alpine` → `18.4-alpine@sha256:1b1689b2...` in `trivy-scan-base`, `scan-base-images` sowie Compose (`base.yml`, `compose.blue.yml`, `test.yml`, `tls.yml`); PG18-Volume-Mount unter `/var/lib/postgresql` im selben Slice. Trivy-SARIF-Kategorie `trivy-base-postgres` bleibt stabil; keine Aenderung an Triggern, Permissions, Upload-Verhalten oder Control-Surface-Semantik. Runtime-Migration/Recreate bleibt separates Ops-Ticket #3600. Kein LR-/Live-/Echtgeld-Signal.
- `security-scan.yml` (PR #3630, gemergt 2026-07-01T19:15:11Z, Commit `20554b7f`): CVE-2026-25680 — Prometheus/Promtool/Grafana `golang.org/x/net` Pin-Reconciliation: `prom/prometheus:v3.11.3` → `v3.12.0@sha256:69f524…`, `grafana/grafana:12.4.3-security-02-ubuntu` → `13.0.3-ubuntu@sha256:7c1acd…` in `trivy-scan-base`-Matrix und `infrastructure/compose/base.yml` an bereits scan-verifizierte RED-Runtime-Pins in `compose.red.yml` angeglichen. Closes #3626, #3627, #3628. Trivy-SARIF-Kategorien `trivy-base-prometheus` und `trivy-base-grafana` bleiben stabil; keine Aenderung an Triggern, Permissions, Upload-Verhalten oder Control-Surface-Semantik. Evidence-Dokument: `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3626-3628-CVE-25680_2026-07-01.md`. Control-Reconcile #3631 **CLOSED** via #3665 (`91c6ed0b`). Kein LR-/Live-/Echtgeld-Signal.
- NOISE-FREEZE restore (PR #3662, gemergt 2026-07-01T22:36:27Z, Commit `5f2f1af5`, Issue #3659 / Kampagne #3654): Push- und PR-Trigger fuer 8 security-relevante Workflows nach Billing-Recovery reaktiviert (`codeql-python.yml`, `contracts.yml`, `core-guard.yml`, `docs-conflict-guard.yml`, `docs-hub-guard.yml`, `gitleaks.yml`, `security-scan.yml`, `trivy.yml`). Historische NOISE-FREEZE-Kommentare (#2613) bleiben mit `RESTORED (#3659)` markiert. Kein LR-/Live-/Echtgeld-Signal.
- `GITHUB_WORKFLOW_REGISTER.md` (PR #3664, gemergt 2026-07-01T22:46:40Z, Commit `78ae9beb`, Issue #3660): Register nach Restore-Welle synchronisiert; Known-Failure-Eintraege fuer wieder sichtbare non-required Failures dokumentiert. Kein LR-/Live-/Echtgeld-Signal.
- Self-hosted runner docs (PR #3666, gemergt 2026-07-01T23:00:28Z, Commit `030fc8eb`, Issue #3661): Runner-Doku auf decommissioned-Status finalisiert; Merge-Gate laeuft auf `ubuntu-latest` (#3405). Kein LR-/Live-/Echtgeld-Signal.
- `docs-hub-guard.yml` / artifact hygiene (PR #3668, gemergt 2026-07-01T23:07:48Z, Commit `0eae84ac`, Issue #3667): Vier tracked generierte `artifacts/**/audit.log` entfernt; `.gitignore` gehaertet; Guard auf `main` gruen. Kein LR-/Live-/Echtgeld-Signal.
- `codeql-python.yml` (PR #3673, gemergt 2026-07-01T23:22:26Z, Commit `c961c30e`, Issue #3670): **Aktuelle Posture** — GitHub CodeQL Default Setup ist autoritativ fuer Code-Scanning-Alerts; Advanced-Workflow behaelt `security-and-quality`-Queries und `config-file`, setzt aber `upload: false` im analyze-Step (kein SARIF-Upload solange Default Setup aktiv). Non-required Check `Analyze Python` gruen auf `main`. Option B (Trigger-Reduktion auf `workflow_dispatch`-only) bewusst **Later**. Register-Detail in `GITHUB_WORKFLOW_REGISTER.md` (#3672). Kein LR-/Live-/Echtgeld-Signal.
- `security-scan.yml` (PR #3702, gemergt 2026-07-03T17:32:38Z, Commit `17160ad5`): CVE-2026-27145 + CVE-2026-39827/28/29 — Prometheus/Promtool Image-Bump `prom/prometheus:v3.12.0@sha256:69f524…` → `v3.13.0@sha256:c6b27ea…` in `trivy-scan-base`-Matrix, `base.yml`, `compose.red.yml`, `compose.prometheus-v3.yml` und `SERVICE_CATALOG.md`. Closes #3692, #3693, #3696–#3701. Trivy local: 0 HIGH/CRITICAL auf Ziel-Digest. Evidence: `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3692-3701_2026-07-03.md`. #3694/#3695 bleiben upstream-blocked unter #2933. Kein LR-/Live-/Echtgeld-Signal.
- Security residual docs (PR #3704, gemergt 2026-07-03T18:05:40Z, Commit `69222965`): #3694 (gosu/postgres, CVE-2026-27145) und #3695 (Grafana bundled elasticsearch plugin, CVE-2026-27145) repo-backed als **UPSTREAM_BLOCKED** unter Residual-Cluster [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933) / Parent [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513) dokumentiert. Evidence: `docs/evidence/security/CDB_SECURITY_RESIDUALS_3694-3695_2026-07-03.md`. Keine Alert-Dismissals, kein Grafana-/Postgres-/Redis-Bump, keine Runtime-Aktion. LR bleibt NO-GO.
- libsqlite3/CVE-2026-11824 residual cluster (Slice 2026-07-03, Residual-Cluster [#3705](https://github.com/jannekbuengener/Claire_de_Binare/issues/3705)): #3619–#3625 (7 BLUE custom services, `libsqlite3-0` in `python:3.14-slim-trixie`) repo-backed als **UPSTREAM_BLOCKED** unter Parent [#2513](https://github.com/jannekbuengener/Claire_de_Binare/issues/2513). Evidence: `docs/evidence/security/CDB_SECURITY_BATCH_MATRIX_3619-3625-CVE-11824_2026-07-01.md` (PR #3629). Re-Triage wenn Debian Trixie `libsqlite3-0` >= SQLite 3.53.2 liefert. Keine Alert-Dismissals, kein Base-Image-Bump, keine Runtime-Aktion. LR bleibt NO-GO.
- Action-Dependency-Bump (PR #3752, gemergt 2026-07-06, Commit `d8469751`): `docker/build-push-action` 7.2.0→7.3.0 (`53b7df96c91f9c12dcc8a07bcb9ccacbed38856a`) in `docker-publish.yml`. Kein Control-Workflow; keine Aenderung an Triggern, Permissions oder Registry-Publish-Semantik. Control-Reconcile [#3795](https://github.com/jannekbuengener/Claire_de_Binare/issues/3795). Kein LR-/Live-/Echtgeld-Signal.
- Action-Dependency-Bump (PR #3796, gemergt 2026-07-06, Commit `ba2c5d33`): Konsolidierter `github/codeql-action` Bump 4.36.2→4.36.3 (`54f647b7e1bb85c95cddabcd46b0c578ec92bc1a`) fuer alle `init`/`analyze`/`upload-sarif`-Refs in `codeql-python.yml`, `gitleaks.yml`, `security-scan.yml`, `trivy.yml`; supersediert partielle Dependabot-PRs #3751/#3753/#3754. Dependabot-Gruppe `codeql-action` in `.github/dependabot.yml` ergaenzt. SARIF-Kategorien und Security-Triage-Postur unveraendert; `codeql-python.yml` upload-Posture (#3673) bleibt `upload: false`. Control-Reconcile [#3797](https://github.com/jannekbuengener/Claire_de_Binare/issues/3797). Kein LR-/Live-/Echtgeld-Signal.
- Action-Dependency-Bump (PR #3798, gemergt 2026-07-06, Commit `99c8d871`): `docker/setup-buildx-action` 4.1.0→4.2.0 (`bb05f3f5519dd87d3ba754cc423b652a5edd6d2c`) in `docker-publish.yml`. Kein Control-Workflow; Buildx-Setup-Semantik unveraendert. Control-Reconcile [#3800](https://github.com/jannekbuengener/Claire_de_Binare/issues/3800). Kein LR-/Live-/Echtgeld-Signal.
- Dependabot-Queue residual (2026-07-06): Offener Dependabot-PR [#3755](https://github.com/jannekbuengener/Claire_de_Binare/pull/3755) (`grafana/grafana` 13.0.3→13.1.0) **HOLD_UPSTREAM_BLOCKED** — Grafana 13.1.0 loest CVE-2026-42504 nicht; Evidence: `docs/evidence/security/CDB_SECURITY_GRAFANA_3764_CVE-42504_VERIFY_2026-07-06.md` (PR #3799). Kein Merge, keine Security-Alert-Dismissals, keine Security-Issue-Closure in diesem Slice.
- `security-scan.yml` (PR #3921, gemergt 2026-07-08T04:21:30Z, Commit `384de27b`): Postgres-Base-Image digest-only refresh `postgres:18.4-alpine@sha256:1b1689b2…` → `@sha256:ecafd342…` in `trivy-scan-base`, `scan-base-images` sowie Compose (`base.yml`, `compose.blue.yml`) synchron nachgezogen. Semantischer Tag unveraendert; upstream rebuild 2026-07-07. Trivy local: **12 libcurl HIGH** auf altem Pin → **0** alpine HIGH/CRITICAL auf neuem Pin (`libcurl 8.21.0-r0`). Trivy-SARIF-Kategorie `trivy-base-postgres` bleibt stabil; keine Aenderung an Triggern, Permissions, Upload-Verhalten oder Control-Surface-Semantik. `usr/local/bin/gosu` residual (14 HIGH/CRITICAL) bleibt **UPSTREAM_BLOCKED** unter [#2933](https://github.com/jannekbuengener/Claire_de_Binare/issues/2933). Evidence: `docs/evidence/security/CDB_SECURITY_POSTGRES_ALPINE_LIBCURL_REBUILD_2026-07-08.md`. GitHub Code Scanning alert delta erst nach naechstem `security-scan.yml`-Lauf auf `main` messbar; keine Alert-Dismissals. Control-Reconcile [#3922](https://github.com/jannekbuengener/Claire_de_Binare/issues/3922). Kein LR-/Live-/Echtgeld-Signal.
- Action-Dependency-Bump (PR #4051, gemergt 2026-07-16T11:29:18Z, Commit `2182caaa`): `actions/stale` 10.3.0→10.4.0 (`1e223db275d687790206a7acac4d1a11bd6fe629`) in `stale.yml`. Workflow-Trigger, Permissions, konfigurierte Inaktivitaetsfristen, Meldungen sowie Label-/Close-Semantik bleiben unveraendert; der Upstream-Fix fuer `only-issue-types` betrifft eine im Repo nicht konfigurierte Option. Control-Reconcile [#4100](https://github.com/jannekbuengener/Claire_de_Binare/issues/4100). Kein LR-/Live-/Echtgeld-Signal.
- Action-Dependency-Bump (PR #4050, gemergt 2026-07-16T11:59:57Z, Commit `ef101952`): Konsolidierter `github/codeql-action` Bump 4.36.3→4.37.0 (`99df26d4f13ea111d4ec1a7dddef6063f76b97e9`) fuer `init`/`analyze`/`upload-sarif` in `codeql-python.yml`, `gitleaks.yml`, `security-scan.yml` und `trivy.yml`. Repo-seitig bleiben Trigger, Permissions, Queries, lokale `config-file`-Referenz, SARIF-Kategorien und die `upload: false`-Posture des Advanced-CodeQL-Workflows unveraendert; upstream wechselt das Default-CodeQL-Bundle auf 2.26.0 und ergaenzt schrittweise ein alternatives `config-file`-Kurzformat, das der lokale Pfad nicht nutzt. Control-Reconcile [#4101](https://github.com/jannekbuengener/Claire_de_Binare/issues/4101). Kein LR-/Live-/Echtgeld-Signal.

---

## Manuelle HITL-Klassifikation

- Workflow: `.github/workflows/cdb-control-followup-classifier.yml`
- Prompt-Canon: `.github/prompts/cdb-control-followup.prompt.yml`
- Ausführung: nur `workflow_dispatch`, kein Auto-Issueing, keine automatische Repo-Mutation
- Ausgabe: immer Step Summary + Artefakt; optional zusätzlicher Kommentar auf ein bewusst gesetztes Ziel-Issue
- Guardrail: fail-closed bei ungueltigem JSON, bei `summary_and_issue_comment` ohne `issue_number`, oder bei nicht numerischer `issue_number`

---

## Monatlicher Audit
Spätestens bis 3. des Monats → Audit-Kommentar in Issue #1445 anhängen.
Audit-Template: s. Issue #1445 Body.

## Workflow Evidence Follow-ups

- `gitleaks.yml` (PR #2771; Push/PR-Trigger wiederhergestellt PR #3662 #3659): Gitleaks credential-leak scan mit push/PR/schedule/`workflow_dispatch`. **Read-only Scan-Pfad:** Top-Level `contents: read` + `pull-requests: read`. **GitHub-Schreibpfade (nicht read-only):** Top-Level `security-events: write`; Jobs laden SARIF via `github/codeql-action/upload-sarif` in GitHub Security. Kein Runtime-, DB-, MCP-, Docker-Stack- oder LR-/Live-/Echtgeld-Signal.
- `security-alert-readout.yml` (PR #2787): **Read-only:** Job `security-readout` (Artifact/Step-Summary-only, kein direkter Main-Push); Summary-/Issue-Link-Rendering in `comment-epic` stabilisiert. **GitHub-Schreibpfade (nicht read-only):** `comment-epic` postet Ledger-Kommentare auf Epic #2289 (`issues: write`); `issue-automation` erstellt bei Scheduled-Runs standardmaessig echte Issues (`LIVE_MODE=true`, `issues: write`; manuell nur mit `issue_automation_live=true`); optionaler `persist-via-pr`-Pfad nur bei explizitem `workflow_dispatch`. Keine Alert-Dismissals, kein Auto-Merge, kein LR-/Live-/Echtgeld-Signal.
