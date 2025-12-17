"""Unit tests for core.utils.uuid_gen module."""

from core.utils.uuid_gen import generate_uuid


def test_generate_uuid_returns_string():
    """Test that generate_uuid returns a string."""
    result = generate_uuid()
    assert isinstance(result, str)
    assert len(result) == 36  # Standard UUID format


def test_generate_uuid_deterministic():
    """Test deterministic UUID generation."""
    uuid1 = generate_uuid(deterministic=True, seed=42)
    uuid2 = generate_uuid(deterministic=True, seed=42)
    assert uuid1 == uuid2


def test_generate_uuid_random():
    """Test random UUID generation."""
    uuid1 = generate_uuid(deterministic=False)
    uuid2 = generate_uuid(deterministic=False)
    assert uuid1 != uuid2
