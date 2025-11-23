# Prompt für nächsten Chat - Claire de Binare

**Datum**: 2025-11-23
**Letzter Stand**: Lokale Test-Suite vollständig implementiert und funktionsfähig

---

## 🎯 Kontext für nächsten Chat

Hallo! Ich arbeite am **Claire de Binare** Projekt - einem autonomen Krypto-Trading-Bot. Die lokale Test-Suite wurde gerade vollständig implementiert und alle Tests laufen erfolgreich.

### Aktueller System-Status:

✅ **57 lokale Tests funktionieren** (5:37 min Laufzeit)
- 8 CLI-Tools Tests
- 5 Backup & Recovery Tests
- 4 Chaos/Resilience Tests
- 13 Mock Executor Tests
- 12 Portfolio Manager Tests
- 6 Docker Lifecycle Tests
- 4 Full System Stress Tests
- 5 Analytics Performance Tests

✅ **Docker Compose**: 9/9 Container healthy
✅ **PostgreSQL**: 5 Tabellen (signals, orders, trades, positions, portfolio_snapshots)
✅ **Redis**: Message Bus operational
✅ **Test-Infrastruktur**: pytest.ini, Makefile, Fixtures vollständig

---

## 📋 Wichtige Dateien zum Lesen

**Vor dem Start bitte lesen:**

1. **SESSION_SUMMARY_2025_11_23.md** - Vollständige Zusammenfassung der letzten Session
   - Pfad: `backoffice/docs/testing/SESSION_SUMMARY_2025_11_23.md`
   - Inhalt: Alle 57 Tests, Bug-Fixes, Troubleshooting-Guide
   - Wichtig: Changelog mit Unicode-Fix, Schema-Fix, Import-Fixes

2. **CLAUDE.md** - Haupt-Briefing für KI-Agenten
   - Pfad: `CLAUDE.md`
   - Inhalt: Projektstruktur, Arbeitsweisen, Goldene Regeln

3. **PROJECT_STATUS.md** - Live-Status des Projekts
   - Pfad: `backoffice/PROJECT_STATUS.md`
   - Inhalt: Aktuelle Phase (N1 Paper-Test), Container-Status

---

## 🔧 Lokale Entwicklungs-Umgebung

**System**: Windows 11 mit PowerShell
**Python**: 3.12.10
**Docker**: Docker Desktop (9 Container)

**Wichtige Commands:**

```powershell
# Alle lokalen Tests ausführen
pytest -v -m local_only tests/local/
# → 57 passed, 1 skipped in ~5:37 min

# Docker Status
docker compose ps
# → Sollte 9/9 healthy zeigen

# Git Status
git status
# → Aktuell auf: main (oder Feature-Branch)
```

---

## ⚠️ Wichtige Hinweise (Aus letzter Session)

### Windows-Spezifisch:
1. **Keine Unicode-Emojis** in Python-Scripts (cp1252 Encoding-Problem)
2. **PowerShell-Commands** verwenden (nicht Bash)
3. **Backslash-Pfade** bei Dateipfaden: `tests\local\test_*.py`

### PostgreSQL Schema:
- Tabelle `portfolio_snapshots` hat Spalten:
  - `available_balance` (NICHT `cash`)
  - `open_positions` (NICHT `num_positions`)
  - `total_exposure_pct` ist numeric(5,4) (max 1.0)

### Import-Pfade:
- **Immer** `sys.path` zu Projekt-Root setzen: `Path(__file__).parent.parent.parent`
- **Vollständige Imports**: `from backoffice.services.execution_service.mock_executor import MockExecutor`

---

## 🚀 Mögliche nächste Aufgaben

### Option 1: DeprecationWarnings fixen (8-10h)
**Ziel**: `datetime.utcnow()` → `datetime.now(datetime.UTC)` in allen Services

**Betroffene Dateien:**
- `backoffice/services/execution_service/mock_executor.py` (Zeilen 89, 109)
- `backoffice/services/portfolio_manager/models.py` (Zeilen 60, 33)
- `backoffice/services/portfolio_manager/portfolio_manager.py` (Zeilen 99, 330)

**Aufwand**: ~2h (6 Dateien, ~10 Änderungen)
**Nutzen**: Zukunftssicher für Python 3.13+

---

### Option 2: query_analytics.py Bug fixen (2-3h)
**Ziel**: Crash bei Zeile 222 beheben

**Problem**: Test `test_analytics_query_tool_integration` wird geskippt wegen Bug

**Status**: Bekannter Bug, aber nicht kritisch (Tool funktioniert für andere Commands)

**Aufwand**: ~2-3h
**Nutzen**: 1 zusätzlicher Test grün

---

### Option 3: Event-Sourcing Tests (8-12h)
**Ziel**: Replay-Determinismus validieren

**Neue Tests:**
- `tests/local/test_event_sourcing.py`
  - Replay-Determinismus
  - Event-Store Integrity
  - Audit-Trail Validation

**Aufwand**: ~8-12h
**Nutzen**: Sicherheit für Event-Sourcing-Architektur

---

### Option 4: Paper-Trading Scenarios (8-10h)
**Ziel**: 7-Tage-Simulationen mit verschiedenen Markt-Bedingungen

**Neue Tests:**
- `tests/scenarios/test_trending_market_7d.py`
- `tests/scenarios/test_ranging_market_7d.py`
- `tests/scenarios/test_volatile_market_7d.py`

**Aufwand**: ~8-10h
**Nutzen**: Sehr hoch (Validierung vor echtem Paper-Test)

---

### Option 5: Security-Tests (4-6h)
**Ziel**: Basis-Security-Checks

**Neue Tests:**
- `tests/local/test_security_basics.py`
  - ENV-Secrets nicht in Logs
  - Redis AUTH funktioniert
  - PostgreSQL Permissions

**Aufwand**: ~4-6h
**Nutzen**: Mittel (Nice-to-have vor Production)

---

## 📊 Git-Status (Wichtig!)

**Aktiver Branch**: `claude/create-papertest-todo-017Wt5BhYRexMTgBxWdwyegN`
**Remote**: `origin/claude/create-papertest-todo-017Wt5BhYRexMTgBxWdwyegN`

**Letzter Commit**: `4a07e06 - docs: add comprehensive session summary`

**Wichtig**: Vor dem Start:
```powershell
# Status prüfen
git status

# Wenn "behind", dann pullen
git pull

# Wenn auf main, zu Feature-Branch wechseln (optional)
git checkout claude/create-papertest-todo-017Wt5BhYRexMTgBxWdwyegN
```

---

## 🎯 Empfehlung für nächsten Chat

**Meine Empfehlung**: Option 4 (Paper-Trading Scenarios)

**Grund**:
- Höchster Business-Value
- Projekt ist in "N1 Paper-Test Implementation" Phase
- 7-Tage-Simulationen sind kritisch vor echtem Paper-Test
- Validiert komplettes System End-to-End

**Alternativen**:
- Option 1 (DeprecationWarnings) - Schnell und einfach
- Option 3 (Event-Sourcing) - Wichtig für Daten-Integrität

---

## 📝 Beispiel-Start für nächsten Chat

**Guter Start:**
```
Hallo! Ich möchte als nächstes die Paper-Trading Scenarios implementieren
(Option 4 aus NEXT_CHAT_PROMPT.md). Ich habe SESSION_SUMMARY_2025_11_23.md
und CLAUDE.md gelesen.

Aktueller Stand:
- 57 lokale Tests laufen
- Docker Compose: 9/9 healthy
- Branch: claude/create-papertest-todo-017Wt5BhYRexMTgBxWdwyegN

Kannst du mir helfen, die 7-Tage-Simulationen zu implementieren?
```

**Oder:**
```
Hi! Ich möchte die DeprecationWarnings fixen (Option 1). Alle Tests laufen,
aber es gibt 56 Warnings wegen datetime.utcnow().

Kannst du mir helfen, alle Stellen zu finden und zu fixen?
```

**Oder offen:**
```
Hallo! Ich habe SESSION_SUMMARY_2025_11_23.md gelesen. Alle 57 lokalen Tests
funktionieren. Was empfiehlst du als nächstes?
```

---

## 🔗 Wichtige Links (Intern)

**Dokumentation:**
- `backoffice/docs/testing/SESSION_SUMMARY_2025_11_23.md` - Letzte Session
- `backoffice/docs/testing/LOCAL_TEST_GAP_ANALYSIS.md` - Gap-Analyse
- `backoffice/docs/testing/TESTING_GUIDE.md` - Test-Best-Practices
- `CLAUDE.md` - KI-Agent-Protokoll

**Tests:**
- `tests/local/` - Alle 57 lokalen Tests
- `pytest.ini` - pytest-Konfiguration
- `Makefile` - Test-Targets

**Services:**
- `services/cdb_core/` - Signal Engine
- `services/cdb_risk/` - Risk Manager
- `services/cdb_execution/` - Execution Service

---

## ⚡ Quick-Troubleshooting

**Problem**: Import-Errors trotz korrekter Dateien
```powershell
pytest --cache-clear -v -m local_only tests/local/
```

**Problem**: Branch "behind" Remote
```powershell
git pull
```

**Problem**: Tests finden keine Module
```powershell
# sys.path prüfen - sollte zu Projekt-Root zeigen
# Path(__file__).parent.parent.parent
```

**Problem**: Docker-Container down
```powershell
docker compose up -d
docker compose ps
```

---

## ✅ Checkliste für nächsten Chat-Start

- [ ] `SESSION_SUMMARY_2025_11_23.md` gelesen
- [ ] `CLAUDE.md` überflogen
- [ ] Git-Status geprüft (`git status`)
- [ ] Docker-Status geprüft (`docker compose ps`)
- [ ] Tests laufen (`pytest -v -m local_only tests/local/`)
- [ ] Aufgabe ausgewählt (Option 1-5 oder eigene Idee)

**Wenn alles ✅, dann:**
→ Starte Chat mit klarer Aufgabe und aktuellem Kontext!

---

**Erstellt**: 2025-11-23
**Projekt**: Claire de Binare Cleanroom
**Phase**: N1 - Paper-Test Implementation
**Nächster Meilenstein**: 7-Tage Paper-Test

**Ende Next-Chat-Prompt**
