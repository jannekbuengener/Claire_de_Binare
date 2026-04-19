# Current Status

**Status Class**: Working Repo / Engineering Status
**Authority**: Current repo/main/test/dependency snapshot; not the canonical live-readiness or Echtgeld Go/No-Go source.
**Operational Canon**: `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`
**Last Updated**: 2026-04-19
**GitHub Boundary**: The live commit and PR state is tracked in GitHub (UI/API or `gh`); this file is a curated repo/engineering ledger, not a live mirror.

---

## Repo / Engineering Status (2026-04-19)

- **main**: green
- **Active GitHub focus (manual, non-exhaustive)**: keine
- **Boundary**: Nur aktuell relevante offene PRs gehoeren in den Fokusblock oben. Merged, closed oder rein historische Hinweise gehoeren in den Session-Ledger darunter.

---

## Session Ledger (historical, not active focus)

- **Merged (Session 3, 2026-03-22)**: #1226 P5 prestart normalization (df169f4)
- **Merged (Session 4, 2026-03-22)**: #1257 fix(lr031): liveness floor min=1 (a407838)
- **Merged (Session 5+6, 2026-03-24)**: #1270/#1271 (soak env_interruption/timeline), #1273 (batch soak+alerting fixes, af0f21e), #1274 (docs, ee29e99)
- **Merged (Session 7, 2026-03-26)**: #1266/#1267 — execErrState: KeepLast fix (216d0eb), geschlossen 2026-03-27; #1282/#1283 disk-check + pointer robustness (08f7e7b), geschlossen 2026-03-27.
- **Merged (Session 11, 2026-03-27)**: #1290 — .gitignore Δ1–Δ4 (5a50700), #1234 geschlossen.
- **Merged (Session 12, 2026-03-29)**: #1359/#1360/#1361/#1362/#1363 — Sessions-README, Signal-Alerts-Claim, Monitoring-Terminologie, INV-006 `min_qty_sum`, historische Governance-Artefakte markiert.
- **Merged (Session 13, 2026-03-30)**: #1370 — LR-007-Canon auf 72h-Validierungsfenster ausgerichtet (93daac4).
- **Merged (Session 14, 2026-03-30)**: #1382/#1383/#1384/#1386 — BLUE+RED-Startup-Canon, Solo-Maintainer-SOPs, LR-BLACK-Stack-Terminologie und aktive Infra-Canon-Doku bereinigt.
- **Merged (Session 15, 2026-03-30)**: #1389 — aktive Governance-/Risk-Terminologie auf `Risk Service` / `cdb_risk` vereinheitlicht (e48add6).
- **Merged (Session 17, 2026-03-31)**: #1408 — Batch #1403–#1407: knowledge link drift + secrets helper legacy + contributor docs + test-pack entrypoints (c6a51cd). Issues #1403–#1407 geschlossen.
- **Merged (Session 18, 2026-03-31)**: #1410 — Aktive Runbooks/Playbooks/Templates auf BLUE+RED Runtime-Canon bereinigt. 24 Dateien. PR #1415 (04b91d4b). Issue #1410 geschlossen.
- **Merged (Session 19, 2026-03-31)**: #1411 — Aktive Secrets-/Runbook-/Evidence-Doku auf SECRETS_PATH-Canon gezogen. 21 Dateien. PR #1415 (04b91d4b). Issue #1411 geschlossen.
- **Merged (Session 20, 2026-03-31)**: #1413 — Legacy-Ops-/Secrets-Pointer aus aktiven Discovery-Surfaces entfernt. 9 Dateien. PR #1415 (04b91d4b). Issue #1413 geschlossen.
- **Merged (Session 21+22, 2026-03-31/04-01)**: #1412 — LR-AUDIT-STATUS / CURRENT_STATUS SSOT-Trennung bereinigt. Operative Phasentabelle aus CURRENT_STATUS.md entfernt; Rueckkopplung in LR-AUDIT-STATUS beseitigt; P-Phasen-Inline-Status aus AGENTS.md entfernt. PR #1414 (bb0c42c0). Issue #1412 geschlossen.
- **Merged (Session 22, 2026-04-01)**: Git-Divergenz aufgeloest; PR-Batch #1414+#1415 durchgezogen; Issues #1410/#1411/#1412/#1413 geschlossen. PR #1416 (9f92651c).
- **Merged (Session 23, 2026-04-01)**: #1409 — ARCHITECTURE_MAP + SERVICE_CATALOG gegen BLUE/RED-Runtime reconciled; Logging Overlay als separates Overlay klassifiziert; CDB_DOCKER_STACK_INVENTORY ergaenzt. PR #1416 (9f92651c). Issue #1409 geschlossen.
- **Merged (Session 24, 2026-04-04)**: #1426 — cdb_market healthcheck start_period auf 30s. PR #1430 (7793c028). Issue #1426 geschlossen.
- **Merged (Session 25, 2026-04-04)**: #1421/#1422 — P5-Core-Artefaktsatz mit LR-040 PASS + Live-Captures. PR #1432 (d530a7ea). Human Gate GRANTED. #1421 + #1422 geschlossen. #1423 als naechster Anschluss-Schritt freigegeben; spaeter via PR #1435 geschlossen.
- **Merged (Session 26, 2026-04-05)**: #1423 — Lean Shadow Evidence Run + Handoff. PR #1433 (4cda64ea, Session-Close), PR #1434 (1a0ebaba, formale Gaps), PR #1435 (468414fd, Evidence-Handoff). P4 DONE reconciled. #1423 geschlossen.
- **Merged (Session 27, 2026-04-05)**: #1390 — emoji-filter: compact auto-issue body zu Summary + Artifact-Link. PR #1438 (1f3ec548). #1390 geschlossen.
- **Session 28 (2026-04-05)**: #1418 — P5-Proof-Anchor geschlossen (alle Child-Issues CLOSED, manifest self-konsistent). #1426 Issue-Closure verifiziert (PR #1430 war bereits in Session 24 gemergt).
- **Merged (Session 29, 2026-04-05)**: #1427 — soak-monitor Docker-Disk-Fallback. PR #1429 (ba2b13e4). #1427 geschlossen.
- **Merged (Session 30, 2026-04-05)**: PRs #1438/#1437/#1439 — Session-Close-Batch: emoji-filter compact body, P5-Status-Reconciliation, Session-28/29-Close + Merge-Konflikt-Auflösung + SHA-Korrekturen. PR #1439 (e4d664e5).
- **Session 31 (2026-04-06)**: PR #1441 auf `main` verifiziert (920e1901); superseded PRs #1431/#1436 geschlossen; PR #1398 read-only geprueft und wegen offenem Root-Skript-/Doc-Drift nicht freigegeben. Follow-up #1442 angelegt.
- **Merged (Session 32+33, 2026-04-06)**: #1391 — compose canon drift vollstaendig geschlossen. PR #1398 (26d91693). Issues #1391 + #1442 geschlossen.
- **Merged (Session 35, 2026-04-06)**: #1448 — PR-Batch #1392–#1397 + #1446 disponiert. Gemergt: #1392 HITL solo-maintainer (0a4ac9ea), #1393 historical M7/M8/M9 entrypoints (132eafe7), #1394 M7 testnet historical (7b40c0ca), #1395 M8 security historical (b583e0a2), #1454 CONTROL_REGISTER.md (c3e5b6da). #1446 geschlossen (superseded). Hold: #1396 (DR-Docs Backup-Front-Door-Verifikation), #1397 (policy-gate, → #1449).
- **Session 36 (2026-04-06)**: #1449 — policy-gate RCA abgeschlossen. Befund: eine Blocker-Familie (core/service-Default), 4 Ausprägungen: fehlende infra-only-Inferenz, mixed-file-set, non-privileged script paths (knowledge/operations/), Dependabot-Labels nicht als Override. RCA-Kommentar in #1449 gepostet. Keine Code-/Workflow-Änderungen.
- **Merged (Session 37, 2026-04-06)**: #1450 — 40 untracked Files klassifiziert (alle Bucket 1: commit). PR #1457 (39c5d864). 28 Session-Logs, 2 SDK-Tests, 3 DR-Evidence-Logs, 1 Infra-Script, 6 Docs/Reports. Working Tree clean.
- **Merged (Session 38, 2026-04-07)**: Dep-Queue-Pass + LR-040-Fix — setup-python v6.2.0 (e8784235/#1121), pytest-cov 7.1.0 (4eec57ab/#1365), tabulate 0.10.0 (955e4410/#1115), pyyaml 6.0.3 (92fa39e0/#1179), ruff 0.15.8 (b88dd312/#1367), black 26.3.1 (c1161b5c/#1147). LR-040 soak_monitor fail-closed precheck (8aaf109a/#1467).
- **Merged (Session 39, 2026-04-07)**: CI SSOT Freeze + Governance-Deltas — PR #1475 (f2410e06) [docs-only]: ci.yaml Freeze-Status, Dependabot Override Path, LABELS.md. PR #1476 (53771330) [workflows-only]: ci.yaml Header-Kommentar. Issues geschlossen: #1474 (CI SSOT), #1462 (Dependabot-Pfad), #1471 (setup-python v6 Kompatibilitaet bestaetigt), #1472 (pre-close manual-only Governance-Entscheid). Bewusst offen: #1463 (externe Node.js-Runtime-Verifikation ausstehend), #1473 (Backup-Drill nur nach Stack-Freigabe — Blocker #1478 damals noch offen).
- **Merged (Session 40, 2026-04-07)**: #1478 — Compress-Archive OOM in `backup_all.ps1` behoben; `ZipFile.CreateFromDirectory` (.NET BCL, streaming) als Ersatz. PR #1479 (6b53c6e8). Backup-/Restore-Drill (#1473) erfolgreich abgeschlossen: `make backup` Exit-Code 0, ZIP 78.4 MB, Postgres (9 Tabellen) + Redis restored und verifiziert. Issues #1473 + #1478 geschlossen. Bewusst offen: #1463 (externe Node.js-Runtime-Verifikation).
- **Merged (Session 41, 2026-04-07)**: Batch #1481–#1484 — LR-AUDIT-STATUS SSOT-Reconcile (LR-050 OPEN→NO-GO, LR-011 OPEN→PASS), DR-Front-Door vs. historischer 2025-12-31-Snapshot getrennt, enforce-root-baseline.ps1 repo-relativ, Secrets-Canon fail-closed (compose.blue+red: `:?SECRETS_PATH must be set`; Front-Doors: generischer Default+Guard). PR #1485 (23a6dae0). Issues #1481/#1482/#1483/#1484 geschlossen.
- **Session 42 (2026-04-08)**: #1502 read-only disponiert. Befund: aktive Runtime-Canon kommt aus service-lokalen requirements + real referenzierten Dockerfile-Installationsstellen; root `requirements.txt` ist aktuell CI/Test-/Convenience-Layer, nicht Runtime-Truth. `redis` ist der staerkste Drift-Fall; `prometheus_client` bleibt wegen `db_writer` unpinned nicht sauber root-kontrolliert. Abschlusskommentar in #1502 gepostet; Status: bereit fuer Claude Code. Keine Repo-/Runtime-Reconciliation in dieser Session.
- **Merged (Session 43, 2026-04-08)**: #1488 — Decision-/Policy-/Trace-Kontext ueber den Signal->Order->Trade-Pfad persistiert. PR #1516 (3efe4410). Issue #1488 geschlossen.
- **Merged (Session 44, 2026-04-08)**: #1498 — verbleibende Dual-Writer-Naht fuer `orders`/`trades` reduziert; `trades` kanonisch ueber `db_writer`, `orders` kanonischer Insert plus execution-lokales Lifecycle-Enrichment. PR #1519 (2bfbeb30). Issue #1498 geschlossen.
- **Merged (Session 45, 2026-04-08)**: #1520 — execution-side Order-Fallback-Insert entfernt; Lifecycle-Updates binden jetzt fail-closed an kanonische `metadata.order_id`. PR #1521 (3729c59f). Issue #1520 geschlossen.
- **Merged (Session 46, 2026-04-08)**: #1500 — unowned Phase-2-Metadata-Felder aus dem persistierten Order-Vertrag entfernt; keine neuen `account_context.*`, keine neue `execution_context.slippage_pct`, kein `ingest_ts_ms` ohne kanonischen Producer. PR #1522 (49870e63). Issue #1500 geschlossen.
- **Session 47 (2026-04-08)**: #1509 GitHub-Reconciliation abgeschlossen. Der fruehere `prometheus_client`-Stub-Leak blockiert die gemeinsame Collection auf `main` nicht mehr; effektive Landing-Evidenz laeuft ueber die gemergten Folge-PRs #1516/#1519 statt ueber den urspruenglichen Branch-Commit. Abschlusskommentar in #1509 gepostet; Issue geschlossen.
- **Merged (Session 48, 2026-04-09)**: Cleanup-Strang #1536/#1537/#1538 fachlich in Reihenfolge gelandet: PR #1539 (ac3e92d3) entfernt den stale `cdb_paper_runner`-Scrape fail-closed, PR #1540 (8838a161) zieht `COMPOSE_LAYERS.md` auf den repo-backed dev-Overlay-Status, PR #1541 (4159066d) reconciled `alerts.yml` gegen die aktuelle Metrics-SSOT und zieht `METRICS_MATRIX.md` ohne Drift-Reanimation nach. Issues #1536/#1537/#1538 geschlossen.
- **Merged (Session 49, 2026-04-09)**: #1543 — `gemini-scheduled-triage.yml` fail-closed geparkt. Weekly `schedule` entfernt, `workflow_dispatch` bewusst erhalten, `CONTROL_REGISTER.md` auf `manuell (geparkt fail-closed)` nachgezogen.
- **Session 50 (2026-04-09)**: Wochenfokus-Abgleich fuer Fr 2026-04-10 repo-backed nachgezogen. Der frueher genannte Dependabot-Batch #1367/#1366/#1365 ist obsolet (#1367 + #1365 MERGED, #1366 CLOSED); aktuell keine offenen PRs und kein kleiner neuer PR-Hygiene-/Evidence-Handoff-Blocker belegt.
- **Session 51 (2026-04-10)**: KW15-Kommentare zusammengefasst und bewertet; Monatlicher Audit April 2026 durchgefuehrt (7 Tage ueberfaellig seit 2026-04-03). Befund: Drift-Level GERING — alle KW15-Punkte abgeschlossen, kein neuer Issue erforderlich ausser bereits bestehendem #1603 (Architektur-Drift nach PR #1602). Session-Log: `knowledge/logs/sessions/2026-04-10-kw15-comments-evaluation.md`.
- **Merged (Session 51-55, 2026-04-10)**: Strategy-v1-Cluster current-main-wahr gelandet: PR #1598 (unit/scale reland, `8309f6fc`), PR #1600 (minimaler `primary_breakout_v1` Footprint, `192a8f32`), PR #1602 (statische Strategy-/Execution-Adapter-Grenze, `b1bac4ad`), PR #1613 (deterministischer `primary_breakout_v1` Backtest-/Validation-Pfad, `c0004ed4`), PR #1615 (Paper-/Shadow-Evidence-Bridge, `b3c5ccca`). Danach Issues #1572/#190/#207/#1573 gegen `origin/main` geschlossen; Board-Stage bleibt `trade-capable`, LR bleibt `NO-GO`.
- **Merged (2026-04-11)**: PR #1682 (`aee8685f`) — fix(workflow): weekly_digest.yml jq-Arg-Limit bei Pagination behoben.
- **Merged (2026-04-13)**: PR #1684 (`01cb574f`) — feat(agents): cdb-session-start fail-closed Skill hinzugefuegt (`.codex/cdb_skills/cdb-session-start/`). PR #1685 (`7b5f748e`) — feat(agents): cdb-session-close mit Hard-Complete-Delivery-Verifikation erweitert (`.codex/cdb_skills/cdb-session-close/`). PR #1686 (`9b037ae8`) — docs(control): erwarteten GitHub-Actions-Workflow-Count-Drift in CONTROL_REGISTER.md dokumentiert. Issue #1666 geschlossen. PR #1689 (`8932e25c`) — docs(workflows): Gemini-Command-TOML-Coupling-Modell dokumentiert, Dispatch-Status klargestellt. Issue #1667 geschlossen. PR #1690 (`2b839f9c`) — docs(claude): cdb-session-start/cdb-session-close als Pflicht-Session-Boundary-Skills in CLAUDE.md verdrahtet. Issue #1688 geschlossen.
- **Merged (2026-04-15)**: pip-bump-Batch #1668–#1674 — 7 PRs: #1674 mcp 1.26.0→1.27.0 (`52da3a17`), #1673 requests 2.33.0→2.33.1 (`1a38d57b`), #1672 pytest 9.0.2→9.0.3 (`c89f060d`), #1671 ruff 0.15.9→0.15.10 (`c72dc23b`), #1670 python-json-logger 4.0.0→4.1.0 (`753e094e`), #1669 mypy 1.8.0→1.20.0 (`4adc88a5`), #1668 prometheus-client 0.21.1→0.25.0 (`bfbb015b`). Alle 7 gemergt, CI gruen.
- **Merged (2026-04-16)**: PR #1707 (`d456770e`) — fix(validation): Period-Window-Semantik in `primary_breakout_v1` Backtest-Runner/Report geklaert. Explizite Feldtrennung `requested_period_*` vs effektive `period_*` in `dataset_summary`. Schema-, Doku- und Test-Nachzug. Issue #1706 geschlossen.
- **Session 2026-04-16**: #1709 — Architektur-Drift-Verifikation nach PR #1707. Befund: kein realer Drift. `ARCHITECTURE_MAP.md` und `SERVICE_CATALOG.md` korrekt (kein Eintrag fuer Offline-Tool `strategy_backtest_runner.py` vorgesehen; Contract-Doku bereits durch PR #1707 in `knowledge/contracts/PRIMARY_BREAKOUT_V1_VALIDATION.md` korrekt nachgezogen). Keine Architektur-/Service-Catalog-Aenderung. Issue #1709 geschlossen.
- **Merged (2026-04-16)**: PR #1719 (`3ddfd0ce`) — fix(security): pin `postgres:15.17-alpine` to 2026-04-16 rebuild digest (#1717). Digest `sha256:1c52f5ad...`. Alpine OS 0 CRITICAL/0 HIGH (libssl3/libcrypto3/libxml2 resolved); gosu-binary 8 findings (non-addressable). #1718 (redis) bleibt upstream-blocked. Security-Epic #1649.
- **Merged (2026-04-16)**: PR #1722 (`90d911d0`) — fix(security): pin `python:3.11-slim-trixie` to 2026-04-07 rebuild digest (#1716). Digest `sha256:c8271b1f` → `sha256:233de067`. 8 Dockerfiles (9 FROM-Zeilen): allocation, db_writer, execution (2×), market, regime, risk, signal, ws. cdb_candles intentionally excluded (bookworm, 0 Trivy-Alerts). Erwartete CVE-Reduktion (CVE-2026-0861 libc6, CVE-2026-28390 openssl-Cluster) pending Post-Merge-Trivy-Scan. #1718 (redis) bleibt upstream-blocked. Security-Epic #1649.
- **Merged (2026-04-17)**: PR #1729 (`4f946014`) — fix(workflows): suppress digest-only architecture follow-up noise; `post_merge_followup_scanner.py` erkennt jetzt digest-only Image-Pin-Aenderungen und unterdrueckt `architecture_service_catalog_drift` bei unveraendertem semantischen Tag; Regression-Tests in `tests/unit/scripts/test_post_merge_followup_scanner.py` (5 neue Tests). Issue #1726 geschlossen.
- **Merged (2026-04-17)**: PR #1732 (`55de6984`) — docs(control): reconcile scanner runbook + control register after PR #1729; Suppression-Verhalten in `docs/runbooks/CDB_POST_MERGE_FOLLOWUP_SCANNER.md` und `CONTROL_REGISTER.md` dokumentiert; Session-Ledger-Eintrag fuer PR #1729 in `CURRENT_STATUS.md` ergaenzt. Issue #1730 geschlossen.
- **Session 2026-04-17**: #1725 — OpenSSL-Residual-Befund abgeschlossen. Befund: upstream-blocked, kein Repo-Patch gerechtfertigt. Repo ist bereits auf aktuellem Upstream-Digest (`sha256:233de067...`, 2026-04-07 rebuild) gepinnt. `openssl 3.5.5-1~deb13u2` in `security.debian.org` seit 2026-04-03 verfuegbar (DSA-6201-1), aber Docker Hub hat keinen neueren `python:3.11-slim-trixie` rebuild ausgeliefert (amd64 last_pushed: 2026-04-07, live verifiziert). Status-Kommentar in #1725 gepostet. Naechster Trigger: Docker Hub rebuild mit `openssl >= 3.5.5-1~deb13u2`.
- **Session 2026-04-17**: #1636 — Validation Evidence-Lücken untersucht. Track 1 (Period-Window-Semantik) vollständig bestätigt via PR #1707 (d456770e). Track 2 (zweiter Run ≥20 Trades): Re-Run des Original-420-Candle-Datensatzes mit aktuellem Runner (main @ 8f7a8ebb) produziert schema-valides, deterministisches Artefakt (`run_id: bt-1ab5a47c6449f860`, gate: FAIL, 1 Trade — identisch zum ersten Run, gleicher Datensatz). Echter zweiter Run mit ≥20 Trades bleibt geblockt: kein realer BTCUSDT-1m-Datensatz lokal verfuegbar; synthetisches all-winner Dataset nicht als Closure-Evidence akzeptiert. Status-Kommentar in #1636 gepostet. Naechster Trigger: realer BTCUSDT-1m-Datensatz bereitstellen.
- **Session 2026-04-17 (#1645 Slice 1–3)**: Git-Hygiene-Re-Inventur + Branch-/Worktree-Bereinigung. Re-Inventur: 278 Branches, 9 Worktrees, 0 [gone]-Refs, Salvage-Backlog (Comment #31) vollstaendig obsolet. Slice 1: 31 gemgte, nicht-worktree-gebundene Branches via `git branch -d` entfernt (278 → 247). Slice 2: `feature/656-metrics-overhaul-clean` Worktree + Branch entfernt (247 → 246, 9 → 8 Worktrees) — Dirty-State war stale `.mcp.json`-Loeschung, kein WIP. Slice 3: `Claire_de_Binare_sessionclose` (`docs/status-1707-merged`) — Session-Log `2026-04-16-1706-period-window-semantics.md` gesichert, Worktree + Branch entfernt (246 → 245, 8 → 7 Worktrees). Aktuell: 245 Branches, 7 Worktrees. Restklasse offen: 6 `.worktrees/*`-Branches mit ahead > 0 benoetigen separate Klassifikation.
- **Session 2026-04-17 (#1645 Slices 4–9, ahead-Kandidaten)**: Alle 6 `.worktrees/*`-Branches mit `ahead > 0` einzeln geprüft und bereinigt: `ci/automerge-jules` (ahead=1, automerge-workflow stale, Security-Fix-Content auf main via anderen Pfad), `ci/627-guardrails` (ahead=1, Makefile-Targets stale, test_import_smoke superseded, e2e.yml SMTP auf main), `feature/ci-aggregator` (ahead=1, CI-Aggregator-Konzept auf main anders umgesetzt, PRs #687/#688 CLOSED), `ci/665-planning-lint` (ahead=2, planning_lint.py blob-identisch auf main in tools/test_pack/, Workflow zielt auf obsoletes Docs-Hub-Repo), `feature/432-mcp-stack-green` (ahead=1, mcp-server-time dep in requirements-mcp.txt auf main, ci.yaml durch ci.yml superseded), `feature/sdb-after-soak-evidence-fix2` (ahead=1, redis-exporter-Gate auf main als optional_services geloest, pr_body.txt staler Draft). Muster: Alle hatten `D .mcp.json`-Dirty-State, alle remotes existierten und waren in sync. Ergebnis: 245 → 239 Branches, 7 → 1 Worktrees (nur main). #1645 `.worktrees/*`-Scope vollstaendig abgeschlossen. Offener Restscope: ~239 lokale Branches (separate Klassifikation).
- **Session 2026-04-17 (#1645 Branch-Sprawl-Inventur)**: Frische Klassifikation von 244 non-main lokalen Branches (nach git fetch --prune). Ergebnis: `tracking-live` 14 (live remote, not touch), `tracking-gone` 166 (dominant: squash-merge-pattern, remote deleted, local never cleaned — recent/≤50: 12, medium/51-200: 73, old/>200: 81), `tracking-origin-main` 10 (upstream misconfigured), `local-only` 54 (backup/*: 7 hold, ai/auto: 11, pr-ref: 7, reset/from-codex-green: 1 hold, other: 28). Wave-1-Kandidaten identifiziert: 4 recent-gone-semantic Branches (`docs/status-mark-1716-merged`, `fix/security-trixie-digest-1716`, `docs/status-mark-1717-merged`, `fix/security-postgres-digest-pin-1717`). Inventur-Kommentar in #1645 gepostet. Naechster Schritt: Wave-1-Micro-Batch (separater Slice).
- **Session 2026-04-17 (#1645 Wave-1-Cleanup)**: 4/4 `tracking-gone-recent-semantic` Branches geloescht. Alle commit-inhaltlich und PR-seitig verifiziert: `docs/status-mark-1716-merged` (PR #1722 MERGED, CURRENT_STATUS.md identisch), `fix/security-trixie-digest-1716` (PR #1722 MERGED, trixie digest `sha256:233de067` auf main bestaetigt), `docs/status-mark-1717-merged` (PR #1719 MERGED, CURRENT_STATUS.md identisch), `fix/security-postgres-digest-pin-1717` (PR #1719 MERGED, postgres digest `sha256:1c52f5ad` auf main bestaetigt). Ergebnis: 241 → 237 Branches. Offener Rest: 236 non-main Branches. Naechster Schritt: Wave 2 (8 Branches, behind 34–44).
- **Session 2026-04-17 (#1645 Wave-2-Cleanup)**: 8/8 `tracking-gone` Branches (behind 34–46) geloescht. Alle commit-inhaltlich und PR-seitig verifiziert: `docs/status-ledger-kw16-1689-1690` (PR #1689+#1690), `docs/1688-session-skill-routing` (PR #1690), `docs/1667-commands-coupling-doc` (PR #1689), `docs/current-status-ledger-2026-04-13` (PR #1686), `1666-actions-workflow-drift-doc` (PR #1686), `1663-session-start-skill` (PR #1684), `1664-session-close-skill` (PR #1685), `codex/1659-rest-slice-20260412` (PR #1660) — alle MERGED, alle Inhalte auf main bestaetigt. Ergebnis: 237 → 229 Branches. Kumulativ Wave1+2: 241 → 229 (12 Branches). Offener Rest: 228 non-main Branches. Naechster Schritt: Wave 3 (tracking-gone-medium oder tracking-origin-main, separater Slice).
- **Session 2026-04-17 (#1645 Wave-3-Cleanup)**: `tracking-origin-main`-Sonderklasse (10 Branches) bearbeitet. 8/10 cleanup-ready und geloescht: `ci/extend-soak-window`, `docs/fix-stale-1603-ledger`, `docs/issue-1412-lr-ssot-separation-clean` (PR #1414), `docs/reconcile-1646-signal-risk-market` (PR #1705), `fix/1376-hitl-solo-maintainer` (PR #1392), `fix/1380-entrypoint-milestone-framing` (PR #1393), `issue-1577-primary-breakout-config-canon` (PR #1600), `smart-insights-fix` (PR #1694). 2/10 behalten: `ci/pr-noise-kill-clean` (ci.yml hat echte Diff vs main — stale action-pins, falsches pytest-Command), `issue-1564-canon-drift-cleanup` (Scanner-Fix nicht auf main, Issue #1564 als COMPLETED geschlossen ohne PR — fail-closed). Ergebnis: 229 → 221 Branches. Kumulativ Wave1+2+3: 241 → 221 (20 Branches). Offener Rest: 220 non-main Branches. Naechste Welle: tracking-gone-medium (73 Branches, behind 51–200).
- **Merged (2026-04-19)**: PR #1766 (`acba7f27`) — docs(lr): reconcile LR-012/#781 state in LR-AUDIT-STATUS SSOT; LR-012 Issue `#781` als CLOSED eingetragen. Issue #1765 geschlossen.
- **Merged (2026-04-19)**: PR #1767 (`34d55655`) — security: narrow Prometheus base-image refresh for Trivy; `prom/prometheus` v3.10.0 → v3.11.2 (CVE-2026-40179-Slice). SERVICE_CATALOG entsprechend nachgezogen. Refs #1445.
- **Merged (2026-04-19)**: PR #1768 (`d4b3cf4c`) — security: narrow Redis digest refresh for Trivy reduction; `redis:7.4.8-alpine`-Digest aktualisiert (digest-only, semantischer Tag unveraendert). Refs #1445.
- **Session 2026-04-19 (#1769/#1770/#1771)**: Docs-Reconcile-Batch nach LR-012- und Security-Reduction-Slices. #1769: CONTROL_REGISTER PR-#1768-Note. #1770: CURRENT_STATUS Ledger-Nachzug (#1766–#1768). #1771: SERVICE_CATALOG Prometheus v3.10.0→v3.11.2 Katalog-Nachzug.
- **Merged (2026-04-19)**: PR #1775 (`db948a7b`) — docs(roadmap): ACTIVE_ROADMAP auf Backtesting/Validation-Fokus reorientiert; trade-capable != LR-Go Guardrail explizit gesetzt; kanonische Zeiger ergänzt (CONTROL_REGISTER, PRIMARY_BREAKOUT_V1.md, Validation-Runner). Issue #1772 geschlossen.

---

## Live-Readiness

Operatives Go/No-Go-Verdikt: **NO-GO** — Phasenstatus und Verdikt-Quelle ausschliesslich unter [`docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md`](docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md). Diese Datei ist nicht die operative SSOT fuer Live-Readiness.

---

## Wesentliche Aenderungen seit 2026-02-21

### Live-Readiness
- LR-010: Evidence-Status auf PASS hochgestuft (PR #1223)
- LR-020: IMPLEMENTED / DONE — Tier-2 paper-trade flow mit FILLED-State, Decimal-qty-Fix, TRACE_CONTRACT_V1 (PR #1190)
- LR-007: Spezifikation/Status auf das kanonische 72h-Validierungsfenster ausgerichtet; alte 30d-Draft-Wording entfernt (PR #1370)
- LR-031: Threshold neu kalibriert auf min=1 (liveness floor, PR #1257 a407838); lean Run 23407946292 vollstaendig PASS (soak_gate + comparison + canonical package)
- LR-041: Deterministischer Redis/Postgres-Recovery-Drill hinzugefuegt (PR #1130)

### Operatives / Infra
- Kill-Switch: Shared State + E2E Smoke Test (PR #1198)
- Regime-Heartbeat: Verhindert stale regime_id -> RC_001-Block (PR #1218)
- cdb_market: Write-Ownership fuer market_state uebertragen, Service in BLUE Stack (PR #1203)
- Alerting: Circuit-Breaker-Alert-Chain repariert (#1220); neue Regeln High Error Rate + Orders Rejected (#1249, #1250)
- Makefile: docker-* Targets auf kanonischen BLUE/RED Pfad migriert (#1219)
- Backup: Automatisierungs-Runbook + SurrealDB-Drill (#1175, #1130)
- Governance: TODO/Placeholder-Lifecycle formalisiert (#1239)
- Aktive Runtime-Doku verweist jetzt konsistent auf `compose.blue.yml` + `compose.red.yml`; unqualifiziertes `docker compose up -d` und base/dev-Canon aus aktiven Artefakten entfernt (#1382, #1386)
- Incident-/Emergency-/CI-Dokumente auf Solo-Maintainer-Realitaet umgestellt; Mehrpersonen-Eskalationsketten aus aktiven SOPs entfernt (#1383)
- Obsolete `BLACK`-Terminologie aus aktiven Live-Readiness- und Governance-Artefakten entfernt; aktive Domain-Bezeichnung jetzt `Risk Service` / `cdb_risk` (#1384, #1389)

### Soak-Monitor + Alerting (2026-03-24, Session 6)

6 Issues in PR #1273 geschlossen:

- **#1268** (Regression-Tests): Bash-Octal-Parsing-Bug bei `%H`-Stunden 08/09 dokumentiert; 18 neue Tests in `TestOctalSafeScheduleChecks` (`test_soak_monitor_timeline.py`)
- **#1263** (Service-Health): SUT_SERVICES-Liste auf exakt 12 Services erweitert (BLUE core 8 + postgres/redis + ws/signal); `grep -qx` statt Broad-Filter
- **#1264** (Disk-Evidence): Check 5 nutzt `/repo` (mounted) statt `/var/lib/docker` (nicht gemountet) + `docker system df`; schreibt Disk-Evidence-Artifact pro Checkpoint
- **#1265** (Circuit-Breaker-Alert): `type: gte` → `type: gt`, `params: [1]` → `params: [0]` (binary metric semantisch äquivalent; `gte` war ungültiger Grafana-Operator → DatasourceError)
- **#1266** (Orders-Rejected-Alert): `execErrState: Error` → `execErrState: KeepLastState` (noisy DatasourceError-Mails während Prometheus-Restart unterdrückt)
- **#1267** (High-Error-Rate-Alert): `execErrState: Error` → `execErrState: KeepLastState` (gleicher Root Cause wie #1266)

Neue Testdatei: `tests/unit/scripts/test_grafana_alerting_provisioning.py` (21 Tests, 4 Klassen)
`test_soak_monitor_timeline.py`: 71 Tests total (+46 in dieser Session)

**Geschlossen**: #1269 (midnight-rollover UTC→MESZ) — Live-Evidence aus `soak_test_20260325_121250` bestätigt: beide UTC-Mitternachts-Grenzen (Hour 11 + Hour 35) ohne Fragmentierung oder Schedule-Misfire passiert. #1278 Pointer-Mechanismus wirksam (2026-03-27).

### Observability / Grafana (2026-03-22)
- Dashboard-Canon nach Folgearbeiten #1532 + #1533: 1 aktives Dashboard
  - aktiv: `cdb_operator_kpis_v1.json`
  - entfernt/superseded: `cdb_system_health_owner_v1.json`, `cdb_trading_performance_v1.json`
- `cdb_operator_kpis_v1.json`: PostgreSQL-backed Operator-KPIs fuer `Trades made`, `Positive trades` und `Positive trades %`
- Publish-Kette geschlossen (#1255, Commit c26b08d): `paper_runner` publiziert jetzt stündlich (konfigurierbar) Portfolio-Snapshots auf Redis-Channel `portfolio_snapshots` → `db_writer` → PostgreSQL → Grafana
- CLAUDE.md im Repo-Root angelegt (Commit 1116275)
- Restunsicherheiten Observability:
  - `max_drawdown_pct` im Snapshot aktuell Platzhalter (0.0)
  - keine weiteren Dashboard-Files im aktiven Canon; getrennte Drift-Themen bleiben ausserhalb dieses Blocks

---

## Residual Notes / Not a Live Queue

Nur explizit als offen oder aktuell markierte Punkte sind aktiver Arbeitsfokus. Geschlossene, supersedierte oder historische Hinweise bleiben hier als Restkontext stehen und sind kein GitHub-Live-Mirror; den aktuellen Live-State einzelner Issues oder PRs immer direkt in GitHub pruefen.

1. **#1277 (soak restart scope):** Gemerged (PR #1279, `b5486c9`). Check 1 auf 12 SUT-Services eingeschränkt; Non-SUT-Restarts nur INFO.
2. **#1278 (validation mode):** Gemerged (PR #1280, `ac6ab87`). Separater Artifact-Namespace, Pointer, `run_intent.txt`, Gate-Evaluator `NOT_APPLICABLE` für Validation Runs.
3. **LR-040 72h-Run abgeschlossen — PASS:** `artifacts/soak_test_20260401_114850/lr040_soak_gate_eval.json` — 72.19h, alle 8 Gate-Checks bestanden. Committed unter `reports/p5_canary/2026-04-04/lr040/`. PR #1432 gemergt (d530a7ea).
4. **#1282/#1283 (Disk-Check + generischer Pointer):** Gefixt (08f7e7b, 2026-03-26). `_write_active_run_path()` in `soak_monitor.sh` schreibt jetzt auch `soak_active_run_path.txt` für lr040 Runs; Validation-Runs unberührt. Disk-Check unterscheidet Command-Failure von Parse-Failure, schreibt Reason + Raw-Output in disk_evidence. +6 neue Regressionstests (4 Pointer-Sync, 2 Disk-Check).
5. **#1266/#1267 (Grafana execErrState):** Gefixt (216d0eb, 2026-03-26), geschlossen 2026-03-27. Root Cause: `KeepLastState` war nie ein gültiger Unified-Alerting-Wert; korrekt ist `KeepLast` (Grafana 10.4+/11.0+). Kein Image-Upgrade nötig. Beide Alert-Regeln und Tests aktualisiert.
6. **#1269 (midnight-rollover):** Geschlossen (2026-03-27). Live-Evidence aus `soak_test_20260325_121250`: beide UTC-Mitternachts-Grenzen (Hour 11 @ 2026-03-26 00:00, Hour 35 @ 2026-03-27 00:00) ohne Fragmentierung passiert. #1278 Pointer-Mechanismus bestätigt wirksam. Hour-29-Lücke = bekannte Umgebungsunterbrechung (2026-03-26 18:00 UTC). Formales Gate-Ergebnis: INCONCLUSIVE (s. Eintrag 3).
7. **Grafana circuit_breaker alert aktiv:** Sendet gerade Alerts (laut Log), da circuit_breaker_active evaluiert wird. Normal — kein Blocker.
8. **Human Gate:** GRANTED (2026-04-04). GO fuer kontrollierten P5-Shadow-/Stabilitaetsschritt. Keine Live-Aktivierung, keine Produktionsfreigabe. Formalisiert in `decision_record.yaml` via PR #1434 (1a0ebaba).
9. **#1375:** Historischer Resthinweis. Die Sammel-PR ist auf GitHub zwar noch OPEN, fuer den aktuellen Repo-/Engineering-Fokus aber fachlich supersediert; sie zaehlt daher nicht zur aktiven Open-PR-Liste.
10. **#1423 (Lean Shadow Evidence Run):** Abgeschlossen (2026-04-05). Run 24001373890 PASS (10/10 Checks). Evidence-Handoff unter `reports/p5_canary/2026-04-04/lean_shadow_evidence_handoff.yaml`. PR #1435 (468414fd). Parent-Anchor #1418 ist CLOSED.
11. **P4 DONE:** LR-040 PASS + LR-041/042 CLOSED mit Evidence. LR-AUDIT-STATUS reconciled (2026-04-05).
12. **#1391/#1398 (compose canon drift):** CLOSED (2026-04-06). PR #1398 gemergt (26d91693). Legacy-Stubs fail-closed, $secretDir-Fix, aktive Docs bereinigt. Issues #1391 + #1442 geschlossen.

---

## Postmortem / Session Logs

- `knowledge/logs/sessions/` — aktuelle Session-Logs
- `docs/live-readiness/LR-AUDIT-STATUS-2026-03-05.md` — operativer Live-Readiness-Verdict (letzte Reconciliation 2026-04-05, PR #1437)
