import pytest

"""Unit tests for core.utils.uuid_gen module."""

from core.utils.uuid_gen import (
    DeterministicUUIDGenerator,
    format_runtime_signal_id,
    generate_runtime_id_hex,
    generate_runtime_signal_id_hex,
    generate_uuid,
    generate_uuid_hex,
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
def test_runtime_signal_ids_unique_across_simulated_restarts():
    """Deterministic counter restarts collide; runtime UUID4 ids must not."""
    gen_restart_a = DeterministicUUIDGenerator(seed=0)
    gen_restart_b = DeterministicUUIDGenerator(seed=0)
    assert str(gen_restart_a.generate()) == str(gen_restart_b.generate())

    restart_ids = {format_runtime_signal_id(length=32) for _ in range(32)}
    assert len(restart_ids) == 32


@pytest.mark.unit
def test_runtime_signal_id_hex_is_uuid4_fragment():
    runtime_hex = generate_runtime_signal_id_hex(length=32)
    assert len(runtime_hex) == 32
    assert runtime_hex.isalnum()


@pytest.mark.unit
def test_generate_runtime_id_hex_length_and_uniqueness():
    """General collision-safe runtime helper for non-signal ids (e.g. adr-*)."""
    fragment = generate_runtime_id_hex(length=16)
    assert len(fragment) == 16
    assert fragment.isalnum()
    samples = {generate_runtime_id_hex(16) for _ in range(32)}
    assert len(samples) == 32
    with pytest.raises(ValueError):
        generate_runtime_id_hex(length=0)
    with pytest.raises(ValueError):
        generate_runtime_id_hex(length=33)
