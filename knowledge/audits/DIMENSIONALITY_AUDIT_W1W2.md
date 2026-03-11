# Dimensionality Audit (Week 1-2)

**Kontext:** Issue #128 - BSDE vs. Stochastic Control Framework Selection
**Entscheidung:** Hybrid HJB baseline + selective BSDE track
**Ziel:** Feststellen, welche Dimensionalität (d) wir tatsächlich handhaben müssen

---

## Audit-Checkliste

### 1. Risk Model State Space Mapping

**Ziel:** Jede Komponente des Risk Models auf State Variables abbilden

#### 1.1 Position State (Portfolio Holdings)
- [ ] Anzahl aktiver Symbole/Instrumente (n_symbols)
- [ ] Pro Symbol: Position Size (long/short)
- [ ] Pro Symbol: Entry Price, Current P&L
- [ ] **Dimensionen:** d_positions = n_symbols × 3 (size, entry, pnl)

#### 1.2 Market State (Observable Variables)
- [ ] Pro Symbol: Current Price, Bid/Ask Spread
- [ ] Pro Symbol: Volatility (realized/implied)
- [ ] Pro Symbol: Volume, Liquidity Proxy
- [ ] Market Regime Indicator (1d: bull/neutral/bear)
- [ ] **Dimensionen:** d_market = n_symbols × 4 + 1

#### 1.3 Risk Metrics State
- [ ] Portfolio-Level: Total Exposure, Net Delta, VaR
- [ ] Portfolio-Level: Sharpe, Sortino, Max Drawdown (trailing)
- [ ] Per-Position: Position-level VaR, Contribution to Portfolio Risk
- [ ] **Dimensionen:** d_risk = 3 (portfolio) + n_symbols × 2 (per-position)

#### 1.4 Signal State (Features for Decision)
- [ ] Signal Service Output: Anzahl Features pro Symbol
- [ ] Market Classifier Output: Regime Probabilities (n_regimes)
- [ ] Optimizer Output: Recommended Weights (n_symbols)
- [ ] **Dimensionen:** d_signal = n_symbols × n_features + n_regimes + n_symbols

#### 1.5 Temporal State (History Dependence)
- [ ] Windowed History: Benötigen wir t-1, t-2, ... t-k Zustände?
- [ ] Autocorrelation: Kann History in weniger Dims komprimiert werden (z.B. PCA)?
- [ ] **Dimensionen:** d_temporal = d_total × k (falls k Zeitschritte nötig)

---

### 2. Dimensionality Reduction Opportunities

**Ziel:** Identifiziere, wo wir d senken können ohne Informationsverlust

#### 2.1 Natürliche Dekomposition
- [ ] **Sector Clustering:** Können wir Portfolio in Sektoren zerlegen, die unabhängig optimiert werden?
  - Beispiel: 50 Symbole in 5 Sektoren → 5 × 10d Probleme statt 1 × 50d Problem
- [ ] **Time-Scale Separation:** Kurzfristige vs. langfristige Entscheidungen entkoppelt?
  - Beispiel: Intraday Execution (5d) + Daily Rebalance (20d) statt gemeinsam (25d)
- [ ] **Feature Selection:** Welche Signal-Features sind redundant? (Korrelation > 0.9?)

#### 2.2 Dimensionality Budget
- [ ] Best Case: d_min = ? (nach maximaler Reduktion)
- [ ] Worst Case: d_max = ? (falls keine Reduktion möglich)
- [ ] Realistic Case: d_realistic = ? (praktikabel mit vertretbarem Aufwand)

---

### 3. Framework Selection Thresholds

**Entscheidungsbaum basierend auf d:**

#### 3.1 HJB-Dominated Region (d ≤ 10)
- [ ] Prüfe: Fällt unser d_realistic in diesen Bereich?
- [ ] Falls ja: HJB ist erste Wahl (mature tooling, interpretierbar)
- [ ] Libraries: scipy.optimize, FEniCS, OR-Tools

#### 3.2 Hybrid Region (10 < d ≤ 20)
- [ ] HJB für Subsysteme (nach Dekomposition)
- [ ] BSDE für nicht-Markovian Cases (falls Geschichte wichtig)
- [ ] Prototyping: Beide Ansätze parallel testen

#### 3.3 BSDE-Dominated Region (d > 20)
- [ ] Prüfe: Ist d wirklich > 20 NACH Reduktion?
- [ ] Falls ja: BSDE wird notwendig (HJB nicht mehr tractable)
- [ ] Team-Skill-Gap: Brauchen wir ML Engineers + Stochastic Calculus Expert?

---

### 4. Data Collection for Audit

**Was brauchen wir, um obige Checkliste auszufüllen?**

#### 4.1 Codebase Inventory
- [ ] `services/signal/`: Wie viele Features werden produziert? (Dimensionality des Signal Space)
- [ ] `services/risk/`: Welche Metriken werden getrackt? (Dimensionality des Risk State)
- [ ] `services/execution/`: Welche Position-Variablen werden gehalten? (Portfolio State Dim)
- [ ] `services/market/`: Wie viele Market Variables pro Symbol? (Market State Dim)

#### 4.2 Config Files
- [ ] `.env.example` / Configs: Anzahl Symbole im Universum (n_symbols)
- [ ] Signal Config: n_features, n_regimes
- [ ] Risk Config: VaR Window, Trailing Windows (→ temporal dimensionality)

#### 4.3 Historical Data
- [ ] Backtest Logs: Wie viele Symbole waren durchschnittlich aktiv?
- [ ] Feature Correlation Matrix: Welche Features sind redundant?

---

### 5. Deliverables (Week 1-2)

- [ ] **Tabelle:** State Space Mapping (Component → Dimensionality → Reduction Potential)
- [ ] **Zahl:** d_min, d_realistic, d_max
- [ ] **Entscheidung:** Fällt d_realistic in HJB-Region (≤10), Hybrid-Region (10-20), oder BSDE-Region (>20)?
- [ ] **Risk Assessment:** Falls d > 10, was ist das Risiko, wenn wir trotzdem HJB versuchen?
- [ ] **Recommendation:** Go/No-Go für BSDE Investment basierend auf d_realistic

---

## Nächste Schritte (Post-Audit)

### Falls d ≤ 10:
→ Week 3-4: HJB Prototype (3D Black-Scholes Toy Problem)
→ Week 5-6: Production HJB Implementation

### Falls 10 < d ≤ 20:
→ Week 3-4: Prototype Shootout (HJB vs. BSDE auf Toy Problem)
→ Week 5-6: Hybrid Architecture Decision

### Falls d > 20:
→ Week 3-4: BSDE Prototype + Team Skill Assessment
→ Week 5-6: Investment Decision (2x Headcount + 6-12 Monate Ramp-Up justified?)
