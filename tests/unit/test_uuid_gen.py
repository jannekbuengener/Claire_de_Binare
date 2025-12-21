"""Unit tests for core.utils.uuid_gen module."""

from core.utils.uuid_gen import generate_uuid, generate_uuid_hex


def test_generate_uuid_returns_string():
    """Test that generate_uuid returns a string."""
    result = generate_uuid()
    assert isinstance(result, str)
    assert len(result) == 36  # Standard UUID format


def test_generate_uuid_deterministic_name():
    """Test deterministic UUID generation from name."""
    uuid1 = generate_uuid(name="test-name")
    uuid2 = generate_uuid(name="test-name")
    assert uuid1 == uuid2


def test_generate_uuid_seeded_changes():
    """Test deterministic UUID generation with different seeds."""
    uuid1 = generate_uuid(seed=1)
    uuid2 = generate_uuid(seed=2)
    assert uuid1 != uuid2


def test_generate_uuid_hex_length():
    """Test deterministic UUID hex generation length."""
    short_hex = generate_uuid_hex(name="hex-test", length=12)
    assert len(short_hex) == 12
