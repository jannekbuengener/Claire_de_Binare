# Adaptive Intensity System - "Dry/Wet" Engine

**Automatische Anpassung der Trading-Aggressivität basierend auf Performance-Analyse**

## Konzept: Dry/Wet System

Das System wechselt automatisch zwischen drei Modi basierend auf den letzten 300 Trades:

```
🏜️ DRY (Trocken)      → Konservativ, weniger Trades, sicherer
⚖️ NEUTRAL (Neutral)   → Balanciert, moderate Frequenz
💧 WET (Nass/Fließend) → Aggressiv, mehr Trades, höhere Frequenz
```

**Metapher:**
- **DRY** = Mehr Bodenhaftung = kontrolliert, vorsichtig, weniger Trades
- **WET** = Fließen lassen = lockerer, aggressiv, höhere Trade-Frequenz

---

## Risk Profiles - Parameter

| Parameter | DRY (Konservativ) | NEUTRAL (Moderat) | WET (Aggressiv) |
|-----------|-------------------|-------------------|-----------------|
| **Signal Threshold** | 3.0% | 2.0% | 1.5% |
| **RSI Threshold** | >60 (bullish) | >50 (neutral) | >40 (loose) |
| **Volume Multiplier** | 2.0x | 1.0x | 0.5x |
| **Max Position** | 8% | 10% | 12% |
| **Max Exposure** | 40% | 50% | 60% |
| **Max Daily Drawdown** | 3% | 5% | 5% |

---

## Performance Gates

### Upgrade-Kriterien (→ aggressiver)

Wechsel von DRY → NEUTRAL oder NEUTRAL → WET wenn:
- ✅ Winrate > 60% über 300 Trades
- ✅ Max Drawdown < 3%
- ✅ Profit Factor > 1.5
- ✅ Keine Circuit Breaker Events (letzte 7 Tage)
- ✅ Min 300 Trades im Analyse-Fenster

### Downgrade-Kriterien (→ konservativer)

Wechsel von WET → NEUTRAL oder NEUTRAL → DRY wenn:
- ⚠️ Winrate < 50%
- ⚠️ Max Drawdown > 5%
- ⚠️ Profit Factor < 1.0
- ⚠️ Circuit Breaker aktiviert

### Sofort-Downgrade zu DRY

Bei Circuit-Breaker-Aktivierung → **sofort zu DRY** (unabhängig vom aktuellen Profil)

---

## Architektur

```
┌─────────────────────────────────────────────────┐
│  Adaptive Intensity Service (Port 8004)         │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Background Loop (alle 5min)           │     │
│  │  ├─ Performance Analyzer                │     │
│  │  │  └─ PostgreSQL (letzte 300 Trades)  │     │
│  │  ├─ Profile Manager                     │     │
│  │  │  └─ Check Upgrade/Downgrade          │     │
│  │  └─ Update Prometheus Metriken          │     │
│  └────────────────────────────────────────┘     │
│                                                  │
│  ┌────────────────────────────────────────┐     │
│  │  Flask HTTP API                        │     │
│  │  ├─ GET  /status                        │     │
│  │  ├─ GET  /profile                       │     │
│  │  ├─ POST /profile/<name>                │     │
│  │  ├─ GET  /transitions                   │     │
│  │  └─ GET  /metrics (Prometheus)          │     │
│  └────────────────────────────────────────┘     │
└─────────────────────────────────────────────────┘
```

---

## Komponenten

### 1. Performance Analyzer (`performance_analyzer.py`)

Analysiert die letzten N Trades aus PostgreSQL:

```python
from adaptive_intensity import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(
    db_host="localhost",
    db_port=5432,
    db_name="claire_de_binare",
    db_user="claire_user",
    db_password="***",
    lookback_trades=300,
)

metrics = analyzer.analyze_recent_performance()
# → PerformanceMetrics(winrate=0.58, profit_factor=1.4, ...)
```

**Berechnete Metriken:**
- Winrate (Winning Trades / Total Trades)
- Profit Factor (Total Profit / Total Loss)
- Max Drawdown (größter Peak-to-Trough Verlust)
- Circuit Breaker Events (letzte 7 Tage)

### 2. Profile Manager (`profile_manager.py`)

Verwaltet automatische Profile-Wechsel:

```python
from adaptive_intensity import ProfileManager, RiskProfile

manager = ProfileManager(
    performance_analyzer=analyzer,
    initial_profile=RiskProfile.NEUTRAL,
    auto_adjust=True,
)

# Check und automatische Anpassung
transition = manager.check_and_adjust()

if transition:
    print(f"Profile changed: {transition.from_profile} → {transition.to_profile}")
    print(f"Reason: {transition.reason}")
```

**Transition-Gründe:**
- `UPGRADE` - Performance gut → aggressiver
- `DOWNGRADE` - Performance schlecht → konservativer
- `CIRCUIT_BREAKER` - Circuit Breaker ausgelöst → DRY
- `MANUAL` - Manueller Wechsel via API

### 3. Service (`service.py`)

Flask HTTP Service + Background Loop:

```bash
# Starten
python -m backoffice.services.adaptive_intensity.service

# Oder via Docker
docker-compose up cdb_adaptive_intensity
```

**Umgebungsvariablen:**

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=claire_de_binare
POSTGRES_USER=claire_user
POSTGRES_PASSWORD=***

# Service Config
ADAPTIVE_PORT=8004
ADAPTIVE_INITIAL_PROFILE=NEUTRAL  # DRY, NEUTRAL, WET
ADAPTIVE_AUTO_ADJUST=true
ADAPTIVE_LOOKBACK_TRADES=300
ADAPTIVE_CHECK_INTERVAL_SEC=300  # 5 Minuten
```

---

## HTTP API

### GET /status

Aktueller Status inkl. Performance-Metriken:

```bash
curl http://localhost:8004/status
```

Response:
```json
{
  "current_profile": "NEUTRAL",
  "auto_adjust": true,
  "config": {
    "signal_threshold_pct": 2.0,
    "rsi_threshold": 50.0,
    "max_exposure_pct": 0.5
  },
  "performance": {
    "trade_count": 312,
    "winrate": "58.3%",
    "profit_factor": "1.42",
    "max_drawdown": "2.1%",
    "can_upgrade": false,
    "needs_downgrade": false
  },
  "transitions_count": 3
}
```

### GET /profile

Aktuelles Risk-Profil mit Details:

```bash
curl http://localhost:8004/profile
```

Response:
```json
{
  "profile": "NEUTRAL",
  "description": "NEUTRAL mode - Balanced approach",
  "config": {
    "signal_threshold_pct": 2.0,
    "rsi_threshold": 50.0,
    "volume_multiplier": 1.0,
    "max_position_pct": 0.1,
    "max_exposure_pct": 0.5,
    "max_daily_drawdown_pct": 0.05
  }
}
```

### POST /profile/<name>

Manuell Profil setzen (Override):

```bash
# Wechsel zu WET Mode
curl -X POST http://localhost:8004/profile/WET

# Wechsel zu DRY Mode
curl -X POST http://localhost:8004/profile/DRY
```

Response:
```json
{
  "status": "profile_changed",
  "from_profile": "NEUTRAL",
  "to_profile": "WET"
}
```

### GET /transitions

Letzte 10 Profile-Transitions:

```bash
curl http://localhost:8004/transitions
```

Response:
```json
{
  "count": 3,
  "transitions": [
    {
      "timestamp": "2025-11-30T14:23:45",
      "from_profile": "NEUTRAL",
      "to_profile": "WET",
      "reason": "UPGRADE",
      "metrics": {
        "winrate": "62.5%",
        "profit_factor": "1.58",
        "max_drawdown": "2.3%",
        "trade_count": 305
      }
    },
    ...
  ]
}
```

---

## Prometheus Metriken

Alle Metriken unter `http://localhost:8004/metrics`:

### Core Metriken

```prometheus
# Current Risk Profile (0=DRY, 1=NEUTRAL, 2=WET)
adaptive_intensity_profile 1.0

# Current Winrate (0.0 - 1.0)
adaptive_intensity_winrate 0.583

# Current Profit Factor
adaptive_intensity_profit_factor 1.42

# Current Max Drawdown (0.0 - 1.0)
adaptive_intensity_max_drawdown_pct 0.021

# Number of trades analyzed
adaptive_intensity_analyzed_trades 312

# Profile transitions counter (labeled by from/to/reason)
adaptive_intensity_profile_transitions_total{from_profile="NEUTRAL",to_profile="WET",reason="UPGRADE"} 1

# Check duration histogram
adaptive_intensity_check_duration_seconds_bucket{le="0.5"} 42
```

### Grafana Alert Beispiele

```yaml
# Alert wenn Profil zu DRY wechselt (schlechte Performance)
- alert: TradingPerformanceDegraded
  expr: adaptive_intensity_profile == 0
  for: 10m
  annotations:
    summary: "Trading profile downgraded to DRY mode"

# Alert wenn Winrate unter 50% fällt
- alert: LowWinrate
  expr: adaptive_intensity_winrate < 0.5
  for: 1h
  annotations:
    summary: "Winrate below 50%: {{ $value | humanizePercentage }}"

# Alert bei hohem Drawdown
- alert: HighDrawdown
  expr: adaptive_intensity_max_drawdown_pct > 0.05
  for: 15m
  annotations:
    summary: "Max drawdown exceeded 5%: {{ $value | humanizePercentage }}"
```

---

## Integration mit anderen Services

### Signal Engine Integration

Die Signal Engine holt sich aktuelle Parameter vom Adaptive Intensity Service:

```python
import requests

# Hole aktuelles Profil
response = requests.get("http://cdb_adaptive_intensity:8004/profile")
config = response.json()["config"]

# Verwende dynamische Schwelle
signal_threshold = config["signal_threshold_pct"]
rsi_threshold = config["rsi_threshold"]

# Prüfe ob Signal generiert werden soll
if price_change_pct >= signal_threshold and rsi > rsi_threshold:
    publish_signal(...)
```

### Risk Manager Integration

Der Risk Manager holt sich Risk-Limits vom Adaptive Intensity Service:

```python
# Hole aktuelles Profil
response = requests.get("http://cdb_adaptive_intensity:8004/profile")
config = response.json()["config"]

# Verwende dynamische Risk-Limits
max_position_pct = config["max_position_pct"]
max_exposure_pct = config["max_exposure_pct"]
max_drawdown_pct = config["max_daily_drawdown_pct"]
```

---

## Workflow - Typischer 3-Tage-Block

### Tag 1-2: NEUTRAL Start

```
START → Profile: NEUTRAL (threshold=2.0%, exposure=50%)
  ├─ Performance sammeln (ca. 150 Trades)
  ├─ Winrate tracking
  └─ Drawdown monitoring
```

### Tag 2-3: Performance-basiertes Adjustment

**Szenario A: Gute Performance**
```
Winrate=62%, PF=1.6, Drawdown=2.1%
  → Upgrade zu WET
  → threshold=1.5%, exposure=60%
  → Mehr Trades, höhere Frequenz
```

**Szenario B: Schlechte Performance**
```
Winrate=48%, PF=0.9, Drawdown=5.2%
  → Downgrade zu DRY
  → threshold=3.0%, exposure=40%
  → Weniger Trades, konservativer
```

**Szenario C: Circuit Breaker**
```
Drawdown > 5% → Circuit Breaker aktiv
  → Sofort zu DRY
  → System stoppt neue Trades
  → Manuelle Review erforderlich
```

---

## Testing

Tests für Upgrade/Downgrade-Logik:

```bash
# Unit Tests
pytest tests/unit/test_adaptive_intensity.py -v

# Integration Tests (benötigt PostgreSQL)
pytest tests/integration/test_adaptive_intensity_service.py -v -m local_only
```

Beispiel-Test:

```python
def test_upgrade_criteria():
    """Test dass Upgrade bei guter Performance erfolgt"""
    metrics = PerformanceMetrics(
        timestamp=datetime.now(datetime.UTC),
        trade_count=300,
        lookback_trades=300,
        winrate=0.62,  # > 60%
        profit_factor=1.6,  # > 1.5
        max_drawdown_pct=0.025,  # < 3%
        total_pnl=1250.0,
        avg_win=45.0,
        avg_loss=28.0,
        circuit_breaker_events=0,
    )

    assert metrics.meets_upgrade_criteria() is True
```

---

## Betrieb & Monitoring

### Startup

```bash
# Via Docker Compose
docker-compose up -d cdb_adaptive_intensity

# Manuell
python -m backoffice.services.adaptive_intensity.service
```

### Logs überwachen

```bash
docker logs -f cdb_adaptive_intensity

# Achte auf:
# - "🌧️ Upgrade criteria met" (DRY → NEUTRAL)
# - "💧 Upgrade criteria met" (NEUTRAL → WET)
# - "☀️ Downgrade criteria met" (WET → NEUTRAL)
# - "🏜️ Downgrade criteria met" (NEUTRAL → DRY)
# - "🔄 PROFILE TRANSITION" (jeder Wechsel)
```

### Häufige Wartungsaufgaben

**Manuelles Override bei Incidents:**
```bash
# Sofort zu DRY wechseln (z.B. nach unerwarteten Losses)
curl -X POST http://localhost:8004/profile/DRY
```

**Performance-Check:**
```bash
# Status prüfen
curl http://localhost:8004/status | jq

# Transitions anschauen
curl http://localhost:8004/transitions | jq
```

**Auto-Adjust temporär deaktivieren:**
```bash
# ENV setzen
export ADAPTIVE_AUTO_ADJUST=false

# Service neu starten
docker-compose restart cdb_adaptive_intensity
```

---

## Troubleshooting

### Problem: "No trades found in database"

**Ursache:** Weniger als 300 Trades in PostgreSQL

**Lösung:**
- Warte bis genug Trades gesammelt (ca. 24-48h)
- Oder reduziere `ADAPTIVE_LOOKBACK_TRADES` temporär

### Problem: Profile wechselt nicht automatisch

**Check 1:** Auto-Adjust aktiviert?
```bash
curl http://localhost:8004/status | jq .auto_adjust
# → sollte "true" sein
```

**Check 2:** Genug Trades im Fenster?
```bash
curl http://localhost:8004/status | jq .performance.trade_count
# → sollte >= 300 sein
```

**Check 3:** Performance-Kriterien erfüllt?
```bash
curl http://localhost:8004/status | jq .performance
# → Check "can_upgrade" oder "needs_downgrade"
```

### Problem: Zu viele Transitions (instabil)

**Ursache:** Performance fluktuiert um Schwellenwerte

**Lösung:**
- Hysterese einbauen (in Zukunft)
- Längeres Analyse-Fenster: `ADAPTIVE_LOOKBACK_TRADES=500`
- Längeres Check-Interval: `ADAPTIVE_CHECK_INTERVAL_SEC=600` (10min)

---

## Roadmap / Future Enhancements

- [ ] Hysterese für stabilere Transitions (5% Gap zwischen Up/Downgrade)
- [ ] Sharpe Ratio als zusätzliches Gate-Kriterium
- [ ] Redis-Persistence für ProfileManager-State
- [ ] Webhook-Notifications bei Transitions
- [ ] Grafana Dashboard Template
- [ ] Automated Backtesting über historische Trades
- [ ] Machine Learning für adaptive Gate-Kriterien

---

## Compliance mit CLAUDE.md

✅ **6-Schichten-Analyse:** Performance Analyzer prüft DB (Layer 6)
✅ **Risk-Profile & Ramp-Up:** DRY → NEUTRAL → WET mit klaren Gates
✅ **Tests & Qualität:** Unit + Integration Tests, keine Quick-Hacks
✅ **ENV-Konfiguration:** Alle Parameter über ENV steuerbar
✅ **Prometheus Metriken:** Vollständige Observability
✅ **Zero-Activity Prevention:** DRY Mode als Fallback

---

## Namenskonvention: "Dry/Wet"

Die Reihenfolge "Dry/Wet" (statt "Wet/Dry") wurde bewusst gewählt, um die Progression klar zu machen:
- Start konservativ (DRY)
- Bei guter Performance → aggressiver (WET)
- Bei schlechter Performance → zurück zu DRY

**Metapher erklärt:**
- **DRY** (Trocken) = Mehr Bodenhaftung → Das System greift fester zu, handelt kontrollierter und vorsichtiger
- **WET** (Nass) = Fließen lassen → Das System lässt los, Trades fließen natürlicher, höhere Frequenz

Wie beim Autofahren: Trockene Straße = mehr Grip, sichere Kontrolle. Nasse Straße = man muss fließen lassen, aber mit Erfahrung kann man auch schneller fahren.

**Status:** ✅ **Production Ready** für Paper-Trading Phase N1

**Maintainer:** Claire de Binare Development Team
**Last Updated:** 2025-11-30
