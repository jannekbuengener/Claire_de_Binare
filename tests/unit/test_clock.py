import pytest
"""Unit tests for core.utils.clock module."""

import re
from datetime import datetime
from pathlib import Path

from core.utils.clock import Clock, FixedClock, SystemClock, set_default_clock, utcnow


@pytest.mark.unit
def test_clock_now_returns_float():
    """Test that Clock.now() returns a float timestamp."""
    result = Clock.now()
    assert isinstance(result, float)
    assert result > 0


@pytest.mark.unit
def test_clock_deterministic_mode():
    """Test Clock in deterministic mode."""
    Clock.set_deterministic(True, start_time=1000.0)
    assert Clock.now() == 1000.0
    Clock.advance(10.0)
    assert Clock.now() == 1010.0
    Clock.set_deterministic(False)


@pytest.mark.unit
def test_clock_injection_fixed():
    """Test injected fixed clock for deterministic timestamps."""
    fixed_time = datetime(2020, 1, 1, 0, 0, 0)
    set_default_clock(FixedClock(fixed_time))
    try:
        assert utcnow() == fixed_time
    finally:
        set_default_clock(SystemClock())


@pytest.mark.unit
def test_guardrails_no_forbidden_calls():
    """Ensure forbidden calls stay confined to allowed utility modules."""
    root = Path(__file__).resolve().parents[2]
    allowed = {
        "core/utils/clock.py",
        "core/utils/seed.py",
        "core/utils/uuid_gen.py",
    }
    patterns = {
        "datetime.now": re.compile(r"datetime\.now\("),
        "datetime.utcnow": re.compile(r"datetime\.utcnow\("),
        "uuid.uuid4": re.compile(r"uuid\.uuid4\("),
        "random.": re.compile(r"\brandom\."),
    }
    violations = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        if not (
            rel.startswith("core/")
            or rel.startswith("services/")
            or rel.startswith("tools/")
        ):
            continue
        # Exclude experimental tools from strict guardrails
        if rel.startswith("tools/experiments/"):
            continue
        if rel in allowed:
            continue
        content = path.read_text(encoding="utf-8")
        for label, pattern in patterns.items():
            if pattern.search(content):
                violations.append(f"{rel}:{label}")
    assert not violations, "Forbidden calls detected:\\n" + "\\n".join(sorted(violations))
