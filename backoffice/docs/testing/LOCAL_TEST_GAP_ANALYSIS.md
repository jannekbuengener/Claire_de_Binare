# Gap Analysis: Lokale-Only Tests - Claire de Binare

**Datum**: 2025-11-23
**Analyst**: Claire Local Test Orchestrator
**Status**: 🔍 Identifikation abgeschlossen

---

## Executive Summary

Diese Analyse identifiziert **fehlende lokale-only Tests** für das Claire de Binare Trading-System. Basierend auf der Bestandsaufnahme der bestehenden Test-Infrastruktur (104 Tests total, 18 E2E-Tests) wurden **7 kritische Test-Lücken** identifiziert.

**Empfehlung**: Implementierung von 5-7 neuen Test-Suites, die speziell für lokale Systemvalidierung optimiert sind.

---

## 📊 Bestehende Test-Abdeckung

### ✅ VORHANDEN (Gut abgedeckt):

1. **Stress & Performance** (`test_full_system_stress.py`):
   - ✅ 100+ Events in 10s
   - ✅ Concurrent Event-Flows
   - ✅ Portfolio Snapshots unter Last
   - ✅ All Services unter Load

2. **Docker-Lifecycle** (`test_docker_lifecycle.py`):
   - ✅ Stop/Start/Restart Cycles
   - ✅ Service Recreate
   - ✅ Volume Persistence
   - ✅ Log Error Checking

3. **Analytics-Performance** (`test_analytics_performance.py`):
   - ✅ SQL Query Performance
   - ✅ Database Indexing
   - ✅ JSONB Search

4. **E2E Pipeline** (`tests/e2e/`):
   - ✅ Docker Compose Validation
   - ✅ Redis & PostgreSQL Integration
   - ✅ Event Flow Pipeline

---

## ❌ FEHLENDE TEST-BEREICHE

### 1. ⚠️ KRITISCH: CLI-Tools & Scripts Tests

**Status**: ❌ Nicht vorhanden

**Beschreibung**:
Es existiert `backoffice/scripts/query_analytics.py`, aber keine automatisierten Tests dafür (außer einem geskippten Test wegen Bugs).

**Was fehlt**:
- CLI-Tool Execution Tests
- Script Error-Handling
- Output-Format Validierung
- Integration mit laufendem System

**Beispiel-Test**:
```python
# tests/local/test_cli_tools.py
@pytest.mark.local_only
def test_query_analytics_last_signals():
    """Test: query_analytics.py --last-signals funktioniert"""
    result = subprocess.run(
        ["python", "backoffice/scripts/query_analytics.py", "--last-signals", "5"],
        capture_output=True,
        env={"POSTGRES_HOST": "localhost"}
    )
    assert result.returncode == 0
    assert "BTCUSDT" in result.stdout.decode()
```

**Priorität**: 🔴 HOCH (Scripts sind wichtig für manuelle Debugging)

---

### 2. ⚠️ KRITISCH: Chaos/Resilience Tests

**Status**: ⚠️ Teilweise vorhanden (nur Stop/Start, keine echten Fehler-Szenarien)

**Was fehlt**:
- **Container-Crash-Recovery**: Was passiert, wenn Redis WÄHREND eines Trades crasht?
- **Network Partitions**: Service kann PostgreSQL nicht erreichen
- **Partial Failures**: Nur 1 Service down, andere laufen
- **Cascading Failures**: Ein Service triggert Fehler in anderen

**Beispiel-Test**:
```python
# tests/local/test_chaos_resilience.py
@pytest.mark.local_only
@pytest.mark.slow
def test_redis_crash_during_signal_processing():
    """
    Chaos-Test: Redis crasht während Signal-Processing

    Validiert:
    - Services recovern automatisch
    - Keine Data-Loss
    - Events werden nach Recovery verarbeitet
    """
    # 1. Publish Signal
    publish_signal("BTCUSDT", "buy")

    # 2. KILL Redis während Processing
    subprocess.run(["docker", "compose", "kill", "cdb_redis"])

    # 3. Restart Redis
    time.sleep(5)
    subprocess.run(["docker", "compose", "start", "cdb_redis"])

    # 4. Validate: System recovered
    # 5. Check: Signal wurde verarbeitet ODER ist in Queue
```

**Priorität**: 🔴 HOCH (Production-Readiness kritisch)

---

### 3. ⚠️ Event-Sourcing & Replay Tests

**Status**: ❌ Nicht vorhanden

**Was fehlt**:
- **Replay-Determinismus**: Gleicher Event-Stream → gleicher Output?
- **Event-Store Integrity**: Sind alle Events persistent?
- **Audit-Trail Validation**: Lückenlose Nachverfolgbarkeit?
- **Time-Travel Debugging**: Replay bis zu bestimmtem Zeitpunkt

**CLAUDE.md Referenz**:
> Event-Sourcing & Replay: deterministischer Kernel mit Audit-Trail

**Beispiel-Test**:
```python
# tests/local/test_event_sourcing.py
@pytest.mark.local_only
def test_replay_determinism():
    """
    Event-Sourcing-Test: Replay ist deterministisch

    Validiert:
    - Gleicher Event-Stream
    - Gleiche Risk-Decisions
    - Gleiche Portfolio-State
    """
    # 1. Publish 10 Events
    events = generate_test_events(count=10)
    publish_events(events)

    # 2. Capture State
    state_1 = get_portfolio_state()

    # 3. Clear DB
    reset_database()

    # 4. Replay Events
    replay_events(events)

    # 5. Validate State identical
    state_2 = get_portfolio_state()
    assert state_1 == state_2
```

**Priorität**: 🟡 MITTEL (Nice-to-have, aber wichtig für Debugging)

---

### 4. ⚠️ Backup & Recovery Tests

**Status**: ❌ Nicht vorhanden

**PROJECT_STATUS.md** sagt:
> 3. **Postgres-Backup-Strategie noch nicht produktiv verankert**
>    - Konzept definiert, aber noch nicht als Script/Job umgesetzt

**Was fehlt**:
- Automated Backup-Tests
- Recovery-Tests (Restore funktioniert?)
- Data-Integrity nach Restore
- Backup-Performance (<5min für 1GB?)

**Beispiel-Test**:
```python
# tests/local/test_backup_recovery.py
@pytest.mark.local_only
@pytest.mark.slow
def test_postgres_backup_restore_cycle():
    """
    Backup-Test: PostgreSQL Backup & Restore

    Validiert:
    - Backup funktioniert
    - Restore korrekt
    - Keine Data-Loss
    """
    # 1. Baseline: Count Trades
    baseline_count = count_trades()

    # 2. Backup DB
    backup_file = backup_postgres()
    assert os.path.exists(backup_file)

    # 3. Insert new Trade
    insert_test_trade()
    assert count_trades() == baseline_count + 1

    # 4. Restore Backup
    restore_postgres(backup_file)

    # 5. Validate: Back to baseline
    assert count_trades() == baseline_count
```

**Priorität**: 🟡 MITTEL (Wichtig vor Production)

---

### 5. ⚠️ Security-Tests (Basic)

**Status**: ❌ Nicht vorhanden

**Was fehlt**:
- ENV-Secrets NICHT in Logs
- Redis AUTH funktioniert
- PostgreSQL Permissions korrekt
- No SQL Injection (in query_analytics.py)
- No Command Injection

**Beispiel-Test**:
```python
# tests/local/test_security_basics.py
@pytest.mark.local_only
def test_redis_requires_authentication():
    """
    Security-Test: Redis erfordert Passwort

    Validiert:
    - Connection ohne Password fails
    - Connection mit Password succeeds
    """
    # 1. Try without password
    try:
        client = redis.Redis(host="localhost", port=6379, password=None)
        client.ping()
        pytest.fail("Redis accepted connection without password!")
    except redis.AuthenticationError:
        pass  # Expected

    # 2. With password succeeds
    client = redis.Redis(host="localhost", port=6379, password="claire_redis_secret_2024")
    assert client.ping()

@pytest.mark.local_only
def test_secrets_not_logged():
    """
    Security-Test: Secrets erscheinen NICHT in Logs
    """
    # Check recent logs
    logs = subprocess.run(
        ["docker", "compose", "logs", "--tail", "100"],
        capture_output=True,
        text=True
    ).stdout

    # Should NOT contain secrets
    assert "claire_db_secret_2024" not in logs
    assert "claire_redis_secret_2024" not in logs
```

**Priorität**: 🟡 MITTEL (Best Practice)

---

### 6. ⚠️ PostgreSQL Edge-Cases (erweitert)

**Status**: ⚠️ Teilweise vorhanden (aber erweiterbar)

**Was zusätzlich fehlt**:
- Concurrent Writes (Race Conditions)
- Transaction Rollbacks
- Foreign Key Constraints
- JSONB Metadata Edge-Cases
- NULL Handling in ALL Tabellen (aktuell nur in DB-Writer getestet)

**Beispiel-Test**:
```python
# tests/local/test_postgres_edge_cases.py
@pytest.mark.local_only
def test_concurrent_portfolio_snapshot_writes():
    """
    Edge-Case-Test: 2 Writer schreiben gleichzeitig Portfolio Snapshots

    Validiert:
    - Keine Race-Condition
    - Beide Snapshots werden gespeichert
    - Timestamps korrekt
    """
    import threading

    def write_snapshot(snapshot_id):
        conn = psycopg2.connect(...)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO portfolio_snapshots (...) VALUES (...)",
            {"snapshot_id": snapshot_id}
        )
        conn.commit()

    # Start 2 Threads gleichzeitig
    t1 = threading.Thread(target=write_snapshot, args=(1,))
    t2 = threading.Thread(target=write_snapshot, args=(2,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Validate: Beide wurden gespeichert
    assert count_recent_snapshots() == 2
```

**Priorität**: 🟢 NIEDRIG (Bereits gute Basis vorhanden)

---

### 7. ⚠️ Paper-Trading Scenario Tests

**Status**: ❌ Nicht vorhanden

**CLAUDE.md** erwähnt:
> Paper-Trading + Scenario Orchestrator: N1 Paper-Trading Runner, Szenario-Engine

**Was fehlt**:
- Vollständiger 7-Tage-Simulationslauf
- Mit realistischen Event-Daten
- Statistik-Validierung (Sharpe Ratio, Drawdown, Win Rate)
- Verschiedene Market-Conditions (Trending, Ranging, Volatile)

**Beispiel-Test**:
```python
# tests/local/test_paper_trading_scenarios.py
@pytest.mark.local_only
@pytest.mark.slow  # Kann 5-10 Minuten dauern
def test_7_day_trending_market_scenario():
    """
    Paper-Trading-Test: 7 Tage Trending Market

    Simuliert:
    - 7 Tage Markt-Daten (Trending Up)
    - Signal Engine generiert Signals
    - Risk Manager validiert
    - Execution simuliert Trades

    Validiert:
    - Positive P&L (in Trending Market)
    - Max Drawdown < 5%
    - Win Rate > 50%
    """
    # 1. Load Scenario Data
    events = load_scenario("trending_up_7_days.json")

    # 2. Run Simulation
    run_paper_trading(events)

    # 3. Validate Statistics
    stats = get_trading_statistics()
    assert stats["total_pnl"] > 0
    assert stats["max_drawdown_pct"] < 5.0
    assert stats["win_rate"] > 0.5
```

**Priorität**: 🟡 MITTEL (Wichtig vor echtem Paper-Test)

---

## 📊 Prioritäten-Matrix

| Test-Kategorie | Priorität | Aufwand | Nutzen | Empfehlung |
|----------------|-----------|---------|--------|------------|
| **1. CLI-Tools Tests** | 🔴 HOCH | Niedrig (1-2h) | Hoch | ✅ SOFORT |
| **2. Chaos/Resilience** | 🔴 HOCH | Mittel (4-6h) | Sehr Hoch | ✅ DIESE WOCHE |
| **3. Event-Sourcing** | 🟡 MITTEL | Mittel (3-4h) | Mittel | ⏳ OPTIONAL |
| **4. Backup & Recovery** | 🟡 MITTEL | Niedrig (2-3h) | Hoch | ✅ DIESE WOCHE |
| **5. Security-Tests** | 🟡 MITTEL | Niedrig (1-2h) | Mittel | ⏳ OPTIONAL |
| **6. Postgres Edge-Cases** | 🟢 NIEDRIG | Niedrig (2h) | Niedrig | ⏳ OPTIONAL |
| **7. Paper-Trading Scenarios** | 🟡 MITTEL | Hoch (8-10h) | Sehr Hoch | ✅ VOR PAPER-TEST |

---

## 🎯 Empfohlene Implementierungs-Reihenfolge

### Sprint 1: Kritische Lücken (SOFORT - 2 Tage)
1. ✅ CLI-Tools Tests (`test_cli_tools.py`)
2. ✅ Chaos/Resilience Tests (`test_chaos_resilience.py`)
3. ✅ Backup & Recovery Tests (`test_backup_recovery.py`)

### Sprint 2: Nice-to-Have (OPTIONAL - 1-2 Tage)
4. Event-Sourcing Tests (`test_event_sourcing.py`)
5. Security-Tests (`test_security_basics.py`)
6. Postgres Edge-Cases erweitern (`test_postgres_edge_cases.py`)

### Sprint 3: Vor Paper-Test (VOR 7-TAGE-TEST)
7. Paper-Trading Scenarios (`test_paper_trading_scenarios.py`)

---

## 🔧 Implementierungs-Guidelines

### Test-Struktur (einheitlich):

```python
"""
<Test-Kategorie> - Claire de Binare
Lokaler-only Test: <Beschreibung>

WICHTIG: Dieser Test MUSS lokal mit Docker Compose ausgeführt werden!
    - Erfordert: <Dependencies>
    - Simuliert: <Szenarien>
    - Prüft: <Assertions>
    - NICHT in CI ausführen (zu <Grund>)

Ausführung:
    pytest -v -m local_only tests/local/test_<name>.py
"""

import pytest
# Imports...

@pytest.mark.local_only
@pytest.mark.slow  # Wenn >10s
def test_<descriptive_name>():
    """
    <Kategorie>-Test: <Was wird getestet>

    Validiert:
    - <Assertion 1>
    - <Assertion 2>
    - <Assertion 3>
    """
    print("\n🔥 Starting <test-name>...")

    # Arrange
    # ...

    # Act
    # ...

    # Assert
    # ...

    print("✅ <test-name> completed")
```

### Integration mit Makefile:

```makefile
# tests/local/ Tests
test-local-cli:
	pytest -v -m local_only tests/local/test_cli_tools.py

test-local-chaos:
	pytest -v -m local_only tests/local/test_chaos_resilience.py

test-local-backup:
	pytest -v -m local_only tests/local/test_backup_recovery.py

test-local-all:
	pytest -v -m local_only tests/local/
```

### pytest.ini Marker (bereits vorhanden):

```ini
markers =
    local_only: Explizit nur lokal ausführen (nicht in CI)
    slow: Tests mit >10s Laufzeit
    chaos: Chaos/Resilience Tests (destruktiv!)
```

---

## ✅ Acceptance Criteria

Ein lokaler-only Test ist **vollständig**, wenn:

1. ✅ **Funktioniert lokal** mit `docker compose up -d`
2. ✅ **Wird NICHT in CI ausgeführt** (Marker `@pytest.mark.local_only`)
3. ✅ **Klare Fehler-Messages** (nicht nur `assert False`)
4. ✅ **Dokumentiert** (Docstring erklärt Was/Warum/Wie)
5. ✅ **Robust** (kein Flaky-Verhalten, deterministisch)
6. ✅ **Im Makefile** (eigenes Target für schnelles Ausführen)

---

## 📚 Nächste Schritte

1. ✅ **Gap Analysis approved** (dieses Dokument)
2. 🔄 **Design-Phase**: Detaillierte Test-Specs für Top 3 Prioritäten
3. 🔄 **Implementierung**: Tests schreiben + validieren
4. 🔄 **Dokumentation**: LOCAL_E2E_TESTS.md erweitern
5. 🔄 **Validation**: Alle Tests lokal ausführen + CI bleibt grün

---

**Ende Gap Analysis**
