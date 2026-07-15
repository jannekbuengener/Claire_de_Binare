# Deployment Drift Cutover — Issue #1210

**Datum:** 2026-03-19T10:28Z
**Branch:** fix/deployment-drift-1210
**Status:** PASS — BLUE-Stack vollständig auf `cdb_network` migriert

---

## Ausgangslage

5 BLUE-Services liefen noch auf `claire_de_binare_cdb_network` (Legacy-Netz, erzeugt durch
früheren Start via `base.yml + dev.yml`). Das externe Netz `cdb_network` existierte bereits.

| Service | Netz vor Cutover |
|---|---|
| cdb_allocation | claire_de_binare_cdb_network |
| cdb_candles | claire_de_binare_cdb_network |
| cdb_db_writer | claire_de_binare_cdb_network |
| cdb_paper_runner | claire_de_binare_cdb_network |
| cdb_regime | claire_de_binare_cdb_network |
| cdb_redis | cdb_network + claire_de_binare_cdb_network |

---

## Durchgeführte Schritte

```powershell
# Schritt 1: 5 betroffene Services force-recreate
docker compose -f infrastructure/compose/compose.blue.yml up -d --force-recreate \
  cdb_allocation cdb_candles cdb_db_writer cdb_paper_runner cdb_regime

# Schritt 2: cdb_redis force-recreate (hatte noch beide Netze)
docker compose -f infrastructure/compose/compose.blue.yml up -d --force-recreate cdb_redis

# Schritt 3: cdb_market restart (degraded mode nach Redis-Unterbrechung)
docker compose -f infrastructure/compose/compose.blue.yml restart cdb_market
```

---

## Verifikation nach Cutover

```
Service                  Status    Health     Netzwerk
cdb_redis                 running   healthy    cdb_network
cdb_postgres              running   healthy    cdb_network
cdb_market                running   healthy    cdb_network
cdb_risk                  running   healthy    cdb_network
cdb_execution             running   healthy    cdb_network
cdb_allocation            running   healthy    cdb_network
cdb_candles               running   healthy    cdb_network
cdb_db_writer             running   healthy    cdb_network
cdb_paper_runner          running   healthy    cdb_network
cdb_regime                running   healthy    cdb_network
```

**Netz-Check:** PASS — kein BLUE-Service mehr auf `claire_de_binare_cdb_network`
**Health-Check:** PASS — alle 10 BLUE-Services running/healthy

---

## Repo-Drift (ebenfalls in diesem Branch behoben)

`Makefile` targets `docker-up` / `docker-down` / `docker-health` zeigen jetzt auf
`compose.blue.yml` + `compose.red.yml` (statt `base.yml + dev.yml`).
Commit: `cec6358` — Fix verhindert erneutes Auftreten der Drift.

---

## Restbefunde (außerhalb #1210-Scope)

Auf `claire_de_binare_cdb_network` verbleiben zwei Orphan-Container:

| Container | Projekt | Status |
|---|---|---|
| cdb_prometheus | claire_de_binare (Legacy) | running — Orphan, nicht der kanonische RED-Stack |
| cdb_node_exporter | claire_de_binare (Legacy) | running — in BLUE_RED_SPLIT.md als "Removed" markiert |

Diese Container gehören zum Legacy-Projekt `claire_de_binare` (base.yml/dev.yml-Start),
nicht zum kanonischen `cdb-red`-Stack. Kein akuter Fehler, aber technische Schuld.
Bereinigung: separater Schritt, nicht in #1210.

---

## Fazit

Issue #1210 (BLUE-Stack-Drift) ist operativ geschlossen.
Alle BLUE-Services laufen auf dem kanonischen `cdb_network`.
Repo-seitiger Fix (Makefile) verhindert erneutes Auftreten.
