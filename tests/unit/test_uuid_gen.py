"""Unit tests for core.utils.uuid_gen module."""

import pytest

from core.utils.uuid_gen import (
    generate_uuid,
    generate_uuid_hex,
    compute_policy_hash,
    compute_output_hash,
)


@pytest.mark.unit
def test_generate_uuid_returns_string():
    """Test that generate_uuid returns a string."""
    result = generate_uuid()
    assert isinstance(result, str)
    assert len(result) == 36  # Standard UUID format


@pytest.mark.unit
def test_generate_uuid_deterministic_name():
    """Test deterministic UUID generation from name."""
    uuid1 = generate_uuid(name="test-name")
    uuid2 = generate_uuid(name="test-name")
    assert uuid1 == uuid2


@pytest.mark.unit
def test_generate_uuid_seeded_changes():
    """Test deterministic UUID generation with different seeds."""
    uuid1 = generate_uuid(seed=1)
    uuid2 = generate_uuid(seed=2)
    assert uuid1 != uuid2


@pytest.mark.unit
def test_generate_uuid_hex_length():
    """Test deterministic UUID hex generation length."""
    short_hex = generate_uuid_hex(name="hex-test", length=12)
    assert len(short_hex) == 12


@pytest.mark.unit
def test_compute_policy_hash_deterministic():
    """Test that compute_policy_hash produces identical hashes for identical inputs."""
    thresholds = {
        "signal_pct_change_15m_min": 0.03,
        "signal_volume_15m_min": 0.165,
        "allowed_regimes": ["BULL", "NEUTRAL"],
        "blocked_regimes": ["BEAR"],
    }
    hash1 = compute_policy_hash(thresholds)
    hash2 = compute_policy_hash(thresholds)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest length


@pytest.mark.unit
def test_compute_policy_hash_different_inputs():
    """Test that compute_policy_hash produces different hashes for different inputs."""
    thresholds1 = {
        "signal_pct_change_15m_min": 0.03,
        "signal_volume_15m_min": 0.165,
    }
    thresholds2 = {
        "signal_pct_change_15m_min": 0.04,  # Different value
        "signal_volume_15m_min": 0.165,
    }
    hash1 = compute_policy_hash(thresholds1)
    hash2 = compute_policy_hash(thresholds2)
    assert hash1 != hash2


@pytest.mark.unit
def test_compute_policy_hash_handles_nan_inf():
    """Test that compute_policy_hash sanitizes NaN and Inf values."""
    thresholds = {
        "signal_pct_change_15m_min": float("nan"),
        "signal_volume_15m_min": float("inf"),
        "max_drawdown": float("-inf"),
    }
    # Should not raise exception and should produce deterministic hash
    hash1 = compute_policy_hash(thresholds)
    hash2 = compute_policy_hash(thresholds)
    assert hash1 == hash2
    assert len(hash1) == 64


@pytest.mark.unit
def test_compute_output_hash_deterministic():
    """Test that compute_output_hash produces identical hashes for identical inputs."""
    params = {
        "decision": "ALLOW",
        "reason_code": "RC_NORMAL",
        "decision_pk": "test_decision_pk",
        "decision_id": "test_decision_id",
        "contract_version": "decision_contract_v1",
        "input_hash": "a" * 64,
        "policy_hash": "b" * 64,
    }
    hash1 = compute_output_hash(**params)
    hash2 = compute_output_hash(**params)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest length


@pytest.mark.unit
def test_compute_output_hash_different_inputs():
    """Test that compute_output_hash produces different hashes for different inputs."""
    params1 = {
        "decision": "ALLOW",
        "reason_code": "RC_NORMAL",
        "decision_pk": "test_decision_pk",
        "decision_id": "test_decision_id",
        "contract_version": "decision_contract_v1",
        "input_hash": "a" * 64,
        "policy_hash": "b" * 64,
    }
    params2 = {
        **params1,
        "decision": "BLOCK",  # Different decision
    }
    hash1 = compute_output_hash(**params1)
    hash2 = compute_output_hash(**params2)
    assert hash1 != hash2


@pytest.mark.unit
def test_compute_output_hash_with_none_reason_code():
    """Test that compute_output_hash handles None reason_code correctly."""
    params = {
        "decision": "ALLOW",
        "reason_code": None,
        "decision_pk": "test_decision_pk",
        "decision_id": "test_decision_id",
        "contract_version": "decision_contract_v1",
        "input_hash": "a" * 64,
        "policy_hash": "b" * 64,
    }
    # Should not raise exception and should produce deterministic hash
    hash1 = compute_output_hash(**params)
    hash2 = compute_output_hash(**params)
    assert hash1 == hash2
    assert len(hash1) == 64
