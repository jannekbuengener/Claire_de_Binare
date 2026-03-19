# MARKET_V3 Live-Write Runbook — ETHUSDT

- **Status:** `WATCH`
- **Kanonischer Tracking-Ort:** dieses Dokument (Issue #1208)
- **Letzte Aktualisierung:** 2026-03-19

---

## Promotion-Kontext

| Feld | Wert |
|------|------|
| Promotion-Zeitpunkt | `2026-03-18T19:04 MESZ` |
| Commit | `d4e3c40` |
| Branch | `feat/cdb-market-move-to-blue-1202` |
| Container | `cdb_market_eth` (Port 8011) |
| Flag | `MARKET_V3_LIVE_WRITE=true` |
| Gate | `live_write_smoke` PASS — `reports/v3_smoke_ETHUSDT_live_write_2026-03-18.json` |
| Gate-Ergebnis | 50/50 Samples, 0 missing, 0 stale |

---

## Single-Source-Risiko (explizit)

`cdb_market_eth` ist der **einzige** Schreiber von `market_price:ETHUSDT`.
`cdb_ws` abonniert nur BTCUSDT — **kein Fallback für ETHUSDT**.

**Ausfall-Konsequenz:**
- TTL 30s läuft ab → `market_price:ETHUSDT` absent
- Downstream (Risk, Signal) erhält stale/absent ETH-Daten
- Kein automatischer Recovery-Pfad
- Rollback auf `MARKET_V3_LIVE_WRITE=false` stellt ETH-Preis **nicht wieder her**
  (nur Shadow-Key `market_price_v3:ETHUSDT` aktiv) — manueller Eingriff nötig

---

## Alerting

| Regel | Ausdruck | Schwellwert | Severity |
|-------|----------|-------------|----------|
| `ETHMarketV3Disconnected` | `market_v3_ws_connected{job="cdb_market_eth"} == 0` | for 60s | critical |
| `ETHMarketV3FeedFrozen` | `rate(market_v3_decoded_total{job="cdb_market_eth"}[2m]) == 0` | for 2m | critical |

**Routing-Status:**
- Prometheus → Alertmanager: ✅ (hostname-fix commit `1cb6294`)
- Alertmanager → SMTP (Notification): ✅ (end-to-end SMTP-Kette verifiziert, nflog-Eintrag `2026-03-18T21:01 MESZ`)

---

## WATCH-Status und Exit-Kriterien für STABLE

**Promotions-Zeitpunkt:** `2026-03-18T19:04 MESZ`
**24h-Fensterende:** `2026-03-19T19:04 MESZ`

| Kriterium | Status |
|-----------|--------|
| 24h ohne WS-Disconnect | ⏳ Fensterende: 2026-03-19T19:04 MESZ |
| Rollback-Drill ausgeführt + dokumentiert | ⏳ offen (nach 24h-Ablauf) |
| Alerting end-to-end verifiziert | ✅ |

**→ STABLE erst nach Abschluss beider ⏳-Kriterien.**

---

## Rollback-Drill-Plan

**Ziel:** Empirisch belegen wie lange nach `MARKET_V3_LIVE_WRITE=false` + Redeploy der ETH-Preis absent ist und kein automatischer Recovery erfolgt.

**Ablauf:**

```bash
# 1. Flag deaktivieren in compose.blue.yml (cdb_market_eth)
# MARKET_V3_LIVE_WRITE: "false"

# 2. Redeploy
docker compose -f infrastructure/compose/compose.blue.yml up -d --no-deps cdb_market_eth

# 3. TTL-Ablauf beobachten (~30s)
# Erwartet: market_price:ETHUSDT absent, market_price_v3:ETHUSDT (Shadow-Key) vorhanden

# 4. Re-Promote
# MARKET_V3_LIVE_WRITE: "true"
docker compose -f infrastructure/compose/compose.blue.yml up -d --no-deps cdb_market_eth

# 5. Smoke Gate erneut ausführen
# Abbruch wenn: live_write_smoke missing_live_count > 0 nach 60s
```

**Erwarteter ETH-Preislücken-Gap:** ~40s (30s TTL + ~10s Redeploy)
**Akzeptabler Impact:** Bis 60s (Paper-Trading, kein Live-Exposure)

**Hinweis:** Die Alerts `ETHMarketV3Disconnected` / `ETHMarketV3FeedFrozen` feuern beim Rollback **nicht** — WS bleibt verbunden, `decoded_total` steigt weiter (schreibt nur Shadow-Key). Der Drill testet operatives Verhalten, nicht Alert-Logik.

---

## Abbruchkriterium (WATCH → Rollback)

Falls `ETHMarketV3Disconnected` oder `ETHMarketV3FeedFrozen` innerhalb des Beobachtungsfensters feuern:
→ sofort `MARKET_V3_LIVE_WRITE=false` + manuell prüfen, kein automatischer Retry.

---

## Statusverlauf

| Zeitpunkt | Ereignis |
|-----------|----------|
| `2026-03-18T19:04 MESZ` | Promotion: MARKET_V3_LIVE_WRITE=true, Gate PASS (50/50) |
| `2026-03-18T19:09 UTC` | Erstes Monitoring-Update: WS connected, 0 Errors, feed flowing |
| `2026-03-18T20:xx UTC` | Alertmanager-Prometheus-Hop fix (commit 1cb6294) |
| `2026-03-18T21:01 MESZ` | SMTP end-to-end Alerting verifiziert, Status WATCH bestätigt |
| `2026-03-19T19:04 MESZ` | 24h-Fenster-Ziel |
| — | Rollback-Drill ausstehend |
| — | STABLE-Bestätigung ausstehend |
