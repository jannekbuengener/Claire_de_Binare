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
| Lokale read-only Query-Config vorhanden | `make context-query-config-init` |
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

**Lokale Query-Config anlegen (secret-frei):**

```bash
make context-query-config-init
```

Der Befehl kopiert `infrastructure/config/surrealdb/context_query.local.example.yaml`
nach `infrastructure/config/surrealdb/context_query.local.yaml`, validiert die
read-only Guardrails und lässt die lokale Datei gitignored. Die Datei darf keine
Secrets enthalten; Credentials bleiben ausschließlich in `SURREALDB_ENV`.

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

## Onboarding Doctor (Preflight)

```bash
make context-doctor
# oder:
python -m tools.surrealdb.context_onboarding_doctor --format json
```

Read-only Preflight für neue Agents/Operatoren (#2642). Prüft:

- MCP HTTP-Port `127.0.0.1:8811` (TCP, optional — stdio `cdb_context` kann trotzdem funktionieren)
- SurrealDB `127.0.0.1:8010` (`/health`, `/version`, read-only Schema)
- `SECRETS_PATH` / `CDB_CONTEXT_SECRETS_PATH` (nur SET/VALID/INVALID, keine Werte)
- Canon Secret Store und `SURREALDB_ENV` (EXISTS/MISSING)
- `context_query.local.yaml` (EXISTS/MISSING)

Wenn `context_query.local.yaml` fehlt, zuerst `make context-query-config-init`
ausführen. Keine Secret-Werte in die Query-Config eintragen.

Keine Secrets im Output. Kein Docker-Start/Stop. Kein DB-Write. LR bleibt **NO-GO**.

Exit codes: `0` = nutzbar oder nur Warnings, `1` = blockierender Befund, `2` = CLI-Fehler.

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

**Wichtiger Hinweis:** `make context-smoke` ist ein **Pfad-Smoke-only**. Der finale
`[OK]` beweist nicht, dass `cdb_surrealdb` online ist oder Daten tatsächlich
geschrieben wurden. Für echten DB-backed Nachweis → `make context-smoke-db`.

---

## Hard DB-backed Smoke (`context-smoke-db`)

**Issue:** #2460 — fail-closed DB-backed context smoke.

Beweist, dass der echte SurrealDB-Container läuft, das Schema vollständig ist,
Daten importiert wurden und mindestens 1 Record lesbar ist. Schlägt fehl (Exit 1)
wenn eine Bedingung nicht erfüllt ist.

```bash
make context-smoke-db
```

Voraussetzung: `cdb_surrealdb` muss laufen (`make context-up`).

**Schritte:**

| Schritt | Befehl / Flag | Fail-closed |
|---|---|---|
| 1 | `local_schema_check.py --hard-mode` | Exit 1 wenn Container offline oder Schema fehlt |
| 2 | `make context-scan` | Scan + JSONL in `artifacts/context-intelligence/latest/` |
| 3 | `context_importer apply --adapter surrealdb-local` | Exit 1 wenn DB-Write fehlschlägt |
| 4 | `context_query --adapter surrealdb-local --hard-mode --min-count 1` | Exit 1 wenn DB offline oder 0 Records |

**Unterschied zu `context-smoke`:**

| Eigenschaft | `context-smoke` | `context-smoke-db` |
|---|---|---|
| Container erforderlich | nein (graceful skip) | **ja** (Exit 1 wenn offline) |
| Echter DB-Write | nein (InMemory-Adapter) | **ja** (`surrealdb-local`-Adapter) |
| Query-Ergebnis enforced | nein (`[NOTE]` graceful) | **ja** (`--min-count 1`, Exit 1 wenn 0 Records) |
| CI-geeignet | ja (ohne Container) | nur mit laufendem `cdb_surrealdb` |

**Erfolg:** `[OK] context-smoke-db: fail-closed DB-backed smoke complete (LR: NO-GO)`

**LR-Hinweis:** Dieser Nachweis ist lokale Context-Infrastruktur. LR-Go bleibt
**NO-GO**. Kein Trading-Start. Kein Echtgeld.

---

## Memory DB proof (read-only) — `#2603`

Narrow operator path for #2606 DB-backed **read** + **stale scan** (not the full
`context-smoke-db` pipeline). Run-scoped fixtures via `context_importer`
`local-dev`; cleanup in `finally`. No productive memory write.

**Doc:** [`docs/surrealdb/db-runtime-ci-proof-path-v1.md`](../surrealdb/db-runtime-ci-proof-path-v1.md)

```bash
make context-up
make context-memory-db-proof
```

CLI equivalent:

```bash
python -m tools.surrealdb.memory_db_proof_cli run-proof --confirm
```

### Claim evidence at rest (#2719)

Narrow operator proof that run-scoped `claim` rows reference persisted
`evidence_ref` records (fail-closed; no productive write). See
[`docs/surrealdb/claim-evidence-at-rest-v1.md`](../surrealdb/claim-evidence-at-rest-v1.md).

```bash
make context-claim-evidence-proof
```

CLI equivalent:

```bash
python -m tools.surrealdb.claim_evidence_proof_cli run-proof --confirm
```

### Cross-session memory rediscovery (#2720)

Two-process proof: manifest under ``.cdb_memory_rediscovery/<run_id>/`` plus DB
lookup by ``memory_id`` and ``scope``. See
[`docs/surrealdb/cross-session-memory-rediscovery-v1.md`](../surrealdb/cross-session-memory-rediscovery-v1.md).

```bash
make context-memory-rediscovery-proof
```

### Optional GitHub Actions proof (#2721)

Non-required, opt-in workflow for self-hosted runners with the `docker` label.
Does **not** gate merges; failures are informational. LR remains **NO-GO**.

| Item | Value |
|------|-------|
| Workflow | `.github/workflows/surrealdb-memory-proof.yml` |
| Trigger | `workflow_dispatch` only |
| Runner | `[self-hosted, cdb, docker]` |
| Permissions | `contents: read` |
| Inputs | `proof_suite` (`all` / `db-read-only` / `preflight-only`); `attempt_runtime_proof` |

**Runner prerequisites:** Docker, `SECRETS_PATH` with `SURREALDB_ENV`, local query config
(`make context-query-config-init`). The workflow runs preflight first; when preflight passes
and `attempt_runtime_proof=true`, it may invoke the same `make` targets as the operator path
above and uploads redacted artifacts (`proof_plan.json`, `summary.md`, logs).

**Manual fallback** (canonical when GHA preflight fails or runner lacks secrets):

```bash
make context-up
make context-memory-db-proof
make context-claim-evidence-proof
make context-memory-rediscovery-proof
```

Doc matrix row 6: [`docs/surrealdb/db-runtime-ci-proof-path-v1.md`](../surrealdb/db-runtime-ci-proof-path-v1.md).

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

## MCP-Posture (v1)

### Entscheidung

**Kein separater Context-MCP-Dauercontainer in v1.**

Der lokale Mindestbetrieb für SurrealDB Context Intelligence erfordert in v1 keinen
eigenen `cdb_context_mcp`-Service. Docker Desktop muss für diesen Stack ausschließlich
`cdb_surrealdb` zeigen — keinen weiteren dauerhaft laufenden Container.

### Begründung

- Weniger Container → weniger Fehlerquellen.
- `cdb_surrealdb` ist der einzige erforderliche Dauercontainer für den lokalen Context-DB-Stack.
- Harter lokaler Betriebsnachweis ist `make context-status` (Containerstatus/Health) und,
  wenn Docker/Env/Schema verfügbar sind, der vollständige `make context-smoke`.
  `context-query-smoke` ist ein read-only Komfortcheck mit graceful Notes und kein
  verlässlicher Proof-of-Life — er kann `[OK]` melden, auch wenn `cdb_surrealdb` offline ist.
- MCP kann Operator-Befehle orchestrieren, ist aber **nicht Voraussetzung** für lokalen Betrieb.
- Ein MCP-Service kann später separat ergänzt werden, wenn der CLI-Betrieb stabil ist.

### Was MCP nicht nötig ist

- `cdb_surrealdb` starten → kein MCP nötig.
- Schema anwenden → kein MCP nötig.
- Scan/Import/Query ausführen → kein MCP nötig.
- Smoke-Test bestehen → kein MCP nötig.

CDB-MCP / OpenCode kann vorhandene Makefile-Targets orchestrieren, gehört aber
nicht zur lokalen Runtime-Pflicht.

### Optionale Zukunftsoption

Ein späterer read-only `cdb_context_mcp`-Service ist denkbar, aber:

| Bedingung | Wert |
|---|---|
| Eigenes Issue/PR/Gate | erforderlich |
| Read-only | zwingend, kein DB-Apply, kein Reset |
| Kein Trading-Scope | keine Verbindung zu Risk/Execution |
| Kein Write-fähiger MCP | Schema-/Daten-Writes immer nur via CLI-Jobs |
| Kein Remote-MCP | nur `127.0.0.1`/`localhost` als lokaler Betriebsweg |
| Kein Live-Go | kein LR-Effekt durch MCP-Einführung |
| Kein Echtgeld-Go | kein Auto-Trading via MCP |

Dieser Entscheid gilt für v1 und wird in einem separaten Issue/PR geändert, falls
eine spätere Implementierung gewünscht wird.

---

## Abschluss-Gate (v1)

Dieses Gate dokumentiert die Kriterien, unter denen der lokale SurrealDB Context
Intelligence Runtime-Block als abgeschlossen gilt. Es ist der kanonische Nachweis-
Rahmen für Issue #2399.

**Wichtige Trennung:**

- **Repo-backed readiness** — Makefile-Targets, Compose-Dateien, Skripte und
  Runbook sind im Repo vorhanden und getestet. Dieser Teil ist mit PR-Merge
  vollständig nachweisbar.
- **Lokaler Echt-Durchstich** — Nachweis auf Janneks Maschine mit laufendem
  Docker Desktop, aktiver Container-Health und vollständiger Pipeline. Dieser
  Teil erfordert die lokale Laufzeitumgebung und kann nicht im CI erbracht werden.

---

### Gate 1 — Docker Runtime

| Kriterium | Befehl | Erwartetes Ergebnis | Blockiert Abschluss |
|---|---|---|---|
| Container startet | `make context-up` | `cdb_surrealdb` läuft, kein Fehler | ja |
| Container-/Health-Status | `make context-status` | Containername, Status `running`, Health `healthy`, Port `127.0.0.1:8010→8000`, Volume | ja |
| Container-Logs | `make context-logs` | Keine fatalen Fehler, SurrealDB bereit | nein (Info) |

**Hinweise:**
- `cdb_surrealdb` ist der einzige erwartete persistente lokale Dauercontainer für
  diesen Stack.
- `make context-status` ist der **visuelle/operatorische Container-/Health-Nachweis** —
  der Operator prüft anhand der Ausgabe, ob `cdb_surrealdb` existiert, Status `running`
  und Health `healthy` meldet sowie Port und Volume passen. Das Target ist **nicht
  fail-closed über den Exit-Code**: es gibt immer Exit 0 zurück und druckt nur
  Status-Text. Der Exit-Code allein darf nicht als bestandenes Gate interpretiert werden.
- `make context-up` setzt `context-env-check` voraus (Guard bei fehlender Env).
- **Restunsicherheit:** Wenn Docker Desktop lokal nicht verfügbar ist, kann dieser
  Gate-Punkt nicht lokal nachgewiesen werden. Repo-Artefakte (Compose, Makefile)
  sind dennoch vorhanden und geprüft.

---

### Gate 2 — Env / Bootstrap

| Kriterium | Befehl | Erwartetes Ergebnis | Blockiert Abschluss |
|---|---|---|---|
| Env-Guard grün | `make context-env-check` | Keine fehlenden Pflicht-Vars, kein Secret-Leak | ja |
| Fehlender Env → klare Meldung | `make context-up` ohne Env | Guard gibt `ERROR`-Ausgabe, kein Docker-Start | ja |
| Keine echten Secrets im Repo | — | `.env`-Dateien in `.gitignore`, keine Klartext-Credentials eingecheckt | ja |

**Restunsicherheit:** Kein Docker-Start nötig, um diesen Gate-Punkt im Repo zu
verifizieren — die Guard-Logik ist in `Makefile` und `context-env-check` nachweisbar.

---

### Gate 3 — Schema

| Kriterium | Befehl | Erwartetes Ergebnis | Blockiert Abschluss |
|---|---|---|---|
| Schema anwenden | `make context-schema-apply` | Schema-Definitionen erfolgreich in `cdb_context_local/cdb_context_intel` geschrieben | ja |
| Schema prüfen | `make context-schema-check` | Relevante Context-Tabellen/Definitionen bestätigt | ja |
| Reset vorhanden + geschützt | `make context-reset-local CONFIRM=1` | Löscht lokale Context-Daten; verweigert ohne `CONFIRM=1`; akzeptiert nur `127.0.0.1`/`localhost` | ja |

**Hinweise:**
- `make context-reset-local CONFIRM=1` ist **destruktiv** und **local-only** —
  er verweigert Remote-/Produktivziele.
- Ohne `CONFIRM=1` gibt das Target eine explizite `ERROR`-Meldung aus und
  bricht ab.
- **Restunsicherheit:** Schema-Apply und -Check setzen laufenden Container voraus.
  Repo-Artefakte (`context_intelligence_v0.surql`, `local_schema_apply.py`,
  `local_schema_check.py`) sind unabhängig vom Container prüfbar.

---

### Gate 4 — Pipeline / Smoke

| Kriterium | Befehl | Erwartetes Ergebnis | Blockiert Abschluss |
|---|---|---|---|
| Vollständige Pipeline | `make context-smoke` | Orchestrierungs-Pfad läuft durch (`[OK]`); **kein Container-/Runtime-Nachweis** — `context-schema-check` gibt `[SKIP]` + Exit 0 wenn Container offline, `context-import-local` nutzt `InMemoryContextApplyAdapter`, `context-query-smoke` maskiert mit `[NOTE]` | nein (Pfad-Smoke only) |
| Repo-Scan | `make context-scan` | `scan-report.json` in `artifacts/context-intelligence/latest/` | ja |
| Import Dry-Run | `make context-import-dry-run` | Importer-Pfad läuft durch (`[OK]`); **kein Blocking-Kriterium** — Fehler (kein JSONL-Input) werden mit `[NOTE]` maskiert, `[OK]` wird bedingungslos gedruckt (Makefile Zeile 337-338) | nein (Pfad-Smoke only) |
| Lokaler Import | `make context-import-local` | Import-Pfad läuft durch (`InMemoryContextApplyAdapter`); kein echter SurrealDB-DB-Write in diesem Slice — `REAL_SURREALDB_ADAPTER_AVAILABLE = False` | ja (Pfad-Smoke) |
| Query Smoke | `make context-query-smoke` | Mindestens `show-snapshot`, `show-drift`, `find-artifact` liefern Ergebnisse oder `[NOTE]` | nein (graceful) |

**Hinweise zu `context-smoke`** (Pipeline-Reihenfolge):

```
context-schema-check → context-scan → context-import-dry-run
  → context-import-local → context-query-smoke
```

**Kritische Unterscheidung:**

- `make context-status` — **visueller/operatorischer Betriebsnachweis**: gibt
  Container-/Health-/Port-/Volume-Status als Text aus. **Nicht fail-closed über den
  Exit-Code** — das Target liefert immer Exit 0. Der Operator liest die Ausgabe;
  für automatisierbare fail-closed Gates ist der vollständige Smoke-Pfad oder ein
  eigener Skript-Check nötig.
- `make context-smoke` — **vollständiger Orchestrierungs-Pfad**: beweist, dass
  alle Pipeline-Schritte ohne Fehler *laufen*, **nicht** dass `cdb_surrealdb`
  online ist. `context-schema-check` gibt `[SKIP]` + Exit 0 wenn Container offline
  (`local_schema_check.py` Zeile 165-166); `context-import-local` nutzt nur
  `InMemoryContextApplyAdapter` (kein echter DB-Write,
  `REAL_SURREALDB_ADAPTER_AVAILABLE = False`); `context-query-smoke` maskiert
  Fehler mit `[NOTE]`. **Der finale `[OK]` ist kein Container- oder
  Persistenznachweis.** Echter DB-backed Durchstich erfordert einen separaten
  SurrealDB Apply Adapter (eigenes Issue/PR/Gate).
- `make context-query-smoke` — **read-only Komfortcheck**: maskiert Fehler mit
  graceful `|| echo "[NOTE]..."` und kann `[OK]` ausgeben, auch wenn
  `cdb_surrealdb` offline ist. **Kein alleiniger Proof-of-Life.**

**Restunsicherheit:** Vollständiger Pipeline-Durchstich setzt laufenden Container
voraus. `context-scan` und `context-import-dry-run` laufen ohne Container.
Echte Persistenz in `cdb_context_local/cdb_context_intel` ist erst mit einem
realen SurrealDB Apply Adapter nachweisbar (nicht Teil dieses Gates).

---

### Gate 5 — Operator Runbook

| Kriterium | Nachweis | Erwartetes Ergebnis | Blockiert Abschluss |
|---|---|---|---|
| Runbook existiert | `docs/runbooks/SURREALDB_LOCAL_CONTEXT_RUNTIME.md` | Datei im Repo | ja |
| Startprozedur dokumentiert | Abschnitt `## Start` | `make context-up` beschrieben | ja |
| Statusprozedur dokumentiert | Abschnitt `## Status prüfen` | `make context-status` beschrieben | ja |
| Schema-Workflow dokumentiert | Abschnitt `## Schema anwenden` | `make context-schema-apply` + `make context-schema-check` beschrieben | ja |
| Smoke-Test dokumentiert | Abschnitt `## Smoke-Test (lokale Pipeline)` | `make context-smoke` und Einzelschritte beschrieben | ja |
| Reset dokumentiert | Abschnitt `## Lokaler Reset (DESTRUKTIV)` | `make context-reset-local CONFIRM=1` mit Warnung beschrieben | ja |
| Häufige Fehler dokumentiert | Abschnitt `## Häufige Fehler` | 9 Fehlerbilder mit Lösungen | ja |
| MCP-Posture dokumentiert | Abschnitt `## MCP-Posture (v1)` | v1-Entscheidung, kein Daemon-Container | ja |

**Restunsicherheit:** Keine — Runbook ist Repo-Artefakt, unabhängig von lokaler
Docker-Env prüfbar.

---

### Gate 6 — MCP-Posture

| Kriterium | Nachweis | Erwartetes Ergebnis | Blockiert Abschluss |
|---|---|---|---|
| v1-Entscheidung dokumentiert | `## MCP-Posture (v1)` in diesem Runbook | Kein `cdb_context_mcp`-Daemon-Container in v1 | ja |
| Sicherheitsgrenzen für MCP | `## MCP-Posture (v1)` Abschnitt Sicherheitsgrenzen | Kein Write-MCP, kein Remote-MCP, kein Auto-Trading via MCP | ja |
| MCP kein Runtime-Requirement | — | `cdb_surrealdb` ist einziger Pflicht-Container; MCP ist Orchestrierungsebene | ja |
| Zukünftige Option dokumentiert | `## MCP-Posture (v1)` | Optional read-only `cdb_context_mcp` braucht eigenes Issue/PR/Gate | nein (Info) |

**MCP-Dauercontainer ist in v1 nicht Teil dieses Gates.**

---

### Gate 7 — Sicherheitsgrenzen

| Grenze | Nachweis | Status |
|---|---|---|
| Kein Live-Go | `## Sicherheitsgrenzen` + LR-Status | ✅ orthogonal |
| Kein Echtgeld-Go | Keine Verbindung zu Trading/Risk/Execution | ✅ orthogonal |
| Kein LR-Go | LR bleibt **NO-GO** | ✅ bestätigt |
| Kein Auto-Trading via MCP | MCP-Posture v1: kein Daemon, kein Write-MCP | ✅ dokumentiert |
| Board-Stage `trade-capable` irrelevant | Board-Stage ist orthogonal zum lokalen Context-Stack | ✅ dokumentiert |
| Kein Remote-DB-Apply | Importer akzeptiert nur `127.0.0.1`/`localhost` | ✅ code-enforced |
| Kein produktiver Reset | `context-reset-local` guard-closed (`CONFIRM=1` + local-only) | ✅ code-enforced |

**Board-Stage `trade-capable` autorisiert weder diesen Container noch DB-Operationen
und ist für den Abschluss dieses Gates irrelevant.**

---

### Gate-Gesamtstatus

| Gate | Repo-backed readiness | Lokaler Echt-Durchstich |
|---|---|---|
| 1 — Docker Runtime | ✅ Compose + Makefile vorhanden | Benötigt Docker Desktop lokal |
| 2 — Env / Bootstrap | ✅ Guard-Logik im Makefile | Benötigt lokale Env-Konfiguration |
| 3 — Schema | ✅ Schema-Dateien + Skripte vorhanden | Benötigt laufenden Container |
| 4 — Pipeline / Smoke | ✅ Alle Targets definiert; Scan + DryRun ohne Container | Vollständige Pipeline benötigt Container |
| 5 — Operator Runbook | ✅ Runbook vollständig im Repo | Keine lokale Env nötig |
| 6 — MCP-Posture | ✅ Entscheidung dokumentiert | Keine lokale Env nötig |
| 7 — Sicherheitsgrenzen | ✅ Alle Grenzen dokumentiert und code-enforced | Keine lokale Env nötig |

**Repo-backed readiness ist vollständig.** Lokaler Echt-Durchstich (Gates 1–4)
ist Betrieb auf Janneks Maschine mit laufendem Docker Desktop. Dieses Issue
(`#2399`) gilt als geschlossen, sobald der lokale Operator den vollständigen
Durchstich bestätigt hat oder explizit auf einen späteren Zeitpunkt verschoben hat.

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

*Issue: #2397 #2398 #2399 | Epic: #2391 | Ledger: #1976 | LR: NO-GO*
