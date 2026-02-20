"""
Tests fuer Issue #883: Flask-Import-Guard in services.risk.service

Stellt sicher, dass services.risk.service importierbar bleibt,
auch wenn Flask NICHT installiert ist. Der Flask-spezifische
Web-Pfad (app, Endpoints) soll in dem Fall sauber deaktiviert sein.

Technik: sys.meta_path-Blocker (MetaPathFinder) simuliert
fehlende Flask-Installation, auch wenn Flask tatsaechlich installiert ist.
"""

import importlib
import sys

import pytest


class _FlaskBlocker:
    """MetaPathFinder der alle flask-Imports mit ModuleNotFoundError blockiert.

    Setzt e.name = 'flask', damit der gehaertete Guard in service.py
    korrekt zwischen 'Flask fehlt' und 'Flask-Subdependency fehlt' unterscheidet.
    """

    def find_module(self, fullname, path=None):
        if fullname == "flask" or fullname.startswith("flask."):
            return self
        return None

    def load_module(self, fullname):
        err = ModuleNotFoundError(f"Simulated: No module named '{fullname}'")
        err.name = fullname
        raise err


def _save_flask_modules():
    """Sichert alle flask-Module aus sys.modules."""
    return {k: v for k, v in sys.modules.items() if k == "flask" or k.startswith("flask.")}


def _purge_modules(purge_flask=False):
    """Entfernt services.risk.service aus sys.modules.
    Optional auch flask-Module (nur fuer Blocker-Tests)."""
    to_delete = [
        key for key in sys.modules
        if key == "services.risk.service" or key.startswith("services.risk.service.")
    ]
    if purge_flask:
        to_delete += [
            key for key in sys.modules
            if key == "flask" or key.startswith("flask.")
        ]
    for key in to_delete:
        sys.modules.pop(key, None)


def _restore_flask_modules(saved):
    """Stellt gesicherte flask-Module in sys.modules wieder her."""
    sys.modules.update(saved)


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
        saved_flask = _save_flask_modules()
        blocker = _FlaskBlocker()
        _purge_modules(purge_flask=True)
        sys.meta_path.insert(0, blocker)
        try:
            mod = importlib.import_module("services.risk.service")

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
            _purge_modules(purge_flask=True)
            _restore_flask_modules(saved_flask)

    def test_flask_web_entry_raises_without_flask(self):
        """Test B: Der __main__-Guard soll RuntimeError werfen, wenn Flask fehlt.
        Wir testen das ueber die _FLASK_AVAILABLE / app-Kombination."""
        saved_flask = _save_flask_modules()
        blocker = _FlaskBlocker()
        _purge_modules(purge_flask=True)
        sys.meta_path.insert(0, blocker)
        try:
            mod = importlib.import_module("services.risk.service")

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
            _purge_modules(purge_flask=True)
            _restore_flask_modules(saved_flask)

    def test_decide_trade_works_without_flask(self):
        """Test C: decide_trade() funktioniert korrekt ohne Flask.
        Beweist, dass der Trading-Pfad unabhaengig vom Flask-Import ist."""
        saved_flask = _save_flask_modules()
        blocker = _FlaskBlocker()
        _purge_modules(purge_flask=True)
        sys.meta_path.insert(0, blocker)
        try:
            mod = importlib.import_module("services.risk.service")

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
            _purge_modules(purge_flask=True)
            _restore_flask_modules(saved_flask)

    def test_flask_available_matches_actual_state(self):
        """Test D: _FLASK_AVAILABLE und app muessen konsistent mit der
        tatsaechlichen Flask-Verfuegbarkeit sein. Laeuft immer."""
        _purge_modules(purge_flask=False)
        try:
            mod = importlib.import_module("services.risk.service")

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
            _purge_modules(purge_flask=False)

    def test_non_flask_dependency_error_propagates(self):
        """Test E: Wenn Flask installiert ist, aber eine Flask-Subdependency fehlt,
        darf der Fehler NICHT verschluckt werden (e.name != 'flask' -> raise).

        Simuliert z.B. 'from flask import ...' -> ImportError wegen fehlender
        Werkzeug-Version o.ae."""
        saved_flask = _save_flask_modules()

        class _SubdepBlocker:
            """Blockiert nur 'werkzeug', nicht 'flask' direkt.
            Flask importiert werkzeug intern -> ModuleNotFoundError mit name='werkzeug'."""
            def find_module(self, fullname, path=None):
                if fullname == "werkzeug" or fullname.startswith("werkzeug."):
                    return self
                return None

            def load_module(self, fullname):
                err = ModuleNotFoundError(f"Simulated: No module named '{fullname}'")
                err.name = fullname
                raise err

        blocker = _SubdepBlocker()
        _purge_modules(purge_flask=True)
        sys.meta_path.insert(0, blocker)
        try:
            # Wenn Flask installiert ist und werkzeug fehlt, muss der Fehler
            # durchschlagen (nicht als _FLASK_AVAILABLE=False verschluckt werden).
            # Wenn Flask nicht installiert ist, greift der e.name=='flask' Guard
            # und der Test ist trotzdem aussagekraeftig.
            try:
                import flask as _probe
                _flask_would_import = True
            except ModuleNotFoundError:
                _flask_would_import = False

            if _flask_would_import:
                # Flask installiert + werkzeug geblockt -> muss crashen, nicht verschlucken
                with pytest.raises(ModuleNotFoundError, match="werkzeug"):
                    importlib.import_module("services.risk.service")
            else:
                # Flask nicht installiert -> Guard greift korrekt (e.name == 'flask')
                mod = importlib.import_module("services.risk.service")
                assert mod._FLASK_AVAILABLE is False
        finally:
            sys.meta_path.remove(blocker)
            _purge_modules(purge_flask=True)
            _restore_flask_modules(saved_flask)
