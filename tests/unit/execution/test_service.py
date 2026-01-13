"""
Unit-Tests für Execution Service.

Governance: CDB_AGENT_POLICY.md, CDB_PSM_POLICY.md

Note: Placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import pytest

from services.execution import config, service

# TODO: Import actual service when implementation is stable
# from services.execution.service import ExecutionService


@pytest.mark.unit
def test_health_endpoint_reports_ok() -> None:
    client = service.app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["service"] == config.SERVICE_NAME
    assert payload["status"] == "ok"


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_service_initialization(mock_redis, mock_postgres, test_config):
    """
    Test: Execution Service kann initialisiert werden.

    Prüft, dass der Service mit Mock-Dependencies korrekt erstellt wird.
    """
    # TODO: Implement when ExecutionService class is available
    # service = ExecutionService(redis_client=mock_redis, db_conn=mock_postgres, config=test_config)
    # assert service is not None
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_config_validation(test_config):
    """
    Test: Config wird korrekt validiert.

    Prüft, dass ungültige Configs abgelehnt werden.
    """
    # TODO: Implement config validation test
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_order_submission(mock_redis, order_factory):
    """
    Test: Order kann submitted werden.

    Prüft, dass Orders korrekt an die Exchange weitergeleitet werden.
    """
    # TODO: Implement order submission test
    pass
