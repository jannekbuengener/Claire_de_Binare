# Session Log: 2026-03-24 — Operativer Cleanup + neuer Soak-Run-Start (Session 7)

**Datum:** 2026-03-24
**Status:** CLOSED
**Scope:** Operativer Cleanup nach PR #1273-Merge; Prometheus-Wiederherstellung; #1266/#1267 Reopen; neuer LR-040-Soak-Run gestartet

---

## Ausgangslage

Nach PR #1273-Merge (Session 6) waren drei operative Restpunkte offen:
1. `cdb_prometheus` seit 2026-03-20T10:00 UTC exited (Exit 255 = Docker-Daemon-Restart)
2. `#1266/#1267` fälschlich CLOSED, Fix effektiv zurückgerollt (Grafana-Provisioning-Inkompatibilität)
3. Alter LR-040-Soak FAILED (Bulk-Restart 2026-03-24T17:22 UTC), neuer Run nötig

---

## A) Prometheus-Wiederherstellung

**Root Cause für Exited (255):**
Docker-Daemon-/Desktop-Restart am 2026-03-20T10:00 UTC. Prometheus-Logs zeigen keine
Fehler — saubere TSDB-Kompression bis 2026-03-19T21:00 UTC. Exit 255 ist SIGKILL durch
Runtime-Stop (kein Anwendungsfehler). Restart-Policy `unless-stopped` hat nicht angesprungen,
weil der Container vor dem Daemon-Restart manuell gestoppt worden war.

**Fix:** `docker start cdb_prometheus` — sauber, kein Compose-Neustart nötig.
Prometheus ist auf `cdb_network` (Port 19090 intern, 9090/tcp). Antwort: `Server is Ready`.

---

## B) #1266 / #1267 Reopen

Beide Issues waren fälschlich CLOSED (Fix-Commit f22ad9f wurde als aktiv angenommen,
war aber bei Grafana-Restart nicht aktivierbar).

**Technischer Grund für Rollback:**
Grafana 11.4.7-ubuntu akzeptiert `KeepLastState` als Wert für `execErrState` im
Provisioning-YAML-Parser nicht:
```
failure parsing rules: rule 'CDB - Orders Rejected' failed to parse:
unknown Error state option KeepLastState
```
→ Grafana-Restart-Loop. Zurückgerollt auf `execErrState: Error`.

**Aktion:** Issues #1266 und #1267 reopened mit vollständiger Erklärung.
Session-Log `2026-03-24-alerting-1266-1267.md` aktualisiert (PR #1274, Commit ee29e99).

**Entscheidungsmatrix echte Behebung:**

| Option | Empfehlung |
|---|---|
| A) Grafana-Image-Upgrade | Bevorzugt — löst direkt, YAML-Fix f22ad9f reaktivierbar |
| B) Alertmanager-Routing für DatasourceError | Ergänzend sinnvoll, kein Ersatz |
| C) execErrState: Alerting | Nicht empfohlen (weiterhin noisy) |

---

## C) Alt-Soak-Run abgrenzen

**Fehlgeschlagener Run:** `soak_test_20260322_181856` → durch Midnight-Rollover zu
`soak_test_20260323_000002` → `soak_test_20260324_000002`.

- `soak_test_20260324_000002/soak_test_FAILED.txt`: `2026-03-24 18:00:01 UTC — ABORT: Service restart detected`
- Ursache: Bulk-Restart aller Container 2026-03-24T17:22 UTC (Docker Desktop/Windows-Restart)
- Alle Artefakte erhalten, nicht gelöscht

**Vorbereitung neuer Run:**
1. Neues Verzeichnis `artifacts/soak_test_20260324_224419` angelegt
2. `artifacts/soak_active_run_path.txt` → neues Verzeichnis umgezeigt
3. Alter `lr040_soak_monitor`-Container gestoppt + entfernt
4. Neues Entrypoint-Script `/soak_entrypoint4.sh` erstellt

---

## D) Neuer Soak-Run

**Run-Identifier:** `soak_test_20260324_224419`
**Startzeit:** 2026-03-24T22:44:19 UTC
**Ziel-Ende:** 2026-03-27T22:44 UTC (72h)
**Artefaktpfad:** `artifacts/soak_test_20260324_224419/`
**Entrypoint:** `D:/soak_entrypoint4.sh`

**Checkpoint 0 (22:46 UTC):**
- Check 1: RESTART DETECTED — cdb_grafana (Up 27min), cdb_prometheus (Up 15min) → `soak_test_FAILED.txt` geschrieben
- Check 2: ✓ All 12/12 SUT services running (inventory: 23 cdb_* containers)
- Check 3: ✓ Resources snapshot gespeichert
- Check 4: ✓ DB metrics gespeichert
- Check 5: ✓ Disk 13% used (free: 852G)

**Bekannte Einschränkung des Immediate-FAILED:**
Der Restart-Detection-Check (Check 1) prüft ALLE `cdb_*`-Container, nicht nur die
12 SUT-Services. cdb_grafana (Alerting-YAML-Reload) und cdb_prometheus (Wiederherstellung
aus Exited) zeigten "minute"-Uptime → triggerten Restart-Detection.

Klassifizierung als `sut_restart` weil:
- FRACTION_MET = FALSE (2/23 = 8.7%, Schwelle >=50%)
- TIGHT_SPREAD = FALSE (Spread = 720s, Schwelle <= 30s)
- MONITOR_FRESH = TRUE (neuer Container), aber FRACTION_MET=0 macht Gesamtbedingung FALSE

Beide Container sind **keine ZRP-relevanten SUT-Services**. Das ist eine bekannte
Limitation des Check-1-Scopes (kein offenes Fix-Issue in dieser Session).

Ab Checkpoint 1 (23:46 UTC) zeigen beide Container "hours"-Uptime → keine weiteren
Restart-Detections erwartet. Der Monitor läuft weiter (cron aktiv).

---

## E) Beobachtungshinweise für #1269 (midnight-rollover)

Der neue Run läuft über den nächsten UTC-00:00-Übergang. Zu beobachten:

**Beim Übergang 2026-03-24 23:59 UTC → 2026-03-25 00:00 UTC:**

| Artefakt | Erwartetes Verhalten (Fix aktiv) | Beobachten ob |
|---|---|---|
| `artifacts/soak_active_run_path.txt` | Bleibt auf `soak_test_20260324_224419` | Kein Wechsel auf neues `soak_test_20260325_*` |
| `artifacts/soak_test_20260324_224419/hourly_checks.log` | Neue Einträge mit steigendem `Hour X` jenseits von Hour 1/2 | Kein Reset auf Hour 00 nach Mitternacht |
| `artifacts/soak_test_20260324_224419/last_checkpoint.txt` | Monoton steigend (1, 2, 3, ...) | Kein Zurückspringen auf 0 |
| Neues Verzeichnis `soak_test_20260325_*` | Sollte NICHT angelegt werden | Wenn doch → #1269-Bug weiterhin aktiv |

**#1269 bleibt offen** bis diese Beobachtungen gemacht werden.

---

## Preflight-Ergebnis

| Check | Ergebnis |
|---|---|
| cdb_postgres | ✓ PASS (healthy, 5h+ up) |
| cdb_redis | ✓ PASS (healthy) |
| cdb_market / cdb_candles / cdb_regime / cdb_allocation | ✓ PASS (healthy) |
| cdb_risk / cdb_execution / cdb_db_writer / cdb_paper_runner | ✓ PASS (healthy) |
| cdb_ws / cdb_signal | ✓ PASS (healthy) |
| cdb_prometheus | ✓ PASS (healthy, nach Start) |
| cdb_grafana | ✓ PASS (healthy, nach Restart) |
| cdb_redis_exporter | ⚠ unhealthy — kein SUT-Service, kein Blocker |
| Kein konkurrierender Monitor | ✓ PASS (alter Container gestoppt+entfernt) |
| soak_active_run_path.txt → neue Dir | ✓ PASS |

**Gesamtpreflight: PASS** (ein unhealthy Exporter, kein Blocker)

---

## Commits / PRs dieser Session

| Commit/PR | Inhalt |
|---|---|
| PR #1273 gemerged (af0f21e) | Batch soak-monitor + alerting fixes |
| PR #1274 gemerged (ee29e99) | Session-Log #1266/#1267 Rollback-Notiz |
| PR #1275 gemerged (bb0592d) | CURRENT_STATUS Session 7 |
| #1266 reopened | KeepLastState Grafana-Inkompatibilität |
| #1267 reopened | wie #1266 |

---

## Offene Punkte nach dieser Session

- **#1266/#1267**: Echter Fix (Option A/B) ausstehend
- **#1269**: Midnight-Rollover-Evidence aus neuem Run abwarten
- **Immediate-FAILED checkpoint 0**: Bekannte Limitation (nicht SUT-Restart), ab Checkpoint 1 clean
- **cdb_redis_exporter**: unhealthy, separates Thema
