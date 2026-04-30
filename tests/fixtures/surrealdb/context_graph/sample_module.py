"""Sample Python module fixture for Wave 9 context graph tests."""

from __future__ import annotations

import os
import json
from core.utils.clock import utcnow
from services.risk.models import RiskModel

CONSTANT = 42


def top_level_function(x: int, y: int) -> int:
    return x + y


async def async_top_level(name: str) -> str:
    return f"hello {name}"


class SampleClass:
    """A simple class with a couple of methods."""

    def regular_method(self) -> None:
        pass

    async def async_method(self, value: int) -> int:
        return value * 2

    @staticmethod
    def static_method() -> bool:
        return True


class TestSampleClass:
    def test_regular_method(self) -> None:
        obj = SampleClass()
        assert obj.regular_method() is None

    def test_static_method(self) -> None:
        assert SampleClass.static_method() is True


def test_top_level_function() -> None:
    assert top_level_function(1, 2) == 3
