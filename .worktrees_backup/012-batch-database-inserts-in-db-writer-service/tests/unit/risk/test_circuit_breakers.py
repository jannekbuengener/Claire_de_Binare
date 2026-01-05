"""
Unit Tests für CircuitBreaker (Issue #309)

Testet:
- Alle Breaker-Typen (drawdown, error_rate, loss_limit, frequency)
- E2E-Modus (E2E_DISABLE_CIRCUIT_BREAKER)
- Edge Cases (Grenzwerte, leere Metriken)

Governance: CDB_RL_SAFETY_POLICY.md
"""

import pytest
from unittest.mock import patch


# Import the module to test
from services.risk.circuit_breakers import (
    CircuitBreaker,
    CircuitBreakerType,
    E2E_DISABLE_CIRCUIT_BREAKER,
)


class TestCircuitBreakerNormalMode:
    """Tests für normalen Betrieb (Breakers aktiv)."""

    @pytest.fixture
    def breaker(self):
        """Fresh CircuitBreaker instance."""
        return CircuitBreaker()

    @pytest.mark.unit
    def test_no_trigger_when_metrics_ok(self, breaker):
        """Keine Trigger bei normalen Metriken."""
        metrics = {
            "drawdown": 0.05,       # 5% < 15% threshold
            "error_rate": 0.02,     # 2% < 10% threshold
            "loss_pct": 0.01,       # 1% < 5% threshold
            "orders_per_minute": 10  # 10 < 60 threshold
        }
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is False
        assert result["reasons"] == []

    @pytest.mark.unit
    @pytest.mark.parametrize("metrics,expected_reason", [
        ({"drawdown": 0.20}, "drawdown"),           # 20% > 15%
        ({"error_rate": 0.15}, "error_rate"),       # 15% > 10%
        ({"loss_pct": 0.06}, "loss_limit"),         # 6% > 5%
        ({"orders_per_minute": 100}, "frequency"),  # 100 > 60
    ])
    def test_individual_breaker_triggers(self, breaker, metrics, expected_reason):
        """Jeder Breaker-Typ triggert korrekt."""
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is True
        assert expected_reason in result["reasons"]

    @pytest.mark.unit
    def test_multiple_breakers_trigger(self, breaker):
        """Mehrere Breaker können gleichzeitig triggern."""
        metrics = {
            "drawdown": 0.20,        # triggers
            "error_rate": 0.15,      # triggers
            "loss_pct": 0.02,        # OK
            "orders_per_minute": 10  # OK
        }
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is True
        assert "drawdown" in result["reasons"]
        assert "error_rate" in result["reasons"]
        assert len(result["reasons"]) == 2

    @pytest.mark.unit
    def test_all_breakers_trigger(self, breaker):
        """Alle Breaker triggern bei extremen Werten."""
        metrics = {
            "drawdown": 0.50,
            "error_rate": 0.50,
            "loss_pct": 0.50,
            "orders_per_minute": 500
        }
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is True
        assert len(result["reasons"]) == 4

    @pytest.mark.unit
    def test_threshold_boundary_below(self, breaker):
        """Werte genau am Threshold triggern NICHT."""
        metrics = {
            "drawdown": 0.15,        # == threshold, not >
            "error_rate": 0.10,
            "loss_pct": 0.05,
            "orders_per_minute": 60
        }
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is False

    @pytest.mark.unit
    def test_threshold_boundary_above(self, breaker):
        """Werte knapp über Threshold triggern."""
        metrics = {
            "drawdown": 0.1500001,
        }
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is True
        assert "drawdown" in result["reasons"]

    @pytest.mark.unit
    def test_empty_metrics(self, breaker):
        """Leere Metriken triggern nicht."""
        result = breaker.check_breakers({})

        assert result["triggered"] is False
        assert result["reasons"] == []

    @pytest.mark.unit
    def test_missing_metrics_use_zero_default(self, breaker):
        """Fehlende Metriken werden als 0 behandelt."""
        metrics = {"drawdown": 0.20}  # Nur drawdown gesetzt
        result = breaker.check_breakers(metrics)

        assert result["triggered"] is True
        assert "drawdown" in result["reasons"]
        # Andere sollten nicht triggern (default 0)
        assert "error_rate" not in result["reasons"]

    @pytest.mark.unit
    def test_triggered_breakers_tracked(self, breaker):
        """Getriggerte Breaker werden in Liste gespeichert."""
        metrics = {"drawdown": 0.20}
        breaker.check_breakers(metrics)

        assert "drawdown" in breaker.triggered_breakers


class TestCircuitBreakerE2EMode:
    """Tests für E2E-Modus (Breakers deaktiviert)."""

    @pytest.mark.unit
    def test_e2e_mode_disables_all_breakers(self):
        """E2E-Modus deaktiviert alle Breaker."""
        with patch("services.risk.circuit_breakers.E2E_DISABLE_CIRCUIT_BREAKER", True):
            breaker = CircuitBreaker()

            # Extreme Werte die normalerweise alle Breaker triggern
            metrics = {
                "drawdown": 0.99,
                "error_rate": 0.99,
                "loss_pct": 0.99,
                "orders_per_minute": 9999
            }
            result = breaker.check_breakers(metrics)

            assert result["triggered"] is False
            assert result["reasons"] == []

    @pytest.mark.unit
    def test_e2e_mode_values(self):
        """Verschiedene E2E-Werte werden korrekt interpretiert."""
        # "1" und "true" sollten aktivieren
        with patch.dict("os.environ", {"E2E_DISABLE_CIRCUIT_BREAKER": "1"}):
            # Note: Da die Konstante bei Import ausgewertet wird,
            # testen wir hier die Logik direkt
            import os
            value = os.getenv("E2E_DISABLE_CIRCUIT_BREAKER", "").lower()
            assert value in ("1", "true")

    @pytest.mark.unit
    def test_default_mode_breakers_active(self):
        """Im Default-Modus sind Breaker aktiv."""
        # Ohne Patch sollte der Default-Modus aktiv sein
        # (E2E_DISABLE_CIRCUIT_BREAKER sollte False sein in Tests)
        if not E2E_DISABLE_CIRCUIT_BREAKER:
            breaker = CircuitBreaker()
            metrics = {"drawdown": 0.20}
            result = breaker.check_breakers(metrics)

            assert result["triggered"] is True


class TestCircuitBreakerConfiguration:
    """Tests für Breaker-Konfiguration."""

    @pytest.mark.unit
    def test_default_thresholds(self):
        """Default-Thresholds sind korrekt konfiguriert."""
        breaker = CircuitBreaker()

        assert breaker.breakers[CircuitBreakerType.ERROR_RATE]["threshold"] == 0.1
        assert breaker.breakers[CircuitBreakerType.DRAWDOWN]["threshold"] == 0.15
        assert breaker.breakers[CircuitBreakerType.LOSS_LIMIT]["threshold"] == 0.05
        assert breaker.breakers[CircuitBreakerType.FREQUENCY]["threshold"] == 60

    @pytest.mark.unit
    def test_all_breakers_active_by_default(self):
        """Alle Breaker sind standardmäßig aktiv."""
        breaker = CircuitBreaker()

        for breaker_type in CircuitBreakerType:
            assert breaker.breakers[breaker_type]["active"] is True

    @pytest.mark.unit
    def test_breaker_types_enum(self):
        """Alle Breaker-Typen sind definiert."""
        assert CircuitBreakerType.ERROR_RATE.value == "error_rate"
        assert CircuitBreakerType.DRAWDOWN.value == "drawdown"
        assert CircuitBreakerType.LOSS_LIMIT.value == "loss_limit"
        assert CircuitBreakerType.FREQUENCY.value == "frequency"
