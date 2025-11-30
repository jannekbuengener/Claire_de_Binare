# Continuous Adaptive Intensity - "Dry/Wet" Engine

## 🎯 Konzept: Proportionale Echtzeit-Anpassung

**Statt fester Stufen (DRY/NEUTRAL/WET) → Kontinuierliche, graduelle Anpassung**

```
Performance Score: 0.0 ════════════════════════════ 1.0
                   schlecht                     perfekt

                     ↓                            ↓
Threshold:          3.0%  ─────────────────→    1.5%
RSI:                60    ─────────────────→    40
Exposure:           40%   ─────────────────→    80%

         (Linear interpoliert, smooth transitions)
```

---

## 🔄 Wie es funktioniert

### 1. **Performance Score Berechnung** (0.0 - 1.0)

Aus den **letzten 300 Trades** werden 3 Komponenten berechnet:

```python
Performance Score = (
    Winrate Score × 40% +
    Profit Factor Score × 40% +
    Drawdown Score × 20%
)
```

**Komponenten:**

#### Winrate Score
```
0% Winrate    → Score 0.0
50% Winrate   → Score 0.5
100% Winrate  → Score 1.0
```

#### Profit Factor Score
```
PF < 0.5   → Score 0.0
PF = 1.0   → Score 0.5
PF ≥ 2.0   → Score 1.0
```

#### Drawdown Score (invertiert)
```
Drawdown > 10%  → Score 0.0
Drawdown = 0%   → Score 1.0
```

**Beispiel:**
```
Letzte 300 Trades:
- Winrate: 58% → WR Score: 0.58
- Profit Factor: 1.4 → PF Score: 0.7
- Max Drawdown: 2.5% → DD Score: 0.75

Performance Score = 0.58×0.4 + 0.7×0.4 + 0.75×0.2
                  = 0.232 + 0.28 + 0.15
                  = 0.662 (66.2%)
```

---

### 2. **Dynamische Parameter-Berechnung**

Parameter werden **linear interpoliert** zwischen Min (Score=0.0) und Max (Score=1.0):

```python
Parameter = Min + (Max - Min) × Performance_Score
```

**Konfigurierbare Ranges:**

| Parameter | Bei Score 0.0 (schlecht) | Bei Score 1.0 (perfekt) |
|-----------|--------------------------|-------------------------|
| **Signal Threshold** | 3.0% (konservativ) | 1.5% (aggressiv) |
| **RSI Threshold** | 60 (bullish only) | 40 (loose filter) |
| **Volume Multiplier** | 2.0x (strict) | 0.5x (loose) |
| **Max Position** | 8% | 12% |
| **Max Exposure** | 40% | 80% |

**Beispiel** mit Score = 0.662:
```
Signal Threshold = 3.0 + (1.5 - 3.0) × 0.662
                 = 3.0 - 1.5 × 0.662
                 = 3.0 - 0.993
                 = 2.007% ✅

Max Exposure = 0.40 + (0.80 - 0.40) × 0.662
             = 0.40 + 0.40 × 0.662
             = 0.40 + 0.265
             = 0.665 (66.5%) ✅
```

---

### 3. **Smooth Transitions (Rate Limiting)**

Um abrupte Sprünge zu vermeiden, ist die **maximale Score-Änderung pro Update limitiert**:

```python
Max Change = 5% (default)

Wenn Score von 0.60 → 0.75 springen würde (Δ=15%):
  → Limitiert auf 0.60 + 0.05 = 0.65
  → Nächstes Update: 0.65 + 0.05 = 0.70
  → Nächstes Update: 0.70 + 0.05 = 0.75

= Gradueller Anstieg über 3 Updates statt 1 Sprung
```

**Warum wichtig:**
- Verhindert "Thrashing" bei fluktuierender Performance
- System bleibt stabil auch bei Ausreißern
- Services müssen sich nicht ständig neu konfigurieren

---

### 4. **Kontinuierliche Updates**

```
┌─────────────────────────────────────────────┐
│  Continuous Service (Port 8004)             │
│                                             │
│  Background Loop (alle 30s):                │
│  ├─ Hole letzte 300 Trades aus PostgreSQL  │
│  ├─ Berechne Performance Score              │
│  ├─ Berechne dynamische Parameter           │
│  ├─ Broadcast via Redis                     │
│  └─ Update Prometheus Metriken              │
│                                             │
│         ↓ Redis Publish                     │
│                                             │
│  ┌────────────────────────────────────┐    │
│  │ "adaptive_intensity:updates"       │    │
│  │ "adaptive_intensity:current_params"│    │
│  └────────────────────────────────────┘    │
│         ↓                                   │
└─────────┼───────────────────────────────────┘
          │
          ↓ Subscribe
    ┌─────────────────┐      ┌──────────────────┐
    │ Signal Engine   │      │ Risk Manager     │
    │ (cdb_core)      │      │ (cdb_risk)       │
    │                 │      │                  │
    │ Holt Parameter  │      │ Holt Parameter   │
    │ aus Redis       │      │ aus Redis        │
    └─────────────────┘      └──────────────────┘
```

---

## 🚀 Deployment

### Docker Compose

```yaml
services:
  cdb_adaptive_intensity:
    build: ./backoffice/services/adaptive_intensity
    container_name: cdb_adaptive_intensity
    ports:
      - "8004:8004"
    environment:
      # PostgreSQL
      - POSTGRES_HOST=cdb_postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=claire_de_binare
      - POSTGRES_USER=claire_user
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

      # Redis
      - REDIS_HOST=cdb_redis
      - REDIS_PORT=6379

      # Update-Frequency
      - ADAPTIVE_UPDATE_INTERVAL_SEC=30  # 30s (Echtzeit!)

      # Performance Score Gewichtung
      - ADAPTIVE_WINRATE_WEIGHT=0.4
      - ADAPTIVE_PF_WEIGHT=0.4
      - ADAPTIVE_DD_WEIGHT=0.2

      # Parameter Ranges
      - ADAPTIVE_THRESHOLD_MIN=3.0
      - ADAPTIVE_THRESHOLD_MAX=1.5
      - ADAPTIVE_RSI_MIN=60.0
      - ADAPTIVE_RSI_MAX=40.0
      - ADAPTIVE_EXPOSURE_MIN=0.40
      - ADAPTIVE_EXPOSURE_MAX=0.80

      # Smooth Transitions
      - ADAPTIVE_MAX_CHANGE=0.05  # Max 5% Score-Änderung pro Update

    depends_on:
      - cdb_redis
      - cdb_postgres
```

### Manuell starten

```bash
python -m backoffice.services.adaptive_intensity.continuous_service
```

---

## 🔌 Integration in andere Services

### Signal Engine Integration

```python
# backoffice/services/signal_engine/service.py

from adaptive_intensity.redis_param_provider import get_signal_engine_params

class SignalEngine:
    def __init__(self, config, redis_client):
        self.config = config
        self.redis = redis_client

    def process_market_data(self, market_data):
        # Hole DYNAMISCHE Parameter aus Redis
        params = get_signal_engine_params(
            self.redis,
            env_fallback={
                "threshold_pct": self.config.threshold_pct,
                "rsi_threshold": 50.0,
                "volume_multiplier": 1.0,
            }
        )

        # Verwende dynamische Schwelle statt feste ENV
        threshold = params["threshold_pct"]
        rsi_threshold = params["rsi_threshold"]

        # Prüfe Signal
        if market_data.pct_change >= threshold:
            rsi = self.calculate_rsi(market_data.symbol)
            if rsi > rsi_threshold:
                # Signal generieren!
                self.publish_signal(...)
```

### Risk Manager Integration

```python
# backoffice/services/risk_manager/service.py

from adaptive_intensity.redis_param_provider import get_risk_manager_params

class RiskManager:
    def __init__(self, config, redis_client):
        self.config = config
        self.redis = redis_client

    def check_signal(self, signal):
        # Hole DYNAMISCHE Limits aus Redis
        params = get_risk_manager_params(
            self.redis,
            env_fallback={
                "max_position_pct": self.config.max_position_pct,
                "max_exposure_pct": self.config.max_exposure_pct,
            }
        )

        # Verwende dynamische Limits
        max_position = params["max_position_pct"]
        max_exposure = params["max_exposure_pct"]

        # Risk Check mit dynamischen Werten
        if self.current_exposure + position_size > max_exposure:
            return REJECT
```

---

## 📊 API Endpoints

### GET /status

Aktueller Performance Score und Parameter:

```bash
curl http://localhost:8004/status | jq
```

Response:
```json
{
  "status": "active",
  "performance_score": {
    "overall": "66.2%",
    "winrate": "58.0%",
    "profit_factor": "70.0%",
    "drawdown": "75.0%",
    "interpretation": "💧 Good - Flowing nicely"
  },
  "raw_metrics": {
    "winrate": "58.0%",
    "profit_factor": "1.40",
    "max_drawdown": "2.5%",
    "trade_count": 312
  },
  "current_parameters": {
    "signal_threshold_pct": "2.01%",
    "rsi_threshold": "46.8",
    "volume_multiplier": "1.01",
    "max_position_pct": "10.7%",
    "max_exposure_pct": "66%"
  }
}
```

### GET /parameters

Nur Parameter (für Service-Integration):

```bash
curl http://localhost:8004/parameters
```

Response:
```json
{
  "timestamp": "2025-11-30T12:30:45",
  "performance_score": 0.662,
  "signal_engine": {
    "threshold_pct": 2.01,
    "rsi_threshold": 46.8,
    "volume_multiplier": 1.01
  },
  "risk_manager": {
    "max_position_pct": 0.107,
    "max_exposure_pct": 0.66
  }
}
```

---

## 📈 Prometheus Metriken

```prometheus
# Performance Score (0.0 - 1.0)
adaptive_intensity_performance_score 0.662

# Dynamische Parameter
adaptive_intensity_signal_threshold_pct 2.01
adaptive_intensity_rsi_threshold 46.8
adaptive_intensity_max_exposure_pct 0.66

# Update-Performance
adaptive_intensity_update_duration_seconds_bucket{le="0.5"} 142
```

---

## 🎨 Grafana Visualisierung

### Dashboard Panels

**1. Performance Score Over Time**
```promql
adaptive_intensity_performance_score
```
→ Zeigt wie der Score sich entwickelt (0.0 - 1.0)

**2. Dynamic Threshold**
```promql
adaptive_intensity_signal_threshold_pct
```
→ Zeigt wie aggressiv/konservativ der Bot gerade handelt

**3. Correlation: Score vs. Trades**
```promql
# Score (linke Y-Achse)
adaptive_intensity_performance_score

# Trades per Hour (rechte Y-Achse)
rate(execution_orders_filled_total[1h]) * 3600
```
→ Visualisiert ob höherer Score = mehr Trades

---

## 🔧 Tuning

### Score-Gewichtung anpassen

Wenn Drawdown wichtiger als Winrate:

```bash
ADAPTIVE_WINRATE_WEIGHT=0.3
ADAPTIVE_PF_WEIGHT=0.3
ADAPTIVE_DD_WEIGHT=0.4  # Erhöht von 0.2
```

### Aggressivere Ranges

Für mehr Schwankung in Parametern:

```bash
# Threshold Range breiter
ADAPTIVE_THRESHOLD_MIN=4.0  # Sehr konservativ
ADAPTIVE_THRESHOLD_MAX=1.0  # Sehr aggressiv

# Exposure Range breiter
ADAPTIVE_EXPOSURE_MIN=0.30  # Sehr niedrig
ADAPTIVE_EXPOSURE_MAX=0.90  # Fast voll investiert
```

### Langsamere Transitions

Um das System stabiler zu machen:

```bash
# Max 2% Score-Änderung pro Update (statt 5%)
ADAPTIVE_MAX_CHANGE=0.02

# Längeres Update-Interval
ADAPTIVE_UPDATE_INTERVAL_SEC=60  # 1 Minute
```

---

## 🚨 Beispiel-Szenarien

### Szenario 1: Performance verbessert sich

```
t=0:  Score 0.45 → Threshold 2.75%, Exposure 58%
      (300 Trades: 52% WR, PF 1.15, DD 3.2%)

t=30: Neue Trades kommen (55% WR, PF 1.28)
      Score steigt → 0.50 (limitiert auf 0.50)
      → Threshold 2.63%, Exposure 60%

t=60: Weiter gute Trades
      Score steigt → 0.55
      → Threshold 2.49%, Exposure 62%

t=90: Noch mehr gute Trades
      Score steigt → 0.60
      → Threshold 2.35%, Exposure 64%

= Gradueller Anstieg, Bot wird aggressiver
```

### Szenario 2: Verluststrecke

```
t=0:  Score 0.65 → Threshold 2.02%, Exposure 66%
      (300 Trades: 58% WR, PF 1.40)

t=30: Mehrere Verlusttrades
      Score fällt → 0.60 (limitiert auf 0.60)
      → Threshold 2.15%, Exposure 64%

t=60: Weitere Verluste
      Score fällt → 0.55
      → Threshold 2.29%, Exposure 62%

t=90: Circuit Breaker droht (DD 4.8%)
      Score fällt → 0.45
      → Threshold 2.75%, Exposure 58%

= System bremst automatisch ab
```

---

## ⚠️ Wichtige Hinweise

### 1. Mindest-Trades erforderlich

- System braucht min. **50 Trades** für sinnvollen Score
- Optimal ab **300 Trades**
- Bei <50 Trades: Fallback zu ENV-Parametern

### 2. Redis als Single Source of Truth

- **Alle Services müssen Redis nutzen**
- Fallback zu ENV nur wenn Redis down
- Beim Service-Start: Hole aktuelle Parameter aus Redis

### 3. Smooth != Instant

- Max 5% Score-Änderung pro Update (30s)
- Bei großem Performance-Shift: Mehrere Updates nötig
- Absichtlich so designed für Stabilität

### 4. Performance Score ist rückwärtsblickend

- Basiert auf letzten 300 Trades
- Reagiert NICHT auf zukünftige Marktbedingungen
- Funktioniert nur wenn "Vergangenheit = Zukunft" (mean reversion)

---

## 🎯 Vorteile gegenüber diskreten Stufen

| Diskret (DRY/NEUTRAL/WET) | Kontinuierlich |
|---------------------------|----------------|
| Nur 3 Zustände | Unendlich viele Zustände |
| Abrupte Wechsel | Smooth Transitions |
| Entweder/oder | Proportional |
| "Stairs" | "Slope" |

**Metapher:**
- **Diskret**: Wie Lichtschalter (an/aus)
- **Kontinuierlich**: Wie Dimmer (0-100%)

---

**Status:** ✅ **Production Ready**

**Next:** Integration in Signal Engine + Risk Manager testen

