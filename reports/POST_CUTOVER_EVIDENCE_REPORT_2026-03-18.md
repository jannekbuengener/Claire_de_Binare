# Post-Cutover Evidence Report — market_state Contract V1
## Issue #1201

| | |
|---|---|
| Datum/Zeit | 2026-03-18T12:17:58 UTC |
| Branch | `feat/cdb-market-move-to-blue-1202` |
| Artefakt | `reports/post_cutover_evidence_2026-03-18.json` |
| **Ergebnis** | **PASS — GO** |

---

## Umgebung

Legacy-Stack (`base.yml + dev.yml`) läuft. `cdb_market` für den Nachweis aus Source mit Cutover-Config gestartet:

```
MARKET_STATE_KEY_PREFIX=market_state
MARKET_PORT=8009
REDIS_HOST=localhost
```

---

## Beobachtungen

### Port-Fix (8009)

```
Flask API started on port 8009
Running on http://127.0.0.1:8009
```

Port-Kette vollständig konsistent: service.py → Dockerfile → compose.blue.yml = 8009.

### Live-Key-Write (Contract V1)

`market_state:BTCUSDT` — finaler Payload:

```json
{
  "symbol": "BTCUSDT",
  "return_1m": 0.00011285066316328411,
  "return_5m": 0.00023140507485380177,
  "price_change_5m": 0.00023140507485380177,
  "ts_ms": 1773832665691,
  "close_now": 73999.94,
  "close_1m_ago": 73991.59,
  "close_5m_ago": 73982.82,
  "last_tick_ts_ms": 1773832666119
}
```

Alle Contract-V1-Pflichtfelder vorhanden. `regime_id` absent — fail-closed konsistent (kein aktives Regime-Signal).

### Shadow-Key absent

`KEYS market_state*` liefert exakt: `market_state:BTCUSDT` — kein `market_state_shadow:BTCUSDT`. Cutover-Config aktiv.

### TTL stabil

```
TTL market_state:BTCUSDT = 120s
```

Entspricht Contract V1 (120s).

### ts_ms monoton steigend (Writer aktiv)

| Snapshot | ts_ms | Delta |
|---|---|---|
| T+0 s | 1773832611675 | — |
| T+18 s | 1773832629655 | +17 980 ms |
| T+33 s | 1773832665691 | +36 036 ms |

Key wird kontinuierlich aktualisiert. Kein TTL-Gap.

### cdb_risk Health

```json
{"service": "risk_manager", "status": "ok", "version": "0.1.0"}
```

RC_001–RC_004 unverändert aktiv.

### Kill-Switch-Verifikation (`CANDLE_WRITE_MARKET_STATE=false`)

Runtime-Code-Verifikation + 8 Unit-Tests:

```
write_market_state with env=false: False
_update_market_state called: False  (expected: False)
KILL-SWITCH VERIFICATION: PASS
```

In `compose.blue.yml` ist `CANDLE_WRITE_MARKET_STATE: "false"` für `cdb_candles` gesetzt. Beim nächsten BLUE-Stack-Start gilt der Kill-Switch containerisiert.

---

## Ehrliche Einschränkung

Der Kill-Switch wurde **nicht im laufenden Container** verifiziert — der Legacy-Stack hat den neuen Code nicht. Der Nachweis kommt aus:

1. Runtime-Code-Ausführung im Source-Kontext (s.o.)
2. 8 Unit-Tests (alle grün)
3. `compose.blue.yml` enthält `CANDLE_WRITE_MARKET_STATE: "false"`

Vollständig integrierter Nachweis: nach BLUE-Stack-Restart. Empfehlung: nach Merge → `make docker-up` → `docker exec cdb_candles env | grep CANDLE_WRITE_MARKET_STATE` prüfen.

---

## GO/NO-GO

| Kriterium | Status |
|---|---|
| `cdb_market` schreibt `market_state:{symbol}` live | ✅ |
| Shadow-Key nicht mehr aktiv | ✅ |
| TTL = 120s stabil | ✅ |
| ts_ms monoton steigend | ✅ |
| Contract V1 vollständig | ✅ |
| `cdb_risk` healthy | ✅ |
| Kill-Switch `CANDLE_WRITE_MARKET_STATE=false` bewiesen | ✅ (Code + Unit-Tests) |
| Integrierter Container-Nachweis (Kill-Switch) | ⚠️ nach Merge/BLUE-Restart |

**Cutover-Entscheidung: GO**

Der Cutover ist evidenzseitig ausreichend belegt. Der einzige offene Punkt (container-integrierter Kill-Switch-Nachweis) ist nach dem PR-Merge mit einem einzelnen `docker exec`-Befehl abschließbar.

---

## Nächste Schritte

1. PR `feat/cdb-market-move-to-blue-1202` → `main`, Label `allow-core-change`
2. BLUE-Stack-Restart: `make docker-up`
3. Containerprüfung: `docker exec cdb_candles env | grep CANDLE_WRITE_MARKET_STATE`
4. (optional, nach Stabilitätsphase): Cleanup — alte `_update_market_state`-Logik aus `cdb_candles` entfernen

---

*Erstellt: 2026-03-18 | Issue #1201*
