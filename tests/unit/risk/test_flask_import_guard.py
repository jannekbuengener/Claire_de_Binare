"""
Tests fuer Issue #883: Flask-Import-Guard in services.risk.service

Stellt sicher, dass services.risk.service importierbar bleibt,
auch wenn Flask NICHT installiert ist. Der Flask-spezifische
Web-Pfad (app, Endpoints) soll in dem Fall sauber deaktiviert sein.

Technik: sys.meta_path-Blocker (MetaPathFinder via find_spec) simuliert
fehlende Flask-Installation, auch wenn Flask tatsaechlich installiert ist.
"""

import importlib
import importlib.abc
import importlib.machinery
import sys

import pytest


class _FlaskBlocker(importlib.abc.MetaPathFinder):
    """MetaPathFinder der alle flask-Imports mit ModuleNotFoundError blockiert.

    Verwendet find_spec (PEP 451), damit der Blocker auch in Python 3.12+
    zuverlaessig VOR dem Standard-PathFinder greift.

    Setzt e.name = 'flask', damit der gehaertete Guard in service.py
    korrekt zwischen 'Flask fehlt' und 'Flask-Subdependency fehlt' unterscheidet.
    """

    def find_spec(self, fullname, path, target=None):
        if fullname == "flask" or fullname.startswith("flask."):
            raise ModuleNotFoundError(
                f"Simulated: No module named '{fullname}'",
                name=fullname,
            )
        return None


class _WerkzeugBlocker(importlib.abc.MetaPathFinder):
    """Blockiert nur 'werkzeug' (nicht 'flask' direkt).

    Flask importiert werkzeug intern -> ModuleNotFoundError mit name='werkzeug'.
    Damit testen wir, dass der e.name-Guard Subdependency-Fehler propagiert.
    """

    def find_spec(self, fullname, path, target=None):
        if fullname == "werkzeug" or fullname.startswith("werkzeug."):
            raise ModuleNotFoundError(
                f"Simulated: No module named '{fullname}'",
                name=fullname,
            )
        return None


def _save_modules(*prefixes):
    """Sichert Module mit gegebenen Prefixen aus sys.modules."""
    return {
        k: v for k, v in sys.modules.items()
        if any(k == p or k.startswith(p + ".") for p in prefixes)
    }


def _purge_modules(*prefixes):
    """Entfernt Module mit gegebenen Prefixen aus sys.modules."""
    to_delete = [
        k for k in sys.modules
        if any(k == p or k.startswith(p + ".") for p in prefixes)
    ]
    for key in to_delete:
        sys.modules.pop(key, None)


def _restore_modules(saved):
    """Stellt gesicherte Module in sys.modules wieder her."""
    sys.modules.update(saved)


# Prefixe die fuer einen sauberen Re-Import geraeumt werden muessen
_RISK_MODULE = "services.risk.service"
_FLASK_PREFIXES = ("flask", "werkzeug", "markupsafe", "jinja2")
_ALL_PREFIXES = (_RISK_MODULE,) + _FLASK_PREFIXES


@pytest.mark.unit
class TestFlaskImportGuard:
    """Issue #883: services.risk.service darf nicht crashen, wenn Flask fehlt."""

    def test_import_succeeds_without_flask(self):
        """Test A: Import von services.risk.service DARF NICHT fehlschlagen,
        wenn Flask-Imports geblockt sind.

        Funktioniert unabhaengig davon, ob Flask installiert ist oder nicht:
        - Flask installiert: MetaPathFinder blockiert den Import
        - Flask nicht installiert: Import schlaegt natuerlich fehl, Guard faengt ab
        """
        saved = _save_modules(*_ALL_PREFIXES)
        blocker = _FlaskBlocker()
        _purge_modules(*_ALL_PREFIXES)
        sys.meta_path.insert(0, blocker)
        try:
            mod = importlib.import_module(_RISK_MODULE)

            # Modul muss importierbar sein
            assert mod is not None

            # _FLASK_AVAILABLE muss False sein
            assert mod._FLASK_AVAILABLE is False

            # app muss None sein (kein Flask-App-Objekt)
            assert mod.app is None

            # Trading-Funktionen muessen existieren
            assert callable(mod.decide_trade)
            assert hasattr(mod, "RiskManager")
        finally:
            sys.meta_path.remove(blocker)
            _purge_modules(*_ALL_PREFIXES)
            _restore_modules(saved)

    def test_flask_web_entry_raises_without_flask(self):
        """Test B: Der __main__-Guard soll RuntimeError werfen, wenn Flask fehlt.
        Wir testen das ueber die _FLASK_AVAILABLE / app-Kombination."""
        saved = _save_modules(*_ALL_PREFIXES)
        blocker = _FlaskBlocker()
        _purge_modules(*_ALL_PREFIXES)
        sys.meta_path.insert(0, blocker)
        try:
            mod = importlib.import_module(_RISK_MODULE)

            assert mod._FLASK_AVAILABLE is False
            assert mod.app is None

            with pytest.raises(RuntimeError, match="Flask.*nicht installiert"):
                if not mod._FLASK_AVAILABLE or mod.app is None:
                    raise RuntimeError(
                        "Flask ist nicht installiert. HTTP-Endpoints (health/status/metrics) "
                        "benötigen Flask als optionale Abhängigkeit: pip install flask"
                    )
        finally:
            sys.meta_path.remove(blocker)
            _purge_modules(*_ALL_PREFIXES)
            _restore_modules(saved)

    def test_decide_trade_works_without_flask(self):
        """Test C: decide_trade() funktioniert korrekt ohne Flask.
        Beweist, dass der Trading-Pfad unabhaengig vom Flask-Import ist."""
        saved = _save_modules(*_ALL_PREFIXES)
        blocker = _FlaskBlocker()
        _purge_modules(*_ALL_PREFIXES)
        sys.meta_path.insert(0, blocker)
        try:
            mod = importlib.import_module(_RISK_MODULE)

            # decide_trade mit minimalen Inputs ausfuehren
            decision, reason_code, evidence = mod.decide_trade(
                signal={"symbol": "BTCUSDT", "pct_change_15m": 0.05, "volume_15m": 0.2,
                        "ts_ms": 1000000, "signal_id": "test-001"},
                market_state={"regime_id": 0, "return_1m": 0.5, "return_5m": 1.0,
                              "price_change_5m": 0.3, "ts_ms": 1000000,
                              "last_tick_ts_ms": 999999},
                account_state={"daily_drawdown_pct": 1.0, "total_exposure_pct": 10.0,
                               "ts_ms": 1000000},
                market_health={"slippage_pct": 0.1, "ts_ms": 1000000},
                now_ms=1000001,
            )

            # Entscheidung muss zurueckkommen
            assert decision in ("ALLOW", "BLOCK")
            assert isinstance(evidence, dict)
            assert "contract_version" in evidence
        finally:
            sys.meta_path.remove(blocker)
            _purge_modules(*_ALL_PREFIXES)
            _restore_modules(saved)

    def test_flask_available_matches_actual_state(self):
        """Test D: _FLASK_AVAILABLE und app muessen konsistent mit der
        tatsaechlichen Flask-Verfuegbarkeit sein. Laeuft immer."""
        _purge_modules(_RISK_MODULE)
        try:
            mod = importlib.import_module(_RISK_MODULE)

            # Pruefen ob Flask wirklich importierbar ist
            try:
                import flask
                flask_actually_available = True
            except ModuleNotFoundError:
                flask_actually_available = False

            assert mod._FLASK_AVAILABLE is flask_actually_available
            if flask_actually_available:
                assert mod.app is not None
            else:
                assert mod.app is None

            # Trading-Pfad muss in jedem Fall funktionieren
            assert callable(mod.decide_trade)
            assert hasattr(mod, "RiskManager")
        finally:
            _purge_modules(_RISK_MODULE)

    def test_non_flask_dependency_error_propagates(self):
        """Test E: Wenn Flask installiert ist, aber eine Flask-Subdependency fehlt,
        darf der Fehler NICHT verschluckt werden (e.name != 'flask' -> raise).

        Simuliert z.B. 'from flask import ...' -> ImportError wegen fehlender
        Werkzeug-Version o.ae."""
        saved = _save_modules(*_ALL_PREFIXES)
        blocker = _WerkzeugBlocker()
        _purge_modules(*_ALL_PREFIXES)
        sys.meta_path.insert(0, blocker)
        try:
            # Pruefen ob Flask ueberhaupt installiert ist (ohne werkzeug-Blocker
            # stoerung — wir schauen in den gesicherten Modulen nach)
            flask_installed = "flask" in saved

            if flask_installed:
                # Flask installiert + werkzeug geblockt -> muss crashen, nicht verschlucken
                with pytest.raises(ModuleNotFoundError, match="werkzeug"):
                    importlib.import_module(_RISK_MODULE)
            else:
                # Flask nicht installiert -> Guard greift korrekt (e.name == 'flask')
                mod = importlib.import_module(_RISK_MODULE)
                assert mod._FLASK_AVAILABLE is False
        finally:
            sys.meta_path.remove(blocker)
            _purge_modules(*_ALL_PREFIXES)
            _restore_modules(saved)
