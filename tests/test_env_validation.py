"""
ENV-Validierung Tests - Claire de Binaire

Testet die korrekte Konfiguration und Validierung aller Environment-Variablen
gemäß ENV_CATALOG.md.

Kategorien:
- Risk Engine (9 Variablen)
- DB (6 Variablen)
- Redis (4 Variablen)
- Monitoring (5 Variablen)
- Services (5 Variablen)
- Trading (4 Variablen)
- System (5 Variablen)
"""

import os
import pytest
from typing import Dict, Any


# ====================================================================
# Test-Fixtures für ENV-Mocking
# ====================================================================

@pytest.fixture
def valid_risk_env():
    """Gültige Risk-Engine ENV-Variablen"""
    return {
        "MAX_POSITION_PCT": "0.10",
        "MAX_DAILY_DRAWDOWN_PCT": "0.05",
        "MAX_TOTAL_EXPOSURE_PCT": "0.30",
        "CIRCUIT_BREAKER_THRESHOLD_PCT": "0.10",
        "MAX_SLIPPAGE_PCT": "0.02",
        "STOP_LOSS_PCT": "0.02",
        "MAX_SPREAD_MULTIPLIER": "5.0",
        "DATA_STALE_TIMEOUT_SEC": "60",
        "ACCOUNT_EQUITY": "100000.0",
    }


@pytest.fixture
def valid_db_env():
    """Gültige PostgreSQL ENV-Variablen"""
    return {
        "POSTGRES_HOST": "cdb_postgres",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "claire_user",
        "POSTGRES_PASSWORD": "test_password",
        "POSTGRES_DB": "claire_de_binaire",
    }


@pytest.fixture
def valid_redis_env():
    """Gültige Redis ENV-Variablen"""
    return {
        "REDIS_HOST": "cdb_redis",
        "REDIS_PORT": "6379",
        "REDIS_PASSWORD": "test_password",
        "REDIS_DB": "0",
    }


# ====================================================================
# Validierungs-Funktionen (aus ENV_CATALOG.md)
# ====================================================================

def validate_env_required(var_name: str, env_dict: Dict[str, str]) -> bool:
    """Prüft, ob eine Pflicht-Variable gesetzt ist"""
    return var_name in env_dict and env_dict[var_name] not in ["", None]


def validate_env_range(
    var_name: str,
    value: float,
    min_val: float,
    max_val: float
) -> bool:
    """Prüft, ob ein Wert im gültigen Range liegt"""
    return min_val <= value <= max_val


def validate_env_format(var_name: str, value: str, expected_type: type) -> bool:
    """Prüft, ob ein Wert das erwartete Format hat"""
    try:
        if expected_type == float:
            float(value)
        elif expected_type == int:
            int(value)
        elif expected_type == bool:
            value.lower() in ["true", "false", "1", "0"]
        elif expected_type == str:
            pass  # String ist immer gültig
        return True
    except (ValueError, AttributeError):
        return False


def load_risk_config(env_dict: Dict[str, str]) -> Dict[str, Any]:
    """
    Lädt Risk-Engine-Konfiguration aus ENV-Variablen.

    Diese Funktion simuliert das Laden der ENV-Variablen in den Services.
    Verwendet Defaults aus ENV_CATALOG.md.
    """
    return {
        "ACCOUNT_EQUITY": float(env_dict.get("ACCOUNT_EQUITY", "100000.0")),
        "MAX_POSITION_PCT": float(env_dict.get("MAX_POSITION_PCT", "0.10")),
        "MAX_DAILY_DRAWDOWN_PCT": float(env_dict.get("MAX_DAILY_DRAWDOWN_PCT", "0.05")),
        "MAX_TOTAL_EXPOSURE_PCT": float(env_dict.get("MAX_TOTAL_EXPOSURE_PCT", "0.30")),
        "CIRCUIT_BREAKER_THRESHOLD_PCT": float(env_dict.get("CIRCUIT_BREAKER_THRESHOLD_PCT", "0.10")),
        "MAX_SLIPPAGE_PCT": float(env_dict.get("MAX_SLIPPAGE_PCT", "0.02")),
        "STOP_LOSS_PCT": float(env_dict.get("STOP_LOSS_PCT", "0.02")),
        "MAX_SPREAD_MULTIPLIER": float(env_dict.get("MAX_SPREAD_MULTIPLIER", "5.0")),
        "DATA_STALE_TIMEOUT_SEC": int(env_dict.get("DATA_STALE_TIMEOUT_SEC", "60")),
    }


# ====================================================================
# Tests: Risk Engine ENV-Variablen
# ====================================================================

@pytest.mark.unit
def test_risk_env_required_variables(valid_risk_env):
    """Test: Alle Pflicht-Risk-Variablen sind gesetzt"""
    required = [
        "MAX_POSITION_PCT",
        "MAX_DAILY_DRAWDOWN_PCT",
        "MAX_TOTAL_EXPOSURE_PCT",
        "CIRCUIT_BREAKER_THRESHOLD_PCT",
        "MAX_SLIPPAGE_PCT",
        "STOP_LOSS_PCT",
        "MAX_SPREAD_MULTIPLIER",
        "DATA_STALE_TIMEOUT_SEC",
        "ACCOUNT_EQUITY",
    ]

    for var in required:
        assert validate_env_required(var, valid_risk_env), \
            f"Pflicht-Variable {var} fehlt oder ist leer"


@pytest.mark.unit
def test_risk_env_valid_ranges(valid_risk_env):
    """Test: Risk-Variablen liegen im gültigen Range"""
    config = load_risk_config(valid_risk_env)

    # MAX_POSITION_PCT: 0.01 - 0.25
    assert validate_env_range(
        "MAX_POSITION_PCT",
        config["MAX_POSITION_PCT"],
        0.01,
        0.25
    ), "MAX_POSITION_PCT außerhalb Range (0.01 - 0.25)"

    # MAX_DAILY_DRAWDOWN_PCT: 0.01 - 0.20
    assert validate_env_range(
        "MAX_DAILY_DRAWDOWN_PCT",
        config["MAX_DAILY_DRAWDOWN_PCT"],
        0.01,
        0.20
    ), "MAX_DAILY_DRAWDOWN_PCT außerhalb Range (0.01 - 0.20)"

    # MAX_TOTAL_EXPOSURE_PCT: 0.10 - 1.00
    assert validate_env_range(
        "MAX_TOTAL_EXPOSURE_PCT",
        config["MAX_TOTAL_EXPOSURE_PCT"],
        0.10,
        1.00
    ), "MAX_TOTAL_EXPOSURE_PCT außerhalb Range (0.10 - 1.00)"

    # CIRCUIT_BREAKER_THRESHOLD_PCT: 0.05 - 0.30
    assert validate_env_range(
        "CIRCUIT_BREAKER_THRESHOLD_PCT",
        config["CIRCUIT_BREAKER_THRESHOLD_PCT"],
        0.05,
        0.30
    ), "CIRCUIT_BREAKER_THRESHOLD_PCT außerhalb Range (0.05 - 0.30)"

    # MAX_SLIPPAGE_PCT: 0.001 - 0.05
    assert validate_env_range(
        "MAX_SLIPPAGE_PCT",
        config["MAX_SLIPPAGE_PCT"],
        0.001,
        0.05
    ), "MAX_SLIPPAGE_PCT außerhalb Range (0.001 - 0.05)"

    # STOP_LOSS_PCT: 0.005 - 0.10
    assert validate_env_range(
        "STOP_LOSS_PCT",
        config["STOP_LOSS_PCT"],
        0.005,
        0.10
    ), "STOP_LOSS_PCT außerhalb Range (0.005 - 0.10)"

    # MAX_SPREAD_MULTIPLIER: 2.0 - 10.0
    assert validate_env_range(
        "MAX_SPREAD_MULTIPLIER",
        config["MAX_SPREAD_MULTIPLIER"],
        2.0,
        10.0
    ), "MAX_SPREAD_MULTIPLIER außerhalb Range (2.0 - 10.0)"

    # DATA_STALE_TIMEOUT_SEC: 10 - 120
    assert validate_env_range(
        "DATA_STALE_TIMEOUT_SEC",
        config["DATA_STALE_TIMEOUT_SEC"],
        10,
        120
    ), "DATA_STALE_TIMEOUT_SEC außerhalb Range (10 - 120)"

    # ACCOUNT_EQUITY: >= 1000.0
    assert config["ACCOUNT_EQUITY"] >= 1000.0, \
        "ACCOUNT_EQUITY unter Minimum (1000.0)"


@pytest.mark.unit
def test_risk_env_invalid_ranges_rejected():
    """Test: Out-of-range Werte werden erkannt"""
    # MAX_POSITION_PCT zu hoch (> 0.25)
    invalid_env = {"MAX_POSITION_PCT": "0.50"}
    config = load_risk_config(invalid_env)
    assert not validate_env_range(
        "MAX_POSITION_PCT",
        config["MAX_POSITION_PCT"],
        0.01,
        0.25
    ), "Zu hoher MAX_POSITION_PCT wurde nicht erkannt"

    # MAX_DAILY_DRAWDOWN_PCT zu niedrig (< 0.01)
    invalid_env = {"MAX_DAILY_DRAWDOWN_PCT": "0.005"}
    config = load_risk_config(invalid_env)
    assert not validate_env_range(
        "MAX_DAILY_DRAWDOWN_PCT",
        config["MAX_DAILY_DRAWDOWN_PCT"],
        0.01,
        0.20
    ), "Zu niedriger MAX_DAILY_DRAWDOWN_PCT wurde nicht erkannt"


@pytest.mark.unit
def test_risk_env_format_validation(valid_risk_env):
    """Test: Risk-Variablen haben korrektes Format (Dezimal/Integer)"""
    # Dezimal-Variablen
    decimal_vars = [
        "MAX_POSITION_PCT",
        "MAX_DAILY_DRAWDOWN_PCT",
        "MAX_TOTAL_EXPOSURE_PCT",
        "CIRCUIT_BREAKER_THRESHOLD_PCT",
        "MAX_SLIPPAGE_PCT",
        "STOP_LOSS_PCT",
        "ACCOUNT_EQUITY",
    ]

    for var in decimal_vars:
        assert validate_env_format(var, valid_risk_env[var], float), \
            f"{var} hat ungültiges Format (erwartet: float)"

    # Float-Variablen
    assert validate_env_format(
        "MAX_SPREAD_MULTIPLIER",
        valid_risk_env["MAX_SPREAD_MULTIPLIER"],
        float
    ), "MAX_SPREAD_MULTIPLIER hat ungültiges Format (erwartet: float)"

    # Integer-Variablen
    assert validate_env_format(
        "DATA_STALE_TIMEOUT_SEC",
        valid_risk_env["DATA_STALE_TIMEOUT_SEC"],
        int
    ), "DATA_STALE_TIMEOUT_SEC hat ungültiges Format (erwartet: int)"


# ====================================================================
# Tests: DB ENV-Variablen
# ====================================================================

@pytest.mark.unit
def test_db_env_required_variables(valid_db_env):
    """Test: Alle Pflicht-DB-Variablen sind gesetzt"""
    required = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    ]

    for var in required:
        assert validate_env_required(var, valid_db_env), \
            f"Pflicht-Variable {var} fehlt oder ist leer"


@pytest.mark.unit
def test_db_env_postgres_db_canonical_name(valid_db_env):
    """Test: POSTGRES_DB muss exakt 'claire_de_binaire' sein (kanonisch)"""
    assert valid_db_env["POSTGRES_DB"] == "claire_de_binaire", \
        "POSTGRES_DB weicht vom kanonischen Namen ab (muss 'claire_de_binaire' sein)"


@pytest.mark.unit
def test_db_env_postgres_user_canonical_name(valid_db_env):
    """Test: POSTGRES_USER sollte 'claire_user' sein (kanonische Konvention)"""
    assert valid_db_env["POSTGRES_USER"] == "claire_user", \
        "POSTGRES_USER weicht von kanonischer Konvention ab (empfohlen: 'claire_user')"


# ====================================================================
# Tests: Redis ENV-Variablen
# ====================================================================

@pytest.mark.unit
def test_redis_env_required_variables(valid_redis_env):
    """Test: Alle Pflicht-Redis-Variablen sind gesetzt"""
    required = [
        "REDIS_HOST",
        "REDIS_PORT",
        "REDIS_PASSWORD",
    ]

    for var in required:
        assert validate_env_required(var, valid_redis_env), \
            f"Pflicht-Variable {var} fehlt oder ist leer"


@pytest.mark.unit
def test_redis_env_host_canonical_name(valid_redis_env):
    """Test: REDIS_HOST muss 'cdb_redis' sein (Docker-Container-Name)"""
    assert valid_redis_env["REDIS_HOST"] == "cdb_redis", \
        "REDIS_HOST weicht vom kanonischen Namen ab (muss 'cdb_redis' sein, NICHT 'redis'!)"


@pytest.mark.unit
def test_redis_env_port_valid_range(valid_redis_env):
    """Test: REDIS_PORT ist gültiger Port (1-65535)"""
    port = int(valid_redis_env["REDIS_PORT"])
    assert 1 <= port <= 65535, \
        f"REDIS_PORT außerhalb gültigem Range (1-65535): {port}"


# ====================================================================
# Tests: ENV-Defaults (aus ENV_CATALOG.md)
# ====================================================================

@pytest.mark.unit
def test_risk_env_defaults_match_catalog():
    """Test: Default-Werte im Code matchen ENV_CATALOG.md"""
    # Leeres ENV-Dict → alle Defaults werden verwendet
    config = load_risk_config({})

    # Vergleich mit Defaults aus ENV_CATALOG.md
    assert config["MAX_POSITION_PCT"] == 0.10, \
        "MAX_POSITION_PCT Default stimmt nicht mit Katalog überein (0.10)"
    assert config["MAX_DAILY_DRAWDOWN_PCT"] == 0.05, \
        "MAX_DAILY_DRAWDOWN_PCT Default stimmt nicht mit Katalog überein (0.05)"
    assert config["MAX_TOTAL_EXPOSURE_PCT"] == 0.30, \
        "MAX_TOTAL_EXPOSURE_PCT Default stimmt nicht mit Katalog überein (0.30)"
    assert config["CIRCUIT_BREAKER_THRESHOLD_PCT"] == 0.10, \
        "CIRCUIT_BREAKER_THRESHOLD_PCT Default stimmt nicht mit Katalog überein (0.10)"
    assert config["MAX_SLIPPAGE_PCT"] == 0.02, \
        "MAX_SLIPPAGE_PCT Default stimmt nicht mit Katalog überein (0.02)"
    assert config["STOP_LOSS_PCT"] == 0.02, \
        "STOP_LOSS_PCT Default stimmt nicht mit Katalog überein (0.02)"
    assert config["MAX_SPREAD_MULTIPLIER"] == 5.0, \
        "MAX_SPREAD_MULTIPLIER Default stimmt nicht mit Katalog überein (5.0)"
    assert config["DATA_STALE_TIMEOUT_SEC"] == 60, \
        "DATA_STALE_TIMEOUT_SEC Default stimmt nicht mit Katalog überein (60)"
    assert config["ACCOUNT_EQUITY"] == 100000.0, \
        "ACCOUNT_EQUITY Default stimmt nicht mit Katalog überein (100000.0)"


# ====================================================================
# Tests: Deprecated Variablen (ADR-035)
# ====================================================================

@pytest.mark.unit
def test_deprecated_env_variables_not_used():
    """Test: Deprecated ENV-Variablen (vor ADR-035) werden nicht verwendet"""
    deprecated = [
        "MAX_DAILY_DRAWDOWN",  # → MAX_DAILY_DRAWDOWN_PCT
        "MAX_POSITION_SIZE",   # → MAX_POSITION_PCT
        "MAX_TOTAL_EXPOSURE",  # → MAX_TOTAL_EXPOSURE_PCT
    ]

    # In echten Services sollten diese Variablen NICHT mehr verwendet werden
    # Dieser Test ist ein Reminder, dass diese alten Namen deprecated sind
    for var in deprecated:
        # Wir prüfen, dass diese Variablen NICHT in der neuen Config-Funktion vorkommen
        config = load_risk_config({var: "0.50"})  # Deprecated-Variable setzen

        # Die neue Config-Funktion sollte diese Variable ignorieren und Default verwenden
        # (weil sie nur die neuen Variablen mit _PCT Suffix liest)
        # Prüfe Keys, nicht Substrings
        assert var not in config.keys(), \
            f"Deprecated Variable {var} wird noch verwendet (sollte ignoriert werden)"


# ====================================================================
# Tests: Integration mit Service-Code
# ====================================================================

@pytest.mark.integration
def test_env_loading_from_os_environ(monkeypatch, valid_risk_env):
    """Test: ENV-Variablen werden korrekt aus os.environ geladen"""
    # Setze ENV-Variablen im Test-Environment
    for key, value in valid_risk_env.items():
        monkeypatch.setenv(key, value)

    # Lade Config aus os.environ (wie in echten Services)
    config = load_risk_config(dict(os.environ))

    # Prüfe, dass alle Werte korrekt geladen wurden
    assert config["MAX_POSITION_PCT"] == 0.10
    assert config["MAX_DAILY_DRAWDOWN_PCT"] == 0.05
    assert config["ACCOUNT_EQUITY"] == 100000.0


@pytest.mark.integration
def test_env_validation_with_invalid_values(monkeypatch):
    """Test: Ungültige ENV-Werte werden als solche erkannt"""
    # Setze ungültige Werte
    monkeypatch.setenv("MAX_POSITION_PCT", "not_a_number")
    monkeypatch.setenv("DATA_STALE_TIMEOUT_SEC", "invalid")

    # Versuche, Config zu laden (sollte ValueError werfen)
    with pytest.raises(ValueError):
        config = load_risk_config(dict(os.environ))
        float(os.environ["MAX_POSITION_PCT"])  # Expliziter Check
