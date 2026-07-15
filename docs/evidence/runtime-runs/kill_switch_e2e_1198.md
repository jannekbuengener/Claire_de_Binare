# Kill-Switch E2E Evidence — Issue #1198

## Run-Metadaten

| Feld | Wert |
|---|---|
| Datum/Zeit | 2026-03-18T10:40:35+01:00 |
| Branch | feat/market-prometheus-metrics-1148 |
| Befehl (äquivalent) | `E2E_RUN=1 pytest tests/e2e/test_kill_switch_live.py -v` |
| Stack | `compose.blue.yml` (cdb_risk + cdb_execution, Project `cdb-blue`) |
| Kill-Switch-State-Pfad | `/app/kill_switch/.cdb_kill_switch.state` (shared Volume `kill_switch_state`) |
| Ausführungsumgebung | Host (localhost:8002 Risk, localhost:6379 Redis) |

## Ergebnis

**PASS**

## Assertion-Chain

| Schritt | Erwartung | Tatsächlich | Status |
|---|---|---|---|
| 1 | Redis erreichbar | `PONG` (localhost:6379) | ✓ |
| 2 | Kill-Switch inaktiv bei Start | `active=False` | ✓ |
| 3 | Baseline-Order ohne Kill-Switch | `status=FILLED`, kein kill-switch-Fehler | ✓ |
| 4a | `POST /kill-switch/activate` HTTP 200 | `activated=True, reason=manual` | ✓ |
| 4b | State-File tatsächlich geschrieben (Re-Read) | `active=True, reason=manual` via `GET /kill-switch` | ✓ |
| 5 | Order unter aktivem Kill-Switch → REJECTED | `status=REJECTED, error_message="Order blocked: kill-switch active (manual)"` | ✓ |
| 6 | Deaktivierung sauber | `active=False` nach Deactivate | ✓ |

## Nachweis-Aussage

Der Kill-Switch-State wird von `cdb_risk` via `POST /kill-switch/activate` in das shared
Docker Volume `kill_switch_state:/app/kill_switch/.cdb_kill_switch.state` geschrieben.
`cdb_execution` liest denselben Pfad via `CDB_KILL_SWITCH_STATE_FILE` und blockiert
nachfolgende Orders fail-closed mit `status=REJECTED`.

Gap F-1 (struktureller E2E-Bruch durch getrenntes Container-Filesystem) ist durch
Delta 1 (shared Volume) geschlossen und durch diesen Run bewiesen.

## Blocker-Log (während Delta 3 aufgetreten, resolved)

| Blocker | Ursache | Resolution |
|---|---|---|
| Container-Image veraltet | Stack lief mit `base.yml + dev.yml` (gebaut 2026-03-17, vor Kill-Switch-HTTP-Commit) | cdb_risk + cdb_execution aus `compose.blue.yml` neu gebaut |
| Netzwerk-Mismatch | Legacy-Stack nutzt `claire_de_binare_cdb_network`, Blue nutzt `cdb_network` (external) | `docker network connect cdb_network cdb_redis cdb_postgres` |
| Volume-Ownership `root:root` | Docker-Volume bei leerem Erstmount mit root-Ownership erstellt, Container läuft als riskuser (uid 1000) | `docker run --rm -v kill_switch_state:/vol alpine chown -R 1000:1000 /vol` |
| Missing `decision_id` im Test | `TRACE_CONTRACT_V1_ENABLED=1` in compose.blue.yml — Execution lehnt Orders ohne decision_id vor Kill-Switch-Gate ab | `decision_id` zum Test-Payload hinzugefügt (Delta 2 Test aktualisiert) |

## Verbleibende Restrisiken (nicht durch diesen Run abgedeckt)

| Risiko | Beschreibung |
|---|---|
| Volume-Ownership nach `docker compose up` | Neuer Stack-Start ohne manuellen Ownership-Fix → riskuser kann nicht schreiben. Dockerfile-Fix (mkdir + chown in Entrypoint) empfohlen für produktiven Betrieb. |
| Netzwerk beim Vollstart | Bei vollständigem Neustart mit `compose.blue.yml up` müssen cdb_redis + cdb_postgres aus dem alten Projekt explizit mit `cdb_network` verbunden sein — oder alle Services aus `compose.blue.yml` gestartet werden. |
| Race-Condition < 500ms | `time.sleep(0.5)` nach activate ist heuristisch, kein harter FS-Sync-Nachweis. |

## Delta 4 — Pre-Merge Hardening (2026-03-18T10:47:16+01:00)

**Dockerfile-Fix**: `services/risk/Dockerfile` — `mkdir -p /app/kill_switch` vor `chown -R riskuser:riskuser /app`

Docker propagiert beim Erstmount eines leeren Volumes die Image-Layer-Permissions.
Das Verzeichnis existiert jetzt im Image als `riskuser:riskuser` → Volume-Erstmount
erbt korrekte Ownership automatisch. Kein manueller `chown` mehr nötig.

**Delta 4 Verifikationslauf**: PASS
- Volume nach Erstmount: `drwxr-xr-x riskuser riskuser`
- State-File nach activate: `-rw-r--r-- riskuser riskuser .cdb_kill_switch.state`
- Blocked order: `status=REJECTED, error="Order blocked: kill-switch active (manual)"`

## Bewertung für Issue #1198

**GO — merge-ready**

- Delta 1: shared Volume in `compose.blue.yml` ✓
- Delta 2: `tests/e2e/test_kill_switch_live.py` ✓ (inkl. `decision_id` Fix)
- Delta 3: echter Blue-Stack-Run PASS ✓
- Delta 4: Dockerfile-Hardening, kein manueller Stack-Eingriff mehr nötig ✓
- Struktureller Gap F-1 geschlossen ✓
