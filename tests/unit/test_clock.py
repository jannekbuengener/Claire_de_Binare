"""Unit tests for core.utils.clock module."""
import pytest
from core.utils.clock import Clock


def test_clock_now_returns_float():
    """Test that Clock.now() returns a float timestamp."""
    result = Clock.now()
    assert isinstance(result, float)
    assert result > 0


def test_clock_deterministic_mode():
    """Test Clock in deterministic mode."""
    Clock.set_deterministic(True, start_time=1000.0)
    assert Clock.now() == 1000.0
    Clock.advance(10.0)
    assert Clock.now() == 1010.0
    Clock.set_deterministic(False)
