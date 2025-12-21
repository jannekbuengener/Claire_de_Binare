"""Unit tests for core.utils.seed module."""

from core.utils.seed import Seed


def test_seed_set_and_get():
    """Test setting and getting random seed."""
    Seed.set(12345)
    assert Seed.get() == 12345


def test_seed_default_none():
    """Test that seed is None by default."""
    Seed.set(None)
    assert Seed.get() is None


def test_seed_deterministic_float():
    """Test deterministic random float with same seed."""
    Seed.set(123)
    first = Seed.random_float()
    Seed.set(123)
    second = Seed.random_float()
    assert first == second


def test_seed_deterministic_uniform():
    """Test deterministic random uniform output with same seed."""
    Seed.set(456)
    first = Seed.random_uniform(0.1, 1.5)
    Seed.set(456)
    second = Seed.random_uniform(0.1, 1.5)
    assert first == second
