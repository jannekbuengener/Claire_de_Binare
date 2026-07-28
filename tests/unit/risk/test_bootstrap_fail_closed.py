"""Risk bootstrap fail-closed tests for Issue #4152 (S1)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import psycopg2

from services.risk.config import RiskConfig
from services.risk.service import RiskManager
import services.risk.service as risk_service


@pytest.mark.unit
def test_bootstrap_db_error_does_not_continue_with_empty_state(mock_redis, mock_postgres):
    manager = RiskManager()
    with patch("services.risk.service.psycopg2.connect", side_effect=psycopg2.OperationalError("down")):
        with pytest.raises(RuntimeError, match="bootstrap"):
            manager.bootstrap_state_from_db()


@pytest.mark.unit
def test_bootstrap_unexpected_error_does_not_continue_with_empty_state(
    mock_redis, mock_postgres
):
    manager = RiskManager()
    with patch("services.risk.service.psycopg2.connect", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError, match="bootstrap|boom"):
            manager.bootstrap_state_from_db()


@pytest.mark.unit
def test_bootstrap_state_mismatch_raises_and_is_not_swallowed(mock_redis, mock_postgres):
    manager = RiskManager()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    # positions empty
    cursor.fetchall.return_value = []
    # orders show net open position
    cursor.fetchone.return_value = (1.0, 0.0)

    with patch("services.risk.service.psycopg2.connect", return_value=conn):
        with pytest.raises(RuntimeError, match="State mismatch"):
            manager.bootstrap_state_from_db()


@pytest.mark.unit
def test_bootstrap_clean_empty_positions_ok(mock_redis, mock_postgres):
    manager = RiskManager()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = (0.0, 0.0)

    with patch("services.risk.service.psycopg2.connect", return_value=conn):
        manager.bootstrap_state_from_db()
