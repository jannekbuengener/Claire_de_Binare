# ENV-Validierungsbericht – Service-Code-Analyse

**Erstellt:** 2025-11-21
**Scope:** Abgleich Service-Code vs. ENV_CATALOG.md
**Analysierte Services:** 4 (risk_engine.py, position_sizing.py, execution_simulator.py, mexc_perpetuals.py)

---

## 📊 Übersicht

**Validierungs-Status:**
- ✅ **Katalog-Variablen im Code:** 6/9 Risk-Variablen gefunden
- ⚠️ **Naming-Inkonsistenzen:** 3 gefunden
- 📝 **Undokumentierte Variablen:** 20 gefunden (erweiterte Features)

---

## ✅ Korrekt verwendete ENV-Variablen

Diese Variablen aus ENV_CATALOG.md werden korrekt im Service-Code verwendet:

| Variable | Service | Status |
|----------|---------|--------|
| `ACCOUNT_EQUITY` | `risk_engine.py:411` | ✅ Korrekt (Default: `100000.0`) |
| `MAX_POSITION_PCT` | `risk_engine.py:412` | ✅ Korrekt (Default: `0.10`) |
| `STOP_LOSS_PCT` | `risk_engine.py:415`, `position_sizing.py:457` | ✅ Korrekt (Default: `0.02`) |

---

## ⚠️ Naming-Inkonsistenzen

Diese Variablen haben unterschiedliche Namen in Code vs. Katalog:

| Code (Service) | Katalog | Empfehlung |
|----------------|---------|------------|
| `MAX_DRAWDOWN_PCT` (`risk_engine.py:413`) | `MAX_DAILY_DRAWDOWN_PCT` | ⚠️ **Code anpassen** (Katalog ist kanonisch) |
| `MAX_EXPOSURE_PCT` (`risk_engine.py:414`) | `MAX_TOTAL_EXPOSURE_PCT` | ⚠️ **Code anpassen** (Katalog ist kanonisch) |
| `MAX_SLIPPAGE_BPS` (`risk_engine.py:416`) | `MAX_SLIPPAGE_PCT` | ⚠️ **Format-Inkonsistenz** (BPS vs. PCT) |

**Impact:**
- `MAX_DRAWDOWN_PCT` fehlt das `DAILY`-Präfix → Unklare Semantik
- `MAX_EXPOSURE_PCT` fehlt das `TOTAL`-Präfix → Missverständnisse möglich
- `MAX_SLIPPAGE_BPS` (Basis Points) vs. `MAX_SLIPPAGE_PCT` (Prozent) → Format-Konflikt (BPS = 100 = 1%)

**Empfohlene Aktion:**
1. Services auf kanonische Namen aus ENV_CATALOG.md migrieren
2. ADR für Naming-Konvention erweitern (BPS vs. PCT Klarstellung)

---

## 📝 Undokumentierte ENV-Variablen (Feature-Extensions)

Diese Variablen werden im Code verwendet, sind aber **nicht** in ENV_CATALOG.md dokumentiert:

### Position Sizing (`position_sizing.py`)
| Variable | Default | Format | Beschreibung |
|----------|---------|--------|--------------|
| `SIZING_METHOD` | `"fixed_fractional"` | String | Position-Sizing-Methode (fixed_fractional, kelly, volatility_target, atr_based) |
| `RISK_PER_TRADE` | `0.02` | Dezimal | Risk pro Trade (2%) |
| `TARGET_VOL` | `0.20` | Dezimal | Ziel-Volatilität (20%) |
| `KELLY_FRACTION` | `0.25` | Dezimal | Kelly-Fraction (25%) |
| `ATR_MULTIPLIER` | `2.0` | Float | ATR-Multiplikator |

### Execution Simulator (`execution_simulator.py`)
| Variable | Default | Format | Beschreibung |
|----------|---------|--------|--------------|
| `MAKER_FEE` | `0.0002` | Dezimal | Maker-Fee (0.02%) |
| `TAKER_FEE` | `0.0006` | Dezimal | Taker-Fee (0.06%) |
| `BASE_SLIPPAGE_BPS` | `5.0` | BPS | Basis-Slippage (5 BPS = 0.05%) |
| `DEPTH_IMPACT_FACTOR` | `0.10` | Dezimal | Depth-Impact-Faktor (10%) |
| `VOL_SLIPPAGE_MULTIPLIER` | `2.0` | Float | Volatilitäts-Slippage-Multiplikator |
| `FILL_THRESHOLD` | `0.80` | Dezimal | Fill-Threshold (80%) |
| `FUNDING_RATE` | `0.0001` | Dezimal | Funding-Rate (0.01%) |

### MEXC Perpetuals (`mexc_perpetuals.py`)
| Variable | Default | Format | Beschreibung |
|----------|---------|--------|--------------|
| `MARGIN_MODE` | `"isolated"` | String | Margin-Modus (isolated/cross) |
| `MAX_LEVERAGE` | `10` | Integer | Maximaler Leverage (10x) |
| `MIN_LIQUIDATION_DISTANCE` | `0.15` | Dezimal | Minimale Liquidations-Distanz (15%) |
| `CONTRACT_MULTIPLIER` | `0.0001` | Float | Contract-Multiplikator |
| `MAINTENANCE_MARGIN_RATE` | `0.005` | Dezimal | Maintenance-Margin-Rate (0.5%) |
| `FUNDING_RATE` | `0.0001` | Dezimal | Funding-Rate (0.01%) |
| `FUNDING_SETTLEMENT_HOURS` | `8` | Integer | Funding-Settlement-Intervall (8h) |

**Total:** 20 undokumentierte ENV-Variablen

---

## 🚨 Fehlende Variablen im Code

Diese Variablen sind in ENV_CATALOG.md dokumentiert, werden aber **nicht** im analysierten Service-Code verwendet:

| Variable | Kategorie | Service (erwartet) | Status |
|----------|-----------|-------------------|--------|
| `CIRCUIT_BREAKER_THRESHOLD_PCT` | Risk | `risk_engine.py` | ⚠️ Fehlt im analysierten Code |
| `MAX_SPREAD_MULTIPLIER` | Risk | `risk_engine.py` | ⚠️ Fehlt im analysierten Code |
| `DATA_STALE_TIMEOUT_SEC` | Risk | `cdb_ws`, `cdb_risk` | ⚠️ Fehlt im analysierten Code |

**Mögliche Gründe:**
1. Diese Variablen werden in **anderen Service-Dateien** verwendet (z.B. `cdb_risk/service.py`, `cdb_ws/service.py`)
2. Diese Features sind noch **nicht implementiert**
3. Code-Analyse unvollständig (nur 4 Dateien analysiert)

**Empfohlene Aktion:**
- Vollständige Code-Analyse durchführen (alle Services in `services/cdb_*/`)
- Implementierungs-Status für jede Katalog-Variable dokumentieren

---

## 📊 Zusammenfassung

### Nach Kategorie

| Kategorie | Katalog | Code | Status |
|-----------|---------|------|--------|
| **Risk** | 9 | 6 ✅ + 3 ⚠️ | Naming-Inkonsistenzen |
| **Position Sizing** | 0 | 5 📝 | Nicht dokumentiert |
| **Execution** | 0 | 7 📝 | Nicht dokumentiert |
| **MEXC Perpetuals** | 0 | 7 📝 | Nicht dokumentiert |
| **DB** | 6 | 0 | Nicht im analysierten Code |
| **Redis** | 4 | 0 | Nicht im analysierten Code |
| **Monitoring** | 5 | 0 | Nicht im analysierten Code |
| **Services** | 5 | 0 | Nicht im analysierten Code |
| **Trading** | 4 | 0 | Nicht im analysierten Code |
| **System** | 5 | 0 | Nicht im analysierten Code |

### Status-Übersicht

| Status | Anzahl | Beschreibung |
|--------|--------|--------------|
| ✅ **Korrekt** | 3 | Katalog-Variablen korrekt im Code verwendet |
| ⚠️ **Inkonsistent** | 3 | Naming-Abweichungen (Code vs. Katalog) |
| 📝 **Undokumentiert** | 20 | Code-Variablen nicht im Katalog |
| ❓ **Unklar** | 3 | Katalog-Variablen nicht im analysierten Code gefunden |

---

## 🎯 Empfohlene Aktionen

### Sofort (Code-Fixes)
1. **Naming-Migration in Services:**
   - `MAX_DRAWDOWN_PCT` → `MAX_DAILY_DRAWDOWN_PCT`
   - `MAX_EXPOSURE_PCT` → `MAX_TOTAL_EXPOSURE_PCT`
   - `MAX_SLIPPAGE_BPS` → `MAX_SLIPPAGE_PCT` (mit BPS-zu-PCT-Konvertierung)

2. **ENV_CATALOG.md erweitern:**
   - Position-Sizing-Variablen hinzufügen (5 Variablen)
   - Execution-Simulator-Variablen hinzufügen (7 Variablen)
   - MEXC-Perpetuals-Variablen hinzufügen (7 Variablen)

### Mittelfristig (Dokumentation)
3. **Vollständige Code-Analyse:**
   - Alle Services in `services/cdb_*/` durchsuchen
   - Implementierungs-Status für jede Katalog-Variable dokumentieren

4. **ADR für Format-Konventionen:**
   - BPS (Basis Points) vs. PCT (Prozent) Klarstellung
   - Wann BPS, wann PCT verwenden?

5. **ENV-Validierungs-Script erweitern:**
   - `check_env.ps1` um neue Variablen ergänzen
   - Range-Checks für alle 46+ Variablen

---

## 📚 Referenzen

- **ENV_CATALOG.md:** `backoffice/docs/ENV_CATALOG.md`
- **ADR-035:** ENV-Naming-Konvention → `backoffice/docs/DECISION_LOG.md`
- **Services-Analyse:** `services/*.py` (4 Dateien analysiert)

---

**Erstellt von:** Claude Code (claire-architect)
**Nächste Review:** Nach Code-Migration und ENV_CATALOG.md-Erweiterung
**Status:** ⚠️ **Aktionsbedarf** (Naming-Inkonsistenzen + 20 undokumentierte Variablen)
