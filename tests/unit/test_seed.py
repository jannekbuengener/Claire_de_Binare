"""Unit tests for core.utils.seed module."""
import pytest
from core.utils.seed import Seed


def test_seed_set_and_get():
    """Test setting and getting random seed."""
    Seed.set(12345)
    assert Seed.get() == 12345


def test_seed_default_none():
    """Test that seed is None by default."""
    Seed.set(None)
    assert Seed.get() is None
