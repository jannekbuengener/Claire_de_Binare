# Paper Trading Guide – Claire de Binaire

> **N1 Paper-Trading Runner + Scenario-Orchestrator**
> Version: 1.0 | Status: Production Ready

---

## 📋 Inhaltsverzeichnis

1. [Einführung](#1-einführung)
2. [Quick Start](#2-quick-start)
3. [Single Paper Trading Run](#3-single-paper-trading-run)
4. [Multi-Scenario Runs](#4-multi-scenario-runs)
5. [Ergebnisse verstehen](#5-ergebnisse-verstehen)
6. [Risk Profiles](#6-risk-profiles)
7. [Erweiterte Konfiguration](#7-erweiterte-konfiguration)
8. [Beispiele](#8-beispiele)

---

## 1. Einführung

### Was ist Paper Trading?

Paper Trading ermöglicht es, Handelsstrategien **ohne echtes Risiko** zu testen:
- ✅ Echte historische Marktdaten
- ✅ Echte Signal-Generierung
- ✅ Echte Risk-Engine Validierung
- ✅ **Simulierte** Order-Ausführung (kein echtes Geld)

### System-Übersicht

```
Historische Daten
        ↓
┌─────────────────┐
│ Market Data     │ (Event Log oder Mock)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Signal Engine   │ (Momentum-Strategie)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Risk Manager    │ (7-Layer-Validierung)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Paper Execution │ (Simuliert Fills)
└────────┬────────┘
         ↓
┌─────────────────┐
│ Statistics      │ (Metriken & Reports)
└─────────────────┘
```

### Hauptfunktionen

1. **Single Run** (`run-paper`) – Führt einen Paper-Trading-Run aus
2. **Multi-Scenario** (`run-scenarios`) – Vergleicht mehrere Konfigurationen
3. **Reports** – Generiert JSON, CSV, und Text-Reports
4. **Deterministic** – Gleiche Inputs → Gleiche Outputs (reproduzierbar)

---

## 2. Quick Start

### Installation

```bash
# Dependencies installieren
pip install -r requirements-dev.txt
```

### Erster Paper Run (30 Tage)

```bash
# Balanced Risk-Profile, 30 Tage
python claire_cli.py run-paper --days 30 --profile balanced

# Output:
# 📄 Paper Trading Runner initialized (strategy=momentum_v1, profile=balanced)
# 🚀 Starting paper trading run...
# 📅 Period: 2025-10-20 → 2025-11-19
# 📊 Loaded 720 market data events
# ✅ Paper trading run complete
#
# === PAPER TRADING SUMMARY ===
# Strategy: momentum_v1_balanced
# Period: 30 days
#
# Total Trades: 42
# Win Rate: 57.14%
# Total P&L: +$8,432.50
# Total Return: +8.43%
# Max Drawdown: -3.21%
#
# Reports saved to: backtest_results/
```

### Mehrere Szenarien vergleichen

```bash
# Vergleicht Conservative, Balanced, Aggressive
python claire_cli.py run-scenarios --config backtests/momentum_profiles.yaml

# Output:
# 📋 Scenario Orchestrator initialized (5 scenarios)
# 🚀 Running 5 scenarios...
# ▶️  Running scenario: Conservative Momentum
# ✅ Scenario 'Conservative Momentum' complete: 28 trades, +5.12% return
# ▶️  Running scenario: Balanced Momentum
# ✅ Scenario 'Balanced Momentum' complete: 42 trades, +8.43% return
# ...
#
# === SCENARIO COMPARISON ===
# [Comparison table]
```

---

## 3. Single Paper Trading Run

### Kommando: `run-paper`

```bash
python claire_cli.py run-paper [OPTIONS]
```

### Optionen

| Option | Beschreibung | Beispiel |
|--------|--------------|----------|
| `--days N` | Letzten N Tage simulieren | `--days 30` |
| `--from YYYY-MM-DD` | Start-Datum | `--from 2025-02-10` |
| `--to YYYY-MM-DD` | End-Datum | `--to 2025-02-15` |
| `--strategy NAME` | Strategie-Name | `--strategy momentum_v1` |
| `--profile PROFILE` | Risk-Profile | `--profile balanced` |

### Beispiele

#### Letzte 7 Tage

```bash
python claire_cli.py run-paper --days 7 --profile conservative
```

#### Spezifischer Datumsbereich

```bash
python claire_cli.py run-paper \
  --from 2025-02-01 \
  --to 2025-02-28 \
  --profile aggressive
```

#### Custom Strategie

```bash
python claire_cli.py run-paper \
  --days 14 \
  --strategy my_custom_strategy \
  --profile balanced
```

### Was passiert?

1. **Initialisierung**
   - Lädt Risk-Profile (Conservative/Balanced/Aggressive)
   - Erstellt Paper Execution Engine
   - Initialisiert Statistics-Tracker

2. **Datenladen**
   - Lädt Market Data Events aus Event Store
   - Oder nutzt Mock-Daten für Tests

3. **Pipeline-Ausführung**
   - Für jedes Market Data Event:
     - Generiert Signal (Momentum-Strategie)
     - Validiert mit Risk-Engine
     - Führt Paper-Order aus (simuliert)
     - Updated Statistics

4. **Report-Generierung**
   - Berechnet alle Metriken
   - Generiert JSON, CSV, Text-Reports
   - Speichert in `backtest_results/`

### Output

**Console-Output**:
```
📄 Paper Trading Runner initialized (strategy=momentum_v1, profile=balanced)
🚀 Starting paper trading run...
📅 Period: 2025-10-20 → 2025-11-19
📊 Loaded 720 market data events
📊 Trade closed: BTCUSDT P&L=+$312.45
📊 Trade closed: ETHUSDT P&L=-$125.30
...
✅ Paper trading run complete

=== PAPER TRADING SUMMARY ===
Strategy: momentum_v1_balanced
Period: 2025-10-20 → 2025-11-19

Performance Metrics:
--------------------------------------------------
Total Trades:              42
Winning Trades:            24
Losing Trades:             18
Win Rate:                  57.14%
Profit Factor:             1.82

P&L Metrics:
--------------------------------------------------
Total P&L:                 +$8,432.50
Total Return:              +8.43%
Average Win:               +$523.45
Average Loss:              -$287.21
Largest Win:               +$1,234.56
Largest Loss:              -$678.90

Risk Metrics:
--------------------------------------------------
Max Drawdown:              -3.21%
Peak Equity:               $108,432.50
Final Equity:              $108,432.50
Initial Equity:            $100,000.00

📁 Reports saved to backtest_results
```

**Generierte Dateien**:
```
backtest_results/
├── momentum_v1_balanced_20251119_143522_report.json     # Vollständiger Report
├── momentum_v1_balanced_20251119_143522_equity.csv      # Equity Curve
├── momentum_v1_balanced_20251119_143522_trades.csv      # Trade-History
└── momentum_v1_balanced_20251119_143522_summary.txt     # Text-Summary
```

---

## 4. Multi-Scenario Runs

### Kommando: `run-scenarios`

```bash
python claire_cli.py run-scenarios --config <yaml-file> [--output-dir <dir>]
```

### Optionen

| Option | Beschreibung | Default |
|--------|--------------|---------|
| `--config PATH` | YAML-Config mit Szenarien | **Required** |
| `--output-dir DIR` | Output-Verzeichnis | `backtest_results/scenarios` |

### Scenario Config erstellen

**Beispiel: `backtests/my_scenarios.yaml`**

```yaml
# Default-Periode (gilt für alle Szenarien ohne eigene Periode)
default_period:
  days: 30

# Szenarien-Liste
scenarios:
  # 1. Vordefiniertes Risk-Profile
  - name: "Conservative Momentum"
    strategy: "momentum_v1"
    risk_profile: "conservative"
    description: "Niedrigrisiko mit engen Stop-Loss"

  # 2. Vordefiniertes Risk-Profile
  - name: "Balanced Momentum"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    description: "Standard-Risiko"

  # 3. Vordefiniertes Risk-Profile
  - name: "Aggressive Momentum"
    strategy: "momentum_v1"
    risk_profile: "aggressive"
    description: "Höheres Risiko, größere Positionen"

  # 4. Custom Risk-Parameter
  - name: "Custom High-Win-Rate"
    strategy: "momentum_v1"
    description: "Optimiert für hohe Win-Rate"
    risk_params:
      MAX_POSITION_PCT: 0.08        # 8% pro Position
      MAX_DAILY_DRAWDOWN_PCT: 0.04  # 4% max Tagesverlust
      MAX_EXPOSURE_PCT: 0.25        # 25% Gesamt-Exposure
      STOP_LOSS_PCT: 0.01           # 1% Stop-Loss (sehr eng)

  # 5. Custom mit spezifischer Periode
  - name: "February 2025 Test"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    period:
      from: "2025-02-01"
      to: "2025-02-28"
```

### Ausführung

```bash
python claire_cli.py run-scenarios --config backtests/my_scenarios.yaml
```

### Was passiert?

1. **Config Laden**
   - Liest YAML-Datei
   - Validiert Struktur
   - Extrahiert Szenarien

2. **Szenarien Ausführen**
   - Für jedes Szenario:
     - Erstellt Runner mit spezifischen Parametern
     - Führt Paper-Trading Run aus
     - Sammelt Ergebnisse

3. **Vergleichs-Report**
   - Erstellt Comparison-Tabelle
   - Zeigt Key-Metriken für alle Szenarien
   - Speichert JSON + Text

### Output

**Console-Output**:
```
📋 Scenario Orchestrator initialized (5 scenarios)
🚀 Running 5 scenarios...

▶️  Running scenario: Conservative Momentum
📄 Paper Trading Runner initialized (strategy=momentum_v1, profile=conservative)
📅 Period: 2025-10-20 → 2025-11-19
✅ Scenario 'Conservative Momentum' complete: 28 trades, +5.12% return

▶️  Running scenario: Balanced Momentum
📄 Paper Trading Runner initialized (strategy=momentum_v1, profile=balanced)
📅 Period: 2025-10-20 → 2025-11-19
✅ Scenario 'Balanced Momentum' complete: 42 trades, +8.43% return

...

✅ All scenarios complete

=== SCENARIO COMPARISON ===
╔════════════════════════════════╦════════╦══════════╦═══════════╦══════════╦═════════════╗
║ Scenario                       ║ Trades ║ Win Rate ║ Total P&L ║ Return % ║ Max DD %    ║
╠════════════════════════════════╬════════╬══════════╬═══════════╬══════════╬═════════════╣
║ Conservative Momentum          ║     28 ║   64.29% ║  +$5,120  ║   +5.12% ║      -2.1%  ║
║ Balanced Momentum              ║     42 ║   57.14% ║  +$8,432  ║   +8.43% ║      -3.2%  ║
║ Aggressive Momentum            ║     67 ║   52.24% ║ +$12,345  ║  +12.35% ║      -5.8%  ║
║ Custom High-Win-Rate           ║     35 ║   68.57% ║  +$6,789  ║   +6.79% ║      -1.8%  ║
║ February 2025 Test             ║     38 ║   60.53% ║  +$7,234  ║   +7.23% ║      -2.9%  ║
╚════════════════════════════════╩════════╩══════════╩═══════════╩══════════╩═════════════╝

📄 Comparison report saved: backtest_results/scenarios/scenario_comparison.txt
📄 Detailed JSON saved: backtest_results/scenarios/scenario_comparison.json
```

**Generierte Dateien**:
```
backtest_results/scenarios/
├── scenario_comparison.txt                   # Vergleichs-Tabelle
├── scenario_comparison.json                  # Detaillierte Daten
├── Conservative_Momentum/
│   ├── momentum_v1_conservative_..._report.json
│   ├── momentum_v1_conservative_..._equity.csv
│   └── momentum_v1_conservative_..._trades.csv
├── Balanced_Momentum/
│   └── ...
└── Aggressive_Momentum/
    └── ...
```

---

## 5. Ergebnisse verstehen

### Report-Dateien

#### 1. JSON-Report (Vollständig)

**Datei**: `*_report.json`

```json
{
  "metadata": {
    "strategy": "momentum_v1",
    "risk_profile": "balanced",
    "period": {
      "from": "2025-10-20T00:00:00+00:00",
      "to": "2025-11-19T23:59:59+00:00"
    }
  },
  "statistics": {
    "total_trades": 42,
    "winning_trades": 24,
    "losing_trades": 18,
    "win_rate": 0.5714,
    "profit_factor": 1.82,
    "total_pnl": 8432.50,
    "total_return_pct": 8.43,
    "avg_win": 523.45,
    "avg_loss": -287.21,
    "largest_win": 1234.56,
    "largest_loss": -678.90,
    "max_drawdown_pct": -3.21,
    "peak_equity": 108432.50,
    "final_equity": 108432.50,
    "initial_equity": 100000.00
  },
  "equity_curve": [
    {
      "timestamp": "2025-10-20T00:00:00+00:00",
      "equity": 100000.00,
      "pnl": 0.0,
      "drawdown_pct": 0.0
    },
    ...
  ],
  "trades": [
    {
      "symbol": "BTCUSDT",
      "entry_time": "2025-10-20T12:34:56+00:00",
      "exit_time": "2025-10-21T08:15:30+00:00",
      "side": "BUY",
      "entry_price": 50000.0,
      "exit_price": 50625.0,
      "quantity": 0.1,
      "pnl": 312.45,
      "pnl_pct": 1.25,
      "duration_hours": 19.68
    },
    ...
  ]
}
```

#### 2. Equity Curve CSV

**Datei**: `*_equity.csv`

```csv
timestamp,equity,pnl,drawdown_pct
2025-10-20 00:00:00+00:00,100000.00,0.00,0.00
2025-10-20 01:00:00+00:00,100000.00,0.00,0.00
2025-10-20 12:34:56+00:00,100312.45,312.45,0.00
2025-10-21 08:15:30+00:00,100187.15,-125.30,-0.13
...
```

**Verwendung**: Importieren in Excel/Python für Visualisierung

```python
import pandas as pd
import matplotlib.pyplot as plt

# Equity Curve laden
df = pd.read_csv("*_equity.csv", parse_dates=["timestamp"])

# Plotten
df.plot(x="timestamp", y="equity", title="Equity Curve")
plt.show()
```

#### 3. Trades CSV

**Datei**: `*_trades.csv`

```csv
symbol,entry_time,exit_time,side,entry_price,exit_price,quantity,pnl,pnl_pct,duration_hours
BTCUSDT,2025-10-20 12:34:56+00:00,2025-10-21 08:15:30+00:00,BUY,50000.0,50625.0,0.1,312.45,1.25,19.68
ETHUSDT,2025-10-21 09:22:11+00:00,2025-10-21 15:45:30+00:00,SELL,3000.0,2962.5,1.0,-125.30,-1.25,6.39
...
```

**Verwendung**: Analyse in Excel, Jupyter Notebook

#### 4. Text-Summary

**Datei**: `*_summary.txt`

Gleicher Output wie in der Console (siehe Abschnitt 3).

### Key Metriken erklärt

| Metrik | Beschreibung | Ziel |
|--------|--------------|------|
| **Total Trades** | Anzahl abgeschlossener Trades | >30 (statistisch relevant) |
| **Win Rate** | % gewinnende Trades | >50% gut, >60% sehr gut |
| **Profit Factor** | Gewinne / Verluste Ratio | >1.5 gut, >2.0 sehr gut |
| **Total Return %** | Gesamt-Rendite | Positiv |
| **Max Drawdown %** | Größter Peak-to-Trough Verlust | <5% gut (für Balanced) |
| **Avg Win / Avg Loss** | Durchschnitt pro Trade | Avg Win > Avg Loss |

---

## 6. Risk Profiles

### Vordefinierte Profiles

Claire de Binaire bietet 3 vordefinierte Risk-Profiles:

#### 1. Conservative (Niedrigrisiko)

```yaml
risk_profile: "conservative"
```

**Parameter**:
- `MAX_POSITION_PCT: 0.05` (5% pro Position)
- `MAX_DAILY_DRAWDOWN_PCT: 0.03` (3% max Tagesverlust)
- `MAX_EXPOSURE_PCT: 0.20` (20% Gesamt-Exposure)
- `STOP_LOSS_PCT: 0.015` (1.5% Stop-Loss)

**Charakter**:
- Kleine Positionen
- Enge Stop-Loss
- Niedriger Max Drawdown
- **Ziel**: Kapitalerhalt, stetige Gewinne

#### 2. Balanced (Standard)

```yaml
risk_profile: "balanced"
```

**Parameter**:
- `MAX_POSITION_PCT: 0.10` (10% pro Position)
- `MAX_DAILY_DRAWDOWN_PCT: 0.05` (5% max Tagesverlust)
- `MAX_EXPOSURE_PCT: 0.30` (30% Gesamt-Exposure)
- `STOP_LOSS_PCT: 0.02` (2% Stop-Loss)

**Charakter**:
- Moderate Positionen
- Standard Stop-Loss
- Ausgewogenes Risiko/Rendite
- **Ziel**: Solides Wachstum mit kontrolliertem Risiko

#### 3. Aggressive (Höheres Risiko)

```yaml
risk_profile: "aggressive"
```

**Parameter**:
- `MAX_POSITION_PCT: 0.15` (15% pro Position)
- `MAX_DAILY_DRAWDOWN_PCT: 0.08` (8% max Tagesverlust)
- `MAX_EXPOSURE_PCT: 0.50` (50% Gesamt-Exposure)
- `STOP_LOSS_PCT: 0.03` (3% Stop-Loss)

**Charakter**:
- Große Positionen
- Weite Stop-Loss
- Höheres Risiko, höhere Rendite-Potential
- **Ziel**: Maximales Wachstum

### Custom Risk-Parameter

Du kannst eigene Risk-Parameter in der Scenario-Config definieren:

```yaml
scenarios:
  - name: "My Custom Profile"
    strategy: "momentum_v1"
    risk_params:
      MAX_POSITION_PCT: 0.08            # 8%
      MAX_DAILY_DRAWDOWN_PCT: 0.04      # 4%
      MAX_EXPOSURE_PCT: 0.25            # 25%
      STOP_LOSS_PCT: 0.015              # 1.5%
```

**Alle verfügbaren Parameter**:
- `MAX_POSITION_PCT` – Max Positionsgröße (% des Kapitals)
- `MAX_DAILY_DRAWDOWN_PCT` – Max Tagesverlust (% des Kapitals)
- `MAX_EXPOSURE_PCT` – Max Gesamt-Exposure (% des Kapitals)
- `STOP_LOSS_PCT` – Stop-Loss Distance (% vom Entry-Price)
- `ACCOUNT_EQUITY` – Initial Equity (wird automatisch gesetzt)

---

## 7. Erweiterte Konfiguration

### Eigene Strategie implementieren

**Schritt 1**: Strategie in `services/paper_trading_runner.py` erweitern

```python
def _generate_signal(self, market_data: Dict) -> Optional[Dict]:
    """Generate trading signal from market data."""

    # Beispiel: RSI-Strategie
    if self.strategy_name == "rsi_v1":
        rsi = market_data.get("rsi", 50)

        if rsi < 30:  # Oversold
            return {
                "symbol": market_data["symbol"],
                "side": "BUY",
                "confidence": (30 - rsi) / 30,
                "reason": f"RSI oversold ({rsi:.2f})",
                "price": market_data["price"],
            }
        elif rsi > 70:  # Overbought
            return {
                "symbol": market_data["symbol"],
                "side": "SELL",
                "confidence": (rsi - 70) / 30,
                "reason": f"RSI overbought ({rsi:.2f})",
                "price": market_data["price"],
            }

    # Default: Momentum-Strategie
    return self._momentum_strategy(market_data)
```

**Schritt 2**: Nutzen in Config

```yaml
scenarios:
  - name: "RSI Strategy"
    strategy: "rsi_v1"
    risk_profile: "balanced"
```

### Event Store Integration

**Aktuell**: Nutzt Mock-Daten für Tests

**Geplant**: Integration mit Event Store

```python
# In _load_market_data()
from backoffice.services.event_store.service import EventReader, DatabaseConnection

db = DatabaseConnection(os.getenv("DATABASE_URL"))
reader = EventReader(db)

# Load events by date range
events = reader.read_events_by_date_range(
    from_timestamp=from_date,
    to_timestamp=to_date,
    event_type="market_data"
)
```

### Custom Output-Directory

```bash
# Eigenes Output-Verzeichnis
python claire_cli.py run-scenarios \
  --config backtests/my_config.yaml \
  --output-dir my_custom_results/
```

---

## 8. Beispiele

### Beispiel 1: Quick Backtest (7 Tage)

```bash
# Teste letzte 7 Tage mit Balanced-Profile
python claire_cli.py run-paper --days 7 --profile balanced
```

**Use Case**: Schneller Sanity-Check einer Strategie

---

### Beispiel 2: Monatlicher Report

```bash
# Teste gesamten Februar 2025
python claire_cli.py run-paper \
  --from 2025-02-01 \
  --to 2025-02-28 \
  --profile balanced
```

**Use Case**: Monatliche Performance-Auswertung

---

### Beispiel 3: Risk-Profile Vergleich

**Config**: `backtests/profile_comparison.yaml`

```yaml
default_period:
  days: 30

scenarios:
  - name: "Conservative"
    strategy: "momentum_v1"
    risk_profile: "conservative"

  - name: "Balanced"
    strategy: "momentum_v1"
    risk_profile: "balanced"

  - name: "Aggressive"
    strategy: "momentum_v1"
    risk_profile: "aggressive"
```

**Ausführung**:
```bash
python claire_cli.py run-scenarios --config backtests/profile_comparison.yaml
```

**Use Case**: Finde optimales Risk-Level für deine Strategie

---

### Beispiel 4: Parameter-Optimierung

**Config**: `backtests/stop_loss_optimization.yaml`

```yaml
default_period:
  days: 30

scenarios:
  - name: "Stop-Loss 1.0%"
    strategy: "momentum_v1"
    risk_params:
      STOP_LOSS_PCT: 0.01

  - name: "Stop-Loss 1.5%"
    strategy: "momentum_v1"
    risk_params:
      STOP_LOSS_PCT: 0.015

  - name: "Stop-Loss 2.0%"
    strategy: "momentum_v1"
    risk_params:
      STOP_LOSS_PCT: 0.02

  - name: "Stop-Loss 3.0%"
    strategy: "momentum_v1"
    risk_params:
      STOP_LOSS_PCT: 0.03
```

**Ausführung**:
```bash
python claire_cli.py run-scenarios --config backtests/stop_loss_optimization.yaml
```

**Use Case**: Finde optimalen Stop-Loss-Level

---

### Beispiel 5: Position-Size Optimierung

**Config**: `backtests/position_size_test.yaml`

```yaml
default_period:
  days: 30

scenarios:
  - name: "Small Positions (5%)"
    strategy: "momentum_v1"
    risk_params:
      MAX_POSITION_PCT: 0.05

  - name: "Medium Positions (10%)"
    strategy: "momentum_v1"
    risk_params:
      MAX_POSITION_PCT: 0.10

  - name: "Large Positions (15%)"
    strategy: "momentum_v1"
    risk_params:
      MAX_POSITION_PCT: 0.15
```

**Use Case**: Finde optimale Positionsgröße

---

### Beispiel 6: Zeitraum-Analyse

**Config**: `backtests/quarterly_analysis.yaml`

```yaml
scenarios:
  - name: "Q1 2025"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    period:
      from: "2025-01-01"
      to: "2025-03-31"

  - name: "Q2 2025"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    period:
      from: "2025-04-01"
      to: "2025-06-30"

  - name: "Q3 2025"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    period:
      from: "2025-07-01"
      to: "2025-09-30"

  - name: "Q4 2025"
    strategy: "momentum_v1"
    risk_profile: "balanced"
    period:
      from: "2025-10-01"
      to: "2025-12-31"
```

**Use Case**: Vergleiche Performance über verschiedene Quartale

---

## 9. Troubleshooting

### Problem: "No market data found for period"

**Ursache**: Event Store enthält keine Daten für Zeitraum

**Lösung**:
1. Prüfe Event Store: `python claire_cli.py stats`
2. Reduziere Zeitraum: `--days 7` statt `--days 30`
3. Nutze Mock-Daten für Tests (automatisch wenn Event Store leer)

---

### Problem: "Config missing 'scenarios' key"

**Ursache**: YAML-Config fehlerhaft

**Lösung**:
Prüfe YAML-Syntax:
```yaml
scenarios:  # <-- MUSS vorhanden sein
  - name: "Test"
    ...
```

---

### Problem: Keine Trades generiert

**Ursache**: Signal-Threshold nicht erreicht

**Momentum-Strategie**:
- BUY nur bei >+3% Preis-Änderung
- SELL nur bei <-3% Preis-Änderung

**Lösung**:
1. Erhöhe Zeitraum (mehr Daten = mehr Signale)
2. Reduziere Signal-Threshold in Code
3. Nutze andere Strategie

---

### Problem: Alle Signale rejected

**Ursache**: Risk-Limits zu streng

**Lösung**:
1. Nutze weniger striktes Profile: `--profile aggressive`
2. Custom Risk-Params mit höheren Limits
3. Prüfe Logs: `python claire_cli.py run-paper --days 7` (zeigt Reject-Reasons)

---

## 10. Nächste Schritte

### Du hast Paper-Trading getestet?

**Nächste Schritte**:

1. **Optimiere Parameter**
   - Nutze Scenario-Orchestrator für systematische Tests
   - Finde beste Risk-Profile-Parameter für deine Strategie

2. **Erweitere Strategien**
   - Implementiere eigene Signal-Logik
   - Teste verschiedene Indikatoren (RSI, MACD, Bollinger Bands)

3. **Live-Vorbereitung**
   - Teste mit realen Event-Store-Daten
   - Validiere Determinismus: `python claire_cli.py validate --sequence 1 1000`
   - Prüfe Risk-Engine Performance

4. **Production-Deployment**
   - Dokumentiere finale Parameter
   - Erstelle Monitoring für Live-Trading
   - Setup Alerts für Risk-Breaches

---

## 11. Referenzen

### Verwandte Dokumentation

- **[KODEX.md](./KODEX%20–%20Claire%20de%20Binaire.md)** – System-Architektur
- **[EVENT_SOURCING_GUIDE.md](./EVENT_SOURCING_GUIDE.md)** – Event-Sourcing System
- **[CLAUDE_CODE_BRIEFING.md](./CLAUDE_CODE_BRIEFING.md)** – Developer Guide

### Code-Referenzen

- **Paper Execution**: `services/paper_execution.py`
- **Trading Statistics**: `services/trading_statistics.py`
- **Paper Trading Runner**: `services/paper_trading_runner.py`
- **Scenario Orchestrator**: `services/scenario_orchestrator.py`
- **CLI**: `claire_cli.py`

### Test-Referenzen

- **Tests**: `tests/test_paper_trading_runner.py`
- **Test-Ausführung**: `pytest -v tests/test_paper_trading_runner.py`

---

**Version**: 1.0
**Letzte Aktualisierung**: 2025-11-19
**Maintainer**: Claire de Binaire Team
**Status**: ✅ Production Ready
