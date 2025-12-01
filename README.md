Hier ist deine neue **menschenfreundliche, klare, schön lesbare README**.
Sie ist so geschrieben, dass ein neuer Mensch – ohne technische Vorarbeit – sofort versteht:

* Was das Projekt ist
* Was er tun muss
* Wo er klicken muss
* Wo die wichtigen Infos liegen

Keine KI-bezogene Sprache, keine Pipelines, kein Tech-Bullshit.
Einfach verständlich, freundlich, strukturiert.

Ich habe **nur die wirklich relevanten Dateien** verlinkt.
Alles andere fliegt konsequent raus.

---

# **README – Claire de Binare (Cleanroom Edition)**

*Einfacher Einstieg. Klare Struktur. Schneller Überblick.*

---

## 🌟 **Was ist Claire de Binare?**

Claire de Binare ist ein **autonomes Trading-System**, das aus mehreren Modulen besteht:

* **Market Data Screener**
* **Signal Engine** (Strategielogik)
* **Risk Manager** (mehrschichtige Handelskontrolle)
* **Execution Service** (Paper-Trading)
* **Monitoring** (Grafana & Prometheus)

Aktuell befindet sich das Projekt in der **N1-Phase**, also im **Paper-Test**.
Das bedeutet:
👉 **Noch keine echten Trades.**
👉 **Nur Simulation.**
👉 **Alles lokal & sicher.**

---

## 🚀 **Für alle, die neu sind – fang hier an**

Diese drei Dateien erklären dir alles, was du wissen musst:

### **1. Onboarding & Navigation**

📘 **`CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md`**
→ Der perfekte Einstieg.
→ Was liegt wo? Wie ist das Repo aufgebaut?
→ Welche Dateien wichtig sind (und welche nicht).

---

### **2. KODEX – Die Grundregeln des Systems**

📜 **`KODEX – Claire de Binare.md`**
→ Projektprinzipien
→ Architekturleitlinien
→ Sicherheitsrichtlinien
→ Warum das System so aufgebaut ist, wie es ist

---

### **3. Die aktuelle Architektur (N1 – Paper-Test)**

🏗 **`N1_ARCHITEKTUR.md`**
→ Überblick über die Services
→ Datenfluss (Events, Topics, Reihenfolge)
→ Ports, Container, Healthchecks
→ Was jetzt im Fokus steht

---

## 🔧 **Technischer Zustand – kompakter Überblick**

🏁 **Status: Cleanroom vollständig hergestellt**
📌 Phase: **N1 – Paper Test**
✔ MEXC-API-Keys eingerichtet (IP-gebunden + Handelspaare limitiert)
✔ .env sauber, sicher und clean
✔ System vollständig dokumentiert
✔ Backup-Konzept vorbereitet
✔ Tests vollständig (32 Tests: 12 Unit, 2 Integration, 18 E2E - 100% Pass Rate)
✔ Lokale Test-Suite (15 Tests: Performance, Docker Lifecycle, Stress)
⏳ Systemcheck #1 steht an

Für Details sieh dir an:

📊 **`PROJECT_STATUS.md`**
(Sehr kompakt, aber top für schnellen Überblick)

---

## 🧭 **So arbeitest du mit dem Projekt**

### **1. Relevante Dateien**

| Bereich                           | Datei                                         |
| --------------------------------- | --------------------------------------------- |
| Einstieg                          | `CLEANROOM_ONBOARDING_AND_REPO_NAVIGATION.md` |
| Regeln & Prinzipien               | `KODEX – Claire de Binare.md`                 |
| Systemdesign                      | `backoffice/docs/architecture/N1_ARCHITEKTUR.md` |
| Projekt-Fortschritt               | `backoffice/PROJECT_STATUS.md`                |
| Ablaufsteuerung (Claude → Gordon) | `backoffice/docs/runbooks/CLAUDE_GORDON_WORKFLOW.md` |
| Tests & Struktur                  | `tests/README.md`                             |
| E2E-Tests                         | `backoffice/docs/testing/LOCAL_E2E_TESTS.md`  |

---

## 🧪 **Bevor du etwas startest – kurze Checkliste**

1. `.env` ausfüllen (basierend auf `.env.template`)
2. ENV-Check ausführen
3. Docker-Services starten
4. Healthchecks prüfen
5. Tests starten (sobald fertig)

Genau erklärt in:
📄 **`tests/README.md`** und **`backoffice/docs/testing/LOCAL_E2E_TESTS.md`**

---

## 🐍 **Entwicklung starten**

```bash
python -m pip install -r requirements.txt
```

Tests ausführen:

```bash
# CI-Tests (schnell, mit Mocks)
pytest -v -m "not e2e and not local_only"

# E2E-Tests (benötigt Docker Compose)
pytest -v -m e2e

# Lokale Tests (Performance, Stress, Lifecycle)
pytest -v -m local_only
# oder: make test-local (Unix) / .\run-tests.ps1 test-local (Windows)
```

Docker:

```bash
docker compose up -d
```

---

## 📈 **Wenn du tiefer einsteigen willst**

* **Risk-Engine-Logik** → in `backoffice/services/…`
* **Event-Fluss (market_data → order_results)** → in `N1_ARCHITEKTUR.md`
* **System-Status & Aufgaben** → in `PROJECT_STATUS.md`
* **Operative Pipeline (Claude ↔ Gordon)** → `CLAUDE_GORDON_PIPELINE.md`

---

## 💬 **Kontakt & Zusammenarbeit**

* **Jannek** – Projektleitung
* **Claude** – Architektur, Code, Planung
* **Gordon** – Docker & Systemausführung (via MCP)

---

