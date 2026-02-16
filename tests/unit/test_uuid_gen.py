import pytest
"""Unit tests for core.utils.uuid_gen module."""

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
    """Test that compute_policy_hash produces deterministic hashes."""
    thresholds = {
        "signal_pct_change_15m_min": 0.03,
        "signal_volume_15m_min": 0.165,
        "allowed_regimes": ["STABLE", "BULLISH"],
        "blocked_regimes": ["BEARISH"],
    }
    hash1 = compute_policy_hash(thresholds)
    hash2 = compute_policy_hash(thresholds)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


@pytest.mark.unit
def test_compute_policy_hash_different_inputs():
    """Test that different threshold dicts produce different hashes."""
    thresholds1 = {
        "signal_pct_change_15m_min": 0.03,
        "allowed_regimes": ["STABLE"],
    }
    thresholds2 = {
        "signal_pct_change_15m_min": 0.05,
        "allowed_regimes": ["STABLE"],
    }
    hash1 = compute_policy_hash(thresholds1)
    hash2 = compute_policy_hash(thresholds2)
    assert hash1 != hash2


@pytest.mark.unit
def test_compute_output_hash_deterministic():
    """Test that compute_output_hash produces deterministic hashes."""
    hash1 = compute_output_hash(
        decision="ALLOW",
        reason_code="RC_OK",
        decision_pk="decision_pk_123",
        decision_id="dec-uuid-123",
        contract_version="decision_contract_v1",
        input_hash="a" * 64,
        policy_hash="b" * 64,
    )
    hash2 = compute_output_hash(
        decision="ALLOW",
        reason_code="RC_OK",
        decision_pk="decision_pk_123",
        decision_id="dec-uuid-123",
        contract_version="decision_contract_v1",
        input_hash="a" * 64,
        policy_hash="b" * 64,
    )
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


@pytest.mark.unit
def test_compute_output_hash_different_inputs():
    """Test that different outputs produce different hashes."""
    hash1 = compute_output_hash(
        decision="ALLOW",
        reason_code="RC_OK",
        decision_pk="decision_pk_123",
        decision_id="dec-uuid-123",
        contract_version="decision_contract_v1",
        input_hash="a" * 64,
        policy_hash="b" * 64,
    )
    hash2 = compute_output_hash(
        decision="BLOCK",  # Different decision
        reason_code="RC_OK",
        decision_pk="decision_pk_123",
        decision_id="dec-uuid-123",
        contract_version="decision_contract_v1",
        input_hash="a" * 64,
        policy_hash="b" * 64,
    )
    assert hash1 != hash2
