"""
Tests für die Kill-Switch HTTP-Endpoints in services/risk/service.py.

Pflichtnachweis (#657): GET /kill-switch, POST /kill-switch/activate,
POST /kill-switch/deactivate arbeiten alle gegen dieselbe State-Datei,
die via CDB_KILL_SWITCH_STATE_FILE explizit gesetzt wird — kein implizites
Path.cwd()-Fallback.
"""

import json

import pytest

from services.risk import service
from core.safety.kill_switch import KillSwitch, KillSwitchReason


@pytest.fixture()
def state_file(tmp_path):
    """Liefert den Pfad zur temporären Kill-Switch State-Datei."""
    return str(tmp_path / "ks.state")


@pytest.fixture()
def client(state_file, monkeypatch):
    """Flask-Testclient mit isolierter State-Datei via Env-Override."""
    monkeypatch.setenv("CDB_KILL_SWITCH_STATE_FILE", state_file)
    return service.app.test_client()


@pytest.mark.unit
@pytest.mark.skipif(service.app is None, reason="Flask not installed")
class TestKillSwitchEndpoints:
    """Pflicht-Tests für operator-taugliche Kill-Switch HTTP-Endpoints."""

    def test_kill_switch_status_inactive(self, client, state_file):
        """GET /kill-switch liefert active=False wenn keine State-Datei existiert."""
        response = client.get("/kill-switch")
        assert response.status_code == 200
        data = response.get_json()
        assert data["active"] is False

    def test_kill_switch_status_active(self, client, state_file):
        """GET /kill-switch liefert active=True samt Metadaten nach Aktivierung."""
        ks = KillSwitch(state_file)
        ks.activate(KillSwitchReason.MANUAL, "Test-Halt", operator="test-op")

        response = client.get("/kill-switch")
        assert response.status_code == 200
        data = response.get_json()
        assert data["active"] is True
        assert data["reason"] == KillSwitchReason.MANUAL.value
        assert data["activated_at"] is not None

    def test_kill_switch_activate_ok(self, client, state_file):
        """POST /kill-switch/activate aktiviert den Kill-Switch und liefert vollständigen Status."""
        response = client.post(
            "/kill-switch/activate",
            data=json.dumps(
                {"operator": "janne", "reason": "manual", "message": "Emergency stop"}
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["active"] is True
        assert data["activated"] is True
        assert data["reason"] is not None
        assert data["activated_at"] is not None
        assert "message" in data

        # Gegencheck: State-Datei muss tatsächlich aktiv sein
        ks = KillSwitch(state_file)
        assert ks.is_active() is True

    def test_kill_switch_activate_missing_operator(self, client):
        """POST /kill-switch/activate ohne operator liefert 400."""
        response = client.post(
            "/kill-switch/activate",
            data=json.dumps({"reason": "manual", "message": "Test"}),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "operator" in response.get_json().get("error", "")

    def test_kill_switch_deactivate_ok(self, client, state_file):
        """POST /kill-switch/deactivate deaktiviert und liefert active=False."""
        # Erst aktivieren
        ks = KillSwitch(state_file)
        ks.activate(KillSwitchReason.MANUAL, "Setup for deactivate test", operator="test-op")

        response = client.post(
            "/kill-switch/deactivate",
            data=json.dumps(
                {"operator": "janne", "justification": "Test abgeschlossen"}
            ),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["deactivated"] is True
        assert data["active"] is False

        # Gegencheck: State-Datei muss tatsächlich inaktiv sein
        assert ks.is_active() is False

    def test_kill_switch_deactivate_missing_fields(self, client, state_file):
        """POST /kill-switch/deactivate ohne justification liefert 400."""
        ks = KillSwitch(state_file)
        ks.activate(KillSwitchReason.MANUAL, "Setup", operator="test-op")

        response = client.post(
            "/kill-switch/deactivate",
            data=json.dumps({"operator": "janne"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_activate_deactivate_same_state_file(self, client, state_file):
        """GET / activate / deactivate treffen garantiert dieselbe State-Datei.

        Kernnachweis für #657: Alle drei Endpoints nutzen CDB_KILL_SWITCH_STATE_FILE
        via resolve_kill_switch_state_file() — kein Path.cwd()-Seiteneffekt.
        """
        # Vor Aktivierung: inaktiv
        r = client.get("/kill-switch")
        assert r.get_json()["active"] is False

        # Aktivieren
        r = client.post(
            "/kill-switch/activate",
            data=json.dumps({"operator": "janne", "reason": "manual", "message": "halt"}),
            content_type="application/json",
        )
        assert r.status_code == 200

        # GET zeigt aktiv — dieselbe Datei
        r = client.get("/kill-switch")
        assert r.get_json()["active"] is True

        # Deaktivieren
        r = client.post(
            "/kill-switch/deactivate",
            data=json.dumps({"operator": "janne", "justification": "done"}),
            content_type="application/json",
        )
        assert r.status_code == 200
        assert r.get_json()["active"] is False

        # GET zeigt inaktiv — dieselbe Datei
        r = client.get("/kill-switch")
        assert r.get_json()["active"] is False
