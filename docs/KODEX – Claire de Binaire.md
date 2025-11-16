# 🧭 KODEX – Claire de Binaire

**Version:** 1.0  
**Geltungsbereich:** Gesamtes Projekt „Claire de Binaire“ – Architektur, Betrieb, Doku, Automationen  
**Ziel:** Einheitlicher Entscheidungsrahmen für Architektur, Sicherheit, Risiko, Betrieb und Kommunikation.

---

## 1️⃣ Identität & Zweck

- **Name:** Der Bot heißt konsequent **„Claire de Binaire“** – intern wie extern.  
  *„MEXC Momentum Bot“ ist nur eine beschreibende Unterzeile, kein Projektname.*   
- **Domäne:** Vollautonomer, KI-gestützter **Momentum-Trading-Bot** für **Krypto** (MEXC Futures, perspektivisch erweiterbar).   
- **Zielbild:** Technisch sauberes, lokal betreibbares Handelssystem mit maximaler Transparenz und Revisionssicherheit – **nicht** Produkt-SaaS, keine Fremdabhängigkeiten.   

---

## 2️⃣ Unverhandelbare Prinzipien

1. **Sicherheit vor Profit**
   - Capital Preservation > Rendite-Jagd.
   - API-Keys **ohne Withdrawal-Rechte**, idealerweise IP-gebunden.   
   - Keine automatischen Fiat-Transfers, kein Banking im Core.

2. **Determinismus statt Blackbox**
   - Entscheidungen folgen dokumentierten Regeln (ENV-Parameter + Logik), keine undurchsichtigen ML-Experimente im kritischen Pfad.   
   - ML/Sentiment ggf. als **optionale Layer**, niemals als alleinige Entscheidungsinstanz.

3. **Lokal vor Cloud**
   - System ist vollständig lokal lauffähig (Docker, Redis, Postgres, Prom/Grafana).  
   - Keine versteckte Telemetrie, keine Producer-Only-Cloud-Services.   

4. **Klarheit vor Komplexität**
   - Jede Komponente hat **eine** Verantwortung (Single Responsibility).   
   - Kommunikation ausschließlich über definierte Topics (`market_data`, `signals`, `orders`, `order_results`, `alerts`, `health`).   

5. **Transparenz vor Magie**
   - Jeder Trade ist nachvollziehbar: **Input-Daten, Signale, Risk-Entscheidung, Order-Result, Alerts** werden geloggt und persistiert.   

---

## 3️⃣ Architektur-Kodex

### 3.1 Architektur-Topologie

- Referenz-Pfad:  
  `MEXC → Datenfeed → Signal-Engine → Risikomanager → Execution → Persistenz + Alerts → Dashboard`   
- Alle Services laufen als **Docker-Container**, orchestriert über `docker-compose` (Standard) – ein Service pro Container.   

### 3.2 Message-Bus & Topics

- **Bus:** Redis Pub/Sub ist der kanonische Message-Bus.  
- Verbindliche Topics:   
  - `market_data` → Marktdaten-Events (Candles, Volume, Movers)  
  - `signals` → Handelssignale der Strategy/Signal-Engine  
  - `orders` → geprüfte Aufträge vom Risikomanager  
  - `order_results` → Fills, Fees, Status  
  - `alerts` → Risk-/System-Alerts (Critical/Warning/Info)  
  - `health` → Heartbeats & Meta-Infos der Services  

- **Direkte HTTP-Calls zwischen Services sind tabu** (außer Health-/Status-Endpunkte).

### 3.3 Persistenz & Monitoring

- Persistenz: **PostgreSQL** ist Standard-DB; SQLite nur in isolierten Experimenten oder Tools.   
- Alle relevanten Entitäten (Signals, Orders, Trades, Risk-Events) werden persistiert.   
- Monitoring: Prometheus + Grafana sind gesetzt; Health-Checks und Metrics-Endpunkte sind Pflicht für alle Kernservices.   

### 3.4 Deployment & Rebuild

- Deployment: **Compose-first** Strategie, dokumentiert im Rebuild-Kit (PowerSquad / REBUILD_KIT).   
- Rebuild:  
  - Infrastruktur (Redis, Postgres, Prom/Grafana) → Core-Services → Screener/Extras.  
  - Rebuild dauert ~10 Minuten, muss idempotent sein (`docker compose up -d`).

---

## 4️⃣ Risk- & Kapital-Kodex

### 4.1 Treasury & Kapitalabschirmung

- **Trennung Trading vs. Treasury:**  
  - Trading-Core arbeitet ausschließlich mit begrenzter Hot-Wallet (z. B. 5–10 % des Gesamtkapitals).  
  - Hauptkapital liegt in Cold-Wallet / Custody, außerhalb der Reichweite des Bots.   
- Kein Zugriff des Bots auf Bank-APIs oder Fiat-Transaktionen.

### 4.2 Risk-Parameter (ENV-gesteuert)

Aus `.env` / Risk-Logik:   

- `MAX_POSITION_PCT` – max. Kapitalanteil pro Trade  
- `MAX_EXPOSURE_PCT` – max. Gesamt-Exposure  
- `MAX_DAILY_DRAWDOWN_PCT` – Circuit Breaker pro Tag  
- `STOP_LOSS_PCT` – Stop-Loss pro Position  
- `LOOKBACK_MINUTES` – Momentum-Fenster

**Regel:**  
- Risk-Variablen sind **Single Source of Truth**; Änderungen nur über ENV + Dokumentation, niemals hart im Code.

### 4.3 Priorisierte Schutzschichten

Reihenfolge ist verbindlich:   

1. **Daily Drawdown** → Handel stoppen, Positionen schließen, CRITICAL Alert.  
2. **Abnormale Märkte** → Circuit Breaker (Pause), WARNING Alert.  
3. **Datenstille** → Handelsloop pausieren, Alert.  
4. **Exposure-Limits** → keine neuen Orders.  
5. **Positionsgröße** → trimmen oder ablehnen.  
6. **Stop-Loss** → Exit auf Positionsebene.

---

## 5️⃣ Betriebs- & Qualitätskodex

### 5.1 Test- und Qualitätsregeln

- **End-to-End-Test** (E2E-Guide ist verpflichtend):  
  - MEXC WS → Screener → Redis → Signal → Risk → Postgres – alles wird durchlaufen.   
- Kein Live-Betrieb ohne:  
  - Bestehen des E2E-Te
