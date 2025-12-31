"""
Unit-Tests für Risk Manager Service.

Governance: CDB_AGENT_POLICY.md, CDB_RL_SAFETY_POLICY.md

Note: Placeholder tests marked with @pytest.mark.skip (Issue #308)
"""

import pytest


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_service_initialization(mock_redis, mock_postgres, test_config):
    """
    Test: Risk Manager kann initialisiert werden.
    """
    # TODO: Implement when RiskManager class is available
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_config_validation(test_config):
    """
    Test: Config wird korrekt validiert (Hard Limits).
    """
    # TODO: Implement config validation (max_exposure, max_drawdown, etc.)
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="Placeholder - needs implementation (Issue #308)")
def test_action_masking(signal_factory):
    """
    Test: Action Masking blockiert verbotene Aktionen.

    Governance: CDB_RL_SAFETY_POLICY.md (Deterministic Guardrails)
    """
    # TODO: Implement action masking test
    # signal = signal_factory(signal_type="buy")
    # masked_action = risk_manager.apply_action_mask(signal, current_state)
    # assert masked_action in allowed_actions
    pass
