# Market V3 Live-Write — Betriebsrunbook

**Status:** ACTIVE — Live-Write-Modus seit 2026-03-18
**Issue:** #1206 · **PR:** #1207 (gemerged)
**Evidence:** `reports/v3_smoke_BTCUSDT_live_write_2026-03-18.json` (Gate PASS)

**ETH Shadow-Instanz:** AKTIV seit 2026-03-18 — `cdb_market_eth` (Port 8011, ETHUSDT, shadow-only)
**ETH Shadow-Evidence:** `reports/v3_shadow_ETHUSDT_2026-03-18.json` (INCONCLUSIVE — strukturell, siehe unten)

---

## Aktueller Datenpfad in BLUE

```
MEXC Exchange
   │
   ├─► cdb_ws (PubSub via market_data channel)
   │       └─► cdb_market._process_event()
   │                └─► Redis: market_price:{symbol}  TTL 30s
   │
   └─► cdb_market.MexcV3Client (direkte WS-Verbindung, Protobuf)
           └─► cdb_market._v3_live_event()
                    └─► Redis: market_price:{symbol}  TTL 30s  ← gleiche Key
```

Beide Pfade schreiben auf denselben Key (`market_price:{symbol}`).
Last-write-wins. Kein Shadow-Key aktiv.

---

## Env-Variablen (cdb_market)

| Variable | Wert BLUE | Bedeutung |
|---|---|---|
| `MARKET_V3_CLIENT_ENABLED` | `true` | V3-Client läuft als Daemon-Thread |
| `MARKET_V3_LIVE_WRITE` | `true` | V3 schreibt auf Live-Key (nicht Shadow) |
| `MARKET_V3_SYMBOL` | `BTCUSDT` | Aktives Symbol |

---

## Gate-Modi (`v3_compare.py`)

### `shadow_compare` (V3 noch im Shadow-Modus)

Verwendet wenn `MARKET_V3_LIVE_WRITE=false`.
Shadow-Key `market_price_v3:{symbol}` muss vorhanden sein.
Prüft Preis- und Zeitstempel-Abweichung zwischen Live- und Shadow-Key.

```bash
python -m services.market.tools.v3_compare \
  --mode shadow_compare --symbol BTCUSDT --samples 200 --interval 5 \
  --out reports/v3_shadow_BTCUSDT_<datum>.json
```

Gate PASS = bereit für Live-Write-Promotion.

### `live_write_smoke` (V3 im Live-Write-Modus — aktueller BLUE-Stand)

Verwendet wenn `MARKET_V3_LIVE_WRITE=true`.
Shadow-Key fehlt erwartungsgemäß → `INFO`, kein FAIL.
Prüft: Live-Key vorhanden + frisch (Stale-Threshold 30 s).

```bash
REDIS_HOST=localhost REDIS_PORT=6379 REDIS_PASSWORD=<pw> \
python -m services.market.tools.v3_compare \
  --mode live_write_smoke --symbol BTCUSDT --samples 50 --interval 3 \
  --out reports/v3_smoke_BTCUSDT_<datum>.json
```

Gate-Kriterien:

| Kriterium | Threshold | Ergebnis bei Verletzung |
|---|---|---|
| `max_missing_live_pct` | 5 % | FAIL |
| `min_live_samples` | 20 | INCONCLUSIVE |
| `max_stale_live_pct` | 5 % | FAIL |
| `missing_shadow_expected` | — | INFO (nie FAIL) |

---

## Operative Checks

```bash
# Health
curl -s http://127.0.0.1:8009/health

# V3-Metriken
curl -s http://127.0.0.1:8009/metrics | grep market_v3_

# Redis — Live-Key vorhanden und frisch?
docker exec cdb_market python -c "
import redis, json, time, os
r = redis.Redis(host='cdb_redis', port=6379,
    password=open('/run/secrets/redis_password').read().strip(),
    decode_responses=True)
v = r.get('market_price:BTCUSDT')
d = json.loads(v) if v else {}
age = int(time.time()*1000) - int(d.get('ts_ms', 0))
print(f'price={d.get(\"price\")}  age_ms={age}  source={d.get(\"source\")}')
print('shadow key exists:', bool(r.exists('market_price_v3:BTCUSDT')))
"
```

Erwartete Ausgabe im Live-Write-Modus:
- `price=<aktuell>  age_ms=<< 30000  source=mexc`
- `shadow key exists: False`

---

## Rollback-Verfahren

### Stufe 1 — Shadow-Only (schnell, kein Downtime)

V3 schreibt wieder auf `market_price_v3:{symbol}` statt auf den Live-Key.
`cdb_ws`-Pfad übernimmt allein den Live-Key.

```yaml
# infrastructure/compose/compose.blue.yml — cdb_market environment:
MARKET_V3_LIVE_WRITE: "false"   # ← ändern
```

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d --no-deps cdb_market
```

Verifikation: `live_write_smoke` → FAIL erwartet (Live-Key kommt nur noch von cdb_ws).
Stattdessen `shadow_compare` Gate ausführen.

### ETHUSDT-spezifisch: Rollback ≠ Fallback

**Gilt nach ETH Live-Write-Promotion.**

Für BTCUSDT übernimmt `cdb_ws` bei Rollback auf `MARKET_V3_LIVE_WRITE=false` sofort den Live-Key.
Für **ETHUSDT existiert kein solcher Fallback.** `cdb_ws` abonniert ausschließlich BTCUSDT.

→ `MARKET_V3_LIVE_WRITE=false` bei `cdb_market_eth` bedeutet:
- V3 schreibt wieder nur auf `market_price_v3:ETHUSDT` (Shadow-Key).
- `market_price:ETHUSDT` (Live-Key) wird von **niemandem** mehr geschrieben.
- TTL 30s läuft ab → **ETH-Preisversorgung fällt weg.**
- Folgeeffekte: Alle Downstream-Consumer (Risk, Signal) die ETHUSDT lesen erhalten stale/absent data.

**Manueller Eingriff nötig** bevor die Lücke geschlossen ist. Es gibt keinen automatischen Recovery-Pfad.

---

### Stufe 2 — V3-Client vollständig deaktivieren

```yaml
MARKET_V3_CLIENT_ENABLED: "false"
```

```bash
docker compose -f infrastructure/compose/compose.blue.yml up -d --no-deps cdb_market
```

Kein V3-Daemon-Thread, keine Metriken, kein Netzwerk-Overhead.

---

## Wichtige Invarianten

- `cdb_ws` bleibt **immer aktiv** — unabhängig von V3-Modus
- `cdb_ws` schreibt weiterhin auf `market_price:{symbol}` (parallel zu V3 in Live-Write)
- Shadow-Key `market_price_v3:{symbol}` existiert **nicht** im Live-Write-Modus — korrekt
- V3-Metriken (`market_v3_*`) sind unter `/metrics` von cdb_market verfügbar
- `cdb_ws` abonniert **nur BTCUSDT** — `market_price:ETHUSDT` existiert nie (kein anderer Live-Key-Schreiber)
- `shadow_compare` für ETHUSDT ist **strukturell nicht anwendbar** (kein Live-Key zum Vergleich)

### Prometheus-Netzwerk

`cdb_prometheus` ist in `compose.red.yml` auf `cdb_network` (external) deklariert.
Restarts via `compose.red.yml` verbinden sich automatisch korrekt mit `cdb_market` und `cdb_market_eth`.

Falls Market-Targets nach einem Restart `down` zeigen:
```bash
# Netzwerk-Zugehörigkeit prüfen
docker inspect cdb_prometheus --format '{{json .NetworkSettings.Networks}}' | python -m json.tool

# Manuell verbinden (Einmal-Fix, wenn mit Legacy-Compose gestartet)
docker network connect cdb_network cdb_prometheus
```

---

## ETHUSDT Shadow-Instanz (cdb_market_eth) — aktueller Stand

**Status:** AKTIV — shadow-only (`MARKET_V3_LIVE_WRITE=false`), Port 8011, seit 2026-03-18.

### Architekturelle Einschränkung: shadow_compare strukturell nicht anwendbar

`shadow_compare` erfordert einen **Live-Key** (`market_price:ETHUSDT`) für den Vergleich.
`cdb_ws` abonniert ausschließlich BTCUSDT — `market_price:ETHUSDT` wird **niemals** von `cdb_ws` geschrieben.
→ `shadow_compare` für ETHUSDT liefert structural INCONCLUSIVE (0 vergleichbare Samples).

**Befund 2026-03-18:** Shadow-Key `market_price_v3:ETHUSDT` VORHANDEN und frisch.
V3-Client läuft stabil (`decoded_total` steigt, `decode_errors=0`, `ws_connected=1`).
Das ist der einzig mögliche Health-Check im Shadow-Modus für neue Symbole.

### Operative Health-Checks (ETHUSDT Shadow)

```bash
# Health
curl -s http://127.0.0.1:8011/health

# V3-Metriken (decoded_total soll steigen)
curl -s http://127.0.0.1:8011/metrics | grep market_v3_

# Redis — Shadow-Key vorhanden und frisch?
MSYS_NO_PATHCONV=1 docker exec cdb_market_eth python -c "
import redis, json, time
r = redis.Redis(host='cdb_redis', port=6379,
    password=open('/run/secrets/redis_password').read().strip(),
    decode_responses=True)
v = r.get('market_price_v3:ETHUSDT')
d = json.loads(v) if v else {}
age = int(time.time()*1000) - int(d.get('ts_ms', 0)) if d else -1
print(f'shadow price={d.get(\"price\")}  age_ms={age}')
print('live key exists:', bool(r.exists('market_price:ETHUSDT')))
"
```

Erwartete Ausgabe:
- `shadow price=<aktuell>  age_ms=<< 30000`
- `live key exists: False` (korrekt — kein Schreiber für ETHUSDT live key)

### Promotionspfad ETHUSDT → Live-Write

`shadow_compare` wird **übersprungen** (strukturell nicht anwendbar, kein Live-Key-Schreiber).
Stattdessen:

1. **V3 Shadow Health** bestätigen (shadow-key frisch, `decoded_total` steigt, `decode_errors=0`).
2. `MARKET_V3_LIVE_WRITE: "true"` in `compose.blue.yml` für `cdb_market_eth` setzen.
3. Redeploy der ETH-Instanz:
   ```bash
   docker compose -f infrastructure/compose/compose.blue.yml up -d --no-deps cdb_market_eth
   ```
4. `live_write_smoke` Gate ausführen (Live-Key muss jetzt von V3 beschrieben werden):
   ```bash
   REDIS_HOST=localhost REDIS_PORT=6379 REDIS_PASSWORD=<pw> \
   python -m services.market.tools.v3_compare \
     --mode live_write_smoke --symbol ETHUSDT --samples 50 --interval 3 \
     --out reports/v3_smoke_ETHUSDT_<datum>.json
   ```
   Gate-Kriterien: identisch mit BTCUSDT (max_missing_live_pct ≤ 5 %, min 20 Samples, max_stale ≤ 5 %).

### Architektur (Option A)

Ein separater `cdb_market`-Container pro Symbol.
Jeder Container handhabt genau ein `MARKET_V3_SYMBOL`. Laufende BTCUSDT-Instanz unberührt.
`_parse_v3_symbols()` in `service.py` implementiert für zukünftigen Multi-Symbol-Bootstrap.

---

## Verlauf

| Datum | Aktion | Evidence |
|---|---|---|
| 2026-03-18 | `shadow_compare` Gate PASS (200 Samples, BTCUSDT) | `reports/v3_compare_BTCUSDT_*.json` |
| 2026-03-18 | Live-Write-Promotion BTCUSDT (`MARKET_V3_LIVE_WRITE=true`) | PR #1207 |
| 2026-03-18 | `live_write_smoke` Gate PASS (50 Samples, BTCUSDT) | `reports/v3_smoke_BTCUSDT_live_write_2026-03-18.json` |
| 2026-03-18 | Multi-Symbol-Vorbereitung (Option A, `_parse_v3_symbols`, Compose/Prometheus-Template) | PR #1207 follow-up |
| 2026-03-18 | `cdb_market_eth` aktiviert — shadow-only (ETHUSDT, Port 8011) | `compose.blue.yml`, `prometheus.yml` |
| 2026-03-18 | `shadow_compare` ETHUSDT → INCONCLUSIVE (strukturell: kein Live-Key-Schreiber für ETHUSDT) | `reports/v3_shadow_ETHUSDT_2026-03-18.json` |
| 2026-03-18 | Prometheus mit `cdb_network` verbunden — beide Market-Targets `up` | `docker network connect cdb_network cdb_prometheus` |
| 2026-03-18 | Gate-Ausnahme dokumentiert: `shadow_compare` für ETHUSDT nicht anwendbar — Single-Source-Warnung + Rollback-Risk in Runbook + compose.blue.yml | — |
| 2026-03-18 | Live-Write-Promotion ETHUSDT (`MARKET_V3_LIVE_WRITE=true`, `cdb_market_eth`) | `compose.blue.yml` |
| 2026-03-18 | `live_write_smoke` Gate PASS (50 Samples, ETHUSDT, 0 missing, 0 stale) | `reports/v3_smoke_ETHUSDT_live_write_2026-03-18.json` |
