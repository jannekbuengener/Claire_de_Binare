# SurrealDB Local Context Runtime — Operator Runbook

Status: `context-infra-only` | Scope: Local Development | Live-Readiness: NO-GO

> **Diese Runtime ist Context Infrastructure — kein Live-Go, kein Echtgeld-Go, kein Trading-Go.**
>
> `cdb_surrealdb` starten oder stoppen hat null Auswirkung auf Live-Readiness,
> LR-Status, Echtgeld-Trading, BLUE/RED Runtime oder irgendeinen Risk-/Execution-Pfad.
> Board-Stage `trade-capable` ist orthogonal zu diesem Stack und autorisiert weder
> diesen Container noch irgendwelche Datenbankoperationen als Live-Freigabe.

---

## Kurzantwort

**Wo läuft das Ding?**

- Dauerhaft läuft genau **ein** Container: `cdb_surrealdb`.
- Context-Tools (Indexer, Importer, Query-CLI) laufen als **einmalige Jobs/Befehle** — nicht dauerhaft.
- Docker Desktop muss `cdb_surrealdb` als laufenden Container zeigen.
- Wenn `cdb_surrealdb` nicht sichtbar ist, läuft der lokale Context-DB-Stack **nicht**.
- Lokaler Dev-Port: `127.0.0.1:8010 → 8000` (via `surrealdb-dev.yml` Overlay).

---

## Architektur

```
Repo (Dateisystem)
      │
      ▼
context_indexer.py   ──► Snapshot / JSONL-Export
      │
      ▼
context_importer.py  ──► cdb_surrealdb (127.0.0.1:8010)
                                │
                                ▼
context_query.py     ──► read-only Queries
```

- **SurrealDB** = lokale Context-Datenbank (namespace: `cdb_context_local`, database: `cdb_context_intel`).
- **Indexer** = scannt Repo und erzeugt lokalen Snapshot / JSONL-Export.
- **Importer** = importiert Snapshot in lokale DB (nur gegen `127.0.0.1`).
- **Query-CLI** = fragt lokale DB read-only ab.
- Kein Trading-Live. Kein Echtgeld. Kein LR-Go. Kein Remote-DB-Ziel.

---

## Voraussetzungen

| Voraussetzung | Prüfung |
|---|---|
| Docker Desktop läuft | `docker ps` liefert Ausgabe ohne Fehler |
| `cdb_network` vorhanden | `docker network ls \| grep cdb_network` |
| Lokale Env-Datei vorhanden | `make context-env-check` |
| `SECRETS_PATH` gesetzt oder Default-Pfad vorhanden | `ls ${SECRETS_PATH:-$HOME/Documents/.secrets/.cdb}/SURREALDB_ENV` |
| Lokales Repo vorhanden | `git status` |
| Python 3.12 + Tools | `python3 --version` |

**Env-Datei-Pfad:**

| Platform | Pfad |
|---|---|
| Linux/Mac | `~/Documents/.secrets/.cdb/SURREALDB_ENV` |
| Windows | `%USERPROFILE%\Documents\.secrets\.cdb\SURREALDB_ENV` |
| Override | `SECRETS_PATH=/pfad/zu/dir make context-up` |

Template: `infrastructure/config/surrealdb/SURREALDB_ENV.example`

**`cdb_network` anlegen (falls fehlend):**

```bash
docker network create cdb_network
```

---

## Env/Secrets prüfen

```bash
make context-env-check
```

Prüft, ob die Env-Datei vorhanden und lesbar ist — **ohne Secret-Werte auszugeben**.
Exits 0 wenn OK, 1 wenn Datei fehlt oder `SECRETS_PATH` nicht gesetzt.

---

## Start

```bash
make context-up
```

- Führt `context-env-check` zuerst aus (fail-closed).
- Startet `cdb_surrealdb` via Docker Compose (`surrealdb-dev.yml` Overlay).
- BLUE/RED Runtime bleibt unangetastet.

Direkter Compose-Befehl (falls Make nicht verfügbar):

```bash
docker compose \
  -f infrastructure/compose/surrealdb.yml \
  -f infrastructure/compose/surrealdb-dev.yml \
  up -d cdb_surrealdb
```

---

## Status prüfen

```bash
make context-status
```

Gibt Container-/Volume-/Port-Status aus — kein Secret-Leak.

Direkter Docker-Check:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep cdb_surrealdb
```

Erwartete Ausgabe wenn gesund:

```
cdb_surrealdb   Up X minutes (healthy)   127.0.0.1:8010->8000/tcp
```

Health-Endpoint direkt:

```bash
curl -s http://127.0.0.1:8010/health
```

Erwartete Antwort: `OK` (HTTP 200).

---

## Logs

```bash
make context-logs
```

Zeigt die letzten 50 Zeilen von `cdb_surrealdb`.

Direkt:

```bash
docker logs cdb_surrealdb --tail 50
docker logs cdb_surrealdb --follow
```

---

## Stop

```bash
make context-down
```

- Stoppt nur `cdb_surrealdb`.
- BLUE/RED Runtime und alle anderen Container bleiben unangetastet.
- Volume bleibt erhalten — Daten gehen beim Stop nicht verloren.

---

## Restart

```bash
make context-restart
```

Entspricht `context-down` gefolgt von `context-up`.

---

## Schema anwenden

Schema muss einmalig angewendet werden, bevor Daten importiert werden können.
**Voraussetzung:** `cdb_surrealdb` läuft (`make context-up` zuerst).

```bash
make context-schema-apply
```

- Liest `infrastructure/surrealdb/context_intelligence_v0.surql`.
- Verbindet zu `http://127.0.0.1:8010` (hard-guarded — kein Remote-Ziel möglich).
- Namespace: `cdb_context_local` / Database: `cdb_context_intel`.
- `DEFINE TABLE`-Statements — idempotent, sicher mehrfach ausführbar.
- Berührt keine Trading-/Live-Tabellen.

---

## Schema prüfen

```bash
make context-schema-check
```

- Prüft, ob alle 18 v0-Tabellen vorhanden sind.
- Exit 0 wenn alle Tabellen da oder Container offline (graceful fail).
- Exit 1 wenn Tabellen fehlen — gibt an, welche.
- Kein Secret-Leak.

---

## Lokaler Reset (DESTRUKTIV)

> **ACHTUNG:** Löscht alle Datensätze in den Context-Intelligence-Tabellen.
> Schema-Definitionen bleiben erhalten. Trading-/Live-Tabellen werden **nicht** angefasst.
> Kein Echtgeld-Go. Kein LR-Go. Kein Effekt auf BLUE/RED Runtime.

```bash
make context-reset-local CONFIRM=1
```

- `CONFIRM=1` ist zwingend — ohne diese Variable bricht der Befehl mit Exit 2 ab.
- Nur gegen `127.0.0.1`/`localhost` erlaubt (hard-guarded).
- Nach Reset ist Schema noch vorhanden — nur Datensätze sind weg.
- `make context-schema-apply` danach nicht nötig (Schema bleibt).

---

## Smoke-Test (lokale Pipeline)

Testet den vollständigen lokalen Context-Intelligence-Pfad:

```bash
make context-smoke
```

Pipeline-Schritte:

| Schritt | Befehl | Beschreibung |
|---|---|---|
| 1 | `context-schema-check` | Prüft Schema-Tabellen |
| 2 | `context-scan` | Scannt Repo → `artifacts/context-intelligence/latest/scan-report.json` |
| 3 | `context-import-dry-run` | Dry-Run Import (kein DB-Write) |
| 4 | `context-import-local` | Importiert in lokale SurrealDB |
| 5 | `context-query-smoke` | Read-only Queries: `show-snapshot`, `show-drift`, `find-artifact` |

Einzelne Schritte separat:

```bash
make context-scan               # Repo-Scan, kein DB-Write
make context-import-dry-run     # Import planen, kein DB-Write
make context-import-local       # Lokaler Import (Schema-Check vorher)
make context-query-smoke        # Read-only Query-Smoke (graceful fail)
```

Snap-Verzeichnis (Default, überschreibbar):

```bash
CONTEXT_SNAP_DIR=artifacts/context-intelligence/latest  # Default
CONTEXT_SNAP_DIR=/anderer/pfad make context-scan         # Override
```

**Erfolg:** `[OK] context-smoke: vollstaendige Pipeline abgeschlossen` ohne rote Fehler.

**Graceful fail:** `context-query-smoke` gibt `[NOTE]`-Meldungen aus wenn kein Container läuft — das ist kein Fehler, solange `context-scan` und `context-import-dry-run` grün waren.

---

## Häufige Fehler

### Docker Desktop läuft nicht

**Symptom:** `docker ps` schlägt fehl oder `make context-up` gibt `Cannot connect to Docker daemon` aus.

**Fix:** Docker Desktop starten, warten bis `docker ps` sauber antwortet.

---

### `cdb_network` fehlt

**Symptom:** `make context-up` schlägt fehl mit `network cdb_network not found`.

**Fix:**

```bash
docker network create cdb_network
```

---

### `SECRETS_PATH` nicht gesetzt / Env-Datei fehlt

**Symptom:** `make context-env-check` schlägt fehl, `context-up` bricht beim Env-Check ab.

**Fix:** Env-Datei anlegen:

```bash
cp infrastructure/config/surrealdb/SURREALDB_ENV.example \
   ~/Documents/.secrets/.cdb/SURREALDB_ENV
# Dann SURREAL_USER und SURREAL_PASS in der Datei setzen
```

Oder `SECRETS_PATH` explizit setzen:

```bash
SECRETS_PATH=/mein/secrets/pfad make context-up
```

---

### Port 8010 belegt

**Symptom:** Container startet nicht, Fehler `bind: address already in use` auf Port 8010.

**Fix:** Prozess auf Port 8010 finden und beenden:

```bash
lsof -ti:8010 | xargs kill -9   # Linux/Mac
# oder
netstat -ano | findstr :8010     # Windows
```

---

### Container läuft, aber Healthcheck rot

**Symptom:** `docker ps` zeigt `(unhealthy)`.

**Fix:**

```bash
make context-logs                        # Logs prüfen
curl -v http://127.0.0.1:8010/health     # Health-Endpoint direkt
make context-restart                     # Restart versuchen
```

---

### Schema nicht angewendet

**Symptom:** `make context-schema-check` meldet fehlende Tabellen.

**Fix:**

```bash
make context-up              # Container muss laufen
make context-schema-apply    # Schema anwenden
make context-schema-check    # Prüfen
```

---

### Query liefert leer

**Symptom:** `make context-query-smoke` gibt `"count": 0` oder `"results": []` zurück.

**Ursache:** Noch keine Daten importiert.

**Fix:**

```bash
make context-scan
make context-import-local
make context-query-smoke     # Jetzt mit Daten
```

---

### Import verweigert Remote-Ziel

**Symptom:** Importer bricht mit `WRITE_DENIED` oder `remote target not allowed` ab.

**Ursache:** `--apply-mode local-dev` ist die einzige erlaubte Mode — kein Remote-Target möglich. Das ist kein Bug, sondern ein intentionaler Guard.

**Fix:** Keiner nötig — lokalen Stack sicherstellen und `make context-import-local` nutzen.

---

### `context-import-dry-run` meldet kein JSONL-Input

**Symptom:** `[NOTE] Import dry-run: kein JSONL-Input — zuerst context-scan ausfuehren`

**Fix:**

```bash
make context-scan          # Erst scan ausführen
make context-import-dry-run
```

---

## Sicherheitsgrenzen

| Grenze | Regel |
|---|---|
| Kein Live-Go | Dieser Stack hat null Effekt auf Live-Readiness |
| Kein Echtgeld-Go | Keine Verbindung zu Trading-, Risk- oder Execution-Pfaden |
| Kein Remote-DB-Apply | Importer akzeptiert nur `127.0.0.1`/`localhost` als Ziel |
| Kein produktiver Reset | `context-reset-local` ist guard-closed (`CONFIRM=1` + local-only guard) |
| Kein Trading-Runtime-Start | `context-up` startet ausschließlich `cdb_surrealdb` |
| Board-Stage irrelevant | `trade-capable` autorisiert weder diesen Container noch DB-Operationen |
| LR bleibt NO-GO | SurrealDB Local Runtime ist orthogonal zum LR-System |

---

## Referenzen

| Datei | Zweck |
|---|---|
| `docs/surrealdb/local-context-runtime-contract.md` | Kanonischer Stack-Contract |
| `infrastructure/compose/surrealdb-dev.yml` | Dev-Overlay (Port 8010) |
| `infrastructure/surrealdb/context_intelligence_v0.surql` | Schema-Definitionen |
| `infrastructure/config/surrealdb/SURREALDB_ENV.example` | Env-Template |
| `tools/surrealdb/local_schema_apply.py` | Schema-Apply-Script |
| `tools/surrealdb/local_schema_check.py` | Schema-Check-Script |
| `tools/surrealdb/local_reset.py` | Reset-Script |
| `tools/surrealdb/context_indexer.py` | Repo-Scanner |
| `tools/surrealdb/context_importer.py` | DB-Importer |
| `tools/surrealdb/context_query.py` | Query-CLI |

---

*Issue: #2397 | Epic: #2391 | Ledger: #1976 | LR: NO-GO*
